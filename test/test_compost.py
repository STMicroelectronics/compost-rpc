from queue import Queue
import sys
import os
import shlex
from time import sleep, time
from pathlib import Path
import argparse
import protocol_def
from protocol_def import compost_rpc, MockDate, MotorState, MotorDirection, MockMotorControl, MockMotorReport, BitfieldStruct, Voltages, ListFirstAttr

# Get default command to run mock from environment, otherwise use the hardcoded command
mock_path = os.environ.get('COMPOST_MOCK_PATH')
if mock_path:
    default_mock_cmd = f'"{mock_path}"'
else:
    default_mock_cmd = f'"{Path(sys.path[0]) / "mock" / "compost_mock"}"'

parser = argparse.ArgumentParser()
parser.add_argument('--mock', default=default_mock_cmd)
(args, pytest_args) = parser.parse_known_args()

rpc = protocol_def.TestProtocol(compost_rpc.StdioTransport(shlex.split(args.mock)))


# Notification handlers

notification_argument_queue = Queue()

def date_notif_handler(date: MockDate):
    notification_argument_queue.put(date)

rpc.notify_date.subscribe(date_notif_handler)

def motor_report_handler(report: MockMotorReport):
    notification_argument_queue.put(report)

rpc.notify_motor_report.subscribe(motor_report_handler)

def motor_control_handler(control: MockMotorControl):
    notification_argument_queue.put(control)

rpc.notify_motor_control.subscribe(motor_control_handler)

def notify_heartbeat_handler():
    notification_argument_queue.put(None)

rpc.notify_heartbeat.subscribe(notify_heartbeat_handler)

def notify_bitwise_complement_handler(a, b):
    notification_argument_queue.put((a, b))

rpc.notify_bitwise_complement.subscribe(notify_bitwise_complement_handler)

# Testing procedures


def test_void_return():
    assert rpc.void_return(3) is None

def test_void_full():
    assert rpc.void_full() is None

def test_notification():
    rpc.trigger_notification(0xE00)
    notification_argument_queue.get(timeout=1.0)

    rpc.trigger_notification(0xE02)
    arg = notification_argument_queue.get(timeout=1.0)
    assert arg == None
    
    rpc.trigger_notification(0xE03)
    a, b = notification_argument_queue.get(timeout=1.0)
    assert a == (~b & 0xFFFFFFFFFFFFFFFF)


def test_notification_send():
    rpc.notify_date(MockDate(year=2024, month=1, day=24, as_text="24012024", as_digits=b"\x02\x04\x00\x01\x02\x00\x02\x04"))
    rpc.notify_motor_control(MockMotorControl(state=MotorState.ON, direction=MotorDirection.UP, pwm_duty=50))
    report = notification_argument_queue.get(timeout=1.0)
    assert report.state == MotorState.STOP
    assert report.direction == MotorDirection.DOWN
    assert report.voltage == [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
    assert report.current == [41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60]
    rpc.notify_motor_report(MockMotorReport(state=MotorState.START, direction=MotorDirection.UP,
                                 voltage=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
                                 current=[31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50]))
    control = notification_argument_queue.get(timeout=1.0)
    assert control.state == MotorState.STOP
    assert control.direction == MotorDirection.DOWN
    assert control.pwm_duty == 1200

def test_integers():
    assert rpc.add_int(3, 5) == 8

# def test_integers2():
#     assert rpc.add_int(3, 5) == 9

def test_lists():
    assert rpc.sum_list([1, 2, 3, 4, 5, 6]) == 21
    assert rpc.sort_bytes(bytes([3, 1, 2])) == bytes([1, 2, 3])

def test_strings():
    assert rpc.caesar_cipher("secret", 1) == "tfdsfu"

def test_struct_with_str_and_bytes():
    date = rpc.epoch_to_date(1706109534)
    assert date.year == 2024
    assert date.month == 1
    assert date.day == 24
    assert date.as_text == "24012024"
    assert date.as_digits == b"\x02\x04\x00\x01\x02\x00\x02\x04"

def test_struct_with_two_lists():
    twolists = rpc.two_list_attr([2, 4, 6], [3, 5, 10])
    assert twolists.avg_a == 4
    assert twolists.avg_b == 6
    assert twolists.avg_merge == 5
    assert twolists.data_a == [2, 4, 6]
    assert twolists.data_b == [3, 5, 10]

def test_emoji():
    assert rpc.emoji("😘") == "🥰"
    assert rpc.emoji("😛") == "🤔"

def test_list_cat():
    assert rpc.cat_lists([1, 2, 3], [4, 5, 6]) == [1, 2, 3, 4, 5, 6]

def test_floats():
    assert rpc.divide_float(8.0, 1.0) == 8.0
    assert rpc.divide_float(88.16, 856.3) - 0.1029545719957959 < 0.00001

def test_bitints():
    q = Queue()
    config = BitfieldStruct(channel=0,inom=1,hsc=0,tnom=1,temp=0,ststart=1,ccm=0,set=1,state=0,clear=1)
    
    def bitfield_handler(payload: BitfieldStruct):
        q.put(payload)

    rpc.notify_bitfields.subscribe(bitfield_handler)
    rpc.notify_bitfields(config)
    sleep(0.1)

    payload = q.get()
    print(f"{config=}")
    print(f"{payload=}")
    assert ~config.channel & ((1 << 8) - 1) == payload.channel
    assert ~config.inom & ((1 << 5) - 1) == payload.inom
    assert ~config.hsc & ((1 << 4) - 1) == payload.hsc
    assert ~config.tnom & ((1 << 9) - 1) == payload.tnom
    assert Voltages.MV_37_50 == payload.temp
    assert ~config.ststart & ((1 << 3) - 1) == payload.ststart
    assert ~config.ccm & ((1 << 1) - 1) == payload.ccm
    assert ~config.set & ((1 << 1) - 1) == payload.set
    assert ~config.state & ((1 << 1) - 1) == payload.state
    assert ~config.clear & ((1 << 1) - 1) == payload.clear

def test_nested_structs():
    current_epoch = int(time())
    lfsr = rpc.get_random_number(0x1111111111111118, 1)
    current = rpc.epoch_to_date(current_epoch)
    assert(lfsr.value == 0x088888888888888C)
    assert(lfsr.polynomial == 0xD800000000000000)
    assert(lfsr.timestamp.year == current.year)
    assert(lfsr.timestamp.as_text == current.as_text)

def test_struct_in_param():
    structure = ListFirstAttr(data=[1, 2, 3, 4, 5, 10, 6, 7, 8, 9], min=1, max=10)
    rpc.struct_in_param(structure)

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(pytest_args))


