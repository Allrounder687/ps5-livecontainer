#!/usr/bin/env python3
import os
import io
import json
import ftplib
import hashlib
import subprocess
import socket

PS5_HOST = os.getenv("PS5_HOST", "192.168.0.208")
PS5_PORT = int(os.getenv("PS5_PORT", "2121"))
ELFLDR_PORT = int(os.getenv("PS5_ELFLDR_PORT", "9021"))
TITLE_ID = "PPSA99905"
CONTENT_ID = f"EP0001-{TITLE_ID}_00-LIVECONTAINER000"

def check_ps5_connectivity(host, port, timeout=2.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    res = s.connect_ex((host, port))
    s.close()
    return res == 0

def fix_elf_header(filepath):
    print(f"[*] Patching ELF FreeBSD ABI (0x09, 0x02) for '{filepath}'...")
    with open(filepath, "r+b") as f:
        f.seek(7)
        f.write(bytes([0x09, 0x02]))

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
            except Exception:
                pass

def upload_file(ftp, local_path, remote_path):
    print(f"[*] Uploading '{local_path}' -> '{remote_path}'...")
    try:
        ftp.delete(remote_path)
    except Exception:
        pass
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_path}", f)
    print(f"[+] Successfully uploaded '{remote_path}' ({os.path.getsize(local_path)} bytes)")

def upload_bytes(ftp, data_bytes, remote_path):
    print(f"[*] Writing data -> '{remote_path}'...")
    try:
        ftp.delete(remote_path)
    except Exception:
        pass
    bio = io.BytesIO(data_bytes)
    ftp.storbinary(f"STOR {remote_path}", bio)
    print(f"[+] Successfully written '{remote_path}'")

def verify_remote_checksum(ftp, remote_path, local_bytes):
    buf = io.BytesIO()
    ftp.retrbinary(f"RETR {remote_path}", buf.write)
    remote_bytes = buf.getvalue()
    local_hash = hashlib.sha256(local_bytes).hexdigest()
    remote_hash = hashlib.sha256(remote_bytes).hexdigest()
    print(f"[*] Integrity Check: {remote_path}")
    print(f"    Local  ({len(local_bytes)} B): {local_hash}")
    print(f"    Remote ({len(remote_bytes)} B): {remote_hash}")
    assert local_hash == remote_hash, f"Checksum mismatch for {remote_path}!"
    print(f"[+] Verified 100% SHA256 match for {remote_path}")

def main():
    print("==================================================")
    print(f" Deploying PS5 LiveContainer as {TITLE_ID}-app0")
    print(f" Target: {PS5_HOST}:{PS5_PORT} (elfldr: {ELFLDR_PORT})")
    print("==================================================")

    # Pre-flight check
    if not check_ps5_connectivity(PS5_HOST, PS5_PORT):
        print(f"[-] Error: Cannot reach PS5 FTP on {PS5_HOST}:{PS5_PORT}. Is etaHEN active?")
        return

    # 1. Patch local ELF to exact PS5 FreeBSD ABI
    fix_elf_header("ps5_livecontainer.elf")

    # 2. Fake-sign ELF into valid Prospero FSELF (npdrm_exec)
    print("[*] Generating signed FSELF eboot.bin using make_fself.py...")
    auth_arg = "--auth-info auth_info.bin" if os.path.exists("auth_info.bin") else ""
    cmd = f"python scripts/make_fself.py --ptype npdrm_exec {auth_arg} ps5_livecontainer.elf eboot.bin"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists("eboot.bin"):
        print(f"[-] Error generating FSELF: {res.stderr}")
        return
    
    eboot_bytes = open("eboot.bin", "rb").read()
    print(f"[+] Successfully generated signed FSELF eboot.bin ({len(eboot_bytes)} bytes)")

    ftp = ftplib.FTP()
    ftp.connect(PS5_HOST, PS5_PORT, timeout=10)
    ftp.login()
    ftp.voidcmd("TYPE I")
    print("[+] Connected to PS5 FTP Server")

    app0_dir = f"/data/homebrew/{TITLE_ID}-app0"
    sce_sys_dir = f"{app0_dir}/sce_sys"

    ensure_ftp_dir(ftp, app0_dir)
    ensure_ftp_dir(ftp, sce_sys_dir)

    # 3. Upload signed FSELF eboot.bin
    upload_file(ftp, "eboot.bin", f"{app0_dir}/eboot.bin")
    verify_remote_checksum(ftp, f"{app0_dir}/eboot.bin", eboot_bytes)

    # 4. Upload auth_info
    if os.path.exists("auth_info.bin"):
        upload_file(ftp, "auth_info.bin", f"{app0_dir}/eboot.bin.auth_info")

    # 5. Upload contentids.json
    contentids = [CONTENT_ID]
    contentids_bytes = json.dumps(contentids, indent=2).encode('utf-8')
    upload_bytes(ftp, contentids_bytes, f"{app0_dir}/contentids.json")
    verify_remote_checksum(ftp, f"{app0_dir}/contentids.json", contentids_bytes)

    # 6. Upload param.json strictly matching Sony PS5 TitleID schema
    param_data = {
        "applicationCategoryType": 0,
        "applicationDrmType": "free",
        "attribute": 0,
        "attribute2": 0,
        "attribute3": 0,
        "conceptId": "999002",
        "contentBadgeType": 1,
        "contentId": CONTENT_ID,
        "contentVersion": "01.000.000",
        "downloadDataSize": 0,
        "localizedParameters": {
            "defaultLanguage": "en-US",
            "en-US": {
                "titleName": "PS5 LiveContainer"
            }
        },
        "masterVersion": "01.00",
        "pubtools": {
            "creationDate": "2026-08-20 00:50:00",
            "toolVersion": "1.00"
        },
        "requiredSystemSoftwareVersion": "0x0100000000000000",
        "sdkVersion": "0x0100000000000000",
        "targetContentVersion": "01.000.000",
        "titleId": TITLE_ID,
        "userDefinedParam1": 0
    }
    param_bytes = json.dumps(param_data, indent=2).encode('utf-8')
    upload_bytes(ftp, param_bytes, f"{sce_sys_dir}/param.json")
    verify_remote_checksum(ftp, f"{sce_sys_dir}/param.json", param_bytes)

    # 7. Copy keystone and icon/splash assets
    for asset in ['keystone', 'icon0.png', 'pic0.png', 'pic1.png']:
        try:
            buf = io.BytesIO()
            ftp.retrbinary(f"RETR /data/homebrew/PPSA99902-app0/sce_sys/{asset}", buf.write)
            if len(buf.getvalue()) > 0:
                upload_bytes(ftp, buf.getvalue(), f"{sce_sys_dir}/{asset}")
                print(f"[+] Copied {asset} ({len(buf.getvalue())} bytes)")
        except Exception as e:
            print(f"[-] Could not copy {asset}: {e}")

    ftp.quit()
    print("\n==================================================")
    print(" [SUCCESS] Fully Verified PS5 Title Deployed: " + TITLE_ID)
    print(f" Location: {app0_dir}")
    print(" 1. Ensure etaHEN / KStuff FSELF bypass is active.")
    print(" 2. Open Itemzflow -> Refresh Games List -> Launch!")
    print("==================================================")

if __name__ == "__main__":
    main()
