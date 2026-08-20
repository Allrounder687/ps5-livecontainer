#!/usr/bin/env python3
import sys
import socket
import argparse
import os

def send_payload(host, port, payload_path):
    if not os.path.exists(payload_path):
        print(f"[-] Error: Payload '{payload_path}' not found!")
        sys.exit(1)

    print(f"[*] Reading payload: {payload_path} ({os.path.getsize(payload_path)} bytes)...")
    with open(payload_path, "rb") as f:
        data = f.read()

    print(f"[*] Connecting to PS5 at {host}:{port}...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        print(f"[*] Sending payload ({len(data)} bytes)...")
        s.sendall(data)
        s.close()
        print("[+] Payload successfully sent! Check your PS5 screen.")
    except Exception as e:
        print(f"[-] Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send ELF payload to PS5")
    parser.add_argument("--host", default="192.168.1.50", help="PS5 IP Address")
    parser.add_argument("--port", type=int, default=9021, help="PS5 ELF Loader Port (default: 9021)")
    parser.add_argument("--file", default="ps5_livecontainer.elf", help="Path to ELF binary")
    args = parser.parse_args()

    send_payload(args.host, args.port, args.file)
