"""Compost RPC protocol specification

This is an example of Compost RPC protocol specification.

You can edit this file to create your own RPC protocol. Put function signatures
into a class. Base this class on the `Protocol` class from the compost_rpc
module. Mark remote functions with the `rpc` decorator.
For argument and return value type annotation use only the types from
compost. These types are C compatible and are statically sized. Do not put any
code into the remote function body.
"""

from enum import Enum
from compost_rpc import Protocol, Generator
from compost_rpc import rpc, notification, struct, enum
from compost_rpc import U32, U16, U8, F32


@enum
class Result(U8, Enum):
    OK = 0
    ERR = 1


@enum
class LedState(U8, Enum):
    OFF = 0
    ON = 1


@enum
class TofProperty(U8, Enum):
    ZONE_DISTANCE = 0
    ZONE_ENERGY = 1
    ZONE_TARGET_COUNT = 2
    GR_DATA = 16
    HT_DATA = 17


@struct
class TofZoneArray:
    id: U8
    layer: U8
    value: TofProperty
    data: list[U32]


@struct
class LogMessage:
    severity: U8
    tag: U8
    message: str


class ExampleProtocol(Protocol):
    """This class contains all the RPC functions."""

    @rpc(0x101)
    def app_info(self) -> str:
        """Returns the application info."""

    @rpc(0x001)
    def read8(self, address: U32) -> U8:
        """Reads 8 bits of data from the specified address."""

    @rpc(0x002)
    def write8(self, address: U32, data: U8):
        """writes 8 bits of data to the specified address."""

    @rpc(0x003)
    def read32(self, address: U32) -> U32:
        """Reads 32 bits of data from the specified address."""

    @rpc(0x004)
    def write32(self, address: U32, data: U32):
        """Writes 32 bits of data to the specified address."""

    @rpc(0x005)
    def read(self, address: U32, len: U16) -> bytes:
        """Reads data from the specified address."""

    @rpc(0x006)
    def write(self, address: U32, data: bytes):
        """Writes data to the specified address."""

    @rpc(0x007)
    def write_slice(self, data: list[U32]):
        """Sends array of uint32_t with variable length"""

    @rpc(0x008)
    def read_slice(self) -> list[U32]:
        """Gets array of uint32_t with variable length"""

    @rpc(0x009)
    def set_led(self, state: LedState):
        """Sets state of an LED."""

    @rpc(0x00A)
    def float_add(self, a: F32, b: F32) -> F32:
        """Adds two floats and returns the result. Simple test for floats."""

    @rpc(0x00B)
    def adc_read(self, channel: U8) -> U16:
        """Reads specified ADC channel"""

    @rpc(0xA00)
    def get_zone_signal(self, id: U8, layer: U8) -> TofZoneArray:
        """Returns signal rate for each available SPAD zone and selected target number."""

    @notification(0x200)
    def notify_log_static(self, log: LogMessage):
        """Returns a log message."""


if __name__ == "__main__":
   
    with Generator(ExampleProtocol) as gen:
        gen.c.generate()
