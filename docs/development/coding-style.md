# Coding style

## Generally

The suggested coding style is meant as a starting point, but you can deviate
from it if you have a reason.

## C

All C code is formatted with ClangFormat using configuration file
.clang-format available in the repository.

We use PascalCase for custom types like structs and snake_case for everything
else.

Example:

```c
struct CompostSliceU8 {
    uint8_t *ptr;
    uint16_t len;
};

uint8_t compost_slice_u8_get(struct CompostSliceU8 target, uint16_t idx);
```

## Python

All Python code is formatted using Ruff with default rules except for maximum
line length.
