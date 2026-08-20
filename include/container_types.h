#ifndef CONTAINER_TYPES_H
#define CONTAINER_TYPES_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <sys/types.h>

#define LIVECONTAINER_VERSION        "1.0.0"
#define LIVECONTAINER_HTTP_PORT      8080
#define LIVECONTAINER_MAX_SLOTS      16
#define LIVECONTAINER_MAX_LOG_SIZE   (64 * 1024)
#define LIVECONTAINER_BASE_DIR       "/data/containers"
#define LIVECONTAINER_APPS_DIR       "/data/containers/apps"
#define LIVECONTAINER_CONFIG_PATH    "/data/containers/containers.json"

typedef enum {
    CONTAINER_STATE_IDLE = 0,
    CONTAINER_STATE_PREPARING,
    CONTAINER_STATE_RUNNING,
    CONTAINER_STATE_STOPPED,
    CONTAINER_STATE_CRASHED,
    CONTAINER_STATE_ERROR
} container_state_t;

typedef struct {
    char id[64];              /* e.g., "org.ps5.doom" or "ITGA00001" */
    char name[128];           /* Display name: "Doom PS5" */
    char version[32];         /* "1.2.0" */
    char author[64];          /* Author string */
    char description[256];    /* Short description */
    char elf_path[256];       /* Path to .elf inside container */
    char data_dir[256];       /* Sandboxed storage path */
    container_state_t state;  /* Current execution status */
    int last_exit_code;       /* Exit code returned by main() */
    int last_signal;          /* Crash signal (SIGSEGV, SIGBUS, etc.) */
    uint64_t launch_timestamp;/* Launch epoch time */
    uint64_t memory_usage;    /* Mapped memory footprint */
    void *mapped_base;        /* Base address of mapped ELF segments */
    size_t mapped_size;       /* Total mapped allocation */
} container_slot_t;

typedef struct {
    container_slot_t slots[LIVECONTAINER_MAX_SLOTS];
    int slot_count;
    int active_slot_index;
    bool is_server_running;
    int server_socket;
    char log_buffer[LIVECONTAINER_MAX_LOG_SIZE];
    size_t log_length;
} livecontainer_ctx_t;

extern livecontainer_ctx_t g_container_ctx;

void lc_log(const char *fmt, ...);

#endif /* CONTAINER_TYPES_H */
