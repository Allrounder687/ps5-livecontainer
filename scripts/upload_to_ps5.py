#!/usr/bin/env python3
import os
import io
import json
import ftplib

PS5_HOST = "192.168.0.208"
PS5_PORT = 2121

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
    print(f"[+] Successfully uploaded '{remote_path}' ({os.path.getsize(local_path)} bytes)")

def upload_bytes(ftp, data_bytes, remote_path):
    print(f"[*] Writing metadata -> '{remote_path}'...")
    bio = io.BytesIO(data_bytes)
    ftp.storbinary(f"STOR {remote_path}", bio)
    print(f"[+] Successfully written '{remote_path}'")

def main():
    print("==================================================")
    print(f"  Deploying PS5 LiveContainer to {PS5_HOST}:{PS5_PORT}")
    print("==================================================")

    ftp = ftplib.FTP()
    ftp.connect(PS5_HOST, PS5_PORT, timeout=10)
    ftp.login()
    print("[+] Connected to PS5 FTP Server:", ftp.getwelcome().strip())

    # 1. Deploy to /data/pldmgr/payloads/LiveContainer
    pldmgr_dir = "/data/pldmgr/payloads/LiveContainer"
    ensure_ftp_dir(ftp, pldmgr_dir)
    upload_file(ftp, "ps5_livecontainer.elf", f"{pldmgr_dir}/LiveContainer.elf")

    meta = {
        "name": "PS5 LiveContainer",
        "filename": "LiveContainer.elf",
        "description": "In-memory dynamic ELF sandbox runner with crash protection and Port 8080 Web Dashboard.",
        "version": "1.0.0",
        "category": "Utilities & Tools",
        "author": "LiveContainer Team"
    }
    upload_bytes(ftp, json.dumps(meta, indent=2).encode('utf-8'), f"{pldmgr_dir}/LiveContainer.elf.json")

    # 2. Deploy Container Infrastructure under /data/containers
    ensure_ftp_dir(ftp, "/data/containers")
    ensure_ftp_dir(ftp, "/data/containers/apps")
    ensure_ftp_dir(ftp, "/data/containers/logs")

    # 3. Deploy Test Payloads to /data/containers/apps/
    hello_dir = "/data/containers/apps/org.ps5.hello"
    ensure_ftp_dir(ftp, hello_dir)
    upload_file(ftp, "test_payloads/hello_runner/eboot.elf", f"{hello_dir}/eboot.elf")

    crash_dir = "/data/containers/apps/org.ps5.crashtrap"
    ensure_ftp_dir(ftp, crash_dir)
    upload_file(ftp, "test_payloads/crash_catcher/eboot.elf", f"{crash_dir}/eboot.elf")

    # 4. Deploy notify.elf helper to /data/ and /data/pldmgr/payloads/notify/
    if os.path.exists("tools/notify/notify.elf"):
        upload_file(ftp, "tools/notify/notify.elf", "/data/notify.elf")
        notify_dir = "/data/pldmgr/payloads/notify"
        ensure_ftp_dir(ftp, notify_dir)
        upload_file(ftp, "tools/notify/notify.elf", f"{notify_dir}/notify.elf")
        notify_meta = {
            "name": "Notification Helper",
            "filename": "notify.elf",
            "description": "PS5 system notification display tool.",
            "version": "1.0.0",
            "category": "Utilities & Tools"
        }
        upload_bytes(ftp, json.dumps(notify_meta, indent=2).encode('utf-8'), f"{notify_dir}/notify.elf.json")

    ftp.quit()
    print("\n==================================================")
    print(" [SUCCESS] Deployment Completed!")
    print(" You can now:")
    print(" 1. Launch 'PS5 LiveContainer' directly from your PS5 Payload Manager / menu.")
    print(f" 2. Open http://{PS5_HOST}:8080 in your phone or PC browser.")
    print("==================================================")

if __name__ == "__main__":
    main()
