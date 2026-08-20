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
                        print(f"    Deleted file: {item_path}")
                    except Exception as e:
                        print(f"    Failed deleting file {item_path}: {e}")
        ftp.rmd(path)
        print(f"[+] Deleted directory: {path}")
    except Exception as e:
        print(f"[-] Failed deleting directory {path}: {e}")

def main():
    print("========================================================")
    print(" Cleaning up duplicate/old LiveContainer apps from PS5")
    print(f" Target: {HOST}:{FTP_PORT}")
    print("========================================================")

    ftp = ftplib.FTP()
    ftp.connect(HOST, FTP_PORT, timeout=10)
    ftp.login()

    # Targets to remove:
    # 1. /user/app/PPSA99902 and /data/homebrew/PPSA99902-app0
    # 2. /user/app/PPSA99910 and /data/homebrew/PPSA99910-app0
    targets = [
        "/user/app/PPSA99902",
        "/data/homebrew/PPSA99902-app0",
        "/user/app/PPSA99910",
        "/data/homebrew/PPSA99910-app0",
        "/data/livecontainer.fself",
        "/data/eboot_test.bin",
        "/data/zeros.bin"
    ]

    for t in targets:
        print(f"\n[*] Processing: {t}...")
        try:
            # Check if directory or file
            try:
                ftp.delete(t)
                print(f"[+] Deleted file: {t}")
            except Exception:
                remove_dir_recursive(ftp, t)
        except Exception as e:
            print(f"[-] Error on {t}: {e}")

    ftp.quit()
    print("\n========================================================")
    print(" [SUCCESS] OLD LIVECONTAINER DUPLICATES REMOVED!")
    print("========================================================")

if __name__ == "__main__":
    main()
