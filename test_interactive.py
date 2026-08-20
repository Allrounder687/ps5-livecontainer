import socket
import time
import ftplib
import io
import threading

host = '192.168.0.208'
port = 9021

with open('ps5_livecontainer.elf', 'rb') as f:
    payload = f.read()

print(f'[*] Payload size: {len(payload)} bytes')

s = socket.socket()
s.settimeout(30)
s.connect((host, port))
print('[+] Connected to elfldr')

# Send payload
s.sendall(payload)
print(f'[+] Sent {len(payload)} bytes')

# Send stdin data for the payload (like socat would)
# Our payload doesn't read stdin, but hello_stdio does: "enter name"
# The key: socat keeps both read and write open
# Let's send a newline as "stdin" for our payload to consume
time.sleep(0.5)
s.sendall(b"test_user\n")
print('[+] Sent stdin data')

# Now read
print('[*] Reading stdout...')
all_data = b''
try:
    while True:
        data = s.recv(4096)
        if not data:
            print('[*] Connection closed')
            break
        all_data += data
        print(f'  >> {repr(data)}')
except socket.timeout:
    print('[*] 30s timeout')

s.close()

if all_data:
    print(f'\n[+] Total: {len(all_data)} bytes')
    print(all_data.decode('utf-8', errors='replace'))
else:
    print('\n[-] No data')

# FTP check
time.sleep(3)
print('\n[*] FTP check...')
ftp = ftplib.FTP()
ftp.connect(host, 2121, timeout=5)
ftp.login()
for path in ['/data/raw_payload_test.log', '/tmp/raw_payload_test.log']:
    try:
        buf = io.BytesIO()
        ftp.retrbinary(f'RETR {path}', buf.write)
        print(f'[+] FOUND {path}: {buf.getvalue().decode()}')
    except:
        print(f'[-] {path}: not found')
ftp.quit()
