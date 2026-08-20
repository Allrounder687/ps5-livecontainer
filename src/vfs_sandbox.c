#include "vfs_sandbox.h"
#include "container_types.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <dirent.h>
#include <unistd.h>

static int ensure_dir_exists(const char *path) {
    struct stat st;
    if (stat(path, &st) == 0) {
        if (S_ISDIR(st.st_mode)) return 0;
        return -1;
    }
    return mkdir(path, 0777);
}

int vfs_sandbox_init(void) {
    ensure_dir_exists(LIVECONTAINER_BASE_DIR);
    ensure_dir_exists(LIVECONTAINER_APPS_DIR);
    ensure_dir_exists("/data/containers/logs");

    lc_log("[VFS Sandbox] Initialized container root at %s", LIVECONTAINER_BASE_DIR);
    return vfs_sandbox_load_registry();
}

int vfs_sandbox_prepare_app_dirs(const char *app_id, char *out_data_path, size_t max_len) {
    if (!app_id || !out_data_path || max_len == 0) return -1;

    char app_root[256];
    char app_data[256];
    char app_config[256];

    snprintf(app_root, sizeof(app_root), "%s/%s", LIVECONTAINER_APPS_DIR, app_id);
    snprintf(app_data, sizeof(app_data), "%s/data", app_root);
    snprintf(app_config, sizeof(app_config), "%s/config", app_root);

    ensure_dir_exists(app_root);
    ensure_dir_exists(app_data);
    ensure_dir_exists(app_config);

    strncpy(out_data_path, app_data, max_len - 1);
    out_data_path[max_len - 1] = '\0';
    return 0;
}

int vfs_sandbox_register_container(const char *id, const char *name, const char *elf_rel_path, const char *desc) {
    if (g_container_ctx.slot_count >= LIVECONTAINER_MAX_SLOTS) {
        lc_log("[VFS Sandbox] Maximum container slot capacity reached (%d)", LIVECONTAINER_MAX_SLOTS);
        return -1;
    }

    /* Check if already registered */
    for (int i = 0; i < g_container_ctx.slot_count; i++) {
        if (strcmp(g_container_ctx.slots[i].id, id) == 0) {
            strncpy(g_container_ctx.slots[i].name, name, sizeof(g_container_ctx.slots[i].name) - 1);
            strncpy(g_container_ctx.slots[i].description, desc ? desc : "", sizeof(g_container_ctx.slots[i].description) - 1);
            return i;
        }
    }

    int idx = g_container_ctx.slot_count;
    container_slot_t *slot = &g_container_ctx.slots[idx];
    memset(slot, 0, sizeof(container_slot_t));

    strncpy(slot->id, id, sizeof(slot->id) - 1);
    strncpy(slot->name, name, sizeof(slot->name) - 1);
    strncpy(slot->version, "1.0", sizeof(slot->version) - 1);
    strncpy(slot->author, "Homebrew Dev", sizeof(slot->author) - 1);
    strncpy(slot->description, desc ? desc : "PS5 Sandboxed App", sizeof(slot->description) - 1);
    
    if (elf_rel_path[0] == '/') {
        strncpy(slot->elf_path, elf_rel_path, sizeof(slot->elf_path) - 1);
    } else {
        snprintf(slot->elf_path, sizeof(slot->elf_path), "%s/%s/%s", LIVECONTAINER_APPS_DIR, id, elf_rel_path);
    }

    vfs_sandbox_prepare_app_dirs(id, slot->data_dir, sizeof(slot->data_dir));
    slot->state = CONTAINER_STATE_IDLE;

    g_container_ctx.slot_count++;
    vfs_sandbox_save_registry();

    lc_log("[VFS Sandbox] Registered container '%s' [%s] in slot %d", name, id, idx);
    return idx;
}

int vfs_sandbox_save_registry(void) {
    FILE *f = fopen(LIVECONTAINER_CONFIG_PATH, "w");
    if (!f) return -1;

    fprintf(f, "{\n  \"version\": \"%s\",\n  \"slots\": [\n", LIVECONTAINER_VERSION);
    for (int i = 0; i < g_container_ctx.slot_count; i++) {
        container_slot_t *s = &g_container_ctx.slots[i];
        fprintf(f, "    {\n");
        fprintf(f, "      \"id\": \"%s\",\n", s->id);
        fprintf(f, "      \"name\": \"%s\",\n", s->name);
        fprintf(f, "      \"description\": \"%s\",\n", s->description);
        fprintf(f, "      \"elf_path\": \"%s\",\n", s->elf_path);
        fprintf(f, "      \"data_dir\": \"%s\"\n", s->data_dir);
        fprintf(f, "    }%s\n", (i == g_container_ctx.slot_count - 1) ? "" : ",");
    }
    fprintf(f, "  ]\n}\n");
    fclose(f);
    return 0;
}

int vfs_sandbox_load_registry(void) {
    /* If registry doesn't exist yet, scaffold default demo slots */
    FILE *f = fopen(LIVECONTAINER_CONFIG_PATH, "r");
    if (!f) {
        vfs_sandbox_register_container("org.ps5.hello", "Hello LiveContainer", "eboot.elf", "Sample hello world container");
        vfs_sandbox_register_container("org.ps5.crashtrap", "Crash Safety Tester", "eboot.elf", "Tests crash recovery without un-jailbreaking");
        return 0;
    }
    fclose(f);
    return 0;
}
