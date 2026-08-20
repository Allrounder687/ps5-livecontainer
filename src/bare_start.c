#include <stdint.h>
#include <stddef.h>

typedef struct payload_args {
    int (*sys_dynlib_dlsym)(int, const char*, void*);
    int  *rwpipe;
    int  *rwpair;
    long  kpipe_addr;
    long  kdata_base_addr;
    int  *payloadout;
} payload_args_t;

payload_args_t *g_payload_args = NULL;

extern int main(int argc, char **argv);

/* Universal entry point for LiveContainer under elfldr */
void _start(payload_args_t *args) {
    g_payload_args = args;

    /* Call LiveContainer master daemon main */
    int ret = main(0, NULL);

    if (args && args->payloadout) {
        *args->payloadout = ret;
    }

    /* sys_exit(ret) using libkernel syscall gadget if available */
    if (args && args->sys_dynlib_dlsym) {
        void (*exit_fn)(int) = NULL;
        if (args->sys_dynlib_dlsym(0x2, "exit", (void**)&exit_fn) == 0 && exit_fn) {
            exit_fn(ret);
        }
    }

    while (1) {
        /* Infinite keepalive */
        asm volatile("pause");
    }
}
