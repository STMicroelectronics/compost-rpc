import sys
from pathlib import Path
from dataclasses import dataclass

sys.path.append(str(Path(__file__).resolve().parents[1]))

from enum import Enum
import compost_rpc
from compost_rpc import Protocol, Generator, CallDirection
from compost_rpc import rpc, enum, struct, notification
from compost_rpc import I8, U8, I16, U16, I32, U32, F32, U64, BitU


@enum
class Status(U8, Enum):
    OK = 0
    WARN = 1
    ERR = 2
    FAIL = 255

@enum
class MotorState(I8, Enum):
    OFF = 0
    ON = 1
    START = 2
    STOP = 3

@enum
class MotorDirection(I8, Enum):
    DOWN = 0
    UP = 1

@enum
class Voltages(BitU[4], Enum):
    MV_110_92 = 0
    MV_98_76 = 1
    MV_88_07 = 2
    MV_78_66 = 3
    MV_70_38 = 4
    MV_63_08 = 5
    MV_56_64 = 6
    MV_50_95 = 7
    MV_45_92 = 8
    MV_41_46 = 9
    MV_37_50 = 10
    MV_37_50_1 = 11
    MV_37_50_2 = 12
    MV_37_50_3 = 13
    MV_37_50_4 = 14
    MV_37_50_5 = 15

@struct
@dataclass
class BitfieldStruct:
    channel: BitU[8]
    inom:    BitU[5]
    hsc:     BitU[4]
    tnom:    BitU[9]
    temp:    Voltages
    ststart: BitU[3]
    ccm:     BitU[1]
    set:     BitU[1]
    state:   BitU[1]
    clear:   BitU[1]

@struct
class ListFirstAttr:
    data: list[I16]
    min: I16
    max: I16

@struct
class ListMidAttr:
    min: I16
    data: list[I16]
    max: I16

@struct
class ListLastAttr:
    min: I16
    max: I16
    data: list[I16]

@struct
class TwoListAttr:
    avg_a: F32
    data_a: list[I16]
    avg_merge: F32
    data_b: list[I16]
    avg_b: F32

@struct
class MockDate:
    day: U16
    month: U8
    year: I32
    as_text: str
    as_digits: bytes

@struct
class MockMotorReport:
    state: MotorState
    direction: MotorDirection
    voltage: list[U16]
    current: list[U16]

@struct
class MockMotorControl:
    state: MotorState
    direction: MotorDirection
    pwm_duty: U16

@struct
class MockLogMessage:
    severity : Status
    message : str
    timestamp: MockDate
    byte_xor : U8

@struct
class MockLfsr:
    polynomial: U64
    value: U64
    timestamp: MockDate

class TestProtocol(Protocol):
    """This class contains RPC functions used in automatic tests."""

    @rpc(0xB00)
    def trigger_notification(self, rpc_id: U16):
        """Send request for notification with selected msg_id."""

    @rpc(0xC00)
    def add_int(self, a: U32, b: U32) -> U32:
        """Returns addition of two integers."""

    @rpc(0xC01)
    def sum_list(self, a: list[U32]) -> U32:
        """Sums up numbers in a list of integers."""

    @rpc(0xC02)
    def void_return(self, x: I16):
        """Sends number and expects no response data."""

    @rpc(0xC03)
    def void_full(self):
        """Sends nothing, expects nothing."""

    @rpc(0xC04)
    def divide_float(self, a: F32, b: F32) -> F32:
        """Divide two floats."""

    @rpc(0xC05)
    def caesar_cipher(self, str: str, offset: U8) -> str:
        """Offset all characters in a string by certain offset"""

    @rpc(0xC06)
    def sort_bytes(self, data: bytes) -> bytes:
        """Sorts array of bytes in ascending order"""

    @rpc(0xC07)
    def list_first_attr(self, data: list[I16]) -> ListFirstAttr:
        """Get attributes of the list (tests struct with list at the beginning)"""

    @rpc(0xC08)
    def list_mid_attr(self, data: list[I16]) -> ListMidAttr:
        """Get attributes of the list (tests struct with list between members)"""

    @rpc(0xC09)
    def list_last_attr(self, data: list[I16]) -> ListLastAttr:
        """Get attributes of the list (tests struct with list at the end)"""

    @rpc(0xC0A)
    def two_list_attr(self, data_a: list[I16], data_b: list[I16]) -> TwoListAttr:
        """Get attributes of two lists merged. (tests struct with multiple lists)"""

    @rpc(0xC0B)
    def epoch_to_date(self, epoch: I32) -> MockDate:
        """Convert seconds from epoch to date."""

    @rpc(0xC0C)
    def emoji(self, text: str) -> str:
        """Send emoji, receive emoji."""

    @rpc(0xC0D)
    def cat_lists(self, list_a: list[U32], list_b: list[U32]) -> list[U32]:
        """Concatenate two lists into one."""

    @rpc(0xC0E)
    def get_random_number(self, seed : U64, iter : U8) -> MockLfsr:
        """
        Get a pseudorandom 64-bit value.
            Uses a very simple and deterministic algorithm which
            you can read about here: https://en.wikipedia.org/wiki/Linear-feedback_shift_register
        """

    @rpc(0xC0F)
    def struct_in_param(self, structure: ListFirstAttr):
        """Send structure in parameter."""

    @notification(0xE00)
    def notify_date(self, date: MockDate):
        """Notifies a current date."""
        
    @notification(0xE01)
    def notify_log(self, log: MockLogMessage):
        """Notifies a arbitrary string message."""
    
    @notification(0xE02)
    def notify_heartbeat(self):
        """Signal that remote is alive."""
    
    @notification(0xE03)
    def notify_bitwise_complement(self, value: U64, complement: U64):
        """Notifies a value and its bitwise complement."""

    @notification(0xE04, direction=CallDirection.TWO_WAY)
    def notify_bitfields(self, config: BitfieldStruct):
        """Sends struct with bitfields"""

    @notification(0xE05, direction=CallDirection.TWO_WAY)
    def notify_motor_report(self, report: MockMotorReport):
        """Sends motor state and sampled data."""

    @notification(0xE06, direction=CallDirection.TWO_WAY)
    def notify_motor_control(self, control: MockMotorControl):
        """Requests change of the motor state."""


if __name__ == "__main__":

    with Generator(TestProtocol) as gen:
        gen.force_overwrite = True
        gen.csharp.is_partial = True
        gen.csharp.namespace = "CompostRpc.IntegrationTests"
        gen.c.generate()
        #! This is a temporary hack to allow C# generation, until a proper TWO_WAY support is added    
        TestProtocol._rpcs = {k: x for (k, x) in TestProtocol._rpcs.items() if not x.is_notification or x.direction == CallDirection.TO_LOCAL}
        gen.csharp.generate()