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

uint8_t tx_buf[1024];
uint8_t rx_buf[1024];

uint32_t add_int_handler(uint32_t a, uint32_t b)
{
    printf("%d + %d = %d\n", a, b, a + b);
    return a + b;
}

int main(int argc, char *argv[])
{
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

    struct sockaddr_in sockaddr;
    sockaddr.sin_family = AF_INET;
    sockaddr.sin_addr.s_addr = htonl(INADDR_ANY);
    sockaddr.sin_port = htons(3333);
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    const int optval = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, (const char*)&optval, sizeof(optval));
    bind(sock, (struct sockaddr *)&sockaddr, sizeof(sockaddr));
    listen(sock, 5);

    struct sockaddr_in client_sockaddr_in;
    socklen_t len = sizeof(client_sockaddr_in);

    for (;;) {
        int connection = accept(sock, (struct sockaddr *)&client_sockaddr_in, &len);

        for (;;) {
            
            #ifdef _WIN32
                if (recv(connection, rx_buf, 1, 0) < 1)
            #else
                if (read(connection, rx_buf, 1) < 1)
            #endif
                    break;
            
            #ifdef _WIN32
                if (recv(connection, rx_buf + 1, 3 + 4 * rx_buf[0], 0) < 1)
            #else
                if (read(connection, rx_buf + 1, 3 + 4 * rx_buf[0]) < 1)
            #endif
                    break;

            int16_t msg_size = compost_msg_process(tx_buf, sizeof(tx_buf), rx_buf, 4 + 4 * rx_buf[0]);

            if (msg_size > 0) {
                #ifdef _WIN32
                    send(connection, tx_buf, msg_size, 0);
                #else
                    write(connection, tx_buf, msg_size);
                #endif
            } else if (msg_size == 0) {
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