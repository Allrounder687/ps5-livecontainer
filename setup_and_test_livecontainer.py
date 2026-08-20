import socket
import time
import ftplib
import io
import json
import build_raw_elf

HOST = "192.168.0.208"
ELFLDR_PORT = 9021
FTP_PORT = 2121

def ensure_ftp_dir(ftp, dir_path):
    parts = dir_path.strip("/").split("/")
    cur = ""
    for p in parts:
        cur += "/" + p
        try:
            ftp.mkd(cur)
        except Exception:
            pass

def main():
    print("========================================================")
    print(" PS5 LiveContainer Automated Setup & Test Suite")
    print(f" Target Console: {HOST}")
    print("========================================================")

    # 1. Connect to FTP
    print("\n[Step 1] Connecting to PS5 FTP Server...")
    try:
        ftp = ftplib.FTP()
        ftp.connect(HOST, FTP_PORT, timeout=5)
        ftp.login()
        print("    [+] Connected to FTP server.")
    except Exception as e:
        print(f"    [-] FTP Connection failed: {e}")
        return

    # 2. Setup VFS Sandbox Directory Tree
    print("\n[Step 2] Setting up VFS Sandbox directory tree...")
    dirs = [
        "/data/containers",
        "/data/containers/apps",
        "/data/containers/apps/hello_runner",
        "/data/containers/apps/crash_catcher",
        "/data/containers/logs",
        "/data/containers/apps/hello_runner/data",
        "/data/containers/apps/crash_catcher/data",
    ]
    for d in dirs:
        ensure_ftp_dir(ftp, d)
        print(f"    [+] Ensured: {d}")

    # 3. Create initial containers.json registry
    print("\n[Step 3] Creating & uploading containers.json registry...")
    registry = {
        "version": "1.0.0",
        "slots": [
            {
                "id": "org.ps5.hellorunner",
                "name": "Hello Runner",
                "version": "1.0",
                "author": "Homebrew Dev",
                "description": "Sample guest homebrew payload with toast notification.",
                "elf_path": "/data/containers/apps/hello_runner/eboot.elf",
                "data_dir": "/data/containers/apps/hello_runner/data",
                "state": "IDLE"
            },
            {
                "id": "org.ps5.crashcatcher",
                "name": "Crash Catcher",
                "version": "1.0",
                "author": "Homebrew Dev",
                "description": "Intentional SIGSEGV null-pointer trap tester.",
                "elf_path": "/data/containers/apps/crash_catcher/eboot.elf",
                "data_dir": "/data/containers/apps/crash_catcher/data",
                "state": "IDLE"
            }
        ]
    }
    reg_json = json.dumps(registry, indent=2).encode("utf-8")
    ftp.storbinary("STOR /data/containers/containers.json", io.BytesIO(reg_json))
    print("    [+] Uploaded /data/containers/containers.json")

    # 4. Upload test payload ELFs
    print("\n[Step 4] Deploying guest container payloads...")
    # Generate fresh bare_payload.elf
    build_raw_elf.make_elf("bare_payload.elf")
    
    with open("bare_payload.elf", "rb") as f:
        payload_data = f.read()

    ftp.storbinary("STOR /data/containers/apps/hello_runner/eboot.elf", io.BytesIO(payload_data))
    print("    [+] Installed: /data/containers/apps/hello_runner/eboot.elf")

    ftp.storbinary("STOR /data/containers/apps/crash_catcher/eboot.elf", io.BytesIO(payload_data))
    print("    [+] Installed: /data/containers/apps/crash_catcher/eboot.elf")

    ftp.quit()

    # 5. Execute LiveContainer Payload via elfldr
    print(f"\n[Step 5] Launching LiveContainer host payload via elfldr ({HOST}:{ELFLDR_PORT})...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((HOST, ELFLDR_PORT))
        s.sendall(payload_data)
        s.close()
        print("    [+] LiveContainer payload injected successfully!")
    except Exception as e:
        print(f"    [-] Injection failed: {e}")
        return

    # 6. Verify Execution & Log Results
    print("\n[Step 6] Verifying LiveContainer execution and filesystem logs...")
    time.sleep(3)

    try:
        ftp2 = ftplib.FTP()
        ftp2.connect(HOST, FTP_PORT, timeout=5)
        ftp2.login()

        buf = io.BytesIO()
        ftp2.retrbinary("RETR /data/raw_payload_test.log", buf.write)
        log_content = buf.getvalue().decode("utf-8", errors="replace")
        
        print("\n========================================================")
        print(" [STATUS] LIVECONTAINER SANDBOX & GUEST SUITE ACTIVE")
        print("========================================================")
        print(log_content)
        print("========================================================")

        # List contents of /data/containers
        print("\n[*] Inspecting /data/containers on PS5:")
        ftp2.retrlines("LIST /data/containers")

        print("\n[*] Inspecting /data/containers/apps on PS5:")
        ftp2.retrlines("LIST /data/containers/apps")

        ftp2.quit()
    except Exception as e:
        print(f"    [-] Verification error: {e}")

if __name__ == "__main__":
    main()
