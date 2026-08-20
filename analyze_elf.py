import struct

with open('ps5_livecontainer.elf', 'rb') as f:
    data = f.read()

e_shoff = struct.unpack_from('<Q', data, 40)[0]
e_shnum = struct.unpack_from('<H', data, 60)[0]
e_shentsize = struct.unpack_from('<H', data, 58)[0]

print(f'File size: {len(data)}')
print(f'e_shoff: {e_shoff}')
print(f'e_shnum: {e_shnum}')
print(f'e_shentsize: {e_shentsize}')
print(f'Section header table end: {e_shoff + e_shnum * e_shentsize}')
print()

# elfldr uses sizeof(Elf64_Ehdr) = 64 for shdr size (bug but same value)
initial_size = e_shoff + e_shnum * 64
print(f'elfldr initial recv size: {initial_size}')

# Now check each section
print('\n=== Section analysis ===')
shend = 0
for i in range(e_shnum):
    off = e_shoff + i * e_shentsize
    sh_name = struct.unpack_from('<I', data, off)[0]
    sh_type = struct.unpack_from('<I', data, off + 4)[0]
    sh_offset = struct.unpack_from('<Q', data, off + 24)[0]
    sh_size = struct.unpack_from('<Q', data, off + 32)[0]
    
    SHT_NOBITS = 8
    end = sh_offset + sh_size
    if sh_type != SHT_NOBITS and end > shend:
        shend = end
    
    print(f'  [{i:2d}] type={sh_type:2d} offset=0x{sh_offset:06x} size=0x{sh_size:06x} end=0x{end:06x} {"NOBITS" if sh_type == SHT_NOBITS else ""}')

print(f'\nshend (max section data end): 0x{shend:x} = {shend}')
print(f'initial_size: {initial_size}')
print(f'shend <= initial_size? {shend <= initial_size}')
print(f'Actual file size: {len(data)}')

if shend > initial_size:
    extra_read = shend - initial_size
    total_elfldr_reads = initial_size + extra_read
    print(f'elfldr will read additional {extra_read} bytes')
    print(f'Total bytes elfldr expects: {total_elfldr_reads}')
    print(f'File has: {len(data)}')
    print(f'Match? {total_elfldr_reads == len(data)}')
