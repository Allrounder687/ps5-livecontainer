#include "http_server.h"
#include "web_ui_assets.h"
#include "elf_loader.h"
#include "signal_guard.h"
#include "vfs_sandbox.h"
#include "ps5_notify.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <errno.h>

static pthread_t g_http_thread;
static pthread_t g_runner_thread;
static int g_target_slot_index = -1;

static void *container_worker_thread(void *arg) {
    int idx = (int)(intptr_t)arg;
    if (idx < 0 || idx >= g_container_ctx.slot_count) return NULL;

    container_slot_t *slot = &g_container_ctx.slots[idx];
    elf_loaded_image_t image;
    memset(&image, 0, sizeof(image));

    ps5_notify("🚀 LiveContainer: Launching %s", slot->name);
    lc_log("[LiveContainer Runner] Loading ELF image from '%s'...", slot->elf_path);

    if (elf_loader_load_file(slot->elf_path, &image) != 0) {
        slot->state = CONTAINER_STATE_ERROR;
        ps5_notify("❌ LiveContainer: Failed to load %s", slot->name);
        return NULL;
    }

    slot->mapped_base = image.image_base;
    slot->mapped_size = image.image_size;

    char *argv[] = { slot->name, NULL };
    signal_guard_run_safely(slot, image.entry_point, 1, argv);

    elf_loader_unload(&image);
    slot->mapped_base = NULL;
    slot->mapped_size = 0;

    if (slot->state == CONTAINER_STATE_CRASHED) {
        ps5_notify("🛡️ LiveContainer: Container '%s' safely terminated after crash.", slot->name);
    } else {
        ps5_notify("✅ LiveContainer: %s finished execution.", slot->name);
    }

    return NULL;
}

static void send_http_response(int fd, int status_code, const char *content_type, const char *body, size_t body_len) {
    char header[512];
    int header_len = snprintf(header, sizeof(header),
        "HTTP/1.1 %d OK\r\n"
        "Content-Type: %s\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "\r\n",
        status_code, content_type, body_len);
    
    send(fd, header, header_len, 0);
    if (body && body_len > 0) {
        send(fd, body, body_len, 0);
    }
}

void http_server_handle_client(int client_fd) {
    char buffer[4096];
    ssize_t bytes = recv(client_fd, buffer, sizeof(buffer) - 1, 0);
    if (bytes <= 0) {
        close(client_fd);
        return;
    }
    buffer[bytes] = '\0';

    if (strncmp(buffer, "GET / ", 6) == 0 || strncmp(buffer, "GET /index.html", 15) == 0) {
        send_http_response(client_fd, 200, "text/html", INDEX_HTML, strlen(INDEX_HTML));
    } else if (strncmp(buffer, "GET /api/logs", 13) == 0) {
        send_http_response(client_fd, 200, "text/plain", g_container_ctx.log_buffer, g_container_ctx.log_length);
    } else if (strncmp(buffer, "GET /api/containers", 19) == 0) {
        char json[4096];
        int pos = snprintf(json, sizeof(json), "{\"version\":\"%s\",\"slots\":[", LIVECONTAINER_VERSION);
        for (int i = 0; i < g_container_ctx.slot_count; i++) {
            container_slot_t *s = &g_container_ctx.slots[i];
            const char *state_str = "IDLE";
            if (s->state == CONTAINER_STATE_RUNNING) state_str = "RUNNING";
            else if (s->state == CONTAINER_STATE_CRASHED) state_str = "CRASHED";
            else if (s->state == CONTAINER_STATE_ERROR) state_str = "ERROR";

            pos += snprintf(json + pos, sizeof(json) - pos,
                "{\"id\":\"%s\",\"name\":\"%s\",\"description\":\"%s\",\"state\":\"%s\"}%s",
                s->id, s->name, s->description, state_str,
                (i == g_container_ctx.slot_count - 1) ? "" : ",");
        }
        snprintf(json + pos, sizeof(json) - pos, "]}");
        send_http_response(client_fd, 200, "application/json", json, strlen(json));
    } else if (strncmp(buffer, "POST /api/launch", 16) == 0) {
        char *id_param = strstr(buffer, "id=");
        if (id_param) {
            id_param += 3;
            char target_id[64] = {0};
            int i = 0;
            while (id_param[i] && id_param[i] != ' ' && id_param[i] != '&' && id_param[i] != '\r' && i < 63) {
                target_id[i] = id_param[i];
                i++;
            }
            target_id[i] = '\0';

            for (int s = 0; s < g_container_ctx.slot_count; s++) {
                if (strcmp(g_container_ctx.slots[s].id, target_id) == 0) {
                    g_target_slot_index = s;
                    pthread_create(&g_runner_thread, NULL, container_worker_thread, (void *)(intptr_t)s);
                    break;
                }
            }
        }
        send_http_response(client_fd, 200, "application/json", "{\"status\":\"launched\"}", 21);
    } else if (strncmp(buffer, "POST /api/stop", 14) == 0) {
        lc_log("[HTTP Server] Stop container requested");
        send_http_response(client_fd, 200, "application/json", "{\"status\":\"stopped\"}", 20);
    } else {
        send_http_response(client_fd, 404, "text/plain", "Not Found", 9);
    }

    close(client_fd);
}

static void *http_server_daemon_thread(void *arg) {
    int port = (int)(intptr_t)arg;

    signal(SIGPIPE, SIG_IGN);

    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        lc_log("[HTTP Server] Failed to create socket (errno: %d, %s)", errno, strerror(errno));
        return NULL;
    }

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);

    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        lc_log("[HTTP Server] Failed to bind to port %d", port);
        close(server_fd);
        return NULL;
    }

    if (listen(server_fd, 8) < 0) {
        lc_log("[HTTP Server] Failed to listen on port %d", port);
        close(server_fd);
        return NULL;
    }

    g_container_ctx.is_server_running = true;
    g_container_ctx.server_socket = server_fd;
    lc_log("[HTTP Server] Web Dashboard listening at http://<PS5_IP>:%d", port);
    ps5_notify("🌐 LiveContainer Dashboard online at port %d", port);

    while (g_container_ctx.is_server_running) {
        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);
        int client_fd = accept(server_fd, (struct sockaddr *)&client_addr, &client_len);
        if (client_fd >= 0) {
            http_server_handle_client(client_fd);
        }
    }

    close(server_fd);
    return NULL;
}

int http_server_start(int port) {
    int ret = pthread_create(&g_http_thread, NULL, http_server_daemon_thread, (void *)(intptr_t)port);
    lc_log("[HTTP Server] pthread_create returned: %d", ret);
    return ret;
}

void http_server_stop(void) {
    g_container_ctx.is_server_running = false;
    if (g_container_ctx.server_socket >= 0) {
        close(g_container_ctx.server_socket);
        g_container_ctx.server_socket = -1;
    }
}
