from dataclasses import dataclass
from string import Template

@dataclass
class SourcePart:
    is_slice_template : bool
    content : str

source_parts : list[SourcePart] = []
source_parts.append(SourcePart(False,'''/** @file
 * Compost C source file
 */

#include "${filename}.h"
#include <limits.h>
#include <stdint.h>
#include <string.h>

#ifndef COMPOST_ALLOW_SMALL_INT
#if INT_MAX < 2147483647
#error \\
    "int is smaller than 32b - Compost expects Enums to have 32b. You can allow smaller int by defining macro COMPOST_ALLOW_SMALL_INT"
#endif
#endif

#ifdef COMPOST_DEBUG
#define COMPOST_ASSERT(expr)                   \\
    do {                                       \\
        if (!(expr)) {                         \\
            if (compost_assert_func != NULL) { \\
                compost_assert_func(__LINE__); \\
            }                                  \\
            while (1)                          \\
                ;                              \\
        }                                      \\
    } while (0)
#else
#define COMPOST_ASSERT(expr) \\
    do {                     \\
        (void)sizeof(expr);  \\
    } while (0)
#endif

#define LEN_OFFSET                0
#define TXN_OFFSET                1
#define RPC_ID_HI_AND_RESP_OFFSET 2
#define RPC_ID_LO_OFFSET          3
#define PAYLOAD_OFFSET            4

#define RPC_ID_HI_MASK 0x0F
#define FLAGS_MASK     0xF0
#define RESP_MASK      0x10

static void (*compost_assert_func)(uint32_t line) = NULL;

void compost_invoke_switch(struct CompostMsg *tx, const struct CompostMsg rx);


/******************************************************************************/
/*            P R I V A T E   H E L P E R   F U N C T I O N S                 */
/******************************************************************************/

/**
 * Calculates the number of bytes you need to fit the bits
 */
static inline uint32_t compost_bits_to_bytes(uint32_t bits)
{
    return (bits + 7) / 8;
}

/**
 * Calculates the number of 32b words you need to fit the bytes
 */
static inline uint8_t compost_bytes_to_words(uint16_t bytes)
{
    return (bytes + 3) / 4;
}

static uint16_t compost_min(uint16_t len1, uint16_t len2)
{
    if (len1 < len2) {
        return len1;
    } else {
        return len2;
    }
}
'''))

source_parts.append(SourcePart(False,'''
/******************************************************************************/
/*            L O A D   A N D   S T O R E   F U N C T I O N S                 */
/******************************************************************************/

/**
 * Parses uint8_t from raw data in big endian
 */
static inline uint8_t compost_u8_load(const uint8_t **src)
{
    uint8_t val = (*src)[0];
    *src += sizeof(uint8_t);
    return val;
}

/**
 * Stores uint8_t to memory in big endian
 */
static inline void compost_u8_store(uint8_t **dest, uint8_t src)
{
    (*dest)[0] = src;
    *dest += sizeof(uint8_t);
}

/**
 * Parses int8_t from raw data in big endian
 */
static inline int8_t compost_i8_load(const uint8_t **src)
{
    return (int8_t)compost_u8_load(src);
}

/**
 * Serializes int8_t to bytes in big endian
 */
static inline void compost_i8_store(uint8_t **dest, int8_t src)
{
    compost_u8_store(dest, (uint8_t)src);
}

/**
 * Parses uint16_t from bytes in big endian
 */
static inline uint16_t compost_u16_load(const uint8_t **src)
{
    uint16_t val = ((uint16_t)(*src)[0] << 8) | ((uint16_t)(*src)[1]);
    *src += sizeof(uint16_t);
    return val;
}

/**
 * Serializes uint16_t to bytes in big endian
 */
static inline void compost_u16_store(uint8_t **dest, uint16_t src)
{
    (*dest)[0] = (uint8_t)(src >> 8);
    (*dest)[1] = (uint8_t)src;
    *dest += sizeof(uint16_t);
}

/**
 * Parses int16_t from bytes in big endian
 */
static inline int16_t compost_i16_load(const uint8_t **src)
{
    return (int16_t)compost_u16_load(src);
}

/**
 * Serializes int16_t to bytes in big endian
 */
static inline void compost_i16_store(uint8_t **dest, int16_t src)
{
    compost_u16_store(dest, (uint16_t)src);
}

/**
 * Parses uint32_t from bytes in big endian
 */
static inline uint32_t compost_u32_load(const uint8_t **src)
{
    uint32_t val = ((uint32_t)(*src)[0] << 24) | ((uint32_t)(*src)[1] << 16) |
                   ((uint32_t)(*src)[2] << 8) | ((uint32_t)(*src)[3]);
    *src += sizeof(uint32_t);
    return val;
}

/**
 * Serializes uint32_t to bytes in big endian
 */
static inline void compost_u32_store(uint8_t **dest, uint32_t src)
{
    (*dest)[0] = (uint8_t)(src >> 24);
    (*dest)[1] = (uint8_t)(src >> 16);
    (*dest)[2] = (uint8_t)(src >> 8);
    (*dest)[3] = (uint8_t)src;
    *dest += sizeof(uint32_t);
}

/**
 * Parses int32_t from bytes in big endian
 */
static inline int32_t compost_i32_load(const uint8_t **src)
{
    return (int32_t)compost_u32_load(src);
}

/**
 * Stores int32_t to bytes in big endian
 */
static inline void compost_i32_store(uint8_t **dest, int32_t src)
{
    compost_u32_store(dest, (uint32_t)src);
}

/**
 * Parses uint64_t from bytes in big endian
 */
static inline uint64_t compost_u64_load(const uint8_t **src)
{
    uint64_t val = ((uint64_t)(*src)[0] << 56) | ((uint64_t)(*src)[1] << 48) |
                   ((uint64_t)(*src)[2] << 40) | ((uint64_t)(*src)[3] << 32) |
                   ((uint64_t)(*src)[4] << 24) | ((uint64_t)(*src)[5] << 16) |
                   ((uint64_t)(*src)[6] << 8) | ((uint64_t)(*src)[7]);
    *src += sizeof(uint64_t);
    return val;
}

/**
 * Serializes uint64_t to bytes in big endian
 */
static inline void compost_u64_store(uint8_t **dest, uint64_t src)
{
    (*dest)[0] = (uint8_t)(src >> 56);
    (*dest)[1] = (uint8_t)(src >> 48);
    (*dest)[2] = (uint8_t)(src >> 40);
    (*dest)[3] = (uint8_t)(src >> 32);
    (*dest)[4] = (uint8_t)(src >> 24);
    (*dest)[5] = (uint8_t)(src >> 16);
    (*dest)[6] = (uint8_t)(src >> 8);
    (*dest)[7] = (uint8_t)src;
    *dest += sizeof(uint64_t);
}

/**
 * Loads int64_t from bytes in big endian
 */
static inline int64_t compost_i64_load(const uint8_t **src)
{
    return (int64_t)compost_u64_load(src);
}

/**
 * Stores int64_t to bytes in big endian
 */
static inline void compost_i64_store(uint8_t **dest, int64_t src)
{
    compost_u64_store(dest, (uint64_t)src);
}

/**
 * Loads 32 bit float from bytes in big endian
 */
static inline float compost_f32_load(const uint8_t **src)
{
    uint32_t tmp = compost_u32_load(src);
    float val;
    memcpy(&val, &tmp, 4);
    return val;
}

/**
 * Stores 32 bit float to bytes in big endian
 */
static inline void compost_f32_store(uint8_t **dest, float src)
{
    uint32_t tmp;
    memcpy(&tmp, &src, 4);
    compost_u32_store(dest, tmp);
}

/**
 * Loads 64 bit double from bytes in big endian
 */
static inline double compost_f64_load(const uint8_t **src)
{
    uint64_t tmp = compost_u64_load(src);
    double val;
    memcpy(&val, &tmp, 8);
    return val;
}

/**
 * @brief Stores 64bit double to bytes in big endian
 */
static inline void compost_f64_store(uint8_t **dest, double src)
{
    uint64_t tmp;
    memcpy(&tmp, &src, 8);
    compost_u64_store(dest, tmp);
}

/**
 * Loads bit precise integer from the backing value
 */
uint32_t compost_bituint_load(const uint8_t *src, uint32_t offset_bits, uint32_t size_bits)
{
    COMPOST_ASSERT(src != NULL);
    uint64_t val = 0;
    uint32_t byte_index = offset_bits / 8;
    uint32_t bits_remaining = size_bits;
    uint32_t bit_position = offset_bits;
    uint64_t mask;
    while (bits_remaining > 0) {
        uint32_t bits_to_fill = 8 - (bit_position % 8);
        uint32_t bits_to_place = bits_remaining <= bits_to_fill ? bits_remaining : bits_to_fill;
        uint32_t shift = bits_to_fill - bits_to_place;
        mask = (0x1L << bits_to_place) - 1;
        uint64_t bitValue = (src[byte_index] >> shift) & mask;

        bit_position += bits_to_place;
        byte_index++;
        bits_remaining -= bits_to_place;

        val |= bitValue << bits_remaining;
    }
    return val;
}

/**
 * Stores bit precise integer to the backing value
 */
void compost_bituint_store(uint8_t *dest, uint32_t value, uint32_t offset_bits, uint32_t size_bits)
{
    COMPOST_ASSERT(dest != NULL);
    uint32_t byte_index = offset_bits / 8;
    uint32_t bits_remaining = size_bits;
    uint32_t bit_position = offset_bits;
    while (bits_remaining > 0) {
        uint32_t bits_to_fill = 8 - (bit_position % 8);
        uint32_t bits_to_place = bits_remaining <= bits_to_fill ? bits_remaining : bits_to_fill;
        uint32_t shift = bits_to_fill - bits_to_place;
        uint64_t mask = (0x1ULL << bits_to_place) - 1;
        uint64_t bitValue = (value >> (bits_remaining - bits_to_place)) & mask;
        dest[byte_index] &= ~(mask << shift);
        dest[byte_index] |= bitValue << shift;

        bit_position += bits_to_place;
        byte_index++;
        bits_remaining -= bits_to_place;
    }
    offset_bits += size_bits;
}
'''))

source_parts.append(SourcePart(True,'''
static inline struct CompostSlice${struct_suffix} compost_slice_${fn_suffix}_load(const uint8_t **src)
{
    uint16_t len = compost_u16_load(src);
    struct CompostSlice${struct_suffix} ret = (struct CompostSlice${struct_suffix}){.ptr = (uint8_t *)(*src), .len = len / sizeof(${type})};
    *src += len;
    return ret;
}

static inline void compost_slice_${fn_suffix}_store(uint8_t **dest, struct CompostSlice${struct_suffix} src)
{
    uint16_t len = src.len * sizeof(${type});
    if (src.ptr != *dest) {
        memcpy(*dest + sizeof(uint16_t), src.ptr, len);
    }
    compost_u16_store(dest, len);
    *dest += len;
}
'''))

source_parts.append(SourcePart(False,'''${serdes}
/******************************************************************************/
/*      B I T F I E L D   M A N I P U L A T I O N   F U N C T I O N S         */
/******************************************************************************/

/**
 * Sets bitfield to the provided value
 */
static inline uint32_t compost_u32_field_set(uint32_t backing, uint32_t bitfield_value, uint32_t offset_bits, uint32_t size_bits)
{
    uint32_t mask = ((1UL << size_bits) - 1) << offset_bits;
    return (backing & mask) | ((bitfield_value << offset_bits) & mask);
}

/**
 * Gets bitfield value as unsigned integer
 */
static inline uint32_t compost_u32_field_get(uint32_t backing, uint32_t offset_bits, uint32_t size_bits)
{
    return (backing >> offset_bits) & ((1UL << size_bits) - 1);
}

/**
 * Sets bitfield to the provided value
 */
static inline uint32_t compost_u64_field_set(uint64_t backing, uint32_t bitfield_value, uint32_t offset_bits, uint32_t size_bits)
{
    uint64_t mask = ((1ULL << size_bits) - 1) << offset_bits;
    return (backing & mask) | ((bitfield_value << offset_bits) & mask);
}

/**
 * Gets bitfield value as unsigned integer
 */
static inline uint32_t compost_u64_field_get(uint64_t backing, uint32_t offset_bits, uint32_t size_bits)
{
    return (backing >> offset_bits) & ((1ULL << size_bits) - 1);
}

/******************************************************************************/
/*            P U B L I C   A P I   F U N C T I O N S                         */
/******************************************************************************/

int16_t compost_header_set(uint8_t *tx_buf, uint16_t tx_buf_size, const struct CompostMsg tx)
{
    if (tx_buf == NULL ) {
        return COMPOST_EINVAL;
    }
    if (tx_buf_size < 4) {
        return COMPOST_EMSGSIZE;
    }
    COMPOST_ASSERT(tx.rpc_id <= 0x0FFF);
    tx_buf[LEN_OFFSET] = tx.len;
    tx_buf[TXN_OFFSET] = tx.txn;
    tx_buf[RPC_ID_HI_AND_RESP_OFFSET] = tx.rpc_id >> 8;
    if (tx.resp) {
        tx_buf[RPC_ID_HI_AND_RESP_OFFSET] |= RESP_MASK;
    }
    tx_buf[RPC_ID_LO_OFFSET] = tx.rpc_id;
    if (tx.len > 255) {
        return COMPOST_EMSGSIZE;
    }
    int16_t msg_size = (tx.len * 4) + 4;
    if (msg_size > tx_buf_size) {
        return COMPOST_EMSGSIZE;
    }
    return msg_size;
}

int16_t compost_msg_process(uint8_t *tx_buf, const uint16_t tx_buf_size, uint8_t *const rx_buf,
                            const uint16_t rx_buf_size)
{
    if ((rx_buf_size < 4) || (tx_buf_size < 4) || tx_buf == NULL || rx_buf == NULL) {
        return COMPOST_EINVAL;
    }

    uint8_t rpc_id_hi = rx_buf[RPC_ID_HI_AND_RESP_OFFSET] & RPC_ID_HI_MASK;
    uint8_t flags = rx_buf[RPC_ID_HI_AND_RESP_OFFSET] & FLAGS_MASK;

    if (flags & ~RESP_MASK) {
        return COMPOST_EFLAGS;
    }

    const struct CompostMsg rx = {.len = rx_buf[LEN_OFFSET],
                                   .txn = rx_buf[TXN_OFFSET],
                                   .resp = (flags & RESP_MASK) != 0,
                                   .rpc_id = ((uint16_t)rpc_id_hi << 8) | rx_buf[RPC_ID_LO_OFFSET],
                                   .payload_buf = rx_buf + PAYLOAD_OFFSET,
                                   .payload_buf_size = rx_buf_size - PAYLOAD_OFFSET};

    struct CompostMsg tx = {.txn = rx.txn,
                             .resp = true,
                             .payload_buf_size = tx_buf_size - PAYLOAD_OFFSET,
                             .payload_buf = tx_buf + PAYLOAD_OFFSET};

    if (rx.txn != 0 && rx.resp == true) {
        return COMPOST_ETXN; // We don't support sending RPC requests, so we can't get a response
    }

    compost_invoke_switch(&tx, rx);

    if (tx.txn || tx.len) {
        return compost_header_set(tx_buf, tx_buf_size, tx);
    } else {
        return 0; // Nothing to send
    }
}

void compost_set_assert_func(void (*assert_func)(uint32_t line))
{
    compost_assert_func = assert_func;
}

'''))

source_parts.append(SourcePart(True,'''
struct CompostSlice${struct_suffix} compost_slice_${fn_suffix}_init(void *ptr, uint16_t len)
{
    return (struct CompostSlice${struct_suffix}){.ptr = ptr, .len = len};
}

struct CompostSlice${struct_suffix} compost_slice_${fn_suffix}_new(struct CompostAlloc *alloc, uint16_t len)
{
    void *ptr = compost_alloc_next(alloc, sizeof(${type}) * len);
    if (ptr == NULL) {
        len = 0;
    }
    return (struct CompostSlice${struct_suffix}){.ptr = ptr, .len = len};
}

${type} compost_slice_${fn_suffix}_get(struct CompostSlice${struct_suffix} target, uint16_t idx)
{
    COMPOST_ASSERT(idx < target.len);
    COMPOST_ASSERT(target.ptr != NULL);
    const uint8_t *ptr = target.ptr + (sizeof(${type}) * idx);
    return compost_${fn_suffix}_load(&ptr);
}

void compost_slice_${fn_suffix}_set(struct CompostSlice${struct_suffix} target, uint16_t idx, ${type} value)
{
    COMPOST_ASSERT(idx < target.len);
    COMPOST_ASSERT(target.ptr != NULL);
    uint8_t *ptr = target.ptr + (sizeof(${type}) * idx);
    compost_${fn_suffix}_store(&ptr, value);
}

uint16_t compost_slice_${fn_suffix}_copy_from(struct CompostSlice${struct_suffix} dest, ${type} *src, uint16_t len)
{
    COMPOST_ASSERT(dest.ptr != NULL);
    COMPOST_ASSERT(src != NULL);
    int len_limit = len <= dest.len ? len : dest.len;
    if ((uint8_t *)src != dest.ptr) {
        for (int i = 0; i < len_limit; i++) {
            compost_slice_${fn_suffix}_set(dest, i, src[i]);
        }
    }
    return len_limit;
}

void compost_slice_${fn_suffix}_copy_to(struct CompostSlice${struct_suffix} src, ${type} *dest)
{
    COMPOST_ASSERT(src.ptr != NULL);
    COMPOST_ASSERT(dest != NULL);
    compost_slice_${fn_suffix}_ncopy_to(src, dest, src.len);
}

uint16_t compost_slice_${fn_suffix}_ncopy_to(struct CompostSlice${struct_suffix} src, ${type} *dest, uint16_t len)
{
    COMPOST_ASSERT(src.ptr != NULL);
    COMPOST_ASSERT(dest != NULL);
    int len_limit = len <= src.len ? len : src.len;
    if (src.ptr != (uint8_t *)dest) {
        for (int i = 0; i < len_limit; i++) {
            dest[i] = compost_slice_${fn_suffix}_get(src, i);
        }
    }
    return len_limit;
}

struct CompostSlice${struct_suffix} compost_slice_${fn_suffix}_copy(struct CompostSlice${struct_suffix} dest, struct CompostSlice${struct_suffix} src)
{
    COMPOST_ASSERT(src.ptr != NULL);
    COMPOST_ASSERT(dest.ptr != NULL);
    uint16_t len_limit = compost_min(src.len, dest.len);
    dest.len = len_limit;
    if (src.ptr != dest.ptr) {
        memcpy(dest.ptr, src.ptr, len_limit * sizeof(${type}));
    }
    return dest;
}
'''))

source_parts.append(SourcePart(False,'''

struct CompostAlloc compost_alloc_init(uint8_t *buffer, uint16_t len)
{
    return (struct CompostAlloc){.suffixes = NULL,
                                 .suffixes_len = 0,
                                 .alloc_ctr = 0,
                                 .ptr = buffer,
                                 .buffer = compost_slice_u8_init(buffer, len)};
}

void compost_alloc_set_suffixes(struct CompostAlloc *alloc, uint16_t *suffixes, uint16_t len)
{
    COMPOST_ASSERT(alloc != NULL);
    COMPOST_ASSERT(suffixes != NULL);
    alloc->suffixes = suffixes;
    alloc->suffixes_len = len;
}

void compost_alloc_reset(struct CompostAlloc *alloc)
{
    COMPOST_ASSERT(alloc != NULL);
    alloc->suffixes = NULL;
    alloc->suffixes_len = 0;
    alloc->alloc_ctr = 0;
    alloc->ptr = alloc->buffer.ptr;
}

void *compost_alloc_next(struct CompostAlloc *alloc, uint16_t len)
{
    COMPOST_ASSERT(alloc != NULL);
    int capacity = alloc->buffer.len - (alloc->ptr - alloc->buffer.ptr);
    if ((int)len > capacity ||
        (alloc->suffixes != NULL && alloc->alloc_ctr >= alloc->suffixes_len)) {
        return NULL;
    }

    void *ret = (void *)(alloc->ptr);
    alloc->ptr += len;

    if (alloc->suffixes_len > 0) {
        COMPOST_ASSERT(alloc->suffixes != NULL);
        alloc->ptr += alloc->suffixes[alloc->alloc_ctr];
    }
    alloc->alloc_ctr++;

    return ret;
}

struct CompostSliceU8 compost_str_new(struct CompostAlloc *alloc, const char *cstr)
{
    COMPOST_ASSERT(alloc != NULL);
    COMPOST_ASSERT(cstr != NULL);
    size_t len = strlen(cstr);
    struct CompostSliceU8 ret = compost_slice_u8_new(alloc, len);
    compost_slice_copy_from(ret, (void *)cstr, len);
    return ret;
}

void compost_str_copy(struct CompostSliceU8 dest, const char *src)
{
    COMPOST_ASSERT(dest.ptr != NULL);
    COMPOST_ASSERT(src != NULL);
    size_t len = strlen(src);
    compost_slice_copy_from(dest, (void *)src, len);
    if (len < dest.len) {
        for (int i = len; i < dest.len; i++) {
            compost_slice_set(dest, i, 0);
        }
    }
}

'''))

content = ""
for part in source_parts:
    if part.is_slice_template:
        t = Template(part.content)
        content += t.substitute(fn_suffix="u8", struct_suffix="U8", type="uint8_t")
        content += t.substitute(fn_suffix="i8", struct_suffix="I8", type="int8_t")
        content += t.substitute(fn_suffix="u16", struct_suffix="U16", type="uint16_t")
        content += t.substitute(fn_suffix="i16", struct_suffix="I16", type="int16_t")
        content += t.substitute(fn_suffix="u32", struct_suffix="U32", type="uint32_t")
        content += t.substitute(fn_suffix="i32", struct_suffix="I32", type="int32_t")
        content += t.substitute(fn_suffix="u64", struct_suffix="U64", type="uint64_t")
        content += t.substitute(fn_suffix="i64", struct_suffix="I64", type="int64_t")
        content += t.substitute(fn_suffix="f32", struct_suffix="F32", type="float")
        content += t.substitute(fn_suffix="f64", struct_suffix="F64", type="double")
    else:
        content += part.content
