#!/usr/bin/env python

import subprocess
import sys
import os
import platform
import argparse
import json
from typing import Callable
import re


CC = os.environ.get("CC", default="gcc")
CC_PPC = os.environ.get("CC_PPC", default="powerpc-linux-gnu-gcc")
PYTHON = os.environ.get("PYTHON", default=sys.executable)

CFLAGS = [
    "-std=c11",
    "-Og",
    "-g",
    "-Wall",
    "-Wextra",
    "-pedantic",
    "-fanalyzer",
    "-Wno-analyzer-infinite-loop",
    "-I.",
    "-Imock",
    "-DCOMPOST_DEBUG",
]

CFLAGS_SANITIZED = [
    "-fsanitize=undefined",
    "-fsanitize=address",
]

CFLAGS_POWERPC = [
    "-static",
]

already_run: set[str] = set()
targets: dict[str, Callable] = dict()


def target(msg: str = None, dependencies: set[str] = frozenset()):
    def decorator(func):
        def wrapper():
            if func.__name__ in already_run:
                return
            for dep in dependencies:
                dep()
            if msg:
                print(f"\n>\t{msg}\n")
            func()
            already_run.add(func.__name__)

        targets[func.__name__] = wrapper
        return wrapper

    return decorator

def run (args : list[str], **kwargs):
    if "check" not in kwargs:
        kwargs["check"] = True
    print(f"Running command: {' '.join(args)}")
    try:
        return subprocess.run(args, **kwargs)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: \n{e.stderr}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Command {e.filename} does not exist!")
        sys.exit(1)

@target("Generating version from Git")
def version():
    ver = json.loads(run(["dotnet-gitversion"], capture_output=True, text=True).stdout)
    if ver['PreReleaseLabel']:
        prerelease = f".{ver['PreReleaseLabel']}{ver['PreReleaseNumber']}"
    else:
        prerelease = ""
    python_ver = f"{ver['MajorMinorPatch']}{prerelease}"
    with open("../compost_rpc/compost_rpc.py", "r") as file:
        content = file.read()
    content = re.sub(r'^__version__\s*=.*$', f"__version__ = \"{python_ver}\"", content, flags=re.MULTILINE)
    with open("../compost_rpc/compost_rpc.py", "w") as file:
        file.write(content)
    print(f"Detected version {python_ver} from Git repository.")

@target("Generating code")
def codegen():
    run([PYTHON, "protocol_def.py"])


@target("Testing slices", {codegen})
def slices_test():
    run([CC, *CFLAGS, "test_slice.c", "compost.c", "protocol_impl.c", "-o", "test_slice"])
    run(["./test_slice"])


@target("Testing slices (sanitized)", {codegen})
def slices_sanitized_test():
    run([CC, *CFLAGS, *CFLAGS_SANITIZED, "test_slice.c", "compost.c", "protocol_impl.c", "-o", "test_slice"])
    run(["./test_slice"])


@target("Testing slices (PowerPC)", {codegen})
def slices_powerpc_test():
    run([CC_PPC, *CFLAGS, *CFLAGS_POWERPC, "test_slice.c", "compost.c", "protocol_impl.c", "-o", "test_slice"])
    run(["qemu-ppc", "./test_slice"])


@target("Building mock", {codegen})
def mock():
    run([CC, *CFLAGS, "-o", "mock/compost_mock", "mock/main.c", "compost.c", "protocol_impl.c"])


@target("Building mock (sanitized)", {codegen})
def mock_sanitized():
    run([CC, *CFLAGS, *CFLAGS_SANITIZED, "-o", "mock/compost_mock", "mock/main.c", "compost.c", "protocol_impl.c"])


@target("Checking mock", {mock})
def mock_check():
    run(["echo", '"00 01 02 03" | xxd -r -p | ./mock/compost_mock > /dev/null"'], shell=True)


@target("Testing Python with mock", {mock, mock_check})
def mock_test():
    run([PYTHON, "test_compost.py", "--mock", "./mock/compost_mock", "--log-cli-level", "DEBUG"])


@target("Building mock (PowerPC)", {codegen})
def mock_powerpc():
    run([CC_PPC, *CFLAGS, *CFLAGS_POWERPC, "-o", "mock/compost_mock_ppc", "mock/main.c", "compost.c", "protocol_impl.c"])


@target("Checking mock (PowerPC)", {mock_powerpc})
def mock_powerpc_check():
    run(["echo", '"00 01 02 03" | xxd -r -p | qemu-ppc ./mock/compost_mock_ppc > /dev/null"'], shell=True)


@target("Testing Python with mock (PowerPC)", {mock_powerpc, mock_powerpc_check})
def mock_powerpc_test():
    run([PYTHON, "test_compost.py", "--mock", "qemu-ppc ./mock/compost_mock_ppc", "--log-cli-level", "DEBUG"])


@target("Checking mock (sanitized)", {mock_sanitized})
def mock_sanitized_check():
    run(["echo", '"00 01 02 03" | xxd -r -p | ./mock/compost_mock > /dev/null"'], shell=True)


@target("Testing Python with mock (sanitized)", {mock_sanitized, mock_sanitized_check})
def mock_sanitized_test():
    run([PYTHON, "test_compost.py", "--mock", "./mock/compost_mock", "--log-cli-level", "DEBUG"])


@target()
def test():
    if platform.system() == "Linux":
        slices_sanitized_test()
        mock_test()
        slices_powerpc_test()
        mock_powerpc_test()
    else:
        slices_test()
        mock_test()
        print("Not running on Linux - skipping advanced tests")


@target()
def test_native():
    slices_test()
    mock_sanitized_test()


@target()
def test_powerpc():
    slices_powerpc_test()
    mock_powerpc_test()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="test.py", description="Compost test runner")
    parser.add_argument("target", nargs="?", default="test", choices=targets.keys(), help="Target to run")
    args = parser.parse_args()

    # Change current working directory to the script directory
    os.chdir(sys.path[0] + "/test")

    targets[args.target]()

    print("Finished successfully")
