# Let's inspect the exact disasm / offset calculation of our code
import struct

sockaddr_off = 0x300
temp_buf_off = 0x400
http_resp_off = 0x800

code = bytearray()
code += b'\x49\x89\xfc'                 # mov r12, rdi
code += b'\x49\x8b\x1c\x24'             # mov rbx, [r12]
code += b'\x48\x83\xc3\x0a'             # add rbx, 10

# 1. socket
code += b'\x48\xc7\xc7\x02\x00\x00\x00' # mov rdi, 2
code += b'\x48\xc7\xc6\x01\x00\x00\x00' # mov rsi, 1
code += b'\x48\x31\xd2'                 # xor rdx, rdx
code += b'\x48\xc7\xc0\x61\x00\x00\x00' # mov rax, 97
code += b'\xff\xd3'                     # call rbx
code += b'\x49\x89\xc5'                 # mov r13, rax

# 2. bind
code += b'\x4c\x89\xef'                 # mov rdi, r13
next_rip = 0x100 + len(code) + 7
rel_sock = sockaddr_off - next_rip
code += b'\x48\x8d\x35' + struct.pack('<i', rel_sock)
code += b'\x48\xc7\xc2\x10\x00\x00\x00' # mov rdx, 16
code += b'\x48\xc7\xc0\x68\x00\x00\x00' # mov rax, 104
code += b'\xff\xd3'                     # call rbx

# 3. listen
code += b'\x4c\x89\xef'                 # mov rdi, r13
code += b'\x48\xc7\xc6\x0a\x00\x00\x00' # mov rsi, 10
code += b'\x48\xc7\xc0\x6a\x00\x00\x00' # mov rax, 106
code += b'\xff\xd3'                     # call rbx

print(f"Generated {len(code)} bytes of init code")
print(f"Calculated rel_sock = {hex(rel_sock)} (target {hex(sockaddr_off)}, next_rip {hex(next_rip)})")
