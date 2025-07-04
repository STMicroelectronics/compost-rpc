# Compost

Compost is a Remote Procedure Call ([RPC](https://en.wikipedia.org/wiki/Remote_procedure_call))
protocol generator with a simple wire format.

It abstracts communication between a PC and an MCU. Basically it allows you to
call functions on your MCU from a PC.

Compost is meant to be used over any medium, but it's simplicity is best suited
for UART/RS232 or UDP/IP.

## Install

Packages are coming soon...

## Documentation

Documentation is available in the [Wiki](https://github.com/STMicroelectronics/compost-rpc/wiki)

## Introduction

With Compost you can write a function for your MCU in C, but call
it from Python or C# on a PC.

The call on the PC looks like a normal function
call, but Compost takes the arguments, creates a message and sends it
over a transport like serial port. Then, Compost on the MCU parses the message
and calls your function with the arguments you provided on the PC.
Your function returns a value. Compost on the MCU creates a response message
with the return value. The response is sent to PC. Compost on the PC parses the
message and the function you called on the PC returns the value you provided in
the MCU.

The following diagram tries to illustrate how Compost works and to show what is
provided and what has to be implemented by the user.

![Functional overview for light mode](docs/_static/image/getting_started/overview-light.svg#gh-light-mode-only)
![Functional overview for dark mode](docs/_static/image/getting_started/overview-dark.svg#gh-dark-mode-only)

## Features

### Languge support

- C
  - C11 standard
  - Implemented roles
    - RPC server (callee)
    - Notification sender
    - Notification receiver
- Python
  - Needs version >= 3.10
  - Implemented roles
    - RPC client (caller)
    - Notification receiver
- C#
  - Implemented roles
    - RPC client (caller)
    - Notification receiver

### Transports

- UDP transport
- Serial transport
- Raw ethernet transport (Linux only)
- TCP transport
- Stdio transport
- Custom

### Data types

- 8, 16, 32 and 64-bit signed and unsigned integers
- 32 and 64-bit floating-point numbers (IEEE 754)
- Bit-precise integers
- C like Struct
- C like Enum with selectable underlying type
- Dynamically sized array (list) for each supported primitive type
