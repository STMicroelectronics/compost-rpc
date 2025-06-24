# Data types

When defining the remote function or notification signatures, the user may
choose arguments and return values of several types. These types mostly make
sense only in a context of Python definition file. Compost messages do not
contain any metadata about contents, so it is basically possible to send
anything. However, a type safe interface will be ensured by the [code generated
from the definition file](../generating_code).

This chapter goes through all the features and restrictions.

## Primitive types

Table below lists all supported primitive Compost types, with the respective
native type for each supported language.

Compost                 | C        | Python | C#     | Description
-------                 | -------- | ------ | ------ | -----------
[U8](#compost_rpc.U8)   | uint8_t  | int    | byte   | 8-bit unsigned integer
[I8](#compost_rpc.I8)   | int8_t   | int    | sbyte  | 8-bit signed integer
[U16](#compost_rpc.U16) | uint16_t | int    | ushort | 16-bit unsigned integer
[I16](#compost_rpc.I16) | int16_t  | int    | short  | 16-bit signed integer
[U32](#compost_rpc.U32) | uint32_t | int    | uint   | 32-bit unsigned integer
[I32](#compost_rpc.I32) | int32_t  | int    | int    | 32-bit signed integer
[U64](#compost_rpc.U64) | uint64_t | int    | ulong  | 64-bit unsigned integer
[I64](#compost_rpc.I64) | int64_t  | int    | long   | 64-bit signed integer
[F32](#compost_rpc.F32) | float    | float  | float  | 32-bit floating point - IEEE 754 `binary32` or `single`
[F64](#compost_rpc.F64) | double   | float  | double | 64-bit floating point - IEEE 754 `binary64` or `double`

All primitive types are always transmitted in big-endian.

## Composite types

Primitive types can be further wrapped into more complex types.

```{toctree}
:maxdepth: 1

enums
structs
lists
```

## How you can use each type

Context                      | Primitive type | Enum    | List | Struct
---------------------------- | -------------- | ------- | ---- | ------
Remote function parameter    | ✅             | ✅     | ✅    | ✅
Remote function return value | ✅             | ✅     | ✅    | ✅
Member of `compost_struct`   | ✅             | ✅     | ✅    | ✅
Inner type of a list         | ✅             | ❌     | ❌    | ❌
Notification parameter       | ✅             | ✅     | ✅    | ✅