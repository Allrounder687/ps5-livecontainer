import socket
import time
import ftplib

host = '192.168.0.208'
port = 9021

with open('ps5_livecontainer.elf', 'rb') as f:
    payload = f.read()

print(f'[*] Payload size: {len(payload)} bytes')

# Connect and send
s = socket.socket()
s.settimeout(15)
s.connect((host, port))
print('[+] Connected to elfldr')

s.sendall(payload)
print(f'[+] Sent {len(payload)} bytes')

# Don't shutdown - wait for data or connection close
print('[*] Waiting for stdout from payload...')
all_data = b''
try:
    while True:
        data = s.recv(4096)
        if not data:
            break
        all_data += data
        print(f'  >> {data}')
except socket.timeout:
    print('[*] Timeout (15s)')
s.close()

if all_data:
    print(f'\n[+] Total stdout: {len(all_data)} bytes')
    print(all_data.decode('utf-8', errors='replace'))
else:
    print('[-] No stdout received')

# Wait for payload to finish writing files
print('\n[*] Waiting 8 seconds for payload to write files...')
time.sleep(8)

# Check for log file
print('\n[*] Checking for log files via FTP...')
ftp = ftplib.FTP()
ftp.connect(host, 2121, timeout=5)
ftp.login()

for path in ['/data/raw_payload_test.log', '/tmp/raw_payload_test.log']:
    try:
        import io
        buf = io.BytesIO()
        ftp.retrbinary(f'RETR {path}', buf.write)
        content = buf.getvalue().decode('utf-8', errors='replace')
        print(f'\n[+] FOUND {path}!')
        print(content)
    except Exception as e:
        print(f'[-] {path}: {e}')

# Also list /data to see if anything new appeared
print('\n[*] Full /data listing:')
ftp.retrlines('LIST /data')
ftp.quit()
