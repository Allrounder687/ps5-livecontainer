#include "elf_loader.h"
#include "container_types.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <dlfcn.h>
#include <errno.h>

#ifndef R_X86_64_64
#define R_X86_64_64 1
#endif
#ifndef R_X86_64_GLOB_DAT
#define R_X86_64_GLOB_DAT 6
#endif
#ifndef R_X86_64_JUMP_SLOT
#define R_X86_64_JUMP_SLOT 7
#endif
#ifndef R_X86_64_RELATIVE
#define R_X86_64_RELATIVE 8
#endif

#define PAGE_SIZE 0x4000 /* 16KB PS5 page size */
#define PAGE_ALIGN(x) (((x) + (PAGE_SIZE - 1)) & ~(PAGE_SIZE - 1))

int elf_loader_validate_header(const Elf64_Ehdr *ehdr) {
    if (!ehdr) return -1;
    
    if (ehdr->e_ident[EI_MAG0] != ELFMAG0 ||
        ehdr->e_ident[EI_MAG1] != ELFMAG1 ||
        ehdr->e_ident[EI_MAG2] != ELFMAG2 ||
        ehdr->e_ident[EI_MAG3] != ELFMAG3) {
        lc_log("[ELF Loader] Invalid ELF magic signature");
        return -1;
    }
    
    if (ehdr->e_ident[EI_CLASS] != ELFCLASS64) {
        lc_log("[ELF Loader] Only 64-bit ELF binaries are supported");
        return -1;
    }
    
    if (ehdr->e_machine != EM_X86_64) {
        lc_log("[ELF Loader] Invalid machine type (expected x86_64)");
        return -1;
    }
    
    return 0;
}

static void elf_loader_apply_relocations(uint8_t *base, Elf64_Dyn *dyn) {
    if (!base || !dyn) return;

    Elf64_Rela *rela = NULL;
    size_t rela_sz = 0;
    Elf64_Rela *plt_rela = NULL;
    size_t plt_rela_sz = 0;
    Elf64_Sym *symtab = NULL;
    const char *strtab = NULL;

    for (Elf64_Dyn *d = dyn; d->d_tag != DT_NULL; d++) {
        switch (d->d_tag) {
            case DT_RELA:     rela = (Elf64_Rela *)(base + d->d_un.d_ptr); break;
            case DT_RELASZ:   rela_sz = d->d_un.d_val; break;
            case DT_JMPREL:   plt_rela = (Elf64_Rela *)(base + d->d_un.d_ptr); break;
            case DT_PLTRELSZ: plt_rela_sz = d->d_un.d_val; break;
            case DT_SYMTAB:   symtab = (Elf64_Sym *)(base + d->d_un.d_ptr); break;
            case DT_STRTAB:   strtab = (const char *)(base + d->d_un.d_ptr); break;
            default: break;
        }
    }

    /* Process standard RELA relocations */
    if (rela && rela_sz > 0) {
        size_t count = rela_sz / sizeof(Elf64_Rela);
        for (size_t i = 0; i < count; i++) {
            uint32_t type = ELF64_R_TYPE(rela[i].r_info);
            uint32_t sym_idx = ELF64_R_SYM(rela[i].r_info);
            uint64_t *target = (uint64_t *)(base + rela[i].r_offset);

            if (type == R_X86_64_RELATIVE) {
                *target = (uint64_t)(base + rela[i].r_addend);
            } else if (type == R_X86_64_64 || type == R_X86_64_GLOB_DAT) {
                if (symtab && strtab && sym_idx > 0) {
                    const char *sym_name = strtab + symtab[sym_idx].st_name;
                    void *sym_addr = dlsym(RTLD_DEFAULT, sym_name);
                    if (sym_addr) {
                        *target = (uint64_t)sym_addr + rela[i].r_addend;
                    }
                }
            }
        }
    }

    /* Process PLT / JMPREL relocations */
    if (plt_rela && plt_rela_sz > 0) {
        size_t count = plt_rela_sz / sizeof(Elf64_Rela);
        for (size_t i = 0; i < count; i++) {
            uint32_t type = ELF64_R_TYPE(plt_rela[i].r_info);
            uint32_t sym_idx = ELF64_R_SYM(plt_rela[i].r_info);
            uint64_t *target = (uint64_t *)(base + plt_rela[i].r_offset);

            if (type == R_X86_64_JUMP_SLOT) {
                if (symtab && strtab && sym_idx > 0) {
                    const char *sym_name = strtab + symtab[sym_idx].st_name;
                    void *sym_addr = dlsym(RTLD_DEFAULT, sym_name);
                    if (sym_addr) {
                        *target = (uint64_t)sym_addr;
                    }
                }
            }
        }
    }
}

int elf_loader_load_buffer(const uint8_t *buffer, size_t buffer_size, elf_loaded_image_t *out_image) {
    if (!buffer || buffer_size < sizeof(Elf64_Ehdr) || !out_image) {
        return -1;
    }

    const Elf64_Ehdr *ehdr = (const Elf64_Ehdr *)buffer;
    if (elf_loader_validate_header(ehdr) != 0) {
        return -1;
    }

    const Elf64_Phdr *phdrs = (const Elf64_Phdr *)(buffer + ehdr->e_phoff);
    uintptr_t min_vaddr = (uintptr_t)-1;
    uintptr_t max_vaddr = 0;
    Elf64_Dyn *dyn_segment = NULL;

    /* Compute memory footprint across all PT_LOAD segments */
    for (int i = 0; i < ehdr->e_phnum; i++) {
        if (phdrs[i].p_type == PT_LOAD) {
            if (phdrs[i].p_vaddr < min_vaddr) min_vaddr = phdrs[i].p_vaddr;
            if (phdrs[i].p_vaddr + phdrs[i].p_memsz > max_vaddr) {
                max_vaddr = phdrs[i].p_vaddr + phdrs[i].p_memsz;
            }
        }
    }

    if (min_vaddr >= max_vaddr) {
        lc_log("[ELF Loader] No valid PT_LOAD segments found");
        return -1;
    }

    size_t total_size = PAGE_ALIGN(max_vaddr - min_vaddr);

    /* Allocate RWX virtual memory pages for the guest image */
    void *mapped_mem = mmap(NULL, total_size,
                            PROT_READ | PROT_WRITE | PROT_EXEC,
                            MAP_PRIVATE | MAP_ANON, -1, 0);

    if (mapped_mem == MAP_FAILED) {
        lc_log("[ELF Loader] Failed to mmap guest memory (%s)", strerror(errno));
        return -1;
    }

    memset(mapped_mem, 0, total_size);

    /* Map each segment into the allocated memory block */
    for (int i = 0; i < ehdr->e_phnum; i++) {
        const Elf64_Phdr *p = &phdrs[i];
        if (p->p_type == PT_LOAD) {
            uint8_t *seg_dest = (uint8_t *)mapped_mem + (p->p_vaddr - min_vaddr);
            if (p->p_filesz > 0 && (p->p_offset + p->p_filesz <= buffer_size)) {
                memcpy(seg_dest, buffer + p->p_offset, p->p_filesz);
            }
        } else if (p->p_type == PT_DYNAMIC) {
            dyn_segment = (Elf64_Dyn *)((uint8_t *)mapped_mem + (p->p_vaddr - min_vaddr));
        }
    }

    /* Apply dynamic relocations */
    if (dyn_segment) {
        elf_loader_apply_relocations((uint8_t *)mapped_mem, dyn_segment);
    }

    out_image->image_base = mapped_mem;
    out_image->image_size = total_size;
    out_image->base_vaddr = min_vaddr;
    out_image->entry_point = (elf_entry_fn)((uint8_t *)mapped_mem + (ehdr->e_entry - min_vaddr));
    memcpy(&out_image->ehdr, ehdr, sizeof(Elf64_Ehdr));

    lc_log("[ELF Loader] Successfully loaded ELF: base=%p, size=%zu bytes, entry=%p",
           out_image->image_base, out_image->image_size, out_image->entry_point);

    return 0;
}

int elf_loader_load_file(const char *path, elf_loaded_image_t *out_image) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        lc_log("[ELF Loader] Failed to open ELF file '%s': %s", path, strerror(errno));
        return -1;
    }

    off_t file_size = lseek(fd, 0, SEEK_END);
    lseek(fd, 0, SEEK_SET);

    if (file_size <= 0) {
        close(fd);
        return -1;
    }

    uint8_t *buffer = (uint8_t *)malloc(file_size);
    if (!buffer) {
        close(fd);
        return -1;
    }

    ssize_t bytes_read = read(fd, buffer, file_size);
    close(fd);

    if (bytes_read != file_size) {
        free(buffer);
        return -1;
    }

    int ret = elf_loader_load_buffer(buffer, file_size, out_image);
    free(buffer);
    return ret;
}

void elf_loader_unload(elf_loaded_image_t *image) {
    if (image && image->image_base && image->image_size > 0) {
        munmap(image->image_base, image->image_size);
        image->image_base = NULL;
        image->image_size = 0;
        image->entry_point = NULL;
    }
}
