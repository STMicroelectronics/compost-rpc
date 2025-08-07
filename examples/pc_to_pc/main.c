#include <stdint.h>
#include <stdio.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>
#endif

#include "compost.h"

// Compost header is always 4 bytes long
#define HEADER_SIZE 4
// The TCP port on which the server will listen for incoming connections
#define PORT        3333

uint8_t tx_buf[1024]; // Buffer for the incoming request
uint8_t rx_buf[1024]; // Buffer for the outgoing response

// This function is called when a message with the "add_int" request is received
uint32_t add_int_handler(uint32_t a, uint32_t b)
{
    printf("add_int(%d, %d) -> %d\n", a, b, a + b);
    return a + b;
}

// We read incoming messages using this function
int read_bytes(int fd, void *buf, size_t count)
{
#ifdef _WIN32
    recv(fd, buf, count, 0);
#else
    read(fd, buf, count);
#endif
}

// We write outgoing messages using this function
int write_bytes(int fd, const void *buf, size_t count)
{
#ifdef _WIN32
    send(fd, buf, count, 0);
#else
    write(fd, buf, count);
#endif
}

int main(int argc, char *argv[])
{
    // Windows specific initialization
#ifdef _WIN32
    WSADATA wsaData;

    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        fprintf(stderr, "WSAStartup failed.\n");
        exit(1);
    }

    if (LOBYTE(wsaData.wVersion) != 2 || HIBYTE(wsaData.wVersion) != 2) {
        fprintf(stderr, "Versiion 2.2 of Winsock is not available.\n");
        WSACleanup();
        exit(2);
    }
#endif

    // Open a TCP socket and listen for connections
    struct sockaddr_in sockaddr = {
        .sin_family = AF_INET, .sin_addr = {.s_addr = htonl(INADDR_ANY)}, .sin_port = htons(PORT)};
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    const int optval = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, (const char *)&optval, sizeof(optval));
    bind(sock, (struct sockaddr *)&sockaddr, sizeof(sockaddr));
    listen(sock, 5);

    printf("Listening on port %d...\n", PORT);

    struct sockaddr_in client_sockaddr_in;
    socklen_t len = sizeof(client_sockaddr_in);

    for (;;) {
        // Wait for a client connection and accept it
        int connection = accept(sock, (struct sockaddr *)&client_sockaddr_in, &len);

        for (;;) {

            // Read the header (first 4 bytes)
            if (read_bytes(connection, rx_buf, HEADER_SIZE) < 1)
                break;

            // Calculate the size of the payload
            // (first byte of the header indicates the number of 32-bit words of the payload)
            size_t rx_payload_size = 4 * rx_buf[0];

            // Read the payload
            if (read_bytes(connection, rx_buf + HEADER_SIZE, rx_payload_size) < 1)
                break;

            // Process the request and prepare the response
            int16_t tx_msg_size =
                compost_msg_process(tx_buf, sizeof(tx_buf), rx_buf, HEADER_SIZE + rx_payload_size);

            // If the message size is negative, it indicates an error
            if (tx_msg_size > 0) {
                write_bytes(connection, tx_buf, tx_msg_size);
            } else if (tx_msg_size == 0) {
                // No response to send
            } else {
                fprintf(stderr, "error\n");
            }
        }

#ifdef _WIN32
        closesocket(connection);
#else
        close(connection);
#endif
    }

#ifdef _WIN32
    closesocket(sock);
    WSACleanup();
#else
    close(sock);
#endif

    return 0;
}