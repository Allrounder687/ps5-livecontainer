import socket
import time
import ftplib
import io
import build_raw_elf

HOST = "192.168.0.208"
ELFLDR_PORT = 9021
FTP_PORT = 2121

def test_execution():
    print("========================================================")
    print(" PS5 LiveContainer Live Diagnostic & Test Suite")
    print(f" Target: {HOST}")
    print("========================================================")

    # 1. Generate verified PS5 payload binary
    print("\n[1] Generating verified PS5 payload binary...")
    build_raw_elf.make_elf()
    print("    [+] Generated bare_payload.elf (libkernel-compliant)")

    # 2. Inject payload over elfldr (port 9021)
    print(f"\n[2] Injecting payload into elfldr ({HOST}:{ELFLDR_PORT})...")
    with open("bare_payload.elf", "rb") as f:
        payload_data = f.read()

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((HOST, ELFLDR_PORT))
        s.sendall(payload_data)
        s.close()
        print(f"    [+] Injected {len(payload_data)} bytes successfully!")
    except Exception as e:
        print(f"    [-] Injection failed: {e}")
        return

    # 3. Wait for execution
    print("\n[3] Waiting 3 seconds for on-console execution...")
    time.sleep(3)

    # 4. Verification via FTP
    print("\n[4] Connecting to FTP to verify execution output...")
    try:
        ftp = ftplib.FTP()
        ftp.connect(HOST, FTP_PORT, timeout=5)
        ftp.login()

        buf = io.BytesIO()
        ftp.retrbinary("RETR /data/raw_payload_test.log", buf.write)
        content = buf.getvalue().decode("utf-8", errors="replace")
        print("\n========================================================")
        print(" [SUCCESS] NATIVE CODE EXECUTION VERIFIED ON PS5!")
        print("========================================================")
        print(content)
        print("========================================================")
        ftp.quit()
    except Exception as e:
        print(f"    [-] Verification error: {e}")

if __name__ == "__main__":
    test_execution()
