#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <time.h>
#include "../compost.h"

#ifdef _WIN32
#include <io.h>
#include <fcntl.h>
#endif

bool verbose = false;

uint8_t tx_buf[1024];
uint8_t rx_buf[1024];
extern uint16_t notif_request;

void print_info(void)
{
    fprintf(stderr, "Compost device mock, ");
    volatile uint32_t i = 0x01234567;
    // Endianity check
    if ((*((uint8_t *)(&i))) == 0x67) {
        fprintf(stderr, "Little endian\n");
    } else {
        fprintf(stderr, "Big endian\n");
    }
}

void print_array(uint8_t *ptr, size_t len)
{
    for (size_t i = 0; i < len; i++) {
        fprintf(stderr, "%02x ", ptr[i]);
    }
}

void log_msg(char *prefix, uint8_t *ptr, size_t len)
{
    if (verbose) {
        fprintf(stderr, "%s", prefix);
        print_array(ptr, len);
        fprintf(stderr, "\n");
    }
}

int parse_args(int argc, char *argv[])
{
    for (int i = 1; i < argc; i++) {
        if (argv[i][0] == '-') {
            if (argv[i][1] == 'v') {
                verbose = true;
            } else {
                fprintf(stderr, "Error: unknown argument\n");
                return -1;
            }
        } else {
            fprintf(stderr, "Error: unknown argument\n");
            return -1;
        }
    }
    return 0;
}

void compost_assert(uint32_t line)
{
    fprintf(stderr, "Assertion failed at compost.c:%u\n", line);
    exit(1);
}

int main(int argc, char *argv[])
{
    int ret = parse_args(argc, argv);
    if (ret) {
        return ret;
    }

    print_info();

    if (freopen(NULL, "rb", stdin) == NULL) {
        fprintf(stderr, "Warning: stdin == NULL\n");
    }
    if (freopen(NULL, "wb", stdout) == NULL) {
        fprintf(stderr, "Warning: stdout == NULL\n");
    }

#ifdef _WIN32
    setmode(fileno(stdout), O_BINARY);
    setmode(fileno(stdin), O_BINARY);
#endif

    compost_set_assert_func(compost_assert);

    for (;;) {
        if (fread(rx_buf, 1, 4, stdin) != 4) {
            break;
        }
        uint16_t data_len8 = rx_buf[0] * 4;
        if (data_len8 > 0) {
            if (fread(rx_buf + 4, 1, data_len8, stdin) != data_len8) {
                break;
            }
        }
        log_msg("  mock <- ", rx_buf, 4 + data_len8);
        int16_t tx_len = compost_msg_process(tx_buf, sizeof(tx_buf), rx_buf, 4 + data_len8);
        log_msg("  mock -> ", tx_buf, tx_len);

        if (tx_len) {
            fwrite(tx_buf, 1, tx_len, stdout);
            fflush(stdout);
        }

        bool notif_requested = true;
        //! Allocator placed at the beggining of rx_buf, which can safely be rewritten at this
        //! point. Notification serialization handles the copying to correct address in tx buffer.
        struct CompostAlloc alloc = MockDate_alloc_init(rx_buf, sizeof(rx_buf));
        time_t current_epoch;
        switch (notif_request) {
        case 0x0e00:
            time(&current_epoch);
            struct MockDate date = epoch_to_date_handler(current_epoch, &alloc);
            tx_len = notify_date_store(tx_buf, sizeof(tx_buf), date);
            break;
        case 0x0e02:
            tx_len = notify_heartbeat_store(tx_buf, sizeof(tx_buf));
            break;
        case 0x0e03:
            tx_len = notify_bitwise_complement_store(tx_buf, sizeof(tx_buf), 0xAAAAAAAAAAAAAAAA, 0x5555555555555555);
            break;
        default:
            notif_requested = false;
            break;
        }
        if (notif_requested) {
            fwrite(tx_buf, 1, tx_len, stdout);
            fflush(stdout);
            notif_request = 0xFFFF;
        }
    }

    if (feof(stdin)) {
        // stdin EOF
        exit(0);
    } else if (ferror(stdin)) {
        fprintf(stderr, "Error reading stdin\n");
        exit(1);
    }
}
