#include <stdio.h>
#include <string.h>
#include <unistd.h>

typedef struct notify_request {
    char useless1[45];
    char message[3075];
} notify_request_t;

int sceKernelSendNotificationRequest(int device, notify_request_t *req, size_t size, int blocking);

int main(int argc, char **argv) {
    notify_request_t req;
    bzero(&req, sizeof(req));

    if (argc > 1) {
        strncpy(req.message, argv[1], sizeof(req.message) - 1);
    } else {
        strncpy(req.message, "🎮 PS5 LiveContainer Notification Helper Active!", sizeof(req.message) - 1);
    }

    sceKernelSendNotificationRequest(0, &req, sizeof(req), 0);
    
    /* CRITICAL: Keep process alive for 3 seconds so the PS5 Notification Daemon processes the IPC */
    sleep(3);
    return 0;
}
