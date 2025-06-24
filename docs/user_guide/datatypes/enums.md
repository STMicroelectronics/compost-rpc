# Enums

Enums are created with {func}`~compost_rpc.enum` decorator. For a backing
type, you can choose between signed and unsigned 8-bit integers. Bigger enums
are not yet supported.

What you define in protocol_def.py:

```python
from enum import Enum
from compost_rpc import U8, enum

@enum
class Result(U8, Enum):
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
