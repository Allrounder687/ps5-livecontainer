#!/usr/bin/env python3
import os
import socket
import sys

def main():
    host = os.getenv("PS5_HOST", "192.168.0.208")
    port = int(os.getenv("PS5_ELFLDR_PORT", "9021"))
    payload_path = "ps5_livecontainer.elf"

    if not os.path.exists(payload_path):
        print(f"[-] Error: {payload_path} not found. Run 'make' first.")
        sys.exit(1)

    with open(payload_path, "rb") as f:
        payload_data = f.read()

    print("========================================================")
    print(f" Deploying PS5 LiveContainer Payload")
    print(f" Target: {host}:{port} (elfldr)")
    print(f" Payload: {payload_path} ({len(payload_data)} bytes)")
    print("========================================================")

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((host, port))
        print("[+] Connected to elfldr!")
        
        print("[*] Sending payload...")
        s.sendall(payload_data)
        s.close()
        print("[+] Payload injected successfully!")
    except ConnectionRefusedError:
        print(f"[-] Error: Connection refused on port {port}.")
        print("    Ensure etaHEN/jailbreak is active, and elfldr is bootstrapped (send elfldr to 9020 first).")
        sys.exit(1)
    except socket.timeout:
        print(f"[-] Error: Connection timed out.")
        sys.exit(1)
    except Exception as e:
        print(f"[-] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
