#!/usr/bin/env python3
"""
PS4/PS5 Fake Signed ELF (FSELF) Generator
Ported to Python 3 for PS5 Homebrew app0 deployment.
Original research & implementation by flatz.
"""

import sys
import os
import struct
import hashlib
import hmac
import argparse
import re
import string
import traceback

def int_with_base_type(val):
    return int(val, 0)

def try_parse_int(x, base=0):
    try:
        return int(x, base) if isinstance(x, str) else int(x)
    except:
        return None

def align_up(x, alignment):
    return (x + (alignment - 1)) & ~(alignment - 1)

def align_down(x, alignment):
    return x & ~(alignment - 1)

def ilog2(x):
    if x <= 0:
        raise ValueError('math domain error')
    return len(bin(x)) - 3

def check_file_magic(f, expected_magic):
    old_offset = f.tell()
    try:
        magic = f.read(len(expected_magic))
    except:
        return False
    finally:
        f.seek(old_offset)
    return magic == expected_magic

def sha256(data):
    return hashlib.sha256(data).digest()

class ElfError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class ElfEHdr(object):
    FMT = '<4s5B6xB'
    EX_FMT = '<2HI3QI6H'

    MAGIC = b'\x7FELF'
    CLASS64 = 0x2
    DATA2LSB = 0x1
    EM_X86_64 = 0x3E
    EV_CURRENT = 0x1

    ET_EXEC = 0x2
    ET_DYN = 0x3
    ET_SCE_EXEC = 0xFE00
    ET_SCE_EXEC_ASLR = 0xFE10
    ET_SCE_DYNAMIC = 0xFE18

    def __init__(self):
        self.magic = None
        self.machine_class = None
        self.data_encoding = None
        self.version = None
        self.os_abi = None
        self.abi_version = None
        self.nident_size = None
        self.type = None
        self.machine = None
        self.version_ex = None
        self.entry = None
        self.phoff = None
        self.shoff = None
        self.flags = None
        self.ehsize = None
        self.phentsize = None
        self.phnum = None
        self.shentsize = None
        self.shnum = None
        self.shstridx = None

    def load(self, f):
        if not check_file_magic(f, ElfEHdr.MAGIC):
            raise ElfError('Invalid ELF magic.')

        self.magic, self.machine_class, self.data_encoding, self.version, self.os_abi, self.abi_version, self.nident_size = struct.unpack(ElfEHdr.FMT, f.read(struct.calcsize(ElfEHdr.FMT)))
        if self.machine_class != ElfEHdr.CLASS64 or self.data_encoding != ElfEHdr.DATA2LSB:
            raise ElfError('Unsupported class or data encoding.')
        self.type, self.machine, self.version_ex, self.entry, self.phoff, self.shoff, self.flags, self.ehsize, self.phentsize, self.phnum, self.shentsize, self.shnum, self.shstridx = struct.unpack(ElfEHdr.EX_FMT, f.read(struct.calcsize(ElfEHdr.EX_FMT)))
        if self.machine != ElfEHdr.EM_X86_64 or self.version != ElfEHdr.EV_CURRENT:
            raise ElfError('Unsupported machine type or version.')
        if self.phentsize != struct.calcsize(ElfPHdr.FMT) or (self.shentsize > 0 and self.shentsize != struct.calcsize(ElfSHdr.FMT)):
            raise ElfError('Unsupported header entry size.')
        if self.type not in [ElfEHdr.ET_EXEC, ElfEHdr.ET_DYN, ElfEHdr.ET_SCE_EXEC, ElfEHdr.ET_SCE_EXEC_ASLR, ElfEHdr.ET_SCE_DYNAMIC]:
            raise ElfError('Unsupported ELF type.')

    def save(self, f):
        f.write(struct.pack(ElfEHdr.FMT, self.magic, self.machine_class, self.data_encoding, self.version, self.os_abi, self.abi_version, self.nident_size))
        f.write(struct.pack(ElfEHdr.EX_FMT, self.type, self.machine, self.version_ex, self.entry, self.phoff, self.shoff, self.flags, self.ehsize, self.phentsize, self.phnum, self.shentsize, self.shnum, self.shstridx))

    def has_segments(self):
        return self.phentsize > 0 and self.phnum > 0

    def has_sections(self):
        return self.shentsize > 0 and self.shnum > 0

class ElfPHdr(object):
    FMT = '<2I6Q'

    PT_LOAD = 0x1
    PT_DYNAMIC = 0x2
    PT_INTERP = 0x3
    PT_TLS = 0x7
    PT_GNU_EH_FRAME = 0x6474E550
    PT_GNU_STACK = 0x6474E551
    PT_SCE_RELA = 0x60000000
    PT_SCE_DYNLIBDATA = 0x61000000
    PT_SCE_PROCPARAM = 0x61000001
    PT_SCE_MODULE_PARAM = 0x61000002
    PT_SCE_RELRO = 0x61000010
    PT_SCE_COMMENT = 0x6FFFFF00
    PT_SCE_VERSION = 0x6FFFFF01

    PF_EXEC = 0x1
    PF_WRITE = 0x2
    PF_READ = 0x4

    def __init__(self, idx):
        self.idx = idx
        self.type = None
        self.flags = None
        self.offset = None
        self.vaddr = None
        self.paddr = None
        self.filesz = None
        self.memsz = None
        self.align = None

    def load(self, f):
        self.type, self.flags, self.offset, self.vaddr, self.paddr, self.filesz, self.memsz, self.align = struct.unpack(ElfPHdr.FMT, f.read(struct.calcsize(ElfPHdr.FMT)))

    def save(self, f):
        f.write(struct.pack(ElfPHdr.FMT, self.type, self.flags, self.offset, self.vaddr, self.paddr, self.filesz, self.memsz, self.align))

class ElfSHdr(object):
    FMT = '<2I4Q2I2Q'

    def __init__(self, idx):
        self.idx = idx
        self.name = None
        self.type = None
        self.flags = None
        self.addr = None
        self.offset = None
        self.size = None
        self.link = None
        self.info = None
        self.align = None
        self.entsize = None

    def load(self, f):
        self.name, self.type, self.flags, self.addr, self.offset, self.size, self.link, self.info, self.align, self.entsize = struct.unpack(ElfSHdr.FMT, f.read(struct.calcsize(ElfSHdr.FMT)))

    def save(self, f):
        f.write(struct.pack(ElfSHdr.FMT, self.name, self.type, self.flags, self.addr, self.offset, self.size, self.link, self.info, self.align, self.entsize))

class ElfFile(object):
    def __init__(self, ignore_shdrs=False):
        self.ignore_shdrs = ignore_shdrs
        self.ehdr = ElfEHdr()
        self.phdrs = []
        self.shdrs = []
        self.segments = []
        self.sections = []
        self.digest = None

    def load(self, f):
        start_offset = f.tell()
        self.ehdr.load(f)

        if self.ehdr.has_segments():
            for i in range(self.ehdr.phnum):
                f.seek(start_offset + self.ehdr.phoff + i * self.ehdr.phentsize)
                phdr = ElfPHdr(i)
                phdr.load(f)
                self.phdrs.append(phdr)
                if phdr.filesz > 0:
                    f.seek(start_offset + phdr.offset)
                    data = f.read(phdr.filesz)
                else:
                    data = b''
                self.segments.append(data)

        if not self.ignore_shdrs and self.ehdr.has_sections():
            for i in range(self.ehdr.shnum):
                f.seek(start_offset + self.ehdr.shoff + i * self.ehdr.shentsize)
                shdr = ElfSHdr(i)
                shdr.load(f)
                self.shdrs.append(shdr)
                if shdr.size > 0:
                    f.seek(start_offset + shdr.offset)
                    data = f.read(shdr.size)
                else:
                    data = b''
                self.sections.append(data)

        f.seek(start_offset)
        self.digest = sha256(f.read())

    def save(self, f, no_sections=False):
        start_offset = f.tell()
        self.ehdr.save(f)

        if self.ehdr.has_segments():
            for i in range(self.ehdr.phnum):
                f.seek(start_offset + self.ehdr.phoff + i * self.ehdr.phentsize)
                phdr = self.phdrs[i]
                phdr.save(f)

DIGEST_SIZE = 0x20
SIGNATURE_SIZE = 0x100
BLOCK_SIZE = 0x4000
DEFAULT_BLOCK_SIZE = 0x1000

SELF_CONTROL_BLOCK_TYPE_NPDRM = 0x3
SELF_NPDRM_CONTROL_BLOCK_CONTENT_ID_SIZE = 0x13
SELF_NPDRM_CONTROL_BLOCK_RANDOM_PAD_SIZE = 0xD

EMPTY_DIGEST = b'\x00' * DIGEST_SIZE
EMPTY_SIGNATURE = b'\x00' * SIGNATURE_SIZE

class SignedElfEntry(object):
    FMT = '<4Q'

    PROPS_ORDER_SHIFT = 0
    PROPS_ORDER_MASK = 0x1
    PROPS_ENCRYPTED_SHIFT = 1
    PROPS_ENCRYPTED_MASK = 0x1
    PROPS_SIGNED_SHIFT = 2
    PROPS_SIGNED_MASK = 0x1
    PROPS_COMPRESSED_SHIFT = 3
    PROPS_COMPRESSED_MASK = 0x1
    PROPS_WINDOW_BITS_SHIFT = 8
    PROPS_WINDOW_BITS_MASK = 0x7
    PROPS_HAS_BLOCKS_SHIFT = 11
    PROPS_HAS_BLOCKS_MASK = 0x1
    PROPS_BLOCK_SIZE_SHIFT = 12
    PROPS_BLOCK_SIZE_MASK = 0xF
    PROPS_HAS_DIGESTS_SHIFT = 16
    PROPS_HAS_DIGESTS_MASK = 0x1
    PROPS_HAS_EXTENTS_SHIFT = 17
    PROPS_HAS_EXTENTS_MASK = 0x1
    PROPS_HAS_META_SEGMENT_SHIFT = 20
    PROPS_HAS_META_SEGMENT_MASK = 0x1
    PROPS_SEGMENT_INDEX_SHIFT = 20
    PROPS_SEGMENT_INDEX_MASK = 0xFFFF

    def __init__(self, index):
        self.index = index
        self.props = 0
        self.offset = 0
        self.filesz = 0
        self.memsz = 0
        self.data = b''

    def save(self, f):
        f.write(struct.pack(SignedElfEntry.FMT, self.props, self.offset, self.filesz, self.memsz))

    @property
    def encrypted(self):
        return ((self.props >> SignedElfEntry.PROPS_ENCRYPTED_SHIFT) & SignedElfEntry.PROPS_ENCRYPTED_MASK) != 0
    @encrypted.setter
    def encrypted(self, value):
        self.props &= ~(SignedElfEntry.PROPS_ENCRYPTED_MASK << SignedElfEntry.PROPS_ENCRYPTED_SHIFT)
        if value:
            self.props |= SignedElfEntry.PROPS_ENCRYPTED_MASK << SignedElfEntry.PROPS_ENCRYPTED_SHIFT

    @property
    def signed(self):
        return ((self.props >> SignedElfEntry.PROPS_SIGNED_SHIFT) & SignedElfEntry.PROPS_SIGNED_MASK) != 0
    @signed.setter
    def signed(self, value):
        self.props &= ~(SignedElfEntry.PROPS_SIGNED_MASK << SignedElfEntry.PROPS_SIGNED_SHIFT)
        if value:
            self.props |= SignedElfEntry.PROPS_SIGNED_MASK << SignedElfEntry.PROPS_SIGNED_SHIFT

    @property
    def has_blocks(self):
        return ((self.props >> SignedElfEntry.PROPS_HAS_BLOCKS_SHIFT) & SignedElfEntry.PROPS_HAS_BLOCKS_MASK) != 0
    @has_blocks.setter
    def has_blocks(self, value):
        self.props &= ~(SignedElfEntry.PROPS_HAS_BLOCKS_MASK << SignedElfEntry.PROPS_HAS_BLOCKS_SHIFT)
        if value:
            self.props |= SignedElfEntry.PROPS_HAS_BLOCKS_MASK << SignedElfEntry.PROPS_HAS_BLOCKS_SHIFT

    @property
    def has_digests(self):
        return ((self.props >> SignedElfEntry.PROPS_HAS_DIGESTS_SHIFT) & SignedElfEntry.PROPS_HAS_DIGESTS_MASK) != 0
    @has_digests.setter
    def has_digests(self, value):
        self.props &= ~(SignedElfEntry.PROPS_HAS_DIGESTS_MASK << SignedElfEntry.PROPS_HAS_DIGESTS_SHIFT)
        if value:
            self.props |= SignedElfEntry.PROPS_HAS_DIGESTS_MASK << SignedElfEntry.PROPS_HAS_DIGESTS_SHIFT

    @property
    def block_size(self):
        if self.has_blocks:
            return 1 << (12 + (self.props >> SignedElfEntry.PROPS_BLOCK_SIZE_SHIFT) & SignedElfEntry.PROPS_BLOCK_SIZE_MASK)
        else:
            return DEFAULT_BLOCK_SIZE
    @block_size.setter
    def block_size(self, value):
        self.props &= ~(SignedElfEntry.PROPS_BLOCK_SIZE_MASK << SignedElfEntry.PROPS_BLOCK_SIZE_SHIFT)
        if self.has_blocks:
            value = ilog2(value) - 12
        else:
            value = 0
        self.props |= (value & SignedElfEntry.PROPS_BLOCK_SIZE_MASK) << SignedElfEntry.PROPS_BLOCK_SIZE_SHIFT

    @property
    def segment_index(self):
        return (self.props >> SignedElfEntry.PROPS_SEGMENT_INDEX_SHIFT) & SignedElfEntry.PROPS_SEGMENT_INDEX_MASK
    @segment_index.setter
    def segment_index(self, value):
        self.props &= ~(SignedElfEntry.PROPS_SEGMENT_INDEX_MASK << SignedElfEntry.PROPS_SEGMENT_INDEX_SHIFT)
        self.props |= (value & SignedElfEntry.PROPS_SEGMENT_INDEX_MASK) << SignedElfEntry.PROPS_SEGMENT_INDEX_SHIFT

class SignedElfExInfo(object):
    FMT = '<4Q32s'

    PTYPE_FAKE = 0x1
    PTYPE_NPDRM_EXEC = 0x4
    PTYPE_NPDRM_DYNLIB = 0x5
    PTYPE_SYSTEM_EXEC = 0x8
    PTYPE_SYSTEM_DYNLIB = 0x9
    PTYPE_HOST_KERNEL = 0xC
    PTYPE_SECURE_MODULE = 0xE
    PTYPE_SECURE_KERNEL = 0xF

    def __init__(self):
        self.paid = 0
        self.ptype = 0
        self.app_version = 0
        self.fw_version = 0
        self.digest = b'\x00' * 32

    def save(self, f):
        f.write(struct.pack(SignedElfExInfo.FMT, self.paid, self.ptype, self.app_version, self.fw_version, self.digest))

class SignedElfNpdrmControlBlock(object):
    FMT = '<H14x19s13s'

    def __init__(self):
        self.type = SELF_CONTROL_BLOCK_TYPE_NPDRM
        self.content_id = b'\x00' * SELF_NPDRM_CONTROL_BLOCK_CONTENT_ID_SIZE
        self.random_pad = b'\x00' * SELF_NPDRM_CONTROL_BLOCK_RANDOM_PAD_SIZE

    def save(self, f):
        f.write(struct.pack(SignedElfNpdrmControlBlock.FMT, self.type, self.content_id, self.random_pad))

class SignedElfMetaBlock(object):
    FMT = '<80x'
    def save(self, f):
        f.write(struct.pack(SignedElfMetaBlock.FMT))

class SignedElfMetaFooter(object):
    FMT = '<48xI28x'
    def __init__(self):
        self.unk1 = 0x10000
    def save(self, f):
        f.write(struct.pack(SignedElfMetaFooter.FMT, self.unk1))

class SignedElfFile(object):
    COMMON_HEADER_FMT = '<4s4B'
    EXT_HEADER_FMT = '<I2HQ2H4x'

    MAGIC = b'\x4F\x15\x3D\x1D'
    VERSION = 0x00
    MODE = 0x01
    ENDIAN = 0x01
    ATTRIBS = 0x12
    KEY_TYPE = 0x101

    FLAGS_SEGMENT_SIGNED_SHIFT = 4
    FLAGS_SEGMENT_SIGNED_MASK = 0x7

    HAS_NPDRM = 1

    def __init__(self, elf, **kwargs):
        self.elf = elf
        self.paid = kwargs.get('paid', 0x3100000000000002)
        self.ptype = kwargs.get('ptype', SignedElfExInfo.PTYPE_NPDRM_EXEC)
        self.app_version = kwargs.get('app_version', 0)
        self.fw_version = kwargs.get('fw_version', 0)
        self.auth_info = kwargs.get('auth_info', None)

    def _prepare(self):
        self.magic = SignedElfFile.MAGIC
        self.version = SignedElfFile.VERSION
        self.mode = SignedElfFile.MODE
        self.endian = SignedElfFile.ENDIAN
        self.attribs = SignedElfFile.ATTRIBS
        self.key_type = SignedElfFile.KEY_TYPE
        self.flags = 0x2

        signed_block_count = 2
        self.flags |= (signed_block_count & SignedElfFile.FLAGS_SEGMENT_SIGNED_MASK) << SignedElfFile.FLAGS_SEGMENT_SIGNED_SHIFT

        self.entries = []
        self.version_data = None
        entry_idx = 0
        for i in range(self.elf.ehdr.phnum):
            phdr = self.elf.phdrs[i]
            if phdr.type == ElfPHdr.PT_SCE_VERSION:
                self.version_data = self.elf.segments[i]
            if phdr.type not in [ElfPHdr.PT_LOAD, ElfPHdr.PT_SCE_RELRO, ElfPHdr.PT_SCE_DYNLIBDATA, ElfPHdr.PT_SCE_COMMENT]:
                continue
            meta_entry = SignedElfEntry(entry_idx)
            meta_entry.props = 0
            meta_entry.encrypted = False
            meta_entry.signed = True
            meta_entry.has_digests = True
            meta_entry.segment_index = entry_idx + 1
            self.entries.append(meta_entry)

            data_entry = SignedElfEntry(entry_idx + 1)
            data_entry.props = 0
            data_entry.encrypted = False
            data_entry.signed = True
            data_entry.has_blocks = True
            data_entry.block_size = BLOCK_SIZE
            data_entry.segment_index = i
            self.entries.append(data_entry)
            entry_idx += 2
        self.num_entries = len(self.entries)

        self.ex_info = SignedElfExInfo()
        self.ex_info.paid = self.paid
        self.ex_info.ptype = self.ptype
        self.ex_info.app_version = self.app_version
        self.ex_info.fw_version = self.fw_version
        self.ex_info.digest = self.elf.digest

        if SignedElfFile.HAS_NPDRM:
            self.npdrm_control_block = SignedElfNpdrmControlBlock()
            self.npdrm_control_block.content_id = b'\x00' * SELF_NPDRM_CONTROL_BLOCK_CONTENT_ID_SIZE
            self.npdrm_control_block.random_pad = b'\x00' * SELF_NPDRM_CONTROL_BLOCK_RANDOM_PAD_SIZE

        self.header_size = struct.calcsize(SignedElfFile.COMMON_HEADER_FMT) + struct.calcsize(SignedElfFile.EXT_HEADER_FMT)
        self.header_size += self.num_entries * struct.calcsize(SignedElfEntry.FMT)
        self.header_size += max(self.elf.ehdr.ehsize, self.elf.ehdr.phoff + self.elf.ehdr.phentsize * self.elf.ehdr.phnum)
        self.header_size = align_up(self.header_size, 16)
        self.header_size += struct.calcsize(SignedElfExInfo.FMT)
        if SignedElfFile.HAS_NPDRM:
            self.header_size += struct.calcsize(SignedElfNpdrmControlBlock.FMT)
        self.meta_size = self.num_entries * struct.calcsize(SignedElfMetaBlock.FMT) + struct.calcsize(SignedElfMetaFooter.FMT) + SIGNATURE_SIZE

        self.meta_blocks = [SignedElfMetaBlock() for _ in range(self.num_entries)]
        self.meta_footer = SignedElfMetaFooter()
        self.meta_footer.unk1 = 0x10000

        if self.auth_info is not None:
            self.signature = (struct.pack('<QQ', len(self.auth_info), self.ex_info.paid) + self.auth_info[8:]).ljust(SIGNATURE_SIZE, b'\x00')
        else:
            self.signature = EMPTY_SIGNATURE

        entry_idx = 0
        offset = self.header_size + self.meta_size
        for i in range(self.elf.ehdr.phnum):
            phdr = self.elf.phdrs[i]
            if phdr.type not in [ElfPHdr.PT_LOAD, ElfPHdr.PT_SCE_RELRO, ElfPHdr.PT_SCE_DYNLIBDATA, ElfPHdr.PT_SCE_COMMENT]:
                continue

            meta_entry, data_entry = self.entries[entry_idx], self.entries[entry_idx + 1]

            num_blocks = align_up(phdr.filesz, BLOCK_SIZE) // BLOCK_SIZE
            meta_entry.data = EMPTY_DIGEST * num_blocks
            meta_entry.offset = offset
            meta_entry.memsz = meta_entry.filesz = len(meta_entry.data)
            offset += meta_entry.filesz
            offset = align_up(offset, 16)

            data_entry.data = self.elf.segments[i]
            data_entry.offset = offset
            data_entry.memsz = data_entry.filesz = phdr.filesz
            offset += data_entry.filesz
            offset = align_up(offset, 16)

            entry_idx += 2

        self.file_size = offset

    def save(self, f):
        start_offset = f.tell()
        self._prepare()

        f.write(struct.pack(SignedElfFile.COMMON_HEADER_FMT, self.magic, self.version, self.mode, self.endian, self.attribs))
        f.write(struct.pack(SignedElfFile.EXT_HEADER_FMT, self.key_type, self.header_size, self.meta_size, self.file_size, self.num_entries, self.flags))

        for entry in self.entries:
            entry.save(f)

        elf_offset = f.tell()
        elf_header_size = max(self.elf.ehdr.ehsize, self.elf.ehdr.phoff + self.elf.ehdr.phentsize * self.elf.ehdr.phnum)
        elf_header_size = align_up(elf_header_size, 16)
        self.elf.save(f, True)
        f.seek(elf_offset + elf_header_size)

        self.ex_info.save(f)
        if SignedElfFile.HAS_NPDRM:
            self.npdrm_control_block.save(f)

        for meta_block in self.meta_blocks:
            meta_block.save(f)

        self.meta_footer.save(f)
        f.write(self.signature)

        for entry in self.entries:
            f.seek(start_offset + entry.offset)
            f.write(entry.data)

        if self.version_data is not None:
            f.write(self.version_data)

def main():
    parser = argparse.ArgumentParser(description='PS4/PS5 Fake Signed ELF (FSELF) Maker')
    parser.add_argument('input', help='Input ELF file')
    parser.add_argument('output', help='Output signed FSELF (eboot.bin)')
    parser.add_argument('--paid', type=int_with_base_type, default=0x3800000000000010, help='Program Authentication ID')
    parser.add_argument('--ptype', default='npdrm_exec', help='Program type (default: npdrm_exec)')
    parser.add_argument('--auth-info', default=None, help='Path to auth_info.bin or hex string')
    args = parser.parse_args()

    ptype_map = {
        'fake': SignedElfExInfo.PTYPE_FAKE,
        'npdrm_exec': SignedElfExInfo.PTYPE_NPDRM_EXEC,
        'npdrm_dynlib': SignedElfExInfo.PTYPE_NPDRM_DYNLIB,
        'system_exec': SignedElfExInfo.PTYPE_SYSTEM_EXEC,
    }
    ptype = ptype_map.get(args.ptype.lower(), SignedElfExInfo.PTYPE_NPDRM_EXEC)

    auth_info_bytes = None
    if args.auth_info:
        if os.path.exists(args.auth_info):
            with open(args.auth_info, 'rb') as f:
                auth_info_bytes = f.read()
        else:
            try:
                auth_info_bytes = bytes.fromhex(args.auth_info)
            except:
                pass

    print(f"[*] Loading ELF: {args.input}")
    with open(args.input, 'rb') as f:
        elf = ElfFile(ignore_shdrs=True)
        elf.load(f)

    print(f"[*] Fake-signing ELF into FSELF: {args.output} (ptype={args.ptype}, paid=0x{args.paid:016X})...")
    with open(args.output, 'wb') as f:
        self_file = SignedElfFile(elf, paid=args.paid, ptype=ptype, auth_info=auth_info_bytes)
        self_file.save(f)

    print(f"[+] Successfully generated FSELF: {args.output} ({os.path.getsize(args.output)} bytes)")

if __name__ == '__main__':
    main()