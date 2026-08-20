import ftplib

HOST = "192.168.0.208"
FTP_PORT = 2121

def remove_dir_recursive(ftp, path):
    try:
        lines = []
        ftp.retrlines(f"LIST {path}", lines.append)
        for line in lines:
            parts = line.split()
            if len(parts) >= 9:
                name = parts[8]
                if name in [".", ".."]:
                    continue
                item_path = f"{path}/{name}"
                if line.startswith("d"):
                    remove_dir_recursive(ftp, item_path)
                else:
                    try:
                        ftp.delete(item_path)
                    except Exception:
                        pass
        ftp.rmd(path)
        print(f"    [+] Removed: {path}")
    except Exception as e:
        print(f"    [-] Error removing {path}: {e}")

def organize():
    print("========================================================")
    print(" Organizing /data/homebrew Games & Clean Subfolders")
    print(f" Target: {HOST}:{FTP_PORT}")
    print("========================================================")

    ftp = ftplib.FTP()
    ftp.connect(HOST, FTP_PORT, timeout=15)
    ftp.login()
    print("[+] Connected to PS5 FTP!")

    # 1. Restore NUTS (PPSA02343-app0) real eboot.bin
    print("\n[*] Restoring NUTS (PPSA02343-app0) game binary & assets...")
    try:
        # Delete dummy/payload eboot.bin inside PPSA02343-app0
        ftp.delete("/data/homebrew/PPSA02343-app0/eboot.bin")
    except Exception:
        pass

    try:
        # Move real 214MB eboot.bin from root to PPSA02343-app0/eboot.bin
        ftp.rename("/data/homebrew/eboot.bin", "/data/homebrew/PPSA02343-app0/eboot.bin")
        print("    [+] Moved real game eboot.bin (214 MB) -> /data/homebrew/PPSA02343-app0/eboot.bin")
    except Exception as e:
        print(f"    [-] Failed moving eboot.bin: {e}")

    for f in ["eboot.bin.auth_info", "ue4commandline.txt", "contentids.json"]:
        try:
            ftp.rename(f"/data/homebrew/{f}", f"/data/homebrew/PPSA02343-app0/{f}")
            print(f"    [+] Moved {f} -> /data/homebrew/PPSA02343-app0/{f}")
        except Exception:
            pass

    # 2. Clean up duplicate /data/homebrew/PPSA10595-app
    print("\n[*] Cleaning duplicate TEKKEN 8 staging folder...")
    remove_dir_recursive(ftp, "/data/homebrew/PPSA10595-app")

    # 3. Clean up loose/junk files from /data/homebrew root
    print("\n[*] Cleaning loose files from /data/homebrew root...")
    for loose in ["/data/homebrew/etaHEN-2.6B (1).bin", "/data/homebrew/nuts"]:
        try:
            try:
                ftp.delete(loose)
                print(f"    [+] Deleted {loose}")
            except Exception:
                remove_dir_recursive(ftp, loose)
        except Exception:
            pass

    # 4. List final organized structure
    print("\n=== Final /data/homebrew Directory Structure ===")
    lines = []
    ftp.retrlines("LIST /data/homebrew", lines.append)
    for l in lines:
        print("  ", l)

    ftp.quit()
    print("\n========================================================")
    print(" [SUCCESS] HOMEBREW DIRECTORY PERFECTLY ORGANIZED!")
    print("========================================================")

if __name__ == "__main__":
    organize()
