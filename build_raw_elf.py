import struct

def make_elf():
    msg = b"========================================\n" \
          b"[+] PS5 DIRECT CODE EXECUTION CONFIRMED!\n" \
          b"[+] Running natively via elfldr on PS5!\n" \
          b"========================================\n"
    path = b"/data/raw_payload_test.log\x00"

    file_size = 0x1000  # 4096 bytes
    buf = bytearray(file_size)
    
    code = bytearray()
    
    # RDI holds `args` pointer when _start begins.
    # args[0] (qword at [rdi]) is ptr to getpid in libkernel!
    # getpid + 0x0A is the syscall gadget inside libkernel!
    
    # Save args in r12 (callee-saved)
    code += b'\x49\x89\xfc'                 # mov r12, rdi (save args pointer)
    # Calculate gadget = [r12] + 0xA
    code += b'\x49\x8b\x1c\x24'             # mov rbx, [r12] (rbx = getpid)
    code += b'\x48\x83\xc3\x0a'             # add rbx, 10 (rbx = syscall gadget in libkernel)
    
    # sys_open(path, 0x601, 0777)
    # SYS_open = 5
    # path is at 0x200
    # len(code) currently = 11 (0xB). next rip = 0x100 + 0xB + 7 = 0x112
    # target = 0x200. rel = 0x200 - 0x112 = 0xEE
    code += b'\x48\x8d\x3d\xee\x00\x00\x00' # lea rdi, [rip + 0xEE]
    code += b'\x48\xc7\xc6\x01\x06\x00\x00' # mov rsi, 0x601 (O_CREAT | O_WRONLY | O_TRUNC)
    code += b'\x48\xc7\xc2\xff\x01\x00\x00' # mov rdx, 0x1FF (0777)
    code += b'\x48\xc7\xc0\x05\x00\x00\x00' # mov rax, 5 (SYS_open)
    code += b'\xff\xd3'                     # call rbx (execute syscall inside libkernel!)
    
    # check fd
    code += b'\x48\x83\xf8\x00'             # cmp rax, 0
    code += b'\x78\x24'                     # js exit (+0x24)
    
    # sys_write(fd, msg, len)
    # fd in rax
    code += b'\x48\x89\xc7'                 # mov rdi, rax (fd)
    code += b'\x57'                         # push rdi (save fd)
    # msg is at 0x250
    # current len(code) = 11 + 7 + 7 + 7 + 7 + 2 + 4 + 2 + 3 + 1 = 51 (0x33)
    # next rip = 0x100 + 0x33 + 7 = 0x13A
    # rel = 0x250 - 0x13A = 0x116
    code += b'\x48\x8d\x35\x16\x01\x00\x00' # lea rsi, [rip + 0x116]
    code += b'\x48\xc7\xc2' + struct.pack('<I', len(msg)) # mov rdx, len(msg)
    code += b'\x48\xc7\xc0\x04\x00\x00\x00' # mov rax, 4 (SYS_write)
    code += b'\xff\xd3'                     # call rbx (execute syscall inside libkernel!)
    
    # sys_close(fd)
    code += b'\x5f'                         # pop rdi (fd)
    code += b'\x48\xc7\xc0\x06\x00\x00\x00' # mov rax, 6 (SYS_close)
    code += b'\xff\xd3'                     # call rbx (execute syscall inside libkernel!)

    # exit: sys_exit(0)
    code += b'\x48\x31\xff'                 # xor rdi, rdi
    code += b'\x48\xc7\xc0\x01\x00\x00\x00' # mov rax, 1 (SYS_exit)
    code += b'\xff\xd3'                     # call rbx (execute syscall inside libkernel!)
    code += b'\xc3'                         # ret

    buf[0x100:0x100+len(code)] = code
    buf[0x200:0x200+len(path)] = path
    buf[0x250:0x250+len(msg)] = msg

    shstrtab = b'\x00.text\x00.shstrtab\x00'
    shstrtab_off = 0xE00
    buf[shstrtab_off:shstrtab_off+len(shstrtab)] = shstrtab
    sh_off = 0xF80

    buf[0:4] = b'\x7fELF'
    buf[4] = 2 # ELFCLASS64
    buf[5] = 1 # ELFDATA2LSB
    buf[6] = 1 # EV_CURRENT
    buf[7] = 9 # ELFOSABI_FREEBSD
    buf[8] = 0 # ABI version
    
    struct.pack_into('<H', buf, 16, 3)          # e_type: ET_DYN (3)
    struct.pack_into('<H', buf, 18, 0x3E)       # e_machine: EM_X86_64 (62)
    struct.pack_into('<I', buf, 20, 1)          # e_version: EV_CURRENT (1)
    struct.pack_into('<Q', buf, 24, 0x100)      # e_entry: 0x100
    struct.pack_into('<Q', buf, 32, 64)         # e_phoff: 64
    struct.pack_into('<Q', buf, 40, sh_off)     # e_shoff: 0xF80
    struct.pack_into('<I', buf, 48, 0)          # e_flags
    struct.pack_into('<H', buf, 52, 64)         # e_ehsize: 64
    struct.pack_into('<H', buf, 54, 56)         # e_phentsize: 56
    struct.pack_into('<H', buf, 56, 1)          # e_phnum: 1
    struct.pack_into('<H', buf, 58, 64)         # e_shentsize: 64
    struct.pack_into('<H', buf, 60, 2)          # e_shnum: 2
    struct.pack_into('<H', buf, 62, 1)          # e_shstrndx: 1

    # Program Header 0 (56 bytes at offset 64)
    struct.pack_into('<I', buf, 64 + 0, 1)      # p_type: PT_LOAD
    struct.pack_into('<I', buf, 64 + 4, 7)      # p_flags: PF_R | PF_W | PF_X
    struct.pack_into('<Q', buf, 64 + 8, 0)      # p_offset: 0
    struct.pack_into('<Q', buf, 64 + 16, 0)     # p_vaddr: 0
    struct.pack_into('<Q', buf, 64 + 24, 0)     # p_paddr: 0
    struct.pack_into('<Q', buf, 64 + 32, file_size) # p_filesz
    struct.pack_into('<Q', buf, 64 + 40, file_size) # p_memsz
    struct.pack_into('<Q', buf, 64 + 48, 0x1000)    # p_align: 4096

    # Section Headers
    struct.pack_into('<I', buf, sh_off + 64 + 0, 7)   # sh_name (.shstrtab)
    struct.pack_into('<I', buf, sh_off + 64 + 4, 3)   # sh_type: SHT_STRTAB (3)
    struct.pack_into('<Q', buf, sh_off + 64 + 8, 0)   # sh_flags
    struct.pack_into('<Q', buf, sh_off + 64 + 16, 0)  # sh_addr
    struct.pack_into('<Q', buf, sh_off + 64 + 24, shstrtab_off) # sh_offset (0xE00)
    struct.pack_into('<Q', buf, sh_off + 64 + 32, len(shstrtab)) # sh_size
    struct.pack_into('<I', buf, sh_off + 64 + 40, 0)  # sh_link
    struct.pack_into('<I', buf, sh_off + 64 + 44, 0)  # sh_info
    struct.pack_into('<Q', buf, sh_off + 64 + 48, 1)  # sh_addralign
    struct.pack_into('<Q', buf, sh_off + 64 + 56, 0)  # sh_entsize

    return bytes(buf)

elf_bytes = make_elf()
with open("bare_payload.elf", "wb") as f:
    f.write(elf_bytes)
print(f"[+] Fixed bare_payload.elf generated ({len(elf_bytes)} bytes)")
