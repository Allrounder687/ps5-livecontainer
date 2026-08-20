#include "container_types.h"
#include "elf_loader.h"
#include "signal_guard.h"
#include "vfs_sandbox.h"
#include "http_server.h"
#include "ps5_notify.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
#include <ps5/kernel.h>

/* Global LiveContainer Context */
livecontainer_ctx_t g_container_ctx;

void lc_log(const char *fmt, ...) {
    char buf[1024];
    va_list args;
    va_start(args, fmt);
    int len = vsnprintf(buf, sizeof(buf) - 1, fmt, args);
    va_end(args);

    if (len <= 0) return;

    /* Print to console/stdout */
    printf("%s\n", buf);
    fflush(stdout);

    /* Append to in-memory log buffer for Web UI streaming */
    if (g_container_ctx.log_length + len + 2 < LIVECONTAINER_MAX_LOG_SIZE) {
        memcpy(g_container_ctx.log_buffer + g_container_ctx.log_length, buf, len);
        g_container_ctx.log_length += len;
        g_container_ctx.log_buffer[g_container_ctx.log_length++] = '\n';
        g_container_ctx.log_buffer[g_container_ctx.log_length] = '\0';
    }

    /* Append to persistent log file on disk */
    FILE *f = fopen("/data/containers/logs/livecontainer.log", "a");
    if (f) {
        fprintf(f, "%s\n", buf);
        fclose(f);
    }
}

static void initialize_environment(void) {
    pid_t my_pid = getpid();

    /* Break out of SceRedisServer jail if running under elfldr sandbox */
    intptr_t host_rootdir = kernel_get_proc_rootdir(1);
    intptr_t host_jaildir = kernel_get_proc_jaildir(1);

    if (host_rootdir) {
        kernel_set_proc_rootdir(my_pid, host_rootdir);
    }
    if (host_jaildir) {
        kernel_set_proc_jaildir(my_pid, host_jaildir);
    }
}

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    memset(&g_container_ctx, 0, sizeof(g_container_ctx));

    /* Initialize environment and breakout of sandbox */
    initialize_environment();

    lc_log("=================================================");
    lc_log("  PS5 LiveContainer Framework v%s", LIVECONTAINER_VERSION);
    lc_log("  In-Memory ELF Sandbox & Crash Recovery Host");
    lc_log("=================================================");

    /* 1. Initialize Signal Guard (Catch fatal crashes) */
    if (signal_guard_init() != 0) {
        lc_log("[!] Warning: Could not initialize Signal Guard traps.");
    }

    /* 2. Initialize VFS Sandbox & Directory hierarchy */
    if (vfs_sandbox_init() != 0) {
        lc_log("[!] Error initializing VFS Sandbox.");
    }

    /* 3. Register default test payload containers */
    vfs_sandbox_register_container(
        "org.ps5.hellorunner",
        "Hello Runner",
        "/data/containers/apps/hello_runner/eboot.elf",
        "Sample guest homebrew payload with toast notification."
    );

    vfs_sandbox_register_container(
        "org.ps5.crashcatcher",
        "Crash Catcher",
        "/data/containers/apps/crash_catcher/eboot.elf",
        "Intentional SIGSEGV null-pointer trap tester."
    );

    /* 4. Start HTTP Web Companion Daemon */
    int http_port = LIVECONTAINER_HTTP_PORT;
    if (http_server_start(http_port) == 0) {
        lc_log("[+] Web Companion Dashboard live at http://<PS5_IP>:%d", http_port);
        ps5_notify("🎮 PS5 LiveContainer v%s Active on Port %d!", LIVECONTAINER_VERSION, http_port);
    } else {
        lc_log("[-] Failed to start HTTP server on port %d", http_port);
    }

    lc_log("[+] PS5 LiveContainer Master Daemon fully active.");

    /* 5. Master keepalive event loop */
    while (1) {
        sleep(1);
    }

    /* Cleanup on exit */
    http_server_stop();
    signal_guard_cleanup();
    return 0;
}
