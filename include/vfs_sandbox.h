#ifndef VFS_SANDBOX_H
#define VFS_SANDBOX_H

#include "container_types.h"

/* Initialize the filesystem layout under /data/containers/ */
int vfs_sandbox_init(void);

/* Scan /data/containers/apps/ and populate registered container slots */
int vfs_sandbox_scan_apps(void);

/* Create isolated directories for a specific app ID */
int vfs_sandbox_prepare_app_dirs(const char *app_id, char *out_data_path, size_t max_len);

/* Register a new container slot */
int vfs_sandbox_register_container(const char *id, const char *name, const char *elf_rel_path, const char *desc);

/* Save container database to JSON */
int vfs_sandbox_save_registry(void);

/* Load container database from JSON */
int vfs_sandbox_load_registry(void);

#endif /* VFS_SANDBOX_H */
