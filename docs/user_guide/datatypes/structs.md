# Structs

Structs are created with {func}`~compost_rpc.struct` decorator. They may
contain primitive types, enums, bytes, strings, lists and even other structs.

It is important to note that structs are basically invisible when inspecting
the raw message frames - it will look the same as if all member values were sent
as separate arguments. In other words, the layout of struct is not part of
the message, only the data.

```{code-block} python
:caption: What you define in protocol_def.py

from compost_rpc import struct

@struct
class LogMessage:
    severity: U8
    tag: U8
    message: str
```

```{code-block} c
:caption: What you get in compost.h

struct LogMessage {
    uint8_t severity;
    uint8_t tag;
    struct CompostSliceU8 message;
};
```
