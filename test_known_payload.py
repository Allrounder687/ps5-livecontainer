import socket
import ftplib
import io
import sys
import time

host = '192.168.0.208'

# Step 1: Download notify.elf from PS5 via FTP (a known-working payload)
print("[*] Downloading notify.elf from PS5 via FTP...")
ftp = ftplib.FTP()
ftp.connect(host, 2121, timeout=5)
ftp.login()

# Use SELF command to disable self2elf conversion
ftp.sendcmd('SELF')

buf = io.BytesIO()
ftp.retrbinary('RETR /data/notify.elf', buf.write)
ftp.quit()

notify_data = buf.getvalue()
print(f"[+] Downloaded notify.elf: {len(notify_data)} bytes, magic: {notify_data[:4].hex()}")

# Step 2: Send notify.elf to elfldr on port 9021
print(f"\n[*] Sending notify.elf to elfldr on port 9021...")
s = socket.socket()
s.settimeout(10)
s.connect((host, 9021))
s.sendall(notify_data)
s.shutdown(socket.SHUT_WR)
print("[+] Sent and shutdown write side")

# Read response
all_data = b''
try:
    while True:
        data = s.recv(4096)
        if not data:
            break
        all_data += data
except socket.timeout:
    pass
s.close()

if all_data:
    print(f"[+] Received {len(all_data)} bytes from payload stdout:")
    print(all_data.decode('utf-8', errors='replace'))
else:
    print("[-] No stdout received (connection closed immediately)")

# Step 3: Wait and check for file creation
print("\n[*] Waiting 3 seconds then checking /data/ for any new files...")
time.sleep(3)

ftp2 = ftplib.FTP()
ftp2.connect(host, 2121, timeout=5)
ftp2.login()
ftp2.retrlines('LIST /data')
ftp2.quit()
