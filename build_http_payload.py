import struct
import socket
import time
import ftplib
import io
import urllib.request

HOST = "192.168.0.208"
ELFLDR_PORT = 9021
FTP_PORT = 2121
HTTP_PORT = 8080

def build_diagnostic_http_elf(out_path="livecontainer_http.elf"):
    response_body = (
        '{"status":"ONLINE","service":"PS5 LiveContainer Framework",'
        '"version":"1.0.0","slots":[{"id":"org.ps5.hellorunner","name":"Hello Runner","state":"READY"},'
        '{"id":"org.ps5.crashcatcher","name":"Crash Catcher","state":"READY"}]}\n'
    )

    http_response = (
        f"HTTP/1.1 200 OK\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(response_body.encode('utf-8'))}\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"Connection: close\r\n"
        f"\r\n"
        f"{response_body}"
    ).encode("utf-8")

    file_size = 0x2000  # 8192 bytes
    buf = bytearray(file_size)

    sockaddr_off = 0x300
    http_resp_off = 0x800
    temp_buf_off = 0x500
    log_path_off = 0x700
    shstrtab_off = 0x1E00
    sh_off = 0x1F80

    # sockaddr_in on FreeBSD:
    # byte 0: sin_len = 16
    # byte 1: sin_family = AF_INET (2)
    # byte 2-3: sin_port = htons(8080) -> 0x1F, 0x90
    # byte 4-7: sin_addr = INADDR_ANY (0)
    # byte 8-15: sin_zero = 0
    sockaddr_in = bytearray(16)
    sockaddr_in[0] = 16
    sockaddr_in[1] = 2
    sockaddr_in[2] = 0x1F
    sockaddr_in[3] = 0x90

    log_path = b"/data/http_debug.log\x00"

    buf[sockaddr_off:sockaddr_off+16] = sockaddr_in
    buf[http_resp_off:http_resp_off+len(http_response)] = http_response
    buf[log_path_off:log_path_off+len(log_path)] = log_path

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

    # Log successful start to /data/http_debug.log
    # sys_open(log_path, O_CREAT|O_WRONLY|O_TRUNC = 0x601, 0777)
    next_rip = 0x100 + len(code) + 7
    rel_log = log_path_off - next_rip
    code += b'\x48\x8d\x3d' + struct.pack('<i', rel_log)
    code += b'\x48\xc7\xc6\x01\x06\x00\x00' # mov rsi, 0x601
    code += b'\x48\xc7\xc2\xff\x01\x00\x00' # mov rdx, 01777
    code += b'\x48\xc7\xc0\x05\x00\x00\x00' # mov rax, 5
    code += b'\xff\xd3'                     # call rbx
    # r15 = log_fd
    code += b'\x49\x89\xc7'                 # mov r15, rax

    log_msg = b"HTTP Server Listening on 8080!\n"
    buf[0x750:0x750+len(log_msg)] = log_msg
    # sys_write(log_fd, log_msg, len)
    code += b'\x4c\x89\xff'                 # mov rdi, r15
    next_rip = 0x100 + len(code) + 7
    rel_msg = 0x750 - next_rip
    code += b'\x48\x8d\x35' + struct.pack('<i', rel_msg)
    code += b'\x48\xc7\xc2' + struct.pack('<I', len(log_msg))
    code += b'\x48\xc7\xc0\x04\x00\x00\x00' # mov rax, 4
    code += b'\xff\xd3'                     # call rbx

    # sys_close(log_fd)
    code += b'\x4c\x89\xff'                 # mov rdi, r15
    code += b'\x48\xc7\xc0\x06\x00\x00\x00' # mov rax, 6
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
    code += b'\x78' + struct.pack('b', rel_retry) # js loop_accept (if error retry)
    code += b'\x49\x89\xc6'                 # mov r14, rax (r14 = client_fd)

    # 5. read(client_fd, temp_buf, 1024) -> SYS_read = 3
    code += b'\x4c\x89\xf7'                 # mov rdi, r14
    next_rip = 0x100 + len(code) + 7
    rel_temp = temp_buf_off - next_rip
    code += b'\x48\x8d\x35' + struct.pack('<i', rel_temp)
    code += b'\x48\xc7\xc2\x00\x04\x00\x00' # mov rdx, 1024
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

def deploy_and_verify():
    print("========================================================")
    print(" Deploying LiveContainer HTTP Server to PS5")
    print(f" Target: {HOST}:{ELFLDR_PORT}")
    print("========================================================")

    # 1. Clean previous debug log
    try:
        ftp = ftplib.FTP()
        ftp.connect(HOST, FTP_PORT, timeout=5)
        ftp.login()
        try:
            ftp.delete("/data/http_debug.log")
        except:
            pass
        ftp.quit()
    except Exception as e:
        print(f"[-] FTP clean error: {e}")

    # 2. Build and inject
    sz = build_diagnostic_http_elf("livecontainer_http.elf")
    print(f"[1] Built livecontainer_http.elf ({sz} bytes)")

    with open("livecontainer_http.elf", "rb") as f:
        data = f.read()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    s.connect((HOST, ELFLDR_PORT))
    s.sendall(data)
    s.close()
    print("[2] Injected HTTP daemon into elfldr!")

    # 3. Wait and check debug log
    time.sleep(2)
    print("[3] Checking /data/http_debug.log over FTP...")
    try:
        ftp2 = ftplib.FTP()
        ftp2.connect(HOST, FTP_PORT, timeout=5)
        ftp2.login()
        buf = io.BytesIO()
        ftp2.retrbinary("RETR /data/http_debug.log", buf.write)
        print(f"[+] Debug log: {buf.getvalue().decode('utf-8', errors='replace').strip()}")
        ftp2.quit()
    except Exception as e:
        print(f"[-] Debug log check: {e}")

    # 4. Perform HTTP GET
    target_url = f"http://{HOST}:{HTTP_PORT}/api/containers"
    print(f"\n[4] Sending HTTP GET to {target_url}...")
    try:
        req = urllib.request.Request(
            target_url,
            headers={"User-Agent": "PS5-LiveContainer-Tester/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            print("\n========================================================")
            print(" [SUCCESS] HTTP SERVER RESPONDED TO GET REQUEST!")
            print("========================================================")
            print(f"Status Code: {resp.getcode()}")
            print(f"Response:\n{resp.read().decode('utf-8')}")
            print("========================================================")
            return True
    except Exception as e:
        print(f"[-] HTTP GET failed: {e}")
        return False

if __name__ == "__main__":
    deploy_and_verify()
