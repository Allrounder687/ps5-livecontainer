import urllib.request
import ftplib
import io
import os

url = "https://github.com/itsPLK/ps5-payloads-mirror/releases/download/payloads-mirror/elfldr_v0.24.elf"
local_path = "elfldr_v0.24.elf"

print(f"[*] Downloading {url}...")
try:
    urllib.request.urlretrieve(url, local_path)
    sz = os.path.getsize(local_path)
    print(f"[+] Downloaded {local_path} ({sz} bytes)")
except Exception as e:
    print(f"[-] Download failed: {e}")

host = '192.168.0.208'
ftp = ftplib.FTP()
ftp.connect(host, 2121, timeout=10)
ftp.login()
print("[+] Connected to PS5 FTP")

# Ensure /data/pldmgr/payloads/elfldr exists
try:
    ftp.mkd("/data/pldmgr/payloads/elfldr")
except Exception:
    pass

# Upload elfldr_v0.24.elf
if os.path.exists(local_path):
    with open(local_path, "rb") as f:
        ftp.storbinary("STOR /data/pldmgr/payloads/elfldr/elfldr_v0.24.elf", f)
    print("[+] Uploaded /data/pldmgr/payloads/elfldr/elfldr_v0.24.elf")

# Upload metadata json
json_meta = b'{"name":"elfldr","version":"0.24","category":"loader"}'
ftp.storbinary("STOR /data/pldmgr/payloads/elfldr/elfldr_v0.24.elf.json", io.BytesIO(json_meta))

ftp.quit()
print("[+] Finished!")
