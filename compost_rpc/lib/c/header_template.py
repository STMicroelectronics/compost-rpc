from string import Template

header_template_head = '''#ifndef ${filename_caps}_H
#define ${filename_caps}_H

/** @file
 * Compost C header file
 */

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>

${version_info}

#define COMPOST_ERR      -1  ///< Generic error
#define COMPOST_EINVAL   -22 ///< Invalid argument
#define COMPOST_EMSGSIZE -90 ///< Message too long
#define COMPOST_EFLAGS   -91 ///< Reserved flags set
#define COMPOST_ETXN     -92 ///< Unexcepted transaction value

struct CompostMsg {
    uint16_t len;
    uint16_t rpc_id;
    const uint16_t payload_buf_size;
    uint8_t txn;
    bool resp;
    uint8_t *payload_buf;
};

// forward declare compost_alloc to allow usage in compost_slice_xx_new function
struct CompostAlloc;

/******************************************************************************/
/*                            S L I C E S                                     */
/******************************************************************************/
'''

slice_template = '''
struct CompostSlice${struct_suffix} {
    /** Pointer to first element. */
    uint8_t *ptr;
    /** Length in number of elements (not bytes). */
    uint16_t len;
};

/**
 * @brief Initializes CompostSlice${struct_suffix} for storing the ${type} array from allocator
 * @param alloc Pointer to the allocator
 * @param len Initial length of the data (in slice elements)
 */
struct CompostSlice${struct_suffix} compost_slice_${fn_suffix}_new(struct CompostAlloc *alloc, uint16_t len);

/**
 * @brief Gets the ${type} element from the specified index.
 * @param target Target CompostSlice${struct_suffix}
 * @param idx Index of the element
 */
${type} compost_slice_${fn_suffix}_get(struct CompostSlice${struct_suffix} target, uint16_t idx);

/**
 * @brief Stores the ${type} value to the specified index of the slice.
 * @param target Target CompostSlice${struct_suffix}
 * @param idx Index of the element
 * @param value Value to store
 */
void compost_slice_${fn_suffix}_set(struct CompostSlice${struct_suffix} target, uint16_t idx, ${type} value);

/**
 * @brief Copies the native ${type} array to the CompostSlice${struct_suffix}.
 * If the length of the slice is lower than the length of the
 * array, copied data will be truncated.
 * @param dest Destination slice
 * @param src Pointer to the source array
 * @param len Number of elements to copy
 * @return Number of elements copied
 */
uint16_t compost_slice_${fn_suffix}_copy_from(struct CompostSlice${struct_suffix} dest, ${type} *src, uint16_t len);

/**
 * @brief Copies the entire CompostSlice${struct_suffix} to native ${type} array.
 * @param src Source {struct_suffix} slice
 * @param dest Pointer to the destination array
 */
void compost_slice_${fn_suffix}_copy_to(struct CompostSlice${struct_suffix} src, ${type} *dest);

/**
 * @brief Copies the specified number of elements from the slice to native ${type} array.
 * @param src Source CompostSlice${struct_suffix}
 * @param dest Pointer to the destination array
 * @param len Number of elements to copy
 * @return Number of elements to copied
 */
uint16_t compost_slice_${fn_suffix}_ncopy_to(struct CompostSlice${struct_suffix} src, ${type} *dest, uint16_t len);

/**
 * @brief Copies the entire slice to another slice.
 * @param dest Destination CompostSlice${struct_suffix}
 * @param src Source CompostSlice${struct_suffix}
 * @return Slice of the destination memory containing copied data
 */
struct CompostSlice${struct_suffix} compost_slice_${fn_suffix}_copy(struct CompostSlice${struct_suffix} dest, struct CompostSlice${struct_suffix} src);
'''

header_template_tail = '''

/**
  @brief Gets the element from the specified index
  @param target Target slice
  @param idx Index of the element
*/
#define compost_slice_get(target, index)                 \\
    _Generic((target),                                   \\
        struct CompostSliceU8: compost_slice_u8_get,   \\
        struct CompostSliceU16: compost_slice_u16_get, \\
        struct CompostSliceU32: compost_slice_u32_get, \\
        struct CompostSliceU64: compost_slice_u64_get, \\
        struct CompostSliceI8: compost_slice_i8_get,   \\
        struct CompostSliceI16: compost_slice_i16_get, \\
        struct CompostSliceI32: compost_slice_i32_get, \\
        struct CompostSliceI64: compost_slice_i64_get, \\
        struct CompostSliceF32: compost_slice_f32_get, \\
        struct CompostSliceF64: compost_slice_f64_get)(target, index)

/**
  @brief Sets value of the element at the specified index
  @param target Target slice
  @param idx Index of the element
  @param value New value
*/
#define compost_slice_set(target, idx, value)            \\
    _Generic((target),                                   \\
        struct CompostSliceU8: compost_slice_u8_set,   \\
        struct CompostSliceU16: compost_slice_u16_set, \\
        struct CompostSliceU32: compost_slice_u32_set, \\
        struct CompostSliceU64: compost_slice_u64_set, \\
        struct CompostSliceI8: compost_slice_i8_set,   \\
        struct CompostSliceI16: compost_slice_i16_set, \\
        struct CompostSliceI32: compost_slice_i32_set, \\
        struct CompostSliceI64: compost_slice_i64_set, \\
        struct CompostSliceF32: compost_slice_f32_set, \\
        struct CompostSliceF64: compost_slice_f64_set)(target, idx, value)

/**
    @brief Copies the entire slice to another slice.
    @param dest Destination slice
    @param src Source slice
    @return Slice of the destination memory containing copied data
*/
#define compost_slice_copy(dest, src)                     \\
    _Generic((dest),                                      \\
        struct CompostSliceU8: compost_slice_u8_copy,   \\
        struct CompostSliceU16: compost_slice_u16_copy, \\
        struct CompostSliceU32: compost_slice_u32_copy, \\
        struct CompostSliceU64: compost_slice_u64_copy, \\
        struct CompostSliceI8: compost_slice_i8_copy,   \\
        struct CompostSliceI16: compost_slice_i16_copy, \\
        struct CompostSliceI32: compost_slice_i32_copy, \\
        struct CompostSliceI64: compost_slice_i64_copy, \\
        struct CompostSliceF32: compost_slice_f32_copy, \\
        struct CompostSliceF64: compost_slice_f64_copy)(dest, src)

/**
    @brief Copies the entire slice to native array.
    @param src Source slice
    @param dest Pointer to the destination array
    @return Number of elements copied
*/
#define compost_slice_copy_to(src, dest)                     \\
    _Generic((src),                                          \\
        struct CompostSliceU8: compost_slice_u8_copy_to,   \\
        struct CompostSliceU16: compost_slice_u16_copy_to, \\
        struct CompostSliceU32: compost_slice_u32_copy_to, \\
        struct CompostSliceU64: compost_slice_u64_copy_to, \\
        struct CompostSliceI8: compost_slice_i8_copy_to,   \\
        struct CompostSliceI16: compost_slice_i16_copy_to, \\
        struct CompostSliceI32: compost_slice_i32_copy_to, \\
        struct CompostSliceI64: compost_slice_i64_copy_to, \\
        struct CompostSliceF32: compost_slice_f32_copy_to, \\
        struct CompostSliceF64: compost_slice_f64_copy_to)(src, dest)

/**
    @brief Copies the specified number of elements from the slice to native array.
    @param src Source slice
    @param dest Pointer to the destination array
    @param len Number of elements to copy
    @return Number of elements copied
*/
#define compost_slice_ncopy_to(src, dest, len)                \\
    _Generic((src),                                           \\
        struct CompostSliceU8: compost_slice_u8_ncopy_to,   \\
        struct CompostSliceU16: compost_slice_u16_ncopy_to, \\
        struct CompostSliceU32: compost_slice_u32_ncopy_to, \\
        struct CompostSliceU64: compost_slice_u64_ncopy_to, \\
        struct CompostSliceI8: compost_slice_i8_ncopy_to,   \\
        struct CompostSliceI16: compost_slice_i16_ncopy_to, \\
        struct CompostSliceI32: compost_slice_i32_ncopy_to, \\
        struct CompostSliceI64: compost_slice_i64_ncopy_to, \\
        struct CompostSliceF32: compost_slice_f32_ncopy_to, \\
        struct CompostSliceF64: compost_slice_f64_ncopy_to)(src, dest, len)

/**
  @brief Copies the native array to the slice.

  If the length of the slice is lower than the length of the
  array, copied data will be truncated.
  @param dest Destination slice
  @param src Pointer to the source array
  @param len Number of elements to copy
  @return Number of elements copied
 */
#define compost_slice_copy_from(dest, src, len)                \\
    _Generic((dest),                                           \\
        struct CompostSliceU8: compost_slice_u8_copy_from,   \\
        struct CompostSliceU16: compost_slice_u16_copy_from, \\
        struct CompostSliceU32: compost_slice_u32_copy_from, \\
        struct CompostSliceU64: compost_slice_u64_copy_from, \\
        struct CompostSliceI8: compost_slice_i8_copy_from,   \\
        struct CompostSliceI16: compost_slice_i16_copy_from, \\
        struct CompostSliceI32: compost_slice_i32_copy_from, \\
        struct CompostSliceI64: compost_slice_i64_copy_from, \\
        struct CompostSliceF32: compost_slice_f32_copy_from, \\
        struct CompostSliceF64: compost_slice_f64_copy_from)(dest, src, len)

struct CompostAlloc {
    uint8_t *ptr;
    uint16_t *suffixes;
    struct CompostSliceU8 buffer;
    uint16_t suffixes_len;
    uint16_t alloc_ctr;
};

/**
 * @brief Processes incoming Compost message and prepares the response.
 * Call this function for every Compost message you receive.
 * @param tx_buf Pointer to the transmit buffer where to put an outgoing message
 * @param tx_buf_size Transmit buffer size in bytes
 * @param rx_buf Pointer to the buffer with incoming message
 * @param rx_buf_size Receive buffer valid data size in bytes
 * @return Size of valid data in bytes in the transmit buffer, or zero if there
 * is no message to send, or negative value if there was an error
 */
int16_t compost_msg_process(uint8_t *, const uint16_t, uint8_t *const, const uint16_t);

/**
 * @brief Initializes an allocator.
 * @param buffer Pointer to buffer used for allocation
 * @param len Length of the buffer
 * @param alloc_sizes Pointer to array used for storing allocated sizes
 * @param alloc_ptrs Pointer to array used for storing pointers to allocations
 */
struct CompostAlloc compost_alloc_init(uint8_t *buffer, uint16_t len);

/**
 * @brief Sets the suffix array and allocation limit.
 *
 * Each element in suffixes represents the number of bytes which will be added to each subsequent
 * allocation, up to the length of the array.
 * @param alloc Pointer to allocator
 * @param suffixes Pointer to array of suffixes
 * @param len Number of suffixes / allocation limit
 */

void compost_alloc_set_suffixes(struct CompostAlloc *alloc, uint16_t *suffixes, uint16_t len);

/**
 * @brief Resets the allocator to the beginning of buffer.
 * @param alloc Pointer to allocator
 */
void compost_alloc_reset(struct CompostAlloc *alloc);

/**
 * @brief Allocates selected amount of bytes.
 * @param alloc Pointer to allocator
 * @param len Number of bytes
 */
void *compost_alloc_next(struct CompostAlloc *alloc, uint16_t len);

/**
 * @brief Allocates new compost_slice from C string.
 * @param alloc Pointer to allocator
 * @param cstr Null-terminated C string
 */
struct CompostSliceU8 compost_str_new(struct CompostAlloc *alloc, const char *cstr);

/**
 * @brief Copies C string into compost_slice.
 * In case the string is shorter than space in slice, the remaining bytes are set to zero.
 * If the C string is longer, it will be truncated.
 * @param dest Destination CompostSliceU8
 * @param src Source null-terminated C string
 */
void compost_str_copy(struct CompostSliceU8 dest, const char *src);

/**
 * @brief Registers a custom assert function
 *
 * @param assert_func Function pointer to the custom assert function or NULL to reset to default
 */
void compost_set_assert_func(void (*assert_func)(uint32_t));
${protocol}
#endif /* COMPOST_H */
'''

content = header_template_head
t = Template(slice_template)
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
content += header_template_tail
