#include <stdio.h>
#include <unistd.h>

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    printf("[CrashCatcher] Payload started. About to trigger intentional SIGSEGV...\n");
    sleep(1);

    /* Intentionally dereference NULL pointer to test LiveContainer crash protection */
    volatile int *bad_ptr = (volatile int *)0x0;
    *bad_ptr = 1337;

    /* Should never reach here */
    printf("[CrashCatcher] ERROR: Should not reach this line!\n");
    return 0;
}
