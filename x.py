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
    "-Itest",
    "-Itest/mock",
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
        def wrapper(*args, **kwargs):
            if func.__name__ in already_run:
                return
            for dep in dependencies:
                dep()
            if msg:
                print(f"\n>\t{msg}\n")
            result = func(*args, **kwargs)
            already_run.add(func.__name__)
            return result

        targets[func.__name__] = wrapper
        return wrapper

    return decorator

def run(args: list[str], **kwargs):
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


def replace_line(path: str, pattern: str, replacement: str):
    with open(path, "r", encoding="utf-8") as file:
        content = file.read()

    new_content, replaced = re.subn(pattern, replacement, content, flags=re.MULTILINE)
    if replaced != 1:
        print(f"Expected to replace exactly one line in {path}, replaced {replaced} lines instead.")
        sys.exit(1)

    with open(path, "w", encoding="utf-8") as file:
        file.write(new_content)

@target("Generating version from Git")
def version():
    ver = json.loads(run(["dotnet", "tool", "exec", "GitVersion.Tool"], capture_output=True, text=True).stdout)
    if ver['PreReleaseLabel']:
        prerelease = f".{ver['PreReleaseLabel']}{ver['PreReleaseNumber']}"
    else:
        prerelease = ""
    python_ver = f"{ver['MajorMinorPatch']}{prerelease}"
    replace_line("compost_rpc/compost_rpc.py", r'^__version__\s*=.*$', f'__version__ = "{python_ver}"')
    run(["uv", "version", python_ver])
    print(f"Detected version {python_ver} from Git repository.")
    return python_ver


@target("Creating release commit")
def release(release_type: str):
    run(["uv", "version", "--bump", release_type])
    new_version = run(["uv", "version", "--short"], capture_output=True, text=True).stdout.strip()

    replace_line("compost_rpc/compost_rpc.py", r'^__version__\s*=.*$', f'__version__ = "{new_version}"')

    run(["git", "add", "compost_rpc/compost_rpc.py", "pyproject.toml"])
    run(["git", "commit", "-m", f"chore: Release version {new_version}"])
    run(["git", "tag", f"v{new_version}"])

    print(f"Created release commit for version {new_version}.")

@target("Generating code")
def codegen():
    run([PYTHON, "test/protocol_def.py"])


@target("Testing slices", {codegen})
def slices_test():
    run([CC, *CFLAGS, "test/test_slice.c", "test/compost.c", "test/protocol_impl.c", "-o", "test/test_slice"])
    run(["./test/test_slice"])


@target("Testing slices (sanitized)", {codegen})
def slices_sanitized_test():
    run([CC, *CFLAGS, *CFLAGS_SANITIZED, "test/test_slice.c", "test/compost.c", "test/protocol_impl.c", "-o", "test/test_slice"])
    run(["./test/test_slice"])


@target("Testing slices (PowerPC)", {codegen})
def slices_powerpc_test():
    run([CC_PPC, *CFLAGS, *CFLAGS_POWERPC, "test/test_slice.c", "test/compost.c", "test/protocol_impl.c", "-o", "test/test_slice"])
    run(["qemu-ppc", "./test/test_slice"])


@target("Building mock", {codegen})
def mock():
    run([CC, *CFLAGS, "-o", "test/mock/compost_mock", "test/mock/main.c", "test/compost.c", "test/protocol_impl.c"])


@target("Building mock (sanitized)", {codegen})
def mock_sanitized():
    run([CC, *CFLAGS, *CFLAGS_SANITIZED, "-o", "test/mock/compost_mock", "test/mock/main.c", "test/compost.c", "test/protocol_impl.c"])


@target("Checking mock", {mock})
def mock_check():
    run(['echo "00 01 02 03" | xxd -r -p | ./test/mock/compost_mock > /dev/null'], shell=True)


@target("Testing Python with mock", {mock, mock_check})
def mock_test():
    run([PYTHON, "test/test_compost.py", "--mock", "./test/mock/compost_mock", "--log-cli-level", "DEBUG"])


@target("Building mock (PowerPC)", {codegen})
def mock_powerpc():
    run([CC_PPC, *CFLAGS, *CFLAGS_POWERPC, "-o", "test/mock/compost_mock_ppc", "test/mock/main.c", "test/compost.c", "test/protocol_impl.c"])


@target("Checking mock (PowerPC)", {mock_powerpc})
def mock_powerpc_check():
    run(['echo "00 01 02 03" | xxd -r -p | qemu-ppc ./test/mock/compost_mock_ppc > /dev/null'], shell=True)


@target("Testing Python with mock (PowerPC)", {mock_powerpc, mock_powerpc_check})
def mock_powerpc_test():
    run([PYTHON, "test/test_compost.py", "--mock", "qemu-ppc ./test/mock/compost_mock_ppc", "--log-cli-level", "DEBUG"])


@target("Checking mock (sanitized)", {mock_sanitized})
def mock_sanitized_check():
    run(['echo "00 01 02 03" | xxd -r -p | ./test/mock/compost_mock > /dev/null'], shell=True)


@target("Testing Python with mock (sanitized)", {mock_sanitized, mock_sanitized_check})
def mock_sanitized_test():
    run([PYTHON, "test/test_compost.py", "--mock", "./test/mock/compost_mock", "--log-cli-level", "DEBUG"])


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
    parser = argparse.ArgumentParser(prog="x.py", description="Compost development script")
    subparsers = parser.add_subparsers(dest="target")
    parser.set_defaults(target="test")

    for target_name in targets:
        target_parser = subparsers.add_parser(target_name, help=f"Run '{target_name}' target")
        if target_name == "release":
            target_parser.add_argument("release_type", choices=("major", "minor", "patch"), help="Release bump type")

    args = parser.parse_args()

    target_kwargs = {}
    if args.target == "release":
        target_kwargs["release_type"] = args.release_type

    targets[args.target](**target_kwargs)

    print("Finished successfully")
