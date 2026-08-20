import socket
import time
import ftplib
import io

host = '192.168.0.208'
port = 9021

with open('bare_payload.elf', 'rb') as f:
    payload = f.read()

print(f'[*] Sending bare_payload.elf ({len(payload)} bytes) to {host}:{port}...')

s = socket.socket()
s.settimeout(10)
s.connect((host, port))
s.sendall(payload)
s.close()
print('[+] Injected!')

time.sleep(3)

print('\n[*] Checking FTP for /data/raw_payload_test.log...')
ftp = ftplib.FTP()
ftp.connect(host, 2121, timeout=5)
ftp.login()

try:
    buf = io.BytesIO()
    ftp.retrbinary('RETR /data/raw_payload_test.log', buf.write)
    content = buf.getvalue().decode('utf-8', errors='replace')
    print('\n========================================')
    print('[+] EXECUTION CONFIRMED!')
    print(content)
    print('========================================')
except Exception as e:
    print(f'[-] Result: {e}')

ftp.quit()
