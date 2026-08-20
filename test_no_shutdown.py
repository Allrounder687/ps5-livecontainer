import socket
import time
import sys

host = '192.168.0.208'
port = 9021

with open('ps5_livecontainer.elf', 'rb') as f:
    payload = f.read()

print(f'[*] Payload size: {len(payload)} bytes')

s = socket.socket()
s.settimeout(15)
s.connect((host, port))
print('[+] Connected')

# Send the payload
s.sendall(payload)
print(f'[+] Sent {len(payload)} bytes')

# DO NOT shutdown(SHUT_WR) yet — let elfldr finish reading first
# Instead, wait for a response or for the server to close
print('[*] Waiting for response (no SHUT_WR)...')

all_data = b''
try:
    while True:
        data = s.recv(4096)
        if not data:
            break
        all_data += data
        print(f'[+] Chunk: {data}')
except socket.timeout:
    print('[*] Socket timeout (15s)')

s.close()

if all_data:
    print(f'\n[+] Total received: {len(all_data)} bytes')
    print(all_data.decode('utf-8', errors='replace'))
else:
    print('\n[-] No data received at all')
