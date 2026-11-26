# Enums

Enums are created by applying the {func}`~compost_rpc.enum` decorator to an
`IntEnum` class. Pass the backing type to the decorator: supported backings are
`I8`, `U8`, `I16`, and `BitU[n]`, where `n` is a bit width from 0 to 32 inclusive.
The backing alias describes the wire format; it is not a base class.

What you define in protocol_def.py:

```python
from enum import IntEnum
from compost_rpc import U8, enum

@enum(U8)
class Result(IntEnum):
    OK = 0
    ERR = 1
```

What you get in compost.h:

```c
enum Result {
    RESULT_OK = 0x00,
    RESULT_ERR = 0x01
};
```
