import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from compost_rpc import TcpTransport
from protocol_def import SimpleProtocol

rpc = SimpleProtocol(TcpTransport(target_ip="127.0.0.1", target_port=3333))

print(rpc.add_int(1, 2))
