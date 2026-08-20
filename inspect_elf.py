import struct

# Compare our payload vs what we know about notify.elf
with open('ps5_livecontainer.elf', 'rb') as f:
    our = f.read()

print(f'Our ELF size: {len(our)} bytes')
print(f'Magic: {our[:4].hex()}')
print(f'First 16 bytes: {our[:16].hex()}')

e_shnum = struct.unpack_from('<H', our, 60)[0]
e_shoff = struct.unpack_from('<Q', our, 40)[0]
e_phnum = struct.unpack_from('<H', our, 56)[0]
e_type = struct.unpack_from('<H', our, 16)[0]
e_entry = struct.unpack_from('<Q', our, 24)[0]
print(f'e_type: {e_type} (3=DYN)')
print(f'e_entry: 0x{e_entry:x}')
print(f'e_phnum: {e_phnum}')
print(f'e_shoff: {e_shoff}')
print(f'e_shnum: {e_shnum}')
print(f'File size vs shoff+shnum*64: {len(our)} vs {e_shoff + e_shnum*64}')

# Check if stripped properly
print()
print('=== Section names ===')
e_shstrndx = struct.unpack_from('<H', our, 62)[0]
shstrtab_off = struct.unpack_from('<Q', our, e_shoff + e_shstrndx*64 + 24)[0]
shstrtab_size = struct.unpack_from('<Q', our, e_shoff + e_shstrndx*64 + 32)[0]
strtab = our[shstrtab_off:shstrtab_off+shstrtab_size]

for i in range(e_shnum):
    sh_name = struct.unpack_from('<I', our, e_shoff + i*64)[0]
    sh_type = struct.unpack_from('<I', our, e_shoff + i*64 + 4)[0]
    name_end = strtab.find(0, sh_name) if sh_name < len(strtab) else sh_name
    name = strtab[sh_name:name_end].decode('ascii', errors='replace') if sh_name < len(strtab) else '?'
    print(f'  [{i}] type={sh_type} name="{name}"')
