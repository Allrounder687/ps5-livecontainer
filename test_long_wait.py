import socket
import time
import ftplib
import io

host = '192.168.0.208'
port = 9021

with open('ps5_livecontainer.elf', 'rb') as f:
    payload = f.read()

print(f'[*] Payload size: {len(payload)} bytes')

# Connect and send
s = socket.socket()
s.settimeout(30)  # Long timeout - the child needs time to start
s.connect((host, port))
print('[+] Connected to elfldr')

s.sendall(payload)
print(f'[+] Sent {len(payload)} bytes')

# DO NOT call shutdown or close. Just wait for data.
# The parent closes its fd immediately, but the child has a dup'd copy.
# If our side of the TCP connection stays open, the child can still write.
print('[*] Keeping socket alive, waiting up to 30s for stdout from spawned payload...')

all_data = b''
try:
    while True:
        data = s.recv(4096)
        if not data:
            print('[*] Server closed connection')
            break
        all_data += data
        print(f'  >> {data}')
except socket.timeout:
    print('[*] 30s timeout reached')

s.close()

if all_data:
    print(f'\n[+] Total stdout: {len(all_data)} bytes')
    print(all_data.decode('utf-8', errors='replace'))
else:
    print('\n[-] No stdout received')

# Check for log files
print('\n[*] Checking FTP for log files...')
ftp = ftplib.FTP()
ftp.connect(host, 2121, timeout=5)
ftp.login()

for path in ['/data/raw_payload_test.log', '/tmp/raw_payload_test.log']:
    try:
        buf = io.BytesIO()
        ftp.retrbinary(f'RETR {path}', buf.write)
        print(f'\n[+] FOUND {path}!')
        print(buf.getvalue().decode('utf-8', errors='replace'))
    except:
        print(f'[-] {path}: not found')

ftp.quit()
