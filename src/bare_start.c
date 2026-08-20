#include <unistd.h>
#include <fcntl.h>

// Direct entry point invoked by elfldr
// elfldr sets RIP to ehdr.e_entry and passes payload_args in RDI
void _start(void *args) {
    (void)args;

    // Use direct FreeBSD/PS5 syscalls
    // syscall 5 is sys_open(path, flags, mode)
    // syscall 4 is sys_write(fd, buf, nbytes)
    // syscall 6 is sys_close(fd)
    
    // We can do direct inline asm syscalls on FreeBSD/PS5 x86_64:
    // PS5 syscall convention: RAX = syscall_num, RDI = arg1, RSI = arg2, RDX = arg3, R10 = arg4, R8 = arg5, R9 = arg6
    
    const char path[] = "/data/raw_payload_test.log";
    const char msg[] = "====================================\n"
                       "[+] DIRECT _START EXECUTION SUCCESS!\n"
                       "[+] Bypassed SDK crt1.o completely!\n"
                       "====================================\n";
    
    long fd = -1;
    
    // sys_open("/data/raw_payload_test.log", O_CREAT|O_WRONLY|O_TRUNC = 0x601, 0777)
    // In FreeBSD: O_CREAT=0x0200, O_WRONLY=0x0001, O_TRUNC=0x0400 -> 0x0601
    asm volatile(
        "mov $5, %%rax\n"          // SYS_open = 5
        "mov %1, %%rdi\n"          // path
        "mov $0x601, %%rsi\n"      // O_CREAT | O_WRONLY | O_TRUNC
        "mov $0777, %%rdx\n"       // mode
        "syscall\n"
        "mov %%rax, %0\n"
        : "=r"(fd)
        : "r"(path)
        : "rax", "rdi", "rsi", "rdx", "rcx", "r11", "memory"
    );
    
    if (fd >= 0) {
        long written = 0;
        asm volatile(
            "mov $4, %%rax\n"      // SYS_write = 4
            "mov %1, %%rdi\n"      // fd
            "mov %2, %%rsi\n"      // buf
            "mov %3, %%rdx\n"      // len
            "syscall\n"
            "mov %%rax, %0\n"
            : "=r"(written)
            : "r"(fd), "r"(msg), "r"((long)sizeof(msg) - 1)
            : "rax", "rdi", "rsi", "rdx", "rcx", "r11", "memory"
        );
        
        asm volatile(
            "mov $6, %%rax\n"      // SYS_close = 6
            "mov %0, %%rdi\n"
            "syscall\n"
            :
            : "r"(fd)
            : "rax", "rdi", "rcx", "r11", "memory"
        );
    }
    
    // sys_nanosleep / pause or return
    // sys_exit(0) = 1
    asm volatile(
        "mov $1, %%rax\n"
        "xor %%rdi, %%rdi\n"
        "syscall\n"
        :
        :
        : "rax", "rdi", "rcx", "r11"
    );
}
