#include "compost.h"
#include <stdio.h>
#include <assert.h>
#include <inttypes.h>

int main()
{
    // TwoListAttr test RPC call
    uint8_t rx[50] = {4, 2, 12, 20, 0, 3, 0, 2, 0, 4, 0, 6, 0, 3, 0, 3, 0, 5, 0, 10};
    uint8_t tx[50];
    compost_msg_process(tx, 50, rx, 50);
    uint8_t expected[] = {7,  2,   12, 21, 64, 128, 0, 0, 0, 3, 0, 2,  0,  4,   0, 6,
                          64, 160, 0,  0,  0,  3,   0, 3, 0, 5, 0, 10, 64, 192, 0, 0};
    for (int i = 0; i < sizeof(expected); i++) {
        assert(expected[i] == tx[i]);
    }
    printf("Test run: OK\n");
    return 0;
}