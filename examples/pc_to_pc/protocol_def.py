import sys
from pathlib import Path

# Hack to import compost_rpc from the parent directory without installing it
sys.path.append(str(Path(__file__).resolve().parents[1]))

from compost_rpc import rpc, U32, Protocol, Generator

class SimpleProtocol(Protocol):

    @rpc(0xC00)
    def add_int(self, a: U32, b: U32) -> U32:
        """Returns the sum of two integers."""
        ...


if __name__ == "__main__":
    with Generator(SimpleProtocol) as gen:
        gen.c.generate()
