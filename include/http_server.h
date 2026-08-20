#ifndef HTTP_SERVER_H
#define HTTP_SERVER_H

#include "container_types.h"

/* Start the micro HTTP server thread on the specified port */
int http_server_start(int port);

/* Stop the micro HTTP server */
void http_server_stop(void);

/* Process a single HTTP client connection (internal / worker) */
void http_server_handle_client(int client_fd);

#endif /* HTTP_SERVER_H */
