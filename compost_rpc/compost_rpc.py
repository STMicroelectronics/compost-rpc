"""Main module of Compost
"""

__version__ = "0.6.0-dev"

import sys
import subprocess
import logging
import threading
import typing
import socket
from string import Template
from dataclasses import dataclass, astuple
from queue import Queue, Empty
from pathlib import Path
from datetime import datetime
from inspect import Parameter, signature, Signature
from typing import Any, Callable, Concatenate, ParamSpec, TypeVar, runtime_checkable, get_args, get_origin
from abc import ABC, abstractmethod
from struct import Struct, unpack_from, pack
from enum import Enum

MIN_PYTHON = (3, 10)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required." % MIN_PYTHON)

logger = logging.getLogger(__name__)

try:
    import colorful as cf
    import traceback
    COMPOST_COLORS = {
        'info': '#6CA6CD',
        'warn': '#EEEE00',
        'err': '#BB0000',
        'success': '#00CD66'
    }
    cf.update_palette(COMPOST_COLORS)
    # Set colors for exceptions
    def colorful_exception_hook(exc_type, exc_value, exc_traceback):
        # Call the default exception hook for KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        traceback_lines = [str(
                cf.bold(cf.err(line)) if line.startswith(exc_type.__name__)
                else cf.info(line) if not line.startswith(' ')
                else line
            )
            for line in traceback.format_exception(exc_type, exc_value, exc_traceback)
        ]
        traceback_message = ''.join(traceback_lines)
        print(traceback_message)
    sys.excepthook = colorful_exception_hook
except ImportError:
    class ColorfulDummy:
        def __getattr__(cls, name):
            def pipe (s: str) -> str:
                return s
            return pipe
    cf = ColorfulDummy()


class _String:
    def __init__(self, val: str = "", indent: int = 0) -> None:
        self._indent = indent
        self._str = val

    def __add__(self, other):
        return _String(self._str + str(other), self._indent)

    def __str__(self) -> str:
        return self._str

    def indent_inc(self):
        self._indent += 1

    def indent_dec(self):
        self._indent -= 1
        if self._indent < 0:
            self._indent = 0

    def add(self, lines: str | tuple, end: str = "\n"):
        indent = "    " * self._indent
        if isinstance(lines, tuple):
            for line in lines:
                self._str += f"{indent}{line}{end}"
        else:
            self._str += f"{indent}{lines}{end}"


_C = TypeVar("C")

def _ceiling_division(n: int, d: int):
    return -(n // -d)

def _scase(arg: str, to_upper: bool = True) -> str:
    "Convert CamelCase to snake_case"
    if (len(arg) == 0):
        return arg
    out = [ c if c.islower() else f"_{c}"
        for c in arg[1:]
    ]
    out = "".join([arg[0], *out])
    return out.upper() if to_upper else out.lower()

def _pcase(arg: str) -> str:
    "Convert snake_case to PascalCase"
    if (len(arg) == 0):
        return arg
    s = arg.split("_")
    out = []
    for i, part in enumerate(s):
        if len(part) == 0 or part.isspace():
            continue
        part_next = s[i+1] if i+1 < len(s) else " "
        out.append(part[0].upper() + part[1:].lower() if len(part) > 1 else part[0].upper())
        if (part[-1].isdigit() and part_next[0].isdigit()):
            out.append("_")
    return "".join(out)

def _ccase(arg: str) -> str:
    "Convert snake_case to lower camelCase"
    if (len(arg) == 0):
        return arg
    out = _pcase(arg)
    return "".join([out[0].lower(), *out[1:]]) if len(out) > 1 else out[0].lower()

def _issubclass(cls: Any, class_or_tuple: type | tuple[type]) -> bool:
    """Custom version of issubclass that does not raise an exception if cls is not a class, but
    returns False."""
    try:
        return issubclass(cls, class_or_tuple)
    except TypeError:
        return False


class RpcError(Exception):
    """Generic RPC error."""

    pass


class RequestTimeoutError(RpcError):
    """Response not received in time."""

    pass


class RequestError(RpcError):
    """Received error message instead of a result."""

    pass


class UnknownRpcIdError(RpcError):
    """Remote does not know the rpc_id. Incompatible protocol."""

    pass


class UnexpectedTxnError(RpcError):
    """Received unexpected txn value."""

    pass


class MemUnit:
    """Represents a memory size that can be specified in bits or bytes. Now immutable."""

    BITS_PER_BYTE = 8

    @classmethod
    def from_bytes(cls, bytes_: int) -> "MemUnit":
        return cls(bits=bytes_ * cls.BITS_PER_BYTE)

    def __init__(self, bits: int = 0):
        self._bits = bits

    @property
    def bits(self) -> int:
        return self._bits

    @bits.setter
    def bits(self, value: int):
        self._bits = value

    @property
    def bytes(self) -> int:
        return (self.bits + self.BITS_PER_BYTE - 1) // self.BITS_PER_BYTE

    @bytes.setter
    def bytes(self, value: int):
        self._bits = value * self.BITS_PER_BYTE

    def byte_align(self):
        """Aligns the MemUnit to the next byte boundary if not already aligned."""
        if not self.is_byte_aligned():
            self._bits = self.bytes * self.BITS_PER_BYTE

    def is_byte_aligned(self) -> bool:
        return (self._bits % self.BITS_PER_BYTE) == 0

    def __repr__(self) -> str:
        return f"MemUnit(bits={self.bits}, bytes={self.bytes})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MemUnit):
            return NotImplemented
        return self.bits == other.bits

    def __add__(self, other: "MemUnit") -> "MemUnit":
        if not isinstance(other, MemUnit):
            raise TypeError("Expected MemUnit instance")
        return MemUnit(self.bits + other.bits)


class CompostSlice(bytes):
    """Represents dynamically sized array of U8"""

    size = MemUnit()
    fmt = ""


class CompostString(str):
    """String based on the compost_slice_u8"""

    size = MemUnit()
    fmt = ""


class U64(int):
    """64-bit unsigned integer"""

    size = MemUnit(64)
    fmt = ">Q"

    def __new__(cls, value, *args, **kwargs):
        if value < 0:
            raise ValueError("Unsigned type cannot hold negative value")
        if value >= 2**64:
            raise ValueError("Value too large for 64 bit unsigned integer")
        return super().__new__(cls, value)

    def __str__(self):
        return "%d" % int(self)

    def __repr__(self):
        return "U64(%d)" % int(self)


class I64(int):
    """64-bit signed integer"""

    size = MemUnit(64)
    fmt = ">q"

    def __new__(cls, value, *args, **kwargs):
        # TODO
        if value < -(2**64):
            raise ValueError("Unsigned type cannot hold negative value")
        if value >= 2**64:
            raise ValueError("Value too large for 64 bit unsigned integer")
        return super().__new__(cls, value)

    def __str__(self):
        return "%d" % int(self)

    def __repr__(self):
        return "I64(%d)" % int(self)


class U32(int):
    """32-bit unsigned integer"""

    size = MemUnit(32)
    fmt = ">I"

    def __new__(cls, value, *args, **kwargs):
        if value < 0:
            raise ValueError("Unsigned type cannot hold negative value")
        if value >= 2**32:
            raise ValueError("Value too large for 32 bit unsigned integer")
        return super().__new__(cls, value)

    def __str__(self):
        return "%d" % int(self)

    def __repr__(self):
        return "U32(%d)" % int(self)


class I32(int):
    """32-bit signed integer"""

    size = MemUnit(32)
    fmt = ">i"

    def __new__(cls, value, *args, **kwargs):
        # TODO
        if value < -(2**31):
            raise ValueError("Unsigned type cannot hold negative value")
        if value >= 2**31:
            raise ValueError("Value too large for 32 bit unsigned integer")
        return super().__new__(cls, value)

    def __str__(self):
        return "%d" % int(self)

    def __repr__(self):
        return "I32(%d)" % int(self)


class U16(int):
    """16-bit unsigned integer"""

    size = MemUnit(16)
    fmt = ">H"

    def __new__(cls, value, *args, **kwargs):
        if value < 0:
            raise ValueError("Unsigned type cannot hold negative value")
        if value >= 2**16:
            raise ValueError("Value too large for 16 bit unsigned integer")
        return super().__new__(cls, value)

    def __str__(self):
        return f"{int(self)}"

    def __repr__(self):
        return f"U16({int(self)})"


class I16(int):
    """16-bit signed integer"""

    size = MemUnit(16)
    fmt = ">h"

    def __new__(cls, value, *args, **kwargs):
        # TODO
        if value < -(2**15):
            raise ValueError("Value is less than minimum for 16 bit signed integer")
        if value >= 2**15:
            raise ValueError("Value too large for 16 bit signed integer")
        return super().__new__(cls, value)

    def __str__(self):
        return f"{int(self)}"

    def __repr__(self):
        return f"I16({int(self)})"


class U8(int):
    """8-bit unsigned integer"""

    size = MemUnit(8)
    fmt = ">B"

    def __new__(cls, value, *args, **kwargs):
        if value < 0:
            raise ValueError("Unsigned type cannot hold negative value")
        if value >= 2**8:
            raise ValueError("Value too large for 8 bit unsigned integer")
        return super().__new__(cls, value)

    def __str__(self):
        return f"{int(self)}"

    def __repr__(self):
        return f"U8({int(self)})"


class I8(int):
    """8-bit signed integer"""

    size = MemUnit(8)
    fmt = ">b"

    def __new__(cls, value, *args, **kwargs):
        # TODO
        if value < -(2**7):
            raise ValueError("Value is less than minimum for 8 bit signed integer")
        if value >= 2**7:
            raise ValueError("Value too large for 8 bit signed integer")
        return super().__new__(cls, value)

    def __str__(self):
        return f"{int(self)}"

    def __repr__(self):
        return f"I8({int(self)})"


class F32(float):
    """32-bit floating point number"""

    size = MemUnit(32)
    fmt = ">f"

    def __new__(cls, value, *args, **kwargs):
        return super(cls, cls).__new__(cls, value)

    def __str__(self):
        return f"{float(self)}"

    def __repr__(self):
        return f"F32({float(self)})"


class F64(float):
    """64-bit floating point number"""

    size = MemUnit(64)
    fmt = ">d"

    def __new__(cls, value, *args, **kwargs):
        return super(cls, cls).__new__(cls, value)

    def __str__(self):
        return f"{float(self)}"

    def __repr__(self):
        return f"F64({float(self)})"


class BitU(int):
    """Unsigned bit precise integer"""

    size = MemUnit()

    def __class_getitem__(cls, key) -> type["BitU"]:
        if not isinstance(key, int):
            raise TypeError("BitU index must be an integer")
        if key < 0:
            raise ValueError("BitU index must be non-negative")
        if key > 32:
            raise ValueError("BitU index must be less than 32")
        return type(f"BitU[{key}]", (BitU, ), {"size": MemUnit(key)})


    def __new__(cls, value, *args, **kwargs):
        if value < 0:
            raise ValueError("Unsigned type cannot hold negative value")
        if value >= 2**cls.size.bits:
            raise ValueError(f"Value too large for {cls.size.bits} bit unsigned integer")
        return super().__new__(cls, value)

    def __str__(self):
        return "%d" % int(self)

    def __repr__(self):
        return "BitU%d(%d)" % (self.size.bits, int(self))

    @classmethod
    def unpack(cls, buffer: memoryview, offset: MemUnit) -> tuple[int, MemUnit]:
        val = 0
        byte_index = offset.bits // MemUnit.BITS_PER_BYTE
        bits_remaining = cls.size.bits
        bit_position = offset.bits
        while bits_remaining > 0:
            bits_to_fill = 8 - (bit_position % 8)
            bits_to_place = min(bits_remaining, bits_to_fill)
            shift = bits_to_fill - bits_to_place
            mask = (1 << bits_to_place) - 1
            bit_value = (buffer[byte_index] >> shift) & mask

            bit_position += bits_to_place
            byte_index += 1
            bits_remaining -= bits_to_place

            val |= bit_value << bits_remaining
        offset += cls.size
        return val, offset

    @classmethod
    def pack(cls, buffer: memoryview, offset: MemUnit, value: int):
        """Serializes integer numeric type to specific bit offset in the buffer. The value may be packed to lower bit-size."""

        byte_index = offset.bits // MemUnit.BITS_PER_BYTE
        bits_remaining = cls.size.bits
        bit_position = offset.bits
        while bits_remaining > 0:
            bits_to_fill = MemUnit.BITS_PER_BYTE - (bit_position % MemUnit.BITS_PER_BYTE)
            bits_to_place = bits_remaining if bits_remaining <= bits_to_fill else bits_to_fill
            shift = bits_to_fill - bits_to_place
            mask = (1 << bits_to_place) - 1
            bit_value = (value >> bits_remaining - bits_to_place) & mask
            buffer[byte_index] &= ~(mask << shift)
            buffer[byte_index] |= (bit_value << shift)
            bit_position += bits_to_place
            byte_index += 1
            bits_remaining -= bits_to_place
        offset += cls.size
        return offset


_NUMERIC_PRIMITIVE_TYPES = (
    U64,
    I64,
    U32,
    I32,
    U16,
    I16,
    U8,
    I8,
    F32,
    F64
)

_SUPPORTED_PRIMITIVE_TYPES = (
    *_NUMERIC_PRIMITIVE_TYPES,
    str,
    bytes,
)

_CUSTOM_USER_TYPES: list[type] = []


class _CompostStruct:
    size: MemUnit = MemUnit(0)
    dynamic_members: list[tuple[str, type]] = []
    layout: list[MemUnit] = []


def unpack_payload(types: list[type], payload: bytes) -> tuple:
    """Deserializes message payload into a tuple of Python objects"""
    def _unpack(buffer: memoryview, offset, t: type) -> tuple[list, MemUnit]:
        ret = []
        if _issubclass(t, _CompostStruct):
            offset.byte_align()
            members = []
            for _, member_t in t.__annotations__.items():
                values, offset = _unpack(buffer, offset, member_t)
                members.append(*values)
            ret.append(t(*members))
        elif _issubclass(t, (bytes, str)):
            (length,) = unpack_from(">H", payload, offset.bytes)
            offset.bytes += 2
            data_bytes = payload[offset.bytes : offset.bytes + length]
            if _issubclass(t, (bytes,)):
                ret.append(data_bytes)
            if _issubclass(t, (str,)):
                ret.append(data_bytes.decode())
            offset.bytes += length
        elif get_origin(t) is list:
            (length,) = unpack_from(">H", payload, offset.bytes)
            offset.bytes += 2
            (inner_type,) = get_args(t)
            length //= inner_type.size.bytes
            list_ = []
            for o in range(offset.bytes, offset.bytes + length * inner_type.size.bytes, inner_type.size.bytes):
                list_.append(*unpack_from(inner_type.fmt, payload, o))
            ret.append(list_)
            offset.bytes += length * inner_type.size.bytes
        elif _issubclass(t, Enum):
            if _issubclass(t, BitU):
                val, offset = t.unpack(memoryview(payload), offset)
                ret.append(t(val))
            elif _issubclass(t, I8):
                ret.append(t(*unpack_from(I8.fmt, payload, offset.bytes)))
                offset += I8.size
            elif _issubclass(t, U8):
                ret.append(t(*unpack_from(U8.fmt, payload, offset.bytes)))
                offset += U8.size
        elif _issubclass(t, BitU):
            val, offset = t.unpack(memoryview(payload), offset)
            ret.append(val)
        elif _issubclass(t, _NUMERIC_PRIMITIVE_TYPES):
            ret.append(*unpack_from(t.fmt, payload, offset.bytes))
            offset += t.size
        else:
            TypeError("Unsupported type")
        return ret, offset

    ret = []
    offset = MemUnit()
    buffer = memoryview(payload)
    for item in types:
        values, offset = _unpack(buffer, offset, item)
        ret.extend(values)
    return tuple(ret)

def pack_payload(types: list[type], *args) -> bytes:
    """Serializes Python objects in arguments to bytes"""
    def _pack(buffer: memoryview, offset: MemUnit, t: type, value) -> MemUnit:
        if _issubclass(t, (_CompostStruct, )):
            offset.byte_align()
            for (_, member_type), member in zip(t.__annotations__.items(), astuple(value)):
                offset = _pack(buffer, offset, member_type, member)
        elif _issubclass(t, (bytes, str)):
            offset.byte_align()
            if _issubclass(t, (str,)):
                value = str.encode(value)
            value = bytes(value)
            buffer[offset.bytes:offset.bytes+2] = pack(">H", len(value))
            offset.bytes += 2
            buffer[offset.bytes:offset.bytes+len(value)] = value
            offset.bytes += len(value)
        elif get_origin(t) is list:
            offset.byte_align()
            if not isinstance(value, list):
                raise TypeError("value must be of type: list")
            (inner_type,) = get_args(t)
            buffer[offset.bytes:offset.bytes+2] = pack(">H", len(value) * inner_type.size.bytes)
            offset.bytes += 2
            for i in value:
                buffer[offset.bytes:offset.bytes+inner_type.size.bytes] = pack(inner_type.fmt, i)
                offset += inner_type.size
        elif _issubclass(t, (BitU)):
            offset = t.pack(buffer, offset, value)
        elif _issubclass(t, _NUMERIC_PRIMITIVE_TYPES):
            offset.byte_align()
            buffer[offset.bytes:offset.bytes+t.size.bytes] = pack(t.fmt, value)
            offset += t.size
        elif _issubclass(t, Enum):
            if _issubclass(t, BitU):
                t.pack(buffer, offset, value)
                offset += t.size
            elif _issubclass(t, I8):
                offset.byte_align()
                buffer[offset.bytes] = pack(I8.fmt, value.value)
                offset += I8.size
            elif _issubclass(t, U8):
                offset.byte_align()
                buffer[offset.bytes] = pack(U8.fmt, value.value)
                offset += U8.size
        else:
            raise TypeError("Unsupported type")
        return offset

    buffer = memoryview(bytearray(1024))
    offset = MemUnit()
    if len(args) != len(types):
        raise ValueError("Incorrect number of arguments")
    for typ, value in zip(types, args):
        offset = _pack(buffer, offset, typ, value)
    return bytes(buffer[0:offset.bytes])


class CallDirection(Enum):
    TO_REMOTE = 0
    TO_LOCAL = 1
    TWO_WAY = 2


class Header:
    "Compost message header"

    header_struct = Struct(">BBH")

    def __init__(self, len_: int, txn: int, resp: bool, rpc_id: int) -> None:
        self.len = len_
        self.txn = txn
        self.resp = resp
        self.rpc_id = rpc_id

    def __repr__(self) -> str:
        return f"Header(len={self.len}, txn={self.txn}, rpc_id={hex(self.rpc_id)}, resp={self.resp})"
    
    def payload_byte_len(self) -> int:
        """Returns the length of the payload in bytes."""
        return 4 * self.len

    def msg_byte_len(self) -> int:
        """Returns the length of the message in bytes."""
        return 4 + self.payload_byte_len()

    def pack(self) -> bytes:
        rpc_id_and_flags = self.rpc_id & 0x0FFF
        if self.resp:
            rpc_id_and_flags |= 0x1000
        return self.header_struct.pack(self.len, self.txn, rpc_id_and_flags)

    @classmethod
    def unpack(cls, header: bytes) -> "Header":
        (len_, txn, rpc_id_and_flags) = cls.header_struct.unpack(header)
        rpc_id = rpc_id_and_flags & 0x0FFF
        response = bool(rpc_id_and_flags & 0x1000)
        return cls(len_, txn, response, rpc_id)


class Msg:
    """Raw Compost message that does not know the meaning of the payload."""

    def __init__(self, header: Header, payload: bytes):
        self.header = header
        self.payload = payload

    def __len__(self) -> int:
        return 4 + 4 * self.header.len

    def __repr__(self) -> str:
        return f"Msg({self.header}, payload={self.payload.hex(' ')})"

    def pack(self) -> bytes:
        assert 4 * self.header.len >= len(self.payload)
        if 4 * self.header.len > len(self.payload):
            self.payload += b"\0" * (4 * self.header.len - len(self.payload))
        return self.header.pack() + self.payload

    @classmethod
    def unpack(cls, payload: bytes) -> "Msg":
        return cls(Header.unpack(payload[0:4]), payload[4:])

    @classmethod
    def from_data(cls, txn: int, response: bool, rpc_id: int, payload: bytes) -> "Msg":
        return cls(Header(_ceiling_division(len(payload), 4), txn, response, rpc_id), payload)


class PayloadSerdes:

    def __init__(self, types: list[type]):
        self.types = types

    def pack(self, *args) -> bytes:
        return pack_payload(self.types, *args)

    def unpack(self, data: bytes) -> tuple:
        return unpack_payload(self.types, data)


class Rpc:
    def __init__(
        self,
        rpc_id: int,
        name: str,
        req_serdes: PayloadSerdes,
        resp_serdes: PayloadSerdes,
        call_sig: Signature,
        is_notification: bool,
        direction : CallDirection,
        doc: str | None,
    ):
        self.rpc_id = rpc_id
        self.name = name
        self.req_serdes = req_serdes
        self.resp_serdes = resp_serdes
        self.call_sig = call_sig
        self.is_notification = is_notification
        self.direction = direction
        self.subscribers = []
        if doc is None:
            self.__doc__ = name
        else:
            self.__doc__ = doc

    def get_param_items(self) -> list[tuple[str, Parameter]]:
        _, *parameters_items = self.call_sig.parameters.items()
        return parameters_items

    def subscribe(self, callback):
        self.subscribers.append(callback)

    def unsubscribe(self, callback):
        self.subscribers.remove(callback)

    def __get__(self, instance, cls):
        self.instance = instance
        return self

    def __call__(self, *args, **kwargs):
        if self.is_notification:
            self.instance._session.send_notif(self.rpc_id, self.req_serdes.pack(*args))
            return None
        else:
            response = self.instance._session.rpc(self.rpc_id, self.req_serdes.pack(*args))
            ret_tuple = self.resp_serdes.unpack(response)
            if ret_tuple:
                return ret_tuple[0]
            else:
                return None

    def __repr__(self) -> str:
        return f"Rpc(rpc_id=0x{self.rpc_id:04X}, req_types='{self.req_serdes}', resp_types='{self.resp_serdes}')"


class Endpoint(Enum):
    REMOTE = 0
    LOCAL = 1

    def is_call_outbound(self, call: Rpc):
        return (call.direction == CallDirection.TO_LOCAL and self == Endpoint.REMOTE 
                or call.direction == CallDirection.TO_REMOTE and self == Endpoint.LOCAL
                or call.direction == CallDirection.TWO_WAY)
    def is_call_inbound(self, call: Rpc):
        return (call.direction == CallDirection.TO_LOCAL and self == Endpoint.LOCAL
                or call.direction == CallDirection.TO_REMOTE and self == Endpoint.REMOTE
                or call.direction == CallDirection.TWO_WAY)


def _validate_type(t: type, context: str = ""):
    error_message_start = "Type" if len(context) == 0 else f"{context} of"
    if get_origin(t) is list:
        if len(get_args(t)) != 1:
            raise TypeError(f"{error_message_start} list[...] must have exactly one type argument")
        (inner_type,) = get_args(t)
        if not _issubclass(inner_type, _NUMERIC_PRIMITIVE_TYPES):
            raise TypeError(f"{error_message_start} list[...] may only contain primitive types")

def _is_type_dynamic(t: type):
    if get_origin(t) is list or _issubclass(t, (bytes, str)):
        return True
    elif _issubclass(t, _CompostStruct):
        return t.dynamic_members
    else:
        return False


def enum(cls: _C) -> _C:
    """Decorator for enums to make them usable with Compost RPC defintions.

    Use this for enum definitions ala C.

    Example::

        from compost_rpc import enum

        @enum
        class OtaResult(I8, Enum):
            OTA_OK = 0
            OTA_ERR = 1
    """

    if not _issubclass(cls, Enum):
        raise TypeError("compost_enum supports only Enum types")
    if not _issubclass(cls, (I8, U8, BitU)):
        raise TypeError("compost_enum supports only I8, U8 or BitInt data type for Enums")

    def __deepcopy__(self,memo):
        return self

    def __copy__(self):
        return self

    cls.__deepcopy__ = __deepcopy__
    cls.__copy__ = __copy__
    cls.backing_type = cls.__bases__[0]

    _CUSTOM_USER_TYPES.append(cls)
    return cls


def struct(cls: _C) -> type[_C]:
    """Decorator for classes to make them usable with Compost RPC definitions.

    Use this for structure definitions ala C.

    Example::

        from compost_rpc import struct

        @struct
        class OtaCoreLoad:
            core0: I8
            core1: I8
            dsph: I8
    """
    datacls = dataclass(type(cls.__name__, (cls, _CompostStruct), dict(cls.__dict__)))

    datacls.layout = [MemUnit(0)]
    datacls.dynamic_members = []
    for member_name, member_t in datacls.__annotations__.items():
        _validate_type(member_t, "compost_struct member")
        if _issubclass(member_t, _CompostStruct) and member_t.dynamic_members:
            datacls.dynamic_members.append((member_name, member_t))
            datacls.layout[-1] = datacls.layout[-1] + member_t.layout[0]
            datacls.layout.extend(member_t.layout[1:])
        elif get_origin(member_t) is list or _issubclass(member_t, (bytes, str)):
            datacls.dynamic_members.append((member_name, member_t))
            datacls.layout[-1] = datacls.layout[-1] + MemUnit.from_bytes(2)
            datacls.layout.append(MemUnit(0))
        else:
            datacls.layout[-1] = datacls.layout[-1] + member_t.size

    datacls.size = MemUnit(0)
    for x in datacls.layout:
        datacls.size = datacls.size + x

    _CUSTOM_USER_TYPES.append(datacls)
    return datacls


_P = ParamSpec("P")  # Captures the parameters of the function
_R = TypeVar("R")  # Captures the return type of the function


class RpcTypingProtocol(typing.Protocol[_P, _R]):
    def subscribe(self, handler): ...
    def unsubscribe(self, handler): ...
    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...


def rpc(rpc_id: int, notification: bool = False, direction: CallDirection = CallDirection.TO_REMOTE) -> Callable[[Callable[Concatenate[Any, _P], _R]], RpcTypingProtocol[_P, _R]]:
    '''Registers function as remotely callable.

    Example::

        from compost_rpc import rpc

        @rpc(0x001)
        def read8(self, address: U32) -> U8:
            """Reads 8 bits of data from the specified address"""
    '''

    class Decorator:
        def __init__(self, func: Callable):
            sig = signature(func)
            req_types = []
            _, *parameters_items = sig.parameters.items()
            for name, t in parameters_items:
                _validate_type(t.annotation, "rpc parameter")
                if _issubclass(t.annotation, (*_SUPPORTED_PRIMITIVE_TYPES, _CompostStruct)) or get_origin(t.annotation) is list:
                    req_types.append(t.annotation)
                else:
                    raise TypeError(f'Parameter "{name}" has unsupported type: {t.annotation.__name__}')
            resp_types = []
            _validate_type(sig.return_annotation, "rpc return value")
            if sig.return_annotation is sig.empty:
                pass
            elif get_origin(sig.return_annotation) is list or \
                _issubclass(sig.return_annotation, (tuple, _CompostStruct)) or \
                _issubclass(sig.return_annotation, _SUPPORTED_PRIMITIVE_TYPES):
                resp_types.append(sig.return_annotation)
            else:
                raise TypeError(f"Unsupported return type: {sig.return_annotation.__name__}")

            req = PayloadSerdes(req_types)
            resp = PayloadSerdes(resp_types)

            self.rpc = Rpc(rpc_id, func.__name__, req, resp, sig, notification, direction, func.__doc__)

        # Called at the time the owning class owner is created
        def __set_name__(self, owner: Protocol, name):
            owner._validate_rpc_id(rpc_id)
            owner._rpcs[self.rpc.rpc_id] = self.rpc
            # Replace ourselves with the original method
            setattr(owner, name, self.rpc)

    return Decorator

def notification(rpc_id: int, direction : CallDirection = CallDirection.TO_LOCAL) -> Callable[[Callable[Concatenate[Any, _P], _R]], RpcTypingProtocol[_P, _R]]:
    '''Registers function as notification.

    Example::

        from compost_rpc import struct

        @struct
        class LogMessage:
            severity: U8
            tag: U8
            message: list[U8]

        @notification(0x100)
        def notify_log(self, log: LogMessage):
            """Sends the log message."""
    '''
    return rpc(rpc_id, notification=True, direction=direction)


@runtime_checkable
class Transport(typing.Protocol):

    def send(self, msg: bytes):
        """Sends Compost message over the transport"""
        raise NotImplementedError

    def receive(self) -> bytes:
        """Receives Compost message over the transport"""
        raise NotImplementedError


class SerialTransport(Transport):

    def __init__(self, serial_port: str, baudrate: int) -> None:
        try:
            import serial
        except ImportError:
            raise ImportError("Package pyserial not found. Install pyserial to use the serial transport with Compost.")
        self.port = serial.Serial(serial_port, baudrate)

    def send(self, msg: bytes):
        sent = 0
        while sent < len(msg):
            sent += self.port.write(msg[sent:])

    def receive(self) -> bytes:
        header = self.port.read(4)
        if len(header) < 4:
            raise RuntimeError("Malformed message: Header length < 4")
        payload = self.port.read(Header.unpack(header).payload_byte_len())
        return header + payload


class TcpTransport(Transport):

    def __init__(self, target_ip: str, target_port: int) -> None:
        self.tcp_port = target_port
        self.ip_address = target_ip
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.ip_address, self.tcp_port))

    def send(self, msg: bytes):
        sent = 0
        while sent < len(msg):
            sent += self.socket.send(msg[sent:])

    def receive(self) -> bytes:
        received = 0
        header = b""
        while received < 4:
            header += self.socket.recv(4 - received)
            if len(header) == 0:
                raise RuntimeError("Connection closed by peer")
            received += len(header)

        payload_len_bytes = Header.unpack(header).payload_byte_len()
        received = 0
        payload = b""
        while received < payload_len_bytes:
            payload += self.socket.recv(payload_len_bytes - received)
            if len(payload) == 0:
                raise RuntimeError("Connection closed by peer")
            received += len(payload)
        return header + payload


class UdpTransport(Transport):

    def __init__(self, target_ip: str, target_port: int) -> None:
        self.udp_port = target_port
        self.ip_address = target_ip
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("", self.udp_port))

    def __del__(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def send(self, msg: bytes):
        if len(msg) < 64:
            msg += b"\x00" * (64 - len(msg))
        self.socket.sendto(msg, (self.ip_address, self.udp_port))

    def receive(self) -> bytes:
        msg, addr = self.socket.recvfrom(1500)
        return msg


class RawEthernetTransport(Transport):

    def __init__(self, interface: str, destination_mac: bytes, source_mac: bytes) -> None:
        ETH_P_ALL=3
        self.interface = interface
        if len(destination_mac) != 6 or len(source_mac) != 6:
            raise ValueError
        self.destination_mac = destination_mac
        self.source_mac = source_mac
        self.mac_adresses = destination_mac + source_mac
        from socket import AF_PACKET, SOCK_RAW, socket, htons
        self.socket = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL))
        self.socket.bind((interface, 0))

    def __del__(self):
        self.socket.close()

    def send(self, msg: bytes):
        length = len(msg).to_bytes(2, "big")
        msg = self.mac_adresses + length + msg
        if len(msg) < 64:
            msg += b"\x00" * (64 - len(msg))
        self.socket.send(msg)

    def receive(self) -> bytes:
        msg = self.socket.recv(1536)
        msg = msg[14:]
        return msg


class StdioTransport(Transport):

    def __init__(self, executable: str) -> None:
        if executable is None:
            raise ValueError(
                "executable is None: For stdio you have to pass the path to the executable to run and communicate with"
            )
        self.process = subprocess.Popen(executable, stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

    def send(self, msg: bytes):
        self.process.stdin.write(msg)

    def receive(self) -> bytes:
        header = self.process.stdout.read(4)
        if len(header) < 4:
            raise RuntimeError("Malformed packet: Header length < 4")
        data = self.process.stdout.read(Header.unpack(header).payload_byte_len())
        return header + data


class _Session:

    _TXN_MAX = 255

    def __init__(self, transport: Transport, rpcs: dict[int, Rpc], timeout:float=1):
        self.transport = transport
        self.rpcs = rpcs
        self.timeout = timeout
        self.last_txn = 1
        self.q: Queue[Msg] = Queue(0)  # Maybe define some size?
        self.listener = threading.Thread(target=self.receiver, name="Listener_thread")
        self.listener.daemon = True
        self.listener.start()

    def next_txn(self) -> int:
        if self.last_txn >= self._TXN_MAX:
            self.last_txn = 1
        else:
            self.last_txn += 1
        return self.last_txn

    def receiver(self):
        while True:
            msg_bytes = self.transport.receive()
            if len(msg_bytes) < 4:
                logger.error("Malformed message: Length < 4")
                continue
            msg = Msg.unpack(msg_bytes)
            logger.debug(f"<- {msg}")
            if msg.header.rpc_id not in self.rpcs:
                logger.error(f"Received unknown rpc_id {hex(msg.header.rpc_id)}")
                continue
            if msg.header.txn == 0:
                call = self.rpcs[msg.header.rpc_id]
                for sub in call.subscribers:
                    sub(*call.req_serdes.unpack(msg.payload))
            else:
                self.q.put(msg)

    def sender(self, msg: Msg):
        # TODO: maybe make this a thread?
        logger.debug(f"-> {msg}")
        self.transport.send(msg.pack())

    def recv_response(self, txn: int) -> Msg:
        try:
            msg = self.q.get(timeout=self.timeout)
        except(Empty):
            raise RequestTimeoutError("Response not received in time.")
        if msg.header.rpc_id not in self.rpcs:
            logger.error(f"Received unknown rpc_id {hex(msg.header.rpc_id)}")
            raise UnknownRpcIdError()
        if msg.header.txn != txn:
            logger.error(f"Received unexpected txn value {msg.header.txn}. Expected {txn}")
            raise UnexpectedTxnError()
        return msg

    def send_request(self, rpc_id: int, data: bytes):
        txn = self.next_txn()
        msg = Msg.from_data(txn, False, rpc_id, data)
        logger.debug(f"-> {msg}")
        self.transport.send(msg.pack())
        return txn

    def send_notif(self, rpc_id: int, data: bytes, response: bool = False) -> None:
        """Sends a notification."""
        msg = Msg.from_data(0, response, rpc_id, data) # txn=0 for notifications
        logger.debug(f"-> {msg}")
        self.transport.send(msg.pack())

    def rpc(self, rpc_id: int, data: bytes) -> bytes:
        """Calls the remote procedure and returns the result."""
        # if len(args) % 4 != 0:
        #     args += b"\x00" * (4 - (len(args) % 4))
        txn = self.send_request(rpc_id, data)
        return self.recv_response(txn).payload


class Protocol:

    _special_rpcs = {
        "ERROR": 0xFEE,
        "UNKNOWN_MSG": 0xFEF,
    }
    _rpcs: dict[int, Rpc] = dict()

    def __init__(self, transport: Transport, timeout: float = 1):
        if not isinstance(transport, (Transport)):
            raise TypeError("Transport argument is not a subclass of Transport")
        self._session = _Session(transport, self._rpcs, timeout=timeout)

    @classmethod
    def _validate_rpc_id(cls, rpc_id: int):
        if rpc_id in cls._rpcs:
            raise ValueError("rpc_id value already used. Choose a different value.")
        if rpc_id > 0xF00 or rpc_id < 0:
            raise ValueError("rpc_id value out of range. Min: 0x000 Max: 0xF00")


class CodeGeneratorFeatures:
    def __init__(self, inbound_remote: bool, outbound_remote: bool, inbound_notification: bool, outbound_notification: bool):
        self._inbound_rpc = inbound_remote
        self._outbound_rpc = outbound_remote
        self._inbound_notification = inbound_notification
        self._outbound_notification = outbound_notification

    @property
    def inbound_rpc(self) -> bool:
        """Target language can handle incoming RPC calls"""
        return self._inbound_rpc

    @property
    def outbound_rpc(self) -> bool:
        """Target language can invoke RPC"""
        return self._outbound_rpc

    @property
    def inbound_notification(self) -> bool:
        """Target language can handle incoming notifications"""
        return self._inbound_notification

    @property
    def outbound_notification(self) -> bool:
        """Target language can invoke notification"""
        return self._outbound_notification

class CodeGenerator(ABC):
    _GENERATION_NOTE: str = """
/******************************************************************************/
/*                     G E N E R A T E D   P R O T O C O L                    */
/******************************************************************************/
"""

    def __init__(self, protocol: type[Protocol]):
        """Constructor for the interface"""
        # Private properties, common to all generators
        self._protocol: type[Protocol] = protocol
        self._protocol_name: str = protocol.__name__
        self._protocol_doc: str = protocol.__doc__ or ""
        # Public properties, common to all generators - with sensible defaults set
        self._filename: str = self._protocol.__name__
        self._path: Path = Path(sys.path[0])
    
    def _validate_endpoint(self, endpoint: Endpoint):
        for rpc in self._protocol._rpcs.values():
            if rpc.is_notification:
                if endpoint.is_call_inbound(rpc) and self.features.inbound_notification:
                    continue
                elif endpoint.is_call_outbound(rpc) and self.features.outbound_notification:
                    continue
            else:
                if endpoint.is_call_inbound(rpc) and self.features.inbound_rpc:
                    continue
                elif endpoint.is_call_outbound(rpc) and self.features.outbound_rpc:
                    continue
            msg = f"{self.name} generator cannot generate {self._protocol.__name__} for {'remote' if endpoint == Endpoint.REMOTE else 'local'} endpoint, because "
            msg += f"{rpc.name} {'notification' if rpc.is_notification else 'RPC'} has unsupported call direction {rpc.direction.name}." 
            raise ValueError(msg)
    
    @property
    def filename(self) -> str:
        """Filename used for generated source files."""
        return self._filename
    @filename.setter
    def filename(self, value: str):
        self._filename = value

    @property
    def path(self):
        """Filename used for generated source files."""
        return self._path
    @path.setter
    def path(self, value):
        self._path = value

    @abstractmethod
    def generate(self, endpoint: Endpoint) -> list[tuple[Path, str]]:
        """
        Generates the source code as a list of filepaths and string contents.
        Parameters:
            endpoint (Endpoint): The endpoint to generate the code for.
        """
        ...

    @property
    @abstractmethod
    def name(cls) -> str:
        """Full long name of the language"""
        ...

    @property
    @abstractmethod
    def short_name(cls) -> str:
        """Short name used for user input"""
        ...
    
    @property
    @abstractmethod
    def features(cls) -> CodeGeneratorFeatures:
        """Features that the generator supports"""
        ...


class CCodeGenerator(CodeGenerator):

    @property
    def name(cls) -> str:
        return "C"

    @property
    def short_name(cls) -> str:
        return "c"

    @property
    def features(cls) -> CodeGeneratorFeatures:
        """Features that the generator supports"""
        return CodeGeneratorFeatures(
            outbound_remote=False,
            inbound_remote=True,
            inbound_notification=True,
            outbound_notification=True,
        )

    def __init__(self, protocol: type[Protocol]):
        super().__init__(protocol)
        self.filename = "compost"
        self._path_source: Path = self.path
        self._path_header: Path = self.path
        self._enable_notif_handlers = True
        self._enums = _String()
        self._structs = _String()
        self._static_vars = _String()
        self._type_inits = _String()
        self._type_inits_proto = _String()
        self._type_serdes: dict[str, str] = {}

    @property
    def path(self):
        """Path used for generated source files."""
        return self._path
    @path.setter
    def path(self, value):
        self._path = value
        self._path_header = value
        self._path_source = value

    @property
    def path_header(self) -> Path:
        """Change path where the header file (.h) will be generated."""
        return self._path_header
    @path_header.setter
    def path_header(self, value: Path):
        self._path_header = value

    @property
    def path_source(self) -> Path:
        """Change path where the source file (.c) will be generated."""
        return self._path_source
    @path_source.setter
    def path_source(self, value: Path):
        self._path_source = value
    
    _primitive_type_map = {
        U8: "uint8_t",
        I8: "int8_t",
        U16: "uint16_t",
        I16: "int16_t",
        U32: "uint32_t",
        I32: "int32_t",
        U64: "uint64_t",
        I64: "int64_t",
        F32: "float",
        F64: "double",
        str: "struct CompostSliceU8",
        bytes: "struct CompostSliceU8"
    }

    @classmethod
    def _type(cls, t: type) -> str:
        if t in cls._primitive_type_map:
            return cls._primitive_type_map[t]
        elif get_origin(t) is list:
            inner_type = get_args(t)[0]
            return f"struct CompostSlice{inner_type.__name__}"
        elif _issubclass(t, _CompostStruct):
            return f"struct {t.__name__}"
        elif _issubclass(t, BitU):
            return cls._primitive_type_map[U32]
        elif _issubclass(t, Enum):
            return f"enum {t.__name__}"
        else:
            raise TypeError("Unsupported type")

    @classmethod
    def _dynamic_member_names(cls, t: type) -> list[str]:
        if not _issubclass(t, _CompostStruct):
            return []
        names = []
        for member_name, member_t in t.dynamic_members:
            if _issubclass(member_t, _CompostStruct):
                names.extend([f"{member_name}_{x}" for x in cls._dynamic_member_names(member_t)])
            else:
                names.append(member_name)
        return names

    @classmethod
    def _member_default_value(cls, struct: type, member_annotation: tuple[str, type]) -> str:
        name, t = member_annotation
        if t in _NUMERIC_PRIMITIVE_TYPES or _issubclass(t, (BitU, )):
            return "0"
        elif _issubclass(t, (str, bytes)):
            return cls._member_default_value(t, (name, list[U8]))
        elif get_origin(t) is list:
            inner_type = get_args(t)[0]
            return f"compost_slice_{inner_type.__name__.lower()}_new(alloc, {name}_len)"
        elif _issubclass(t, _CompostStruct):
            len_names = ["alloc"] if t.dynamic_members else []
            for x in cls._dynamic_member_names(t):
                for y in cls._dynamic_member_names(struct):
                    if y.endswith(x):
                        len_names.append(f"{y}_len")
                        break
            return f"{t.__name__}_init({', '.join(len_names)})"
        elif _issubclass(t, Enum):
            return f"{_scase(t.__name__)}_{list(t)[0].name}"
        else:
            raise TypeError("Unsupported type")

    @classmethod
    def _handler_signature(cls, rpc: Rpc, as_caller: bool = False) -> _String:
        sig = rpc.call_sig
        call_site_params = []
        prototype_params = []
        parameters_items = rpc.get_param_items()
        for name, typ in parameters_items:
            prototype_params.append(f"{cls._type(typ.annotation)} {name}")
            call_site_params.append(f"l_{name}")
        if sig.return_annotation is sig.empty:
            return_type = "void"
        elif rpc.is_notification:
            raise TypeError("Notification return value must be None")
        else:
            if _is_type_dynamic(sig.return_annotation):
                prototype_params.append("struct CompostAlloc *alloc")
                call_site_params.append("&alloc")
            return_type = cls._type(sig.return_annotation)
        result_assignment = f"{return_type} ret = " if return_type != "void" else ""
        call_site = f"{result_assignment}{rpc.name}_handler({', '.join(call_site_params)});"
        prototype = f"{return_type} {rpc.name}_handler({', '.join(prototype_params) if prototype_params else 'void'});"
        return _String(call_site if as_caller else prototype)

    def _define_type_helper(self, t: type, helper: str) -> None:
        if not _issubclass(t, _CompostStruct):
            raise TypeError()

        if helper == "init":
            t_dynamic_members = self._dynamic_member_names(t)
            init_fn_args = [f'uint16_t {x}_len' for x in t_dynamic_members]

            # alloc_init generation
            if t.dynamic_members:
                suffixes = [x.bytes for x in t.layout[1:]]
                init_fn_args.insert(0, "struct CompostAlloc *alloc")
                self._type_inits_proto += f"struct CompostAlloc {t.__name__}_alloc_init(uint8_t *tx_buf, uint16_t tx_buf_len);\n"
                self._static_vars += f"static uint16_t {t.__name__}_alloc_suffixes[{len(suffixes)}] = {{{', '.join([str(x) for x in suffixes])}}};\n"
                self._type_inits += f"""
struct CompostAlloc {t.__name__}_alloc_init(uint8_t *tx_buf, uint16_t tx_buf_len)
{{
    struct CompostAlloc alloc = compost_alloc_init(tx_buf + 4 + {t.layout[0].bytes}, tx_buf_len);
    compost_alloc_set_suffixes(&alloc, {t.__name__}_alloc_suffixes, {len(suffixes)});
    return alloc;
}}
"""
            # init generation
            self._type_inits_proto += f"{self._type(t)} {t.__name__}_init({', '.join(init_fn_args) if init_fn_args else 'void'});\n\n"
            init_fn_member_init = [f".{member[0]} = {self._member_default_value(t, member)}" for member in t.__annotations__.items()]
            init_fn_member_init = ',\n        '.join(init_fn_member_init)
            self._type_inits += f"""
struct {t.__name__} {t.__name__}_init({', '.join(init_fn_args) if init_fn_args else 'void'})
{{
    return (struct {t.__name__}){{
        {init_fn_member_init}
    }};
}}
"""
        elif helper == "store" or helper == "load":
            is_store = helper == "store"
            fn = self._serdes_fn(t, helper)
            # load
            fn_proto = f"{self._type(t)} {fn}(const uint8_t** src)"
            fn_call = self._load_call
            iter_ptr = "src"
            if is_store: #store
                fn_proto = f"void {fn}(uint8_t** dest, {self._type(t)}* src)"
                fn_call = self._store_call
                iter_ptr = "dest"
            code = _String(indent=0)
            code.add((
                fn_proto,
                "{"
            ))
            code.indent_inc()
            if not is_store:
                code.add((f"struct {t.__name__} ret;"))
            offset = MemUnit()
            for member_name, member_t in t.__annotations__.items():
                member_path = f"src->{member_name}" if is_store else f"ret.{member_name}"
                if _issubclass(member_t, BitU):
                    code.add(fn_call(member_t, member_path, f"*{iter_ptr}", extra_args=[offset.bits, member_t.size.bits]))
                    offset += member_t.size
                else:
                    try:
                        code, offset = self._byte_align(code, offset, ptr=f"*{iter_ptr}")
                        code.add(fn_call(member_t, member_path, iter_ptr))
                    except TypeError:
                        #rethrow with more specific error message
                        raise TypeError(f'{helper} helper for type {t.__name__} is not supported')
            code, offset = self._byte_align(code, offset, ptr=f"*{iter_ptr}")
            if not is_store:
                code.add(('return ret;'))
            code.indent_dec()
            code.add(("}\n"))
            self._type_serdes[fn] = code._str


    def _define_types(self) -> None:
        for t in _CUSTOM_USER_TYPES:
            if _issubclass(t, _CompostStruct):
                self._structs += f"\n\nstruct {t.__name__} {{\n"
                for member in t.__annotations__.items():
                    member_name, member_t = member
                    if _issubclass(member_t, (BitU, )):
                        self._structs += f"    {self._type(member_t)} {member_name} : {member_t.size.bits};\n"
                    else:
                        try:
                            self._structs += f"    {self._type(member_t)} {member_name};\n"
                        except TypeError:
                            #rethrow with more specific error message
                            raise TypeError(f'Unsupported type of compost_struct attribute "{member_name}": {member_t.__name__}')
                self._structs += "};\n"
                self._define_type_helper(t, "init")
            elif _issubclass(t, Enum):
                sep = ",\n"
                self._enums += f"""
enum {t.__name__} {{
{sep.join(f"    {_scase(t.__name__)}_{variant.name.upper()} = {variant.value}" for variant in t)}
}};
"""

    def _serdes_fn(self, t: type, suffix: str) -> str:
        fn = ""
        if t in _NUMERIC_PRIMITIVE_TYPES:
            tstr = t.__name__.lower()
            fn = f"compost_{tstr}_{suffix}"
        elif _issubclass(t, Enum):
            return self._serdes_fn(t.backing_type, suffix)
        elif _issubclass(t, (bytes, str)):
            fn = f"compost_slice_u8_{suffix}"
        elif get_origin(t) is list:
            inner_type = get_args(t)[0].__name__.lower()
            fn = f"compost_slice_{inner_type}_{suffix}"
        elif _issubclass(t, BitU):
            fn = f"compost_bituint_{suffix}"
        elif _issubclass(t, _CompostStruct):
            fn = f"{t.__name__}_{suffix}"
        else:
            raise TypeError(f"No dedicated {suffix} function exists for specified type")
        return fn

    def _store_call(self, t: type, src: str, dest: str = "&dest", *, src_byref = False, extra_args: list[str] = []) -> str:
        fn_name = self._serdes_fn(t, "store")
        is_struct = _issubclass(t, _CompostStruct)
        if is_struct and fn_name not in self._type_serdes:
            self._define_type_helper(t, "store")
        by_ref = "&" if is_struct and not src_byref else ""
        args = [dest, f"{by_ref}{src}"]
        args.extend([str(x) for x in extra_args])
        return f"{fn_name}({', '.join(args)});"

    def _load_call(self, t: type, dest: str, src: str = "src", *, extra_args = []) -> str:
        fn_name = self._serdes_fn(t, "load")
        if _issubclass(t, _CompostStruct) and fn_name not in self._type_serdes:
            self._define_type_helper(t, "load")
        args = [src]
        args.extend([str(x) for x in extra_args])
        return f"{'' if '.' in dest else f'{self._type(t)} '}{dest} = {fn_name}({', '.join(args)});"

    @staticmethod
    def _byte_align(code: _String, offset: MemUnit, ptr: str) -> tuple[_String, MemUnit]:
        offset.byte_align()
        if offset.bytes:
            code.add(f"{ptr} += {offset.bytes};")
            offset.bytes = 0
        return code, offset
    
    def generate(self, endpoint: Endpoint = Endpoint.REMOTE) -> list[tuple[Path, str]]:
        self._validate_endpoint(endpoint)
        self._define_types()
        version_info = f'''#define COMPOST_VERSION "{__version__}"
#define COMPOST_GENTIME "{datetime.now().isoformat(timespec="seconds")}"'''

        protocol_header = _String()
        protocol_source = _String()
        protocol_source += CodeGenerator._GENERATION_NOTE + "\n"

        rpc_id_enum_items = ',\n'.join(f'    {rpc.name.upper()} = 0x{rpc_id:03X}' for (rpc_id, rpc) in self._protocol._rpcs.items())
        rpc_id_enum = f"""
enum RpcId {{
    UNKNOWN_MSG = 0xFEE,
{rpc_id_enum_items}
}};
"""
        protocol_source += rpc_id_enum + "\n\n"

        protocol_source += f"{self._static_vars}\n\n"

        protocol_header += f"""

{CodeGenerator._GENERATION_NOTE}

{self._enums}
{self._structs}

{self._type_inits_proto}

"""
        protocol_source += f"{self._type_inits}\n"
        for notif in self._protocol._rpcs.values():
            if not notif.is_notification or not endpoint.is_call_outbound(notif):
                continue
            params = [f"{self._type(param_type.annotation)} {param_name}" for param_name, param_type in notif.get_param_items()]
            params = ", " + ", ".join(params) if params else ""
            protocol_header += f"""
/**
* {notif.__doc__}
*/
int16_t {notif.name}_store(uint8_t *tx_buf, size_t tx_buf_size{params});
"""
            protocol_source += f"""/**
* Serialization function for {notif.name} notification
*/
int16_t {notif.name}_store(uint8_t *tx_buf, size_t tx_buf_size{params})
{{
    struct CompostMsg tx = {{
        .txn   = 0,
        .payload_buf = tx_buf + PAYLOAD_OFFSET
    }};
    uint8_t* dest = tx.payload_buf;
"""
            protocol_source.indent_inc()
            for param_name, param_type in notif.get_param_items():
                protocol_source.add(self._store_call(param_type.annotation, param_name))
            protocol_source.indent_dec()
            protocol_source += f"""    tx.rpc_id = {notif.name.upper()};
    tx.len = compost_bytes_to_words(dest - tx.payload_buf);
    return compost_header_set(tx_buf, tx_buf_size, tx);
}}

"""

        for rpc in self._protocol._rpcs.values():
            if not endpoint.is_call_inbound(rpc):
                continue
            sig = rpc.call_sig
            parameters_items = rpc.get_param_items()
            doc_prefix = "Deserialization/Serialization"
            invoke_params = ["struct CompostMsg *tx"]
            if rpc.is_notification:
                doc_prefix = "Deserialization"
            if parameters_items:
                invoke_params.append("const struct CompostMsg rx")
            invoke_prototype = _String()
            invoke_prototype += f"""
/**
* {rpc.__doc__}
*/
{self._handler_signature(rpc)}
"""
            invoke_fn = _String()
            invoke_fn += f"""
/**
* {doc_prefix} function for {rpc.name} function
*/
void invoke_{rpc.name}({", ".join(invoke_params)})
{{
"""
            invoke_fn.indent_inc()
            if parameters_items:
                invoke_fn.add("const uint8_t* src = rx.payload_buf;")
            for name, t in parameters_items:
                invoke_fn.add(self._load_call(t.annotation, dest = f"l_{name}", src = "&src"))
            if get_origin(sig.return_annotation) is list or _issubclass(sig.return_annotation, (bytes, str)):
                invoke_fn.add((
                    "struct CompostAlloc alloc = compost_alloc_init(tx->payload_buf + 2, tx->payload_buf_size - 2);"
                ))
            elif _issubclass(sig.return_annotation, _CompostStruct):
                if sig.return_annotation.dynamic_members:
                    invoke_fn.add((
                        f"struct CompostAlloc alloc = {sig.return_annotation.__name__}_alloc_init(tx->payload_buf + {sig.return_annotation.layout[0].bytes}, tx->payload_buf_size - {sig.return_annotation.layout[0].bytes});",
                    ))
            invoke_fn.add(f"{self._handler_signature(rpc, as_caller=True)}")
            if sig.return_annotation is not Signature.empty:
                invoke_fn.add('uint8_t* dest = tx->payload_buf;')
                invoke_fn.add(self._store_call(sig.return_annotation, "ret"))
            if sig.return_annotation is Signature.empty:
                invoke_fn.add("tx->len = 0;")
            else:
                invoke_fn.add("tx->len = compost_bytes_to_words(dest - tx->payload_buf);")
            invoke_fn.add(f"tx->rpc_id = {rpc.name.upper()};")
            invoke_fn += "}\n"

            protocol_header += invoke_prototype
            protocol_source += str(invoke_fn)


        rpc_id_fns = """
void compost_unknown_msg(struct CompostMsg *tx)
{
    tx->rpc_id = UNKNOWN_MSG;
    tx->len = 0;
}

void compost_invoke_switch(struct CompostMsg *tx, const struct CompostMsg rx)
{
    switch (rx.rpc_id) {
"""
        for rpc in self._protocol._rpcs.values():
            if rpc.is_notification and not endpoint.is_call_inbound(rpc):
                continue
            params = "(tx, rx)" if rpc.get_param_items() else "(tx)"
            rpc_id_fns += f"        case {rpc.name.upper()}: invoke_{rpc.name}{params}; break;\n"
        rpc_id_fns += """        default: compost_unknown_msg(tx);
    }
}
"""

        protocol_source += f"{rpc_id_fns}\n\n"

        try:
            if __package__ is None or __package__ == '':
                import compost_rpc.lib.c.header_template # type: ignore
                import compost_rpc.lib.c.source_template # type: ignore
            else:
                from .lib.c import header_template
                from .lib.c import source_template
            header = Template(header_template.content).substitute(version_info=version_info, filename_caps=self.filename.upper(), protocol=protocol_header)
            source = Template(source_template.content).substitute(filename=self.filename, serdes="".join(self._type_serdes.values()))
            source += f"{protocol_source}"
            header_path = Path(self.path_header) / f"{self.filename}.h"
            source_path = Path(self.path_source) / f"{self.filename}.c"
            return [(header_path, header), (source_path, source)]
        except (FileNotFoundError, ModuleNotFoundError):
            print("Error: Compost C templates not found. Python package is missing files.", file=sys.stderr)
            print("Hint: Reinstall the Compost Python package.", file=sys.stderr)
            return []


class CSharpCodeGenerator(CodeGenerator):

    @property
    def name(cls) -> str:
        return "C#"

    @property
    def short_name(cls) -> str:
        return "cs"
    
    @property
    def features(cls) -> CodeGeneratorFeatures:
        """Features that the generator supports"""
        return CodeGeneratorFeatures(
            outbound_remote=True,
            inbound_remote=False,
            inbound_notification=True,
            outbound_notification=False,
        )

    def __init__(self, protocol: type[Protocol]):
        super().__init__(protocol)
        self._use_primary_constructor: bool = True
        self._use_collection_expression: bool = True
        self._is_partial: bool = False
        self._namespace: str = "Compost"

    @property
    def use_primary_constructor(self) -> bool:
        """If true, the mandatory protocol constructor will be generated as primary constructor (C# 12 and later)."""
        return self._use_primary_constructor
    @use_primary_constructor.setter
    def use_primary_constructor(self, value: bool):
        self._use_primary_constructor = value

    @property
    def use_collection_expression(self) -> bool:
        """If true, the arguments for InvokeRpcAsync will be passed as collection expression (C# 12 and later) instead of collection initializer."""
        return self._use_collection_expression
    @use_collection_expression.setter
    def use_collection_expression(self, value: bool):
        self._use_collection_expression = value

    @property
    def is_partial(self) -> bool:
        """If true, the protocol class is declared as partial."""
        return self._is_partial
    @is_partial.setter
    def is_partial(self, value: bool):
        self._is_partial = value

    @property
    def namespace(self) -> str:
        """Specifies the namespace for the generated code."""
        return self._namespace
    @namespace.setter
    def namespace(self, value: str):
        self._namespace = value

    _primitive_type_map = {
        U8: "byte",
        I8: "sbyte",
        U16: "ushort",
        I16: "short",
        U32: "uint",
        I32: "int",
        U64: "ulong",
        I64: "long",
        F32: "float",
        F64: "double",
        str: "string",
        bytes: "List<byte>"
    }

    @classmethod
    def _type(cls, t: type) -> str:
        if t in cls._primitive_type_map:
            return cls._primitive_type_map[t]
        elif get_origin(t) is list:
            inner_type = get_args(t)[0]
            return f"List<{cls._type(inner_type)}>"
        elif _issubclass(t, (Enum, _CompostStruct)):
            return f"{t.__name__}"
        elif _issubclass(t, (BitU)):
            return "ulong" if t.size.bits >= 32 else "int"
        else:
            raise TypeError("Unsupported type")

    def _type_definition(self) -> str:
        cs_types = ""
        for t in _CUSTOM_USER_TYPES:
            if _issubclass(t, _CompostStruct):
                cs_types += f"\npublic class {t.__name__}\n{{\n"
                for member_name, member_t in t.__annotations__.items():
                    if _issubclass(member_t, BitU):
                        cs_types += f"    [Pack({member_t.size.bits})]\n"
                        cs_types += f"    public {self._type(member_t)} {_pcase(member_name)} {{ get; set; }}\n"
                    elif _issubclass(member_t, str):
                        cs_types += f"    public string {_pcase(member_name)} {{ get; set; }} = string.Empty;\n"
                    elif get_origin(member_t) is list or _issubclass(member_t, (str, bytes)):
                        cs_list_init = "[]" if self.use_collection_expression else f"new {self._type(member_t)}()"
                        cs_types += f"    public {self._type(member_t)} {_pcase(member_name)} {{ get; set; }} = {cs_list_init};\n"
                    elif _issubclass(member_t, _CompostStruct):
                        cs_types += f"    public {self._type(member_t)} {_pcase(member_name)} {{ get; set; }} = new ();\n"
                    else:
                        try:
                            cs_types += f"    public {self._type(member_t)} {_pcase(member_name)} {{ get; set; }}\n"
                        except TypeError:
                            #rethrow with more specific error message
                            raise TypeError(f'Unsupported type of compost_struct attribute "{member_name}": {member_t.__name__}')
                cs_types += "}\n"
            elif _issubclass(t, Enum):
                sep = ",\n"
                cs_types += f"""
public enum {t.__name__} : byte\n{{
{sep.join(f"    {_pcase(variant.name)} = {variant.value}" for variant in t)}
}};
"""
            else:
                raise TypeError(f'Unsupported user type: {t.name__}')
        return cs_types

    @classmethod
    def doc_string(cls, doc: str) -> str:
        leading_base = min([len(line) - len(line.lstrip()) for line in doc.splitlines() if line.strip()])
        doc_lines = '\n    /// '.join(line[leading_base:] for line in doc.splitlines() if line.strip())
        return f"""    /// <summary>
    /// {doc_lines}
    /// </summary>\n"""

    def generate(self, endpoint: Endpoint = Endpoint.LOCAL) -> list[tuple[Path, str]]:
        self._validate_endpoint(endpoint)
        protocol_types = self._type_definition()
        protocol_types_empty = len(_CUSTOM_USER_TYPES) == 0
        cs_compost_using = "" if self.namespace == "CompostRpc" else "using CompostRpc;\n"
        cs_header = f"""{CodeGenerator._GENERATION_NOTE}
using System;
using System.Threading.Tasks;
using System.Collections.Generic;
{cs_compost_using}
namespace {self.namespace};
"""
        protocol_cls = f"""{cs_header}
public {"partial " if self.is_partial else ""}class {self._protocol_name}{"(ITransport transport)" if self.use_primary_constructor else ""} : Protocol{"(transport)" if self.use_primary_constructor else ""}
{{
"""
        for rpc in self._protocol._rpcs.values():
            if rpc.is_notification:
                continue
            sig = rpc.call_sig
            rpc_params = rpc.get_param_items()
            if sig.return_annotation is sig.empty:
                cs_rpc_ret = ""
            else:
                cs_rpc_ret = f"<{self._type(sig.return_annotation)}>"
            if rpc.__doc__:
                protocol_cls += self.doc_string(rpc.__doc__)
            protocol_cls += f"""    [Rpc({hex(rpc.rpc_id)})]
    public Task{cs_rpc_ret} {_pcase(rpc.name)}Async("""
            params = []
            for name, typ in rpc_params:
                params.append(f"{self._type(typ.annotation)} {_ccase(name)}")
            protocol_cls += ", ".join(params)
            protocol_cls += ")\n"
            rpc_params_open = "" if not rpc_params else ("[" if self.use_collection_expression else "new object[]{")
            rpc_params_close = "" if not rpc_params else ("]" if self.use_collection_expression else "}")
            protocol_cls += f"        => InvokeRpcAsync{cs_rpc_ret}({rpc_params_open}"
            protocol_cls += ", ".join([_ccase(name) for name, typ in rpc_params])
            protocol_cls += f"{rpc_params_close});\n\n"
        for notif in self._protocol._rpcs.values():
            if not notif.is_notification:
                continue
            params = [ self._type(x.annotation) for _, x in notif.get_param_items() ]
            if notif.__doc__:
                protocol_cls += self.doc_string(notif.__doc__)
            generic_params = f"<{', '.join(params)}>" if params else ''
            protocol_cls += f"""    [Notification({hex(notif.rpc_id)})]
    public event Action{generic_params} {_pcase(notif.name)}
    {{
        add => AddNotificationHandler(value);
        remove => RemoveNotificationHandler(value);
    }}\n
"""
        if not self.use_primary_constructor:
            protocol_cls += f"""    public {self._protocol_name} (ITransport transport) : base(transport)
    {{
    }}
"""
        protocol_cls = protocol_cls.rstrip() + "\n}"
        #output write
        protocol_path = Path(self.path) / f"{self.filename}.cs"
        output = [(protocol_path, protocol_cls)]
        if not protocol_types_empty:
            protocol_types_path = Path(self.path) / f"{self.filename}Types.cs"
            output.append((protocol_types_path, cs_header + protocol_types))
        return output


class Generator:

    @dataclass(eq=True, frozen=True)
    class _OutputKey:
        generator : CodeGenerator
        endpoint : Endpoint

        def as_info_str (self, with_endpoint: bool = True) -> str:
            endpoint_str = f" (endpoint: {self.endpoint.name.lower()})" if with_endpoint else ""
            return f"{self.generator.name}{endpoint_str}"
        
        def as_typed_str (self, with_endpoint: bool = True) -> str:
            endpoint_str = f"_{self.endpoint.name.lower()}" if with_endpoint else ""
            return f"{self.generator.short_name}{endpoint_str}"
    
    def __init__(self, protocol: type[Protocol]):
        if _issubclass(protocol, Protocol):
            self._protocol_class = protocol
        else:
            raise TypeError("Parameter protocol must be a type inherited from compost_rpc.Protocol class")
        self._force_overwrite: bool = False
        self._output_cache: dict[Generator._OutputKey, list[tuple[Path, str]]] = {}
        self._path_cache: dict[Path, Generator._OutputKey] = {}
        self._in_with_context = False

        self._generators: list[CodeGenerator] = [
            CCodeGenerator(self._protocol_class),
            CSharpCodeGenerator(self._protocol_class)
        ]

        # Patches CodeGenerator's generate() method to cache results
        def _patch_generate(gen: CodeGenerator):
            original = gen.generate
            def wrapper(*args, **kwargs):
                result = original(*args, **kwargs)
                endpoint_default = dict(signature(original).parameters)["endpoint"].default
                endpoint : Endpoint = args[0] if len(args) > 0 else kwargs.get("endpoint", endpoint_default)
                key = self._OutputKey(gen, endpoint)
                if key in self._output_cache.keys():
                    raise ValueError(f"Duplicate generate() call for {gen.name} generator detected. Either change target endpoint or use different instance.")
                for path, _ in result:
                    if path in self._path_cache.keys():
                        conflict = self._path_cache[path]
                        raise ValueError(f"{key.as_info_str()} generator is trying to write to same files as {conflict.as_info_str()}.")
                    self._path_cache[path] = key
                self._output_cache[key] = result
                return result
            gen.generate = wrapper

        # Patch each generator
        for generator in self._generators:
            _patch_generate(generator)

    def __enter__(self):
        # Prepare a cache to store outputs from generate() calls
        self._in_with_context = True
        self._output_cache.clear()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._in_with_context = False
        self.run()

    @property
    def c(self) -> CCodeGenerator:
        return typing.cast(CCodeGenerator, self._generators[0])

    @property
    def csharp(self) -> CSharpCodeGenerator:
        return typing.cast(CSharpCodeGenerator, self._generators[1])

    @property
    def force_overwrite(self) -> bool:
        """If true, existing files will be overwritten without prompt."""
        return self._force_overwrite

    @force_overwrite.setter
    def force_overwrite(self, value: bool):
        self._force_overwrite = value

    def run(self):
        verbose : dict[str, bool] = {}
        for lang, _ in self._output_cache.items():
            lang_name = lang.generator.short_name
            if lang_name not in verbose:
                verbose[lang_name] = False
            elif not verbose.get(lang_name):
                verbose[lang_name] = True

        print(cf.bold(cf.info(f"\nRunning code generation for {self._protocol_class.__name__}")))
        if self._in_with_context:
            print(cf.warn(cf.bold("Warning!") + " run() called from within a 'with' context will be ignored. The Generator will finalize code generation automatically upon exiting the with-block."))
            return
        print()
        if not self._output_cache:
            print(cf.info(f"Nothing was generated. Call the {cf.bold('generate()')} method on one of the generator properties to produce output."))
        to_overwrite: dict[Generator._OutputKey, list[Path]] = {}
        for lang, output in self._output_cache.items():
            is_verbose = verbose[lang.generator.short_name]
            existing: list[Path] = []
            for path, content in output:
                if path.exists():
                    existing.append(path)
            if not existing:
                continue
            print(cf.warn(cf.bold("Warning!") + f" Following {lang.as_info_str(is_verbose)} files already exist:"))
            for path in existing:
               print(path)
            to_overwrite[lang] = existing
        
        langs_typed = [x.as_typed_str(verbose[x.generator.short_name]) for x in to_overwrite.keys()]
        overwrite_response = langs_typed
        if to_overwrite:
            print()
            if self.force_overwrite:
                print(cf.info("Forcing overwrite"))
            else:
                while True:
                    overwrite_response = input(cf.info(f"Overwrite files? [N]one/[a]ll/[{', '.join(langs_typed)}]\n")).split(",")
                    overwrite_response = [ x.lower().strip() for x in overwrite_response ]
                    is_overwrite_response_valid = True
                    if len(overwrite_response) == 1:
                        x = overwrite_response[0]
                        if x == "a" or x == "all":
                            overwrite_response = langs_typed
                        elif not x or x == "n" or x == "none":
                            overwrite_response = []
                    for x in overwrite_response:
                        if x not in langs_typed:
                            print(cf.err(f"Invalid language identifier {x} specified. Try again!"))
                            is_overwrite_response_valid = False
                    if is_overwrite_response_valid:
                        break
                if not overwrite_response:
                    print(cf.info("No files were modified"))
                    return
            print()
        for lang, output_items in self._output_cache.items():
            is_verbose = verbose[lang.generator.short_name]
            if lang in to_overwrite:
                if lang.as_typed_str(is_verbose) not in overwrite_response:
                    print(cf.warn(f"Skipping {cf.bold(lang.as_info_str(is_verbose))} files"))
                    continue
            print(cf.success(f"Writing {cf.bold(lang.as_info_str(is_verbose))} files:"))
            for path, content in output_items:
                print(path)
                path.write_text(content)


def main():
    print(f"Compost {__version__}\n")
    print(cf.info("Checking optional dependencies:"))
    try:
        import serial
        print(cf.success("pyserial found."))
    except ImportError:
        print(cf.warn("pyserial not found. Install pyserial if you want to use the serial port."))
    try:
        import colorful
        print(cf.success("colorful found."))
    except ImportError:
        print(cf.warn("colorful not found. Install colorful if you want colored terminal output."))
    print(cf.info("\nThis module does nothing when called as a script, it's only usable as a library."))


if __name__ == "__main__":
    main()
