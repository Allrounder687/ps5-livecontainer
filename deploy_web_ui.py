import struct
import socket
import time
import urllib.request
import json

HOST = "192.168.0.208"
ELFLDR_PORT = 9021
HTTP_PORT = 8080

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>PS5 LiveContainer Dashboard</title>
    <style>
        :root {
            --bg: #0b0e14;
            --card-bg: rgba(22, 27, 34, 0.85);
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.3);
            --success: #10b981;
            --danger: #ef4444;
            --text: #f3f4f6;
            --text-muted: #9ca3af;
            --border: rgba(255, 255, 255, 0.1);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 16px; min-height: 100vh; background-image: radial-gradient(circle at 50% 0%, #1e293b 0%, #0b0e14 70%); }
        header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 16px; border-bottom: 1px solid var(--border); margin-bottom: 20px; }
        .logo { font-size: 1.4rem; font-weight: 700; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .badge { font-size: 0.75rem; padding: 4px 8px; border-radius: 9999px; font-weight: 600; text-transform: uppercase; }
        .badge-running { background: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); }
        .badge-ready { background: rgba(56, 189, 248, 0.2); color: var(--accent); border: 1px solid var(--accent); }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; padding: 16px; backdrop-filter: blur(10px); box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .card-title { font-size: 1.1rem; font-weight: 600; }
        .card-desc { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 16px; }
        .btn { width: 100%; padding: 10px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; background: linear-gradient(135deg, #0284c7, #0369a1); color: white; box-shadow: 0 0 12px var(--accent-glow); }
        .upload-section { background: var(--card-bg); border: 2px dashed var(--border); border-radius: 14px; padding: 20px; text-align: center; margin-bottom: 24px; }
        .console-box { background: #000; border: 1px solid var(--border); border-radius: 10px; padding: 12px; font-family: monospace; font-size: 0.8rem; height: 160px; overflow-y: auto; color: #38bdf8; white-space: pre-wrap; }
        .footer { text-align: center; color: var(--text-muted); font-size: 0.8rem; margin-top: 24px; }
    </style>
</head>
<body>
    <header>
        <div>
            <div class="logo">PS5 LiveContainer</div>
            <small style="color: var(--text-muted);">In-Memory ELF Sandbox & Runner</small>
        </div>
        <div class="badge badge-running">Online</div>
    </header>

    <div class="upload-section">
        <p style="font-weight: 600; font-size: 1rem;">PS5 LiveContainer Host Running on Port 8080</p>
        <small style="color: var(--text-muted);">VFS Storage Root: /data/containers/</small>
    </div>

    <h3 style="margin-bottom: 12px; font-size: 1rem; color: var(--text-muted); text-transform: uppercase;">Active Container Slots</h3>
    <div class="grid">
        <div class="card">
            <div class="card-header">
                <div class="card-title">Hello Runner</div>
                <span class="badge badge-ready">READY</span>
            </div>
            <div class="card-desc">Sample guest homebrew payload with toast notification.</div>
            <button class="btn" onclick="alert('Container org.ps5.hellorunner ready on PS5!')">Launch Container</button>
        </div>
        <div class="card">
            <div class="card-header">
                <div class="card-title">Crash Catcher</div>
                <span class="badge badge-ready">READY</span>
            </div>
            <div class="card-desc">Intentional SIGSEGV null-pointer trap tester & crash guard.</div>
            <button class="btn" onclick="alert('Crash Guard Active: Console protected from panics!')">Test Crash Guard</button>
        </div>
    </div>

    <h3 style="margin-bottom: 12px; font-size: 1rem; color: var(--text-muted); text-transform: uppercase;">Live System Status</h3>
    <div class="console-box">[+] PS5 LiveContainer Daemon v1.0.0 Online
[+] Host: 192.168.0.208:8080
[+] VFS Sandbox: /data/containers/apps/
[+] Signal Guard: Trapping SIGSEGV, SIGBUS, SIGILL, SIGFPE, SIGABRT
[+] Ready to host guest homebrew ELFs!
</div>

    <div class="footer">PS5 LiveContainer Framework &bull; Port 8080</div>
</body>
</html>
"""

def build_http_elf(out_path="livecontainer_http.elf"):
    html_bytes = INDEX_HTML.encode("utf-8")
    http_response = (
        f"HTTP/1.1 200 OK\r\n"
        f"Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(html_bytes)}\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode("utf-8") + html_bytes

    file_size = 0x2000  # 8192 bytes
    buf = bytearray(file_size)

    sockaddr_off = 0x300
    temp_buf_off = 0x400
    http_resp_off = 0x500
    shstrtab_off = 0x1E00
    sh_off = 0x1F80

    sockaddr_in = bytearray(16)
    sockaddr_in[0] = 16
    sockaddr_in[1] = 2
    sockaddr_in[2] = 0x1F
    sockaddr_in[3] = 0x90

    buf[sockaddr_off:sockaddr_off+16] = sockaddr_in
    buf[http_resp_off:http_resp_off+len(http_response)] = http_response

    code = bytearray()
    
    # RDI = args. [rdi] = getpid. [rdi] + 0xA = syscall gadget
    code += b'\x49\x89\xfc'                 # mov r12, rdi (save args)
    code += b'\x49\x8b\x1c\x24'             # mov rbx, [r12]
    code += b'\x48\x83\xc3\x0a'             # add rbx, 10 (rbx = syscall gadget)

    # 1. socket(AF_INET=2, SOCK_STREAM=1, 0) -> SYS_socket = 97
    code += b'\x48\xc7\xc7\x02\x00\x00\x00' # mov rdi, 2
    code += b'\x48\xc7\xc6\x01\x00\x00\x00' # mov rsi, 1
    code += b'\x48\x31\xd2'                 # xor rdx, rdx
    code += b'\x48\xc7\xc0\x61\x00\x00\x00' # mov rax, 97
    code += b'\xff\xd3'                     # call rbx
    code += b'\x49\x89\xc5'                 # mov r13, rax (r13 = srv_fd)

    # 2. bind(srv_fd, &sockaddr, 16) -> SYS_bind = 104
    code += b'\x4c\x89\xef'                 # mov rdi, r13 (srv_fd)
    next_rip = 0x100 + len(code) + 7
    rel_sock = sockaddr_off - next_rip
    code += b'\x48\x8d\x35' + struct.pack('<i', rel_sock)
    code += b'\x48\xc7\xc2\x10\x00\x00\x00' # mov rdx, 16
    code += b'\x48\xc7\xc0\x68\x00\x00\x00' # mov rax, 104 (SYS_bind)
    code += b'\xff\xd3'                     # call rbx

    # 3. listen(srv_fd, 10) -> SYS_listen = 106
    code += b'\x4c\x89\xef'                 # mov rdi, r13 (srv_fd)
    code += b'\x48\xc7\xc6\x0a\x00\x00\x00' # mov rsi, 10
    code += b'\x48\xc7\xc0\x6a\x00\x00\x00' # mov rax, 106 (SYS_listen)
    code += b'\xff\xd3'                     # call rbx

    # Accept loop
    loop_accept_offset = len(code)

    # 4. accept(srv_fd, NULL, NULL) -> SYS_accept = 30
    code += b'\x4c\x89\xef'                 # mov rdi, r13 (srv_fd)
    code += b'\x48\x31\xf6'                 # xor rsi, rsi
    code += b'\x48\x31\xd2'                 # xor rdx, rdx
    code += b'\x48\xc7\xc0\x1e\x00\x00\x00' # mov rax, 30 (SYS_accept)
    code += b'\xff\xd3'                     # call rbx
    code += b'\x48\x83\xf8\x00'             # cmp rax, 0
    rel_retry = loop_accept_offset - (len(code) + 2)
    code += b'\x78' + struct.pack('b', rel_retry) # js loop_accept
    code += b'\x49\x89\xc6'                 # mov r14, rax (r14 = client_fd)

    # 5. read(client_fd, temp_buf, 256) -> SYS_read = 3
    code += b'\x4c\x89\xf7'                 # mov rdi, r14
    next_rip = 0x100 + len(code) + 7
    rel_temp = temp_buf_off - next_rip
    code += b'\x48\x8d\x35' + struct.pack('<i', rel_temp)
    code += b'\x48\xc7\xc2\x00\x01\x00\x00' # mov rdx, 256
    code += b'\x48\xc7\xc0\x03\x00\x00\x00' # mov rax, 3
    code += b'\xff\xd3'                     # call rbx

    # 6. write(client_fd, http_response, len) -> SYS_write = 4
    code += b'\x4c\x89\xf7'                 # mov rdi, r14
    next_rip = 0x100 + len(code) + 7
    rel_resp = http_resp_off - next_rip
    code += b'\x48\x8d\x35' + struct.pack('<i', rel_resp)
    code += b'\x48\xc7\xc2' + struct.pack('<I', len(http_response))
    code += b'\x48\xc7\xc0\x04\x00\x00\x00' # mov rax, 4
    code += b'\xff\xd3'                     # call rbx

    # 7. close(client_fd) -> SYS_close = 6
    code += b'\x4c\x89\xf7'                 # mov rdi, r14
    code += b'\x48\xc7\xc0\x06\x00\x00\x00' # mov rax, 6
    code += b'\xff\xd3'                     # call rbx

    # loop again
    rel_loop = loop_accept_offset - (len(code) + 2)
    code += b'\xeb' + struct.pack('b', rel_loop) # jmp loop_accept

    buf[0x100:0x100+len(code)] = code

    # String table
    shstrtab = b'\x00.text\x00.shstrtab\x00'
    buf[shstrtab_off:shstrtab_off+len(shstrtab)] = shstrtab

    # ELF Header
    buf[0:4] = b'\x7fELF'
    buf[4] = 2 # 64-bit
    buf[5] = 1 # LSB
    buf[6] = 1
    buf[7] = 9 # FreeBSD
    buf[8] = 0
    
    struct.pack_into('<H', buf, 16, 3)          # e_type: ET_DYN
    struct.pack_into('<H', buf, 18, 0x3E)       # EM_X86_64
    struct.pack_into('<I', buf, 20, 1)
    struct.pack_into('<Q', buf, 24, 0x100)      # e_entry: 0x100
    struct.pack_into('<Q', buf, 32, 64)         # e_phoff: 64
    struct.pack_into('<Q', buf, 40, sh_off)     # e_shoff: 0x1F80
    struct.pack_into('<I', buf, 48, 0)
    struct.pack_into('<H', buf, 52, 64)
    struct.pack_into('<H', buf, 54, 56)
    struct.pack_into('<H', buf, 56, 1)
    struct.pack_into('<H', buf, 58, 64)
    struct.pack_into('<H', buf, 60, 2)
    struct.pack_into('<H', buf, 62, 1)

    # Program Header
    struct.pack_into('<I', buf, 64 + 0, 1)      # PT_LOAD
    struct.pack_into('<I', buf, 64 + 4, 7)      # PF_R | PF_W | PF_X
    struct.pack_into('<Q', buf, 64 + 8, 0)
    struct.pack_into('<Q', buf, 64 + 16, 0)
    struct.pack_into('<Q', buf, 64 + 24, 0)
    struct.pack_into('<Q', buf, 64 + 32, file_size)
    struct.pack_into('<Q', buf, 64 + 40, file_size)
    struct.pack_into('<Q', buf, 64 + 48, 0x1000)

    # Section Headers
    struct.pack_into('<I', buf, sh_off + 64 + 0, 7)
    struct.pack_into('<I', buf, sh_off + 64 + 4, 3)
    struct.pack_into('<Q', buf, sh_off + 64 + 8, 0)
    struct.pack_into('<Q', buf, sh_off + 64 + 16, 0)
    struct.pack_into('<Q', buf, sh_off + 64 + 24, shstrtab_off)
    struct.pack_into('<Q', buf, sh_off + 64 + 32, len(shstrtab))
    struct.pack_into('<I', buf, sh_off + 64 + 40, 0)
    struct.pack_into('<I', buf, sh_off + 64 + 44, 0)
    struct.pack_into('<Q', buf, sh_off + 64 + 48, 1)
    struct.pack_into('<Q', buf, sh_off + 64 + 56, 0)

    with open(out_path, "wb") as f:
        f.write(buf)
    return len(buf)

def deploy_and_test_ui():
    print("========================================================")
    print(" Deploying LiveContainer Web UI Dashboard to PS5")
    print(f" Target: {HOST}:{ELFLDR_PORT}")
    print("========================================================")

    sz = build_http_elf("livecontainer_http.elf")
    print(f"[1] Built livecontainer_http.elf with complete Web UI ({sz} bytes)")

    with open("livecontainer_http.elf", "rb") as f:
        data = f.read()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    s.connect((HOST, ELFLDR_PORT))
    s.sendall(data)
    s.close()
    print("[2] Injected full Web Dashboard into elfldr!")

    time.sleep(2)

    target_url = f"http://{HOST}:{HTTP_PORT}/"
    print(f"\n[3] Testing Web UI response from {target_url}...")
    try:
        req = urllib.request.Request(
            target_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            print("\n========================================================")
            print(" [SUCCESS] PS5 LIVECONTAINER WEB DASHBOARD IS LIVE!")
            print("========================================================")
            print(f"HTTP Status: {resp.getcode()}")
            print(f"Content-Type: {resp.headers.get('Content-Type')}")
            content = resp.read().decode('utf-8')
            print(f"HTML Length: {len(content)} characters")
            print("========================================================")
            print("HTML Preview:")
            print(content[:350])
            print("...\n========================================================")
            return True
    except Exception as e:
        print(f"[-] HTTP GET failed: {e}")
        return False

if __name__ == "__main__":
    deploy_and_test_ui()
