#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <ps5/kernel.h>

typedef struct notify_request {
    char useless1[45];
    char message[3075];
} notify_request_t;

int sceKernelSendNotificationRequest(int device, notify_request_t *req, size_t size, int blocking);

int main(void) {
    pid_t my_pid = getpid();

    // Try to break out of jail using PID 1's root/jail dirs
    intptr_t host_rootdir = kernel_get_proc_rootdir(1);
    intptr_t host_jaildir = kernel_get_proc_jaildir(1);

    if (host_rootdir) {
        kernel_set_proc_rootdir(my_pid, host_rootdir);
    }
    if (host_jaildir) {
        kernel_set_proc_jaildir(my_pid, host_jaildir);
    }

    // Try multiple paths for the log file
    const char *paths[] = {
        "/data/raw_payload_test.log",
        "/tmp/raw_payload_test.log",
        NULL
    };
    
    for (int i = 0; paths[i]; i++) {
        int fd = open(paths[i], O_CREAT | O_WRONLY | O_TRUNC, 0777);
        if (fd >= 0) {
            char msg[256];
            int len = snprintf(msg, sizeof(msg),
                "[+] PS5 LiveContainer Payload ALIVE!\n"
                "    PID: %d\n"
                "    host_rootdir: 0x%lx\n"
                "    host_jaildir: 0x%lx\n"
                "    Written to: %s\n",
                my_pid,
                (unsigned long)host_rootdir,
                (unsigned long)host_jaildir,
                paths[i]);
            write(fd, msg, len);
            close(fd);
        }
    }

    // Also stdout (connected to the TCP socket by elfldr)
    printf("[HelloContainer] PID=%d rootdir=0x%lx jaildir=0x%lx\n",
           my_pid, (unsigned long)host_rootdir, (unsigned long)host_jaildir);
    fflush(stdout);

    // Send a notification
    notify_request_t req;
    bzero(&req, sizeof(req));
    strncpy(req.message, "LiveContainer Payload Running!", sizeof(req.message) - 1);
    sceKernelSendNotificationRequest(0, &req, sizeof(req), 0);

    // Keep alive so notification processes 
    sleep(5);
    return 0;
}
