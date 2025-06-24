"""Example script which shows how to use the Python interface to call remote functions over UDP or
Serial port.
"""
from compost_rpc import UdpTransport, SerialTransport
from example_protocol_def import ExampleProtocol

#rpc = ExampleProtocol(UdpTransport(target_ip="16.16.16.16", target_port=5001))
#rpc = ExampleProtocol(SerialTransport(serial_port="COM18", baudrate=1e6))
rpc = ExampleProtocol(SerialTransport(serial_port="/dev/ttyUSB0", baudrate=1e6))

print(rpc.app_info())

# print(rpc.float_add(0.1, 0.2))
# print(rpc.read(0x01000000, 20))
# rpc.write(0x01000000, bytes(b"ahoy!"))
# rpc.set_led(example_protocol_def.LedState.LED_ON)

