import os
import ftplib
import time

HOST = "192.168.0.208"
FTP_PORT = 2121
LOCAL_DIR = r"C:\Users\Achie\Downloads\PPSA10595-app"
REMOTE_DIR = "/data/homebrew/PPSA10595-app0"

def upload_file(ftp, local_path, remote_path):
    sz = os.path.getsize(local_path)
    print(f"[*] Uploading {os.path.basename(local_path)} ({sz / (1024*1024):.2f} MB)...")
    start = time.time()
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_path}", f, blocksize=1024*1024)
    elapsed = time.time() - start
    speed = (sz / (1024*1024)) / elapsed if elapsed > 0 else 0
    print(f"    [+] Finished in {elapsed:.2f}s ({speed:.2f} MB/s)")

def main():
    print("========================================================")
    print(" Uploading Missing TEKKEN 8 eboot.bin to PS5")
    print(f" Source: {LOCAL_DIR}")
    print(f" Target: {HOST}:{FTP_PORT} -> {REMOTE_DIR}")
    print("========================================================")

    ftp = ftplib.FTP()
    ftp.connect(HOST, FTP_PORT, timeout=30)
    ftp.login()
    print("[+] Connected to PS5 FTP!")

    # Upload eboot.bin
    local_eboot = os.path.join(LOCAL_DIR, "eboot.bin")
    if os.path.exists(local_eboot):
        upload_file(ftp, local_eboot, f"{REMOTE_DIR}/eboot.bin")
        try:
            ftp.sendcmd(f"SITE CHMOD 777 {REMOTE_DIR}/eboot.bin")
        except Exception:
            pass

    # Also check and upload prx or small config files if needed
    for fname in ["contentids.json", "uecommandline.txt"]:
        local_f = os.path.join(LOCAL_DIR, fname)
        if os.path.exists(local_f):
            try:
                upload_file(ftp, local_f, f"{REMOTE_DIR}/{fname}")
            except Exception as e:
                print(f"    [-] Error on {fname}: {e}")

    # Verify upload
    print("\n[*] Verifying /data/homebrew/PPSA10595-app0:")
    lines = []
    ftp.retrlines(f"LIST {REMOTE_DIR}", lines.append)
    for l in lines:
        print("  ", l)

    ftp.quit()
    print("\n========================================================")
    print(" [SUCCESS] TEKKEN 8 EBOOT.BIN RESTORED ON PS5!")
    print("========================================================")

if __name__ == "__main__":
    main()
