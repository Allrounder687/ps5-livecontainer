#include "ps5_notify.h"
#include "container_types.h"
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <unistd.h>

void ps5_notify(const char *fmt, ...) {
    notify_request_t req;
    bzero(&req, sizeof(req));
    
    va_list args;
    va_start(args, fmt);
    vsnprintf(req.message, sizeof(req.message) - 1, fmt, args);
    va_end(args);

    /* Output to log file & console */
    lc_log("[PS5 Notification] %s", req.message);

    /* Dispatch to PS5 notification daemon */
    int res = sceKernelSendNotificationRequest(0, &req, sizeof(req), 0);
    lc_log("[PS5 Notification] sceKernelSendNotificationRequest result: %d", res);
}
