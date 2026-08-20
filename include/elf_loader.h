#ifndef ELF_LOADER_H
#define ELF_LOADER_H

#include "container_types.h"
#include <elf.h>

typedef int (*elf_entry_fn)(int argc, char **argv);

typedef struct {
    void *image_base;
    size_t image_size;
    elf_entry_fn entry_point;
    uintptr_t base_vaddr;
    Elf64_Ehdr ehdr;
} elf_loaded_image_t;

/* Validate ELF headers (magic, x86_64, 64-bit, little-endian) */
int elf_loader_validate_header(const Elf64_Ehdr *ehdr);

/* Load an ELF binary buffer into newly mapped executable memory */
int elf_loader_load_buffer(const uint8_t *buffer, size_t buffer_size, elf_loaded_image_t *out_image);

/* Load an ELF from a filesystem path */
int elf_loader_load_file(const char *path, elf_loaded_image_t *out_image);

/* Unload and unmap memory */
void elf_loader_unload(elf_loaded_image_t *image);

#endif /* ELF_LOADER_H */
