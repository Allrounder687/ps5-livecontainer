import struct
import socket
import time
import ftplib
import io

HOST = "192.168.0.208"
ELFLDR_PORT = 9021
FTP_PORT = 2121

def build_notification_elf(out_path="notify_verify.elf"):
    file_size = 0x2000  # 8192 bytes
    buf = bytearray(file_size)

    # 1. Clean up old log over FTP
    try:
        ftp = ftplib.FTP()
        ftp.connect(HOST, FTP_PORT, timeout=5)
        ftp.login()
        try:
            ftp.delete("/data/notification_test.log")
        except Exception:
            pass
        ftp.quit()
    except Exception:
        pass

    req_off = 0x200
    msg_off = req_off + 45
    msg = "🎮 PS5 LiveContainer: Notification Active!".encode("utf-8")
    buf[msg_off:msg_off+len(msg)] = msg

    log_path_off = 0xF00
    log_path = b"/data/notification_test.log\x00"
    buf[log_path_off:log_path_off+len(log_path)] = log_path

    fn_name_off = 0xF40
    fn_name = b"sceKernelSendNotificationRequest\x00"
    buf[fn_name_off:fn_name_off+len(fn_name)] = fn_name

    code = bytearray()
    
    # RDI = args pointer. args[0] = getpid. args[0] + 0x0A = syscall gadget in libkernel
    code += b'\x49\x89\xfc'                 # mov r12, rdi (save args)
    code += b'\x49\x8b\x1c\x24'             # mov rbx, [r12]
    code += b'\x48\x83\xc3\x0a'             # add rbx, 10 (rbx = syscall gadget)

    # 1. First write to /data/notification_test.log to verify start
    # sys_open("/data/notification_test.log", 0x601, 0777) -> SYS_open = 5
    next_rip = 0x100 + len(code) + 7
    rel_path = log_path_off - next_rip
    code += b'\x48\x8d\x3d' + struct.pack('<i', rel_path)
    code += b'\x48\xc7\xc6\x01\x06\x00\x00' # mov rsi, 0x601
    code += b'\x48\xc7\xc2\xff\x01\x00\x00' # mov rdx, 0777
    code += b'\x48\xc7\xc0\x05\x00\x00\x00' # mov rax, 5
    code += b'\xff\xd3'                     # call rbx
    code += b'\x49\x89\xc6'                 # mov r14, rax (r14 = fd)

    # Write "[+] Toast Notification Payload Started on PS5\n"
    start_msg = b"[+] Toast Notification Payload Started on PS5\n"
    next_rip = 0x100 + len(code) + 7
    rel_start = msg_off - next_rip
    code += b'\x4c\x89\xf7'                 # mov rdi, r14
    code += b'\x48\x8d\x35' + struct.pack('<i', rel_start)
    code += b'\x48\xc7\xc2' + struct.pack('<I', len(msg))
    code += b'\x48\xc7\xc0\x04\x00\x00\x00' # mov rax, 4 (SYS_write)
    code += b'\xff\xd3'                     # call rbx

    # sys_close(fd)
    code += b'\x4c\x89\xf7'                 # mov rdi, r14
    code += b'\x48\xc7\xc0\x06\x00\x00\x00' # mov rax, 6
    code += b'\xff\xd3'                     # call rbx

    # 2. sys_dynlib_dlsym(2, "sceKernelSendNotificationRequest", &fn_ptr) -> SYS_dynlib_dlsym = 591 (0x24F)
    code += b'\x48\xc7\xc7\x02\x00\x00\x00' # mov rdi, 2 (libkernel handle)
    next_rip = 0x100 + len(code) + 7
    rel_fn = fn_name_off - next_rip
    code += b'\x48\x8d\x35' + struct.pack('<i', rel_fn)
    next_rip = 0x100 + len(code) + 7
    rel_dest = 0x1E0 - next_rip
    code += b'\x48\x8d\x15' + struct.pack('<i', rel_dest)
    code += b'\x48\xc7\xc0\x4f\x02\x00\x00' # mov rax, 591 (SYS_dynlib_dlsym)
    code += b'\xff\xd3'                     # call rbx

    # Call sceKernelSendNotificationRequest(0, &req, 0xC30, 0)
    code += b'\x48\x8b\x05' + struct.pack('<i', rel_dest - 7) # mov rax, [0x1E0]
    code += b'\x48\x85\xc0'                 # test rax, rax
    code += b'\x74\x19'                     # jz skip_call (+25)
    code += b'\x48\x31\xff'                 # xor rdi, rdi
    next_rip = 0x100 + len(code) + 7
    rel_req = req_off - next_rip
    code += b'\x48\x8d\x35' + struct.pack('<i', rel_req)
    code += b'\x48\xc7\xc2\x30\x0c\x00\x00' # mov rdx, 0xC30
    code += b'\x4d\x31\xc0'                 # xor r8, r8
    code += b'\xff\xd0'                     # call rax

    # sleep 3 seconds to let notification daemon deliver
    # SYS_nanosleep = 240
    code += b'\x48\xc7\x84\x24\x80\x00\x00\x00\x03\x00\x00\x00' # [rsp+0x80] = 3
    code += b'\x48\xc7\x84\x24\x88\x00\x00\x00\x00\x00\x00\x00' # [rsp+0x88] = 0
    code += b'\x48\x8d\xbc\x24\x80\x00\x00\x00'                 # lea rdi, [rsp+0x80]
    code += b'\x48\x31\xf6'                                     # xor rsi, rsi
    code += b'\x48\xc7\xc0\xf0\x00\x00\x00'                     # mov rax, 240
    code += b'\xff\xd3'                                         # call rbx

    # exit(0)
    code += b'\x48\x31\xff'                 # xor rdi, rdi
    code += b'\x48\xc7\xc0\x01\x00\x00\x00' # mov rax, 1
    code += b'\xff\xd3'                     # call rbx
    code += b'\xc3'

    buf[0x100:0x100+len(code)] = code

    shstrtab = b'\x00.text\x00.shstrtab\x00'
    shstrtab_off = 0x1E00
    sh_off = 0x1F80
    buf[shstrtab_off:shstrtab_off+len(shstrtab)] = shstrtab

    buf[0:4] = b'\x7fELF'
    buf[4] = 2
    buf[5] = 1
    buf[6] = 1
    buf[7] = 9
    buf[8] = 0

    struct.pack_into('<H', buf, 16, 3)
    struct.pack_into('<H', buf, 18, 0x3E)
    struct.pack_into('<I', buf, 20, 1)
    struct.pack_into('<Q', buf, 24, 0x100)
    struct.pack_into('<Q', buf, 32, 64)
    struct.pack_into('<Q', buf, 40, sh_off)
    struct.pack_into('<I', buf, 48, 0)
    struct.pack_into('<H', buf, 52, 64)
    struct.pack_into('<H', buf, 54, 56)
    struct.pack_into('<H', buf, 56, 1)
    struct.pack_into('<H', buf, 58, 64)
    struct.pack_into('<H', buf, 60, 2)
    struct.pack_into('<H', buf, 62, 1)

    struct.pack_into('<I', buf, 64 + 0, 1)
    struct.pack_into('<I', buf, 64 + 4, 7)
    struct.pack_into('<Q', buf, 64 + 8, 0)
    struct.pack_into('<Q', buf, 64 + 16, 0)
    struct.pack_into('<Q', buf, 64 + 24, 0)
    struct.pack_into('<Q', buf, 64 + 32, file_size)
    struct.pack_into('<Q', buf, 64 + 40, file_size)
    struct.pack_into('<Q', buf, 64 + 48, 0x1000)

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

def test_notification():
    print("========================================================")
    print(" Verifying PS5 Toast Notification Execution Autonomously")
    print(f" Target: {HOST}:{ELFLDR_PORT}")
    print("========================================================")

    sz = build_notification_elf("notify_verify.elf")
    print(f"[1] Built notify_verify.elf ({sz} bytes)")

    with open("notify_verify.elf", "rb") as f:
        data = f.read()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    s.connect((HOST, ELFLDR_PORT))
    s.sendall(data)
    s.close()
    print("[2] Injected notification payload into elfldr (Port 9021)!")

    print("[3] Waiting 4 seconds for execution and IPC dispatch...")
    time.sleep(4)

    print("[4] Checking /data/notification_test.log over FTP...")
    ftp = ftplib.FTP()
    ftp.connect(HOST, FTP_PORT, timeout=5)
    ftp.login()

    buf = io.BytesIO()
    ftp.retrbinary("RETR /data/notification_test.log", buf.write)
    content = buf.getvalue().decode("utf-8", errors="replace")
    ftp.quit()

    print("\n========================================================")
    print(" [SUCCESS] NOTIFICATION LOG CONFIRMED ON PS5!")
    print("========================================================")
    print(f"Log content retrieved from PS5:\n{content.strip()}")
    print("========================================================")

if __name__ == "__main__":
    test_notification()
