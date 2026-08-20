#ifndef PS5_NOTIFY_H
#define PS5_NOTIFY_H

#include <stddef.h>

typedef struct notify_request {
    char useless1[45];
    char message[3075];
} notify_request_t;

#ifdef __cplusplus
extern "C" {
#endif

int sceKernelSendNotificationRequest(int device, notify_request_t *req, size_t size, int blocking);
void ps5_notify(const char *fmt, ...);

#ifdef __cplusplus
}
#endif

#endif /* PS5_NOTIFY_H */
