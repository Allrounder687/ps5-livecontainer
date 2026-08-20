#!/usr/bin/env python3
import os
import io
import json
import ftplib

PS5_HOST = "192.168.0.208"

def ensure_ftp_dir(ftp, path):
    parts = [p for p in path.split('/') if p]
    cur = ""
    for part in parts:
        cur += "/" + part
        try:
            ftp.cwd(cur)
        except Exception:
            try:
                ftp.mkd(cur)
                print(f"[+] Created remote directory: {cur}")
            except Exception as e:
                pass

def upload_file(ftp, local_path, remote_path):
    print(f"[*] Uploading '{local_path}' -> '{remote_path}'...")
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_path}", f)
    print(f"[+] Uploaded '{remote_path}' ({os.path.getsize(local_path)} bytes)")

def upload_bytes(ftp, data_bytes, remote_path):
    print(f"[*] Writing data -> '{remote_path}'...")
    bio = io.BytesIO(data_bytes)
    ftp.storbinary(f"STOR {remote_path}", bio)
    print(f"[+] Written '{remote_path}'")

def main():
    print("==================================================")
    print(f" Deploying Official elfldr Daemon to PS5")
    print("==================================================")

    ftp = ftplib.FTP()
    # Connect to either port 1337 or 2121
    try:
        ftp.connect(PS5_HOST, 1337, timeout=5)
    except:
        ftp.connect(PS5_HOST, 2121, timeout=5)
    ftp.login()
    print("[+] Connected to PS5 FTP Server")

    # 1. Deploy elfldr to /data/pldmgr/payloads/elfldr/
    elfldr_dir = "/data/pldmgr/payloads/elfldr"
    ensure_ftp_dir(ftp, elfldr_dir)
    upload_file(ftp, "tools/elfldr/elfldr.elf", f"{elfldr_dir}/elfldr.elf")

    meta = {
        "name": "ELF Loader Daemon",
        "filename": "elfldr.elf",
        "description": "Background payload server listening on Port 9021 for Payload Manager and PC tools.",
        "version": "0.24",
        "category": "Payloads & Daemons",
        "author": "John Törnblom"
    }
    upload_bytes(ftp, json.dumps(meta, indent=2).encode('utf-8'), f"{elfldr_dir}/elfldr.elf.json")

    # 2. Append elfldr to /data/pldmgr/autoload.txt
    try:
        buf = io.BytesIO()
        ftp.retrbinary('RETR /data/pldmgr/autoload.txt', buf.write)
        autoload_content = buf.getvalue().decode('utf-8', errors='ignore')
        if 'elfldr.elf' not in autoload_content:
            autoload_content += "\nelfldr.elf\n"
            upload_bytes(ftp, autoload_content.encode('utf-8'), '/data/pldmgr/autoload.txt')
            print("[+] Added elfldr.elf to Payload Manager autoload list!")
    except Exception as e:
        print("[-] Could not update autoload.txt:", e)

    ftp.quit()
    print("\n==================================================")
    print(" [SUCCESS] elfldr Daemon Deployed!")
    print(" Launch 'ELF Loader Daemon' in Payload Manager to open Port 9021.")
    print("==================================================")

if __name__ == "__main__":
    main()
