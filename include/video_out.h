#ifndef VIDEO_OUT_H
#define VIDEO_OUT_H

#include <stdint.h>
#include <stddef.h>

#define SCREEN_WIDTH  1920
#define SCREEN_HEIGHT 1080
#define NUM_BUFFERS   2

typedef struct {
    int handle;
    uint32_t *framebuffers[NUM_BUFFERS];
    int current_buffer_idx;
    uint64_t flip_arg;
    int is_initialized;
} video_out_ctx_t;

extern video_out_ctx_t g_video_ctx;

/* Initialize PS5 VideoOut and register 1080p ARGB double buffers */
int video_out_init(void);

/* Clear current buffer with specified ARGB color */
void video_out_clear(uint32_t color);

/* Draw a filled rectangle */
void video_out_draw_rect(int x, int y, int w, int h, uint32_t color);

/* Draw a text string using built-in 8x16 bitmap font */
void video_out_draw_string(int x, int y, const char *str, uint32_t color);

/* Draw LiveContainer HUD with live system info */
void video_out_render_hud(const char *ip_str, int port);

/* Submit frame flip and wait for VBlank */
void video_out_flip(void);

/* Shutdown VideoOut */
void video_out_cleanup(void);

#endif /* VIDEO_OUT_H */
