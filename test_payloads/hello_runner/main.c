#include <stdio.h>
#include <string.h>
#include <unistd.h>

typedef struct notify_request {
    char useless1[45];
    char message[3075];
} notify_request_t;

int sceKernelSendNotificationRequest(int device, notify_request_t *req, size_t size, int blocking);

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    printf("[HelloContainer] Running inside isolated LiveContainer sandbox!\n");
    
    notify_request_t req;
    bzero(&req, sizeof(req));
    strncpy(req.message, "🎉 Hello from LiveContainer Guest Payload!", sizeof(req.message) - 1);
    sceKernelSendNotificationRequest(0, &req, sizeof(req), 0);

    sleep(2);
    printf("[HelloContainer] Exiting normally.\n");
    return 0;
}
