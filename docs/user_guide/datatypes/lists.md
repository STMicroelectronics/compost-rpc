# Lists

Compost supports a variable-sized array type called "list" which sends the length with the data.
Lists are defined as `list[T]` in Python definition where **T** is the primitive type
of the elements in the list. You can also use `bytes`.
In Python you use the type as a normal list, but respect the internal primitive type.
Generated code for other languages will use their native list or slice type.

Compost     | C                 | Python      | C#          | Description
----------- | ----------------- | ----------- | ----------- | -----------
list[**T**] | CompostSlice**T** | list[**T**] | List<**T**> | List type with internal type **T**

## List interface in C

Unfortunately on the MCU side in plain C, there is no native list or slice type. Therefore, a custom
`CompostSliceT` type is used to represent lists. It does not work as a list in traditional sense,
meaning that the number of elements cannot be dynamically changed. Technically it is just a pointer
that manages a "slice" in the memory (typically somewhere in the RX/TX buffer) with defined length
and type of elements. When the `CompostSliceT` is created, no data is manipulated in the buffer to
maintain zero-copy approach. Obviously, when accessing the data or copying it to the native array,
the data will have to be swapped if the MCU architecture is not big endian, however, this potential
performance penalty is completely in the hands of a user.

### `CompostSliceT` interface

When the dynamic list is contained within a RPC function parameters, it will be
passed to the RPC function as `CompostSliceT`. Every slice contains the number
of elements and a pointer to a data buffer. To access the data use the
`compost_slice` macros from the table below.

Member     | Type                  | Description
---------- | --------------------- | ------------------
data       | `uint8_t*`            | *Pointer to the data buffer*
len        | `uint16_t`            | *Length in number of elements (not bytes)*

Macro                        | Parameters                                               | Description
---------------------------- | -------------------------------------------------------- | ------------------
compost_slice_get            | `struct CompostSliceT target`, `uint16_t idx`            | *Gets element from the specified index*
compost_slice_set            | `struct CompostSliceT target`, `uint16_t idx`, `T value` | *Sets value of element at the specified index*
compost_slice_copy           | `struct CompostSliceT dest`, `struct CompostSliceT src`  | *Copies CompostSlice to CompostSlice*
compost_slice_copy_to        | `struct CompostSliceT src`, `T* dest`                    | *Copies the entire CompostSlice to the native array.*
compost_slice_copy_from      | `struct CompostSliceT dest`, `T* src`, `uint16_t len`    | *Copies the native array to the CompostSlice.*

For example, to get the sum of 32-bit integers passed to the device in a `CompostSliceI32`, you
can do the following:

```c
uint32_t sum_list_handler(struct CompostSliceU32 data)
{
    int sum = 0;
    for (int i = 0; i < data.len; i++)
        sum += compost_slice_get(data, i);
    return sum;
}
```

When the list is used as a return value, the user has to initialize it in the RPC function.
The recommended way is to utilize allocator passed alongside user-defined parameters by calling the
`compost_slice_T_new` function. This ensures that the slice will be allocated directly in the
TX buffer. When the return value is a struct with dynamic list members, `{struct_name}_init`
function should be used instead. This generated function takes as a parameter the allocator and
lengths of each list member. This way, you can avoid errors resulting from allocations of
slices in different order than their order in the struct definition. Examples of both approaches
look like this:

```{code-block} c
:caption: Single list

struct CompostSliceU32 get_fibonacci_handler(uint32_t n, struct CompostAlloc alloc)
{
    struct CompostSliceU32 tmp = compost_slice_u32_new(&alloc, n);
    if (n > 0)
        compost_slice_set(tmp, 0, 0);
    if (n > 1)
        compost_slice_set(tmp, 1, 1);
    for (int i = 2; i < n; i++) {
        uint32_t a = compost_slice_get(tmp, i - 1);
        uint32_t b = compost_slice_get(tmp, i - 2);
        compost_slice_set(tmp, i, a + b);
    }
    return tmp;
}
```

```{code-block} c
:caption: Structure with lists

struct ArithmeticSeq {
    int32_t start;
    int32_t d;
    struct CompostSliceI32 seq;
};

struct ArithmeticSeq arithmetic_seq_handler(int32_t start, int32_t d, uint32_t n, struct CompostAlloc alloc)
{
    struct ArithmeticSeq tmp = ArithmeticSeq_init(&alloc, n);
    tmp.start = start;
    tmp.d = d;
    int32_t a = start;
    for (int i = 0; i < n; i++) {
        a += i*d;
        compost_slice_set(tmp.data, i, a);
    }
    return tmp;
}
```

## Strings

Strings are transported as a list of bytes.

Compost | C                 | Python      | C#
------- | ----------------- | ----------- | ------
str     | CompostSliceU8    | str         | string
