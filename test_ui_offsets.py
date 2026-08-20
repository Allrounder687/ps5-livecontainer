import struct

sockaddr_off = 0x300
temp_buf_off = 0x400
http_resp_off = 0x600

code = bytearray()
code += b'\x49\x89\xfc'
code += b'\x49\x8b\x1c\x24'
code += b'\x48\x83\xc3\x0a'

# socket
code += b'\x48\xc7\xc7\x02\x00\x00\x00'
code += b'\x48\xc7\xc6\x01\x00\x00\x00'
code += b'\x48\x31\xd2'
code += b'\x48\xc7\xc0\x61\x00\x00\x00'
code += b'\xff\xd3'
code += b'\x49\x89\xc5'

# bind
code += b'\x4c\x89\xef'
next_rip = 0x100 + len(code) + 7
rel_sock = sockaddr_off - next_rip
code += b'\x48\x8d\x35' + struct.pack('<i', rel_sock)
code += b'\x48\xc7\xc2\x10\x00\x00\x00'
code += b'\x48\xc7\xc0\x68\x00\x00\x00'
code += b'\xff\xd3'

# listen
code += b'\x4c\x89\xef'
code += b'\x48\xc7\xc6\x0a\x00\x00\x00'
code += b'\x48\xc7\xc0\x6a\x00\x00\x00'
code += b'\xff\xd3'

loop_accept_offset = len(code)

# accept
code += b'\x4c\x89\xef'
code += b'\x48\x31\xf6'
code += b'\x48\x31\xd2'
code += b'\x48\xc7\xc0\x1e\x00\x00\x00'
code += b'\xff\xd3'
code += b'\x48\x83\xf8\x00'
rel_retry = loop_accept_offset - (len(code) + 2)
code += b'\x78' + struct.pack('b', rel_retry)
code += b'\x49\x89\xc6'

# read
code += b'\x4c\x89\xf7'
next_rip = 0x100 + len(code) + 7
rel_temp = temp_buf_off - next_rip
code += b'\x48\x8d\x35' + struct.pack('<i', rel_temp)
code += b'\x48\xc7\xc2\x00\x02\x00\x00'
code += b'\x48\xc7\xc0\x03\x00\x00\x00'
code += b'\xff\xd3'

# write
code += b'\x4c\x89\xf7'
next_rip = 0x100 + len(code) + 7
rel_resp = http_resp_off - next_rip
code += b'\x48\x8d\x35' + struct.pack('<i', rel_resp)
code += b'\x48\xc7\xc2' + struct.pack('<I', 100) # len
code += b'\x48\xc7\xc0\x04\x00\x00\x00'
code += b'\xff\xd3'

# close
code += b'\x4c\x89\xf7'
code += b'\x48\xc7\xc0\x06\x00\x00\x00'
code += b'\xff\xd3'

# loop
rel_loop = loop_accept_offset - (len(code) + 2)
code += b'\xeb' + struct.pack('b', rel_loop)

print(f"Total code len = {len(code)} bytes (0x100 + {len(code)} = {hex(0x100 + len(code))})")
print(f"sockaddr_off = {hex(sockaddr_off)}")
print(f"temp_buf_off = {hex(temp_buf_off)}")
print(f"http_resp_off = {hex(http_resp_off)}")
print(f"rel_loop = {rel_loop}")
