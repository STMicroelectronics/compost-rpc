# Message structure

The common message structure is shown in the following diagram:

```{image} /_static/image/getting_started/msg_structure.svg
:class: only-light
```

```{image} /_static/image/getting_started/msg_structure_white.svg
:class: only-dark
```

| Field     | Size    | Description |
| --------- | ------- | ----------- |
| LEN       | 8 bits  | Length of the payload in 32-bit words. |
| TXN       | 8 bits  | Transaction number. Values link response to the request. (Response is sent with *TXN* value of the request) |
| Reserved  | 2 bits  | These bits are reserved for future use. Must be 0. |
| RESP      | 1 bit   | Response flag. 0 = Request, 1 = Response |
| RPC_ID    | 12 bits | Each RPC[^1] has a unique *RPC_ID* assigned to it. MSB[^2] first. |
| PAYLOAD   | 4 × *LEN* bytes | Meaning is defined by the *RPC_ID* and the *RESP* bit. All data is laid out with no gaps, there is no padding for alignment. |

[^1]: Remote Procedure Call
[^2]: Most Significant Byte

```{important}
All primitive types in *data* are always transmitted as big-endian.
```

```{note}
We assume that byte is always 8 bits long. Byte is equal to octet in Compost.
```

## Example messages

Request and response messages for reading a byte from 32bit address.

### Function signatures

In your protocol definition file you would define the RPC call using Python syntax:

```python
@rpc(0x001)
def read8(address: U32) -> U8:
   """Reads 8 bits of data from the specified address"""
```

The corresponding signature in C that Compost generates for you:

```c
uint8_t read8(uint32_t address);
```

### Request

Request to call

```python
read8(0x60000000)
```

corresponds to the following Compost message

`[0x01, 0x02, 0x00, 0x01, 0x60, 0x00, 0x00, 0x00]`

```{image} /_static/image/getting_started/example_read8_req.svg
:class: only-light
```

```{image} /_static/image/getting_started/example_read8_req_white.svg
:class: only-dark
```

### Response

Response corresponding to result `0xFF`:

`[0x01, 0x02, 0x10, 0x01, 0xFF, 0xXX, 0xXX, 0xXX]`

```{image} /_static/image/getting_started/example_read8_resp.svg
:class: only-light
```

```{image} /_static/image/getting_started/example_read8_resp_white.svg
:class: only-dark
```
