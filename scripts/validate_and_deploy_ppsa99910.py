#!/usr/bin/env python3
import os
import hashlib
import ftplib
from io import BytesIO
from pathlib import Path

host = os.getenv("PS5_HOST", "192.168.0.208")
port = int(os.getenv("PS5_PORT", "2121"))
title_id = "PPSA99910"
remote_root = f"/data/homebrew/{title_id}-app0"
local_root = Path(f"dist/{title_id}-app0")

files = [
    "eboot.bin",
    "contentids.json",
    "sce_sys/param.json",
    "sce_sys/keystone",
    "sce_sys/icon0.png",
    "sce_sys/pic0.png",
    "sce_sys/pic1.png",
]

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
            except Exception:
                pass

def main():
    print("========================================================")
    print(f" Deploying & Validating Clean Title: {title_id}")
    print(f" Target: {host}:{port}")
    print("========================================================")

    ftp = ftplib.FTP()
    ftp.connect(host, port, timeout=10)
    ftp.login()
    ftp.voidcmd("TYPE I")
    print("[+] Connected to PS5 FTP Server")

    ensure_ftp_dir(ftp, remote_root)
    ensure_ftp_dir(ftp, f"{remote_root}/sce_sys")

    # 1. Upload all files
    print("\n[*] Uploading package files...")
    for rel in files:
        local_path = local_root / rel
        remote_path = f"{remote_root}/{rel}"
        data = local_path.read_bytes()
        try:
            ftp.delete(remote_path)
        except Exception:
            pass
        ftp.storbinary(f"STOR {remote_path}", BytesIO(data))
        print(f"  [+] Uploaded {rel} ({len(data)} bytes)")

    # 2. Retrieve and verify SHA256 integrity
    print("\n[*] Validating Bit-for-Bit Remote Integrity...")
    # Disable ftpsrv's automatic self2elf extraction on RETR
    try:
        resp = ftp.sendcmd("SELF")
        print(f"  [i] ftpsrv mode: {resp.strip()}")
    except Exception as e:
        print(f"  [!] Note: SELF command not supported: {e}")

    all_passed = True
    for rel in files:
        local = (local_root / rel).read_bytes()
        received = BytesIO()
        ftp.retrbinary(f"RETR {remote_root}/{rel}", received.write)
        remote = received.getvalue()

        ok = (local == remote)
        status_tag = "OK" if ok else "FAIL"
        loc_hash = hashlib.sha256(local).hexdigest()[:12]
        rem_hash = hashlib.sha256(remote).hexdigest()[:12]
        print(f"  {status_tag:4} {rel:20} | local={len(local):8} remote={len(remote):8} | local={loc_hash} remote={rem_hash}")
        if not ok:
            all_passed = False

    ftp.quit()

    if not all_passed:
        raise RuntimeError("Deployment verification failed: One or more files mismatched!")

    print("\n========================================================")
    print(" [100% VERIFIED] Deployment Bit-for-Bit Validated on PS5!")
    print(f" Target Folder: {remote_root}")
    print("========================================================")

if __name__ == "__main__":
    main()
