#ifndef SIGNAL_GUARD_H
#define SIGNAL_GUARD_H

#include "container_types.h"
#include "elf_loader.h"
#include <signal.h>
#include <setjmp.h>

#define SIGNAL_STACK_SIZE (64 * 1024)

typedef struct {
    sigjmp_buf recovery_env;
    volatile sig_atomic_t in_guarded_execution;
    stack_t alt_stack;
    struct sigaction old_sa_segv;
    struct sigaction old_sa_bus;
    struct sigaction old_sa_ill;
    struct sigaction old_sa_fpe;
    struct sigaction old_sa_abrt;
} signal_guard_ctx_t;

extern signal_guard_ctx_t g_signal_guard;

/* Initialize signal handlers and alternate stack */
int signal_guard_init(void);

/* Restore default signal handlers */
void signal_guard_cleanup(void);

/* Execute a guest payload entry point inside the crash trap */
int signal_guard_run_safely(container_slot_t *slot, elf_entry_fn entry, int argc, char **argv);

#endif /* SIGNAL_GUARD_H */
