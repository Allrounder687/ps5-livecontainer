#include "signal_guard.h"
#include "ps5_notify.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

signal_guard_ctx_t g_signal_guard;

static const char *get_signal_name(int sig) {
    switch (sig) {
        case SIGSEGV: return "SIGSEGV (Segmentation Fault / Null Pointer)";
        case SIGBUS:  return "SIGBUS (Bus Error / Misaligned Access)";
        case SIGILL:  return "SIGILL (Illegal Instruction)";
        case SIGFPE:  return "SIGFPE (Floating Point Exception)";
        case SIGABRT: return "SIGABRT (Abort Called)";
        default:      return "UNKNOWN SIGNAL";
    }
}

static void signal_trap_handler(int sig, siginfo_t *info, void *ucontext) {
    (void)ucontext;
    
    lc_log("\n=======================================================");
    lc_log("[LiveContainer CRASH TRAP] Caught %s!", get_signal_name(sig));
    if (info) {
        lc_log("[LiveContainer CRASH TRAP] Fault address: %p", info->si_addr);
    }
    lc_log("[LiveContainer CRASH TRAP] Rolling back guest context safely...");
    lc_log("=======================================================\n");

    ps5_notify("⚠️ LiveContainer: Caught %s! Console protected.", get_signal_name(sig));

    if (g_signal_guard.in_guarded_execution) {
        g_signal_guard.in_guarded_execution = 0;
        siglongjmp(g_signal_guard.recovery_env, sig);
    } else {
        /* Fatal crash outside guest code, exit cleanly */
        _exit(1);
    }
}

int signal_guard_init(void) {
    memset(&g_signal_guard, 0, sizeof(signal_guard_ctx_t));

    /* Setup alternate signal stack so stack overflows can still be caught */
    void *stack_mem = malloc(SIGNAL_STACK_SIZE);
    if (stack_mem) {
        g_signal_guard.alt_stack.ss_sp = stack_mem;
        g_signal_guard.alt_stack.ss_size = SIGNAL_STACK_SIZE;
        g_signal_guard.alt_stack.ss_flags = 0;
        sigaltstack(&g_signal_guard.alt_stack, NULL);
    }

    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_sigaction = signal_trap_handler;
    sa.sa_flags = SA_SIGINFO | SA_ONSTACK;
    sigemptyset(&sa.sa_mask);

    sigaction(SIGSEGV, &sa, &g_signal_guard.old_sa_segv);
    sigaction(SIGBUS,  &sa, &g_signal_guard.old_sa_bus);
    sigaction(SIGILL,  &sa, &g_signal_guard.old_sa_ill);
    sigaction(SIGFPE,  &sa, &g_signal_guard.old_sa_fpe);
    sigaction(SIGABRT, &sa, &g_signal_guard.old_sa_abrt);

    lc_log("[Signal Guard] Crash traps initialized (SIGSEGV, SIGBUS, SIGILL, SIGFPE, SIGABRT)");
    return 0;
}

void signal_guard_cleanup(void) {
    sigaction(SIGSEGV, &g_signal_guard.old_sa_segv, NULL);
    sigaction(SIGBUS,  &g_signal_guard.old_sa_bus, NULL);
    sigaction(SIGILL,  &g_signal_guard.old_sa_ill, NULL);
    sigaction(SIGFPE,  &g_signal_guard.old_sa_fpe, NULL);
    sigaction(SIGABRT, &g_signal_guard.old_sa_abrt, NULL);

    if (g_signal_guard.alt_stack.ss_sp) {
        free(g_signal_guard.alt_stack.ss_sp);
        g_signal_guard.alt_stack.ss_sp = NULL;
    }
}

int signal_guard_run_safely(container_slot_t *slot, elf_entry_fn entry, int argc, char **argv) {
    if (!slot || !entry) return -1;

    g_signal_guard.in_guarded_execution = 1;
    slot->state = CONTAINER_STATE_RUNNING;
    slot->launch_timestamp = (uint64_t)time(NULL);

    int crash_sig = sigsetjmp(g_signal_guard.recovery_env, 1);
    if (crash_sig == 0) {
        /* Primary execution path */
        lc_log("[LiveContainer] Entering container '%s' [%s]...", slot->name, slot->id);
        int ret = entry(argc, argv);
        
        g_signal_guard.in_guarded_execution = 0;
        slot->state = CONTAINER_STATE_STOPPED;
        slot->last_exit_code = ret;
        slot->last_signal = 0;
        lc_log("[LiveContainer] Container '%s' exited cleanly with code %d", slot->name, ret);
        return ret;
    } else {
        /* Crash recovery path */
        g_signal_guard.in_guarded_execution = 0;
        slot->state = CONTAINER_STATE_CRASHED;
        slot->last_signal = crash_sig;
        slot->last_exit_code = -1;
        lc_log("[LiveContainer] Restored execution state from crash in container '%s'", slot->name);
        return -1;
    }
}
