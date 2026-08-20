#!/usr/bin/env python3
import os
import io
import json
import ftplib

PS5_HOST = "192.168.0.208"
PS5_PORT = 2121
TITLE_ID = "PPSA99902"
CONTENT_ID = f"EP0001-{TITLE_ID}_00-LIVECONTAINER000"

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
            except Exception as e:
                pass

def upload_file(ftp, local_path, remote_path):
    print(f"[*] Uploading '{local_path}' -> '{remote_path}'...")
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_path}", f)
    print(f"[+] Successfully uploaded '{remote_path}' ({os.path.getsize(local_path)} bytes)")

def upload_bytes(ftp, data_bytes, remote_path):
    print(f"[*] Writing data -> '{remote_path}'...")
    bio = io.BytesIO(data_bytes)
    ftp.storbinary(f"STOR {remote_path}", bio)
    print(f"[+] Successfully written '{remote_path}'")

def main():
    print("==================================================")
    print(f" Packaging & Deploying LiveContainer app0 to PS5")
    print("==================================================")

    # 1. Patch local ELF to exact PS5 FreeBSD ABI
    fix_elf_header("ps5_livecontainer.elf")

    # 2. Fake-sign ELF into valid Prospero FSELF (npdrm_exec)
    print("[*] Generating signed FSELF eboot.bin using make_fself.py...")
    import subprocess
    auth_arg = "--auth-info auth_info.bin" if os.path.exists("auth_info.bin") else ""
    cmd = f"python scripts/make_fself.py --ptype npdrm_exec {auth_arg} ps5_livecontainer.elf eboot.bin"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists("eboot.bin"):
        print(f"[-] Error generating FSELF: {res.stderr}")
        return
    print(f"[+] Successfully generated signed FSELF eboot.bin ({os.path.getsize('eboot.bin')} bytes)")

    ftp = ftplib.FTP()
    ftp.connect(PS5_HOST, PS5_PORT, timeout=10)
    ftp.login()
    print("[+] Connected to PS5 FTP Server")

    app0_dir = f"/data/homebrew/{TITLE_ID}-app0"
    sce_sys_dir = f"{app0_dir}/sce_sys"

    ensure_ftp_dir(ftp, app0_dir)
    ensure_ftp_dir(ftp, sce_sys_dir)

    # 3. Upload signed FSELF eboot.bin
    upload_file(ftp, "eboot.bin", f"{app0_dir}/eboot.bin")

    # 4. Upload auth_info
    if os.path.exists("auth_info.bin"):
        upload_file(ftp, "auth_info.bin", f"{app0_dir}/eboot.bin.auth_info")

    # 3. Upload contentids.json
    contentids = [CONTENT_ID]
    upload_bytes(ftp, json.dumps(contentids, indent=2).encode('utf-8'), f"{app0_dir}/contentids.json")

    # 4. Upload param.json
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
            "creationDate": "2026-08-20 00:45:00",
            "toolVersion": "1.00"
        },
        "requiredSystemSoftwareVersion": "0x0100000000000000",
        "sdkVersion": "0x0100000000000000",
        "targetContentVersion": "01.000.000",
        "titleId": TITLE_ID,
        "userDefinedParam1": 0
    }
    upload_bytes(ftp, json.dumps(param_data, indent=2).encode('utf-8'), f"{sce_sys_dir}/param.json")

    # 5. Copy icon if existing
    try:
        buf = io.BytesIO()
        ftp.retrbinary('RETR /data/homebrew/PPSA99901-app0/sce_sys/icon0.png', buf.write)
        if len(buf.getvalue()) > 0:
            upload_bytes(ftp, buf.getvalue(), f"{sce_sys_dir}/icon0.png")
    except Exception:
        pass

    ftp.quit()
    print("\n==================================================")
    print(" [SUCCESS] LiveContainer deployed as Native App!")
    print(f" Location: {app0_dir}")
    print(" Open Itemzflow or your PS5 Dashboard to launch PS5 LiveContainer!")
    print("==================================================")

if __name__ == "__main__":
    main()
