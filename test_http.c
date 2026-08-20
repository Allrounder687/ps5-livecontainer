#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <pthread.h>

typedef struct notify_request {
    char useless1[45];
    char message[3075];
} notify_request_t;
int sceKernelSendNotificationRequest(int device, notify_request_t *req, size_t size, int blocking);

void notify(const char *msg) {
    notify_request_t req;
    bzero(&req, sizeof(req));
    strncpy(req.message, msg, sizeof(req.message) - 1);
    sceKernelSendNotificationRequest(0, &req, sizeof(req), 0);
}

int main() {
    notify("Test HTTP Server Starting on 8080...");
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        notify("Socket create failed!");
        return 1;
    }
    int opt = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    struct sockaddr_in addr;
    bzero(&addr, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(8080);
    if (bind(fd, (struct sockaddr*)&addr, sizeof(addr)) != 0) {
        notify("Bind to 8080 failed!");
        close(fd);
        return 1;
    }
    listen(fd, 5);
    notify("HTTP Server Listening on 8080!");
    while(1) {
        int client = accept(fd, NULL, NULL);
        if (client >= 0) {
            char resp[] = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 13\r\n\r\nHello PS5 8080";
            write(client, resp, sizeof(resp) - 1);
            close(client);
        }
    }
    return 0;
}
