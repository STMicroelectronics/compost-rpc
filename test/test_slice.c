#include "compost.h"
#include <stdio.h>
#include <assert.h>
#include <inttypes.h>
#include <stdlib.h>

enum {
    LE,
    BE
};

int cpu_endianity(void)
{
    volatile uint32_t i = 0x01234567;
    if ((*((uint8_t*)(&i))) == 0x67) {
        return LE;
    } else {
        return BE;
    }
}

void print_info(void)
{
    fprintf(stderr, "Compost slice test, ");
    if (cpu_endianity() == LE) {
        fprintf(stderr, "Little endian\n");
    } else {
        fprintf(stderr, "Big endian\n");
    }
}

void compost_assert(uint32_t line)
{
    fprintf(stderr, "Assertion failed at compost.c:%u\n", line);
    exit(1);
}

int main(void)
{
    print_info();

    compost_set_assert_func(compost_assert);

    uint8_t data[16] = {0xF4, 0x12, 0xB6, 0xFC, 0x00, 0x00, 0x00, 0x00};
    struct CompostSliceU32 slice = { data, 4 };
    // uint8_t *bytes = ((uint8_t *)slice.ptr);
    uint32_t intdata[] = {123, 1023, 10023, 100023};
    uint32_t intdata2[] = {123, 1023, 10023, 100023};
    int index = 0;
    uint32_t val = 0;

    val = compost_slice_get(slice, index);
    assert(val == 4094867196ull);

    index = 1;
    compost_slice_set(slice, index, 501ull);
    val = compost_slice_get(slice, index);
    assert(val == 501ull);

    compost_slice_copy_to(slice, intdata2);
    assert(intdata2[0] == 4094867196ull);
    assert(intdata2[1] == 501ull);

    printf("Index 0: %" PRIu32 "\n", compost_slice_get(slice, 0));
    printf("Index 1: %" PRIu32 "\n", compost_slice_get(slice, 1));

    assert(compost_slice_get(slice, 0) == 4094867196ull);
    assert(compost_slice_get(slice, 1) == 501ull);

    compost_slice_copy_from(slice, intdata, 4);
    assert(compost_slice_get(slice, 0) == 123ull);
    assert(compost_slice_get(slice, 3) == 100023ull);

    // Test with the allocator
    uint8_t data2[10] = {0, 0, 0, 0, 0xAA, 0xBB, 0, 0, 0, 0};
    uint16_t suffixes[] = {2, 0};
    struct CompostAlloc allocator = compost_alloc_init(data2, sizeof(data2));
    compost_alloc_set_suffixes(&allocator, suffixes, 2);
    struct CompostSliceF32 slice2 = compost_slice_f32_new(&allocator, 3);
    assert(slice2.ptr == NULL);
    assert(slice2.len == 0);
    slice2 = compost_slice_f32_new(&allocator, 1);
    assert(slice2.ptr != NULL);
    compost_slice_set(slice2, 0, 42.125);
    float f = compost_slice_get(slice2, 0);
    assert(f == 42.125);
    // compost_slice_endian_convert(&slice2, COMPOST_ENDIAN_NATIVE);
    f = compost_slice_get(slice2, 0);
    assert(f == 42.125);
    struct CompostSliceU32 slice3 = compost_slice_u32_new(&allocator, 1);
    compost_slice_set(slice3, 0, 0xFFFFFFFF);

    printf("Bytes after allocator operations: ");
    for (uint32_t i = 0; i < sizeof(data2); i++)
        printf("%x, ", data2[i]);
    printf("\n");

    assert(data2[4] == 0xAA);
    assert(data2[5] == 0xBB);

    printf("Test run: OK\n");
    return 0;
}
