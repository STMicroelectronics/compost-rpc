# Tutorial

This step-by-step tutorial shows how to call a function in Python
but make it execute on an MCU.

## Prerequisites

PC with Linux or Windows.

### Hardware

To follow this tutorial you need some sort of MCU board.

### Software

You will need Python >= 3.10. And because we will use serial port
for communication, you also need to install pyserial.

```sh
pip install pyserial
```

## Download Compost

Python package management is out of the scope of this tutorial. Compost supports
usage as an installed package, but also without installation. We will use the
most simple approach, which is to use the source archive without installation.

Download the source archive from here: [Getting started](./getting_started)

Extract the archive and enter the `compost_rpc` directory in your favorite
terminal.

```sh
cd compost_rpc-0.1.1/compost_rpc
```

You can check your setup by running the main module:

```console
$ python compost_rpc.py
Compost 0.1.1
Pyserial found.
This module does nothing when called as a script, it's only usable as a library.
```

## Defining the protocol

Compost uses the Python language itself to define the protocol. You may be more
familiar with the name "interface" instead of "protocol". We are talking about a
group of function signatures.

We will create a new file called `protocol_def.py`.

First step is to define prototype of remote functions you would like to call. We
will define one function with one argument of type {class}`compost_rpc.U8` and a
return value of type {class}`compost_rpc.U16`. You always have to type annotate
all the arguments and return value with [supported types](./datatypes/index).

We put all the functions as methods in one class inherited from the
{class}`compost_rpc.Protocol` class.

```{code-block} python
:caption: protocol_def.py
from compost_rpc import Protocol, rpc, U16, U8

# All RPC functions must be in one class inherited from compost_rpc.Protocol
class ExampleProtocol(Protocol):
    # You must use the decorator to assign unique msg types to each function
    @rpc(0x00B)
    def adc_read(self, channel: U8) -> U16: 
        """Reads specified ADC channel"""
        # Function body should be empty
```

```{tip}
For a larger example check out the
[example protocol definition](./examples/protocol_def).
```

We call the Python file with function prototypes the protocol definition file.

From the protocol definition Compost can generate code for other languages.

## Generating C code

We use the same protocol definition file as a script that will generate the
code.

```{code-block} python
:caption: protocol_def.py
:emphasize-lines: 8,9,10
from compost_rpc import Protocol, Generator, rpc, U16, U8

class ExampleProtocol(Protocol):
    @rpc(0x00B)
    def adc_read(self, channel: U8) -> U16: 
        """Reads specified ADC channel"""

if __name__ == "__main__":
    with Generator(ExampleProtocol) as gen:
        gen.c.generate() # Generate the C code files!
```

Run the script to see what it will generate:

```sh
python protocol_def.py
```

The script creates `compost.c` and `compost.h`
files with C code in your current directory.

You need to add all of these files to your C project.

For more information about code generation check out
[Generating code](./generating_code).

## Integration on the MCU side

The main entry point to Compost in C language is the function
`compost_msg_process()`. You have to call this function for every received
Compost message and it will give you the response you have to send back.

Example of integration with blocking `uart_read()` and `uart_write()`
functions. In real application with real serial port, it's recommended to use
timeout for reading the rest of the frame after the first byte is received.

```c
#include "mcu.h"
#include "uart.h"
#include "compost.h"

uint8_t tx_buf[1024];
uint8_t rx_buf[1024];

int main(void)
{
    mcu_init();

    for (;;) {
        /* Receive the first byte of the header which is the msg_data length in 32b words */
        uart_read(rx_buf, 1);

        /* Receive the rest of the header and the msg_data */
        if (uart_read(rx_buf + 1, 3 + 4 * rx_buf[0])) {
            continue;
        }

        /* You pass the rx_buf with received Compost frame
            and Compost will call the function and put the
            Compost response with the return value to tx_buf. */
        int16_t msg_size = compost_msg_process(tx_buf, sizeof(tx_buf), rx_buf, 4 + 4 * rx_buf[0]);

        /* Send the response from tx_buf */
        if (msg_size > 0) {
            uart_write(tx_buf, msg_size);
        } else if (msg_size == 0) {
            // No response to send
        } else {
            // Error handling
        }
    }
}
```

This example does not compile yet:

```console
$ make
    LD build/obj/compost_impl.o
build/obj/compost_rpc.o: In function `invoke_adc_read':
compost_rpc.c:245: undefined reference to `adc_read_handler'
collect2: error: ld returned 1 exit status
make: *** [Makefile:83: SPC582B60_Main] Error 1
```

This is a feature of Compost - you have to implement all of the remote
functions.

### Implement the remote function in C

In C you define body of the function you would like to call remotely.
Compost generates the C function prototype for you from the protocol definition
file. Just include `compost.h`.

```c
#include "compost.h"

uint16_t adc_read_handler(uint8_t channel)
{
    // In real application we would read the adc value here.
    // For this example we will just return a dummy value.
    if (channel == 0)
        return 1;
    else
        return 0;
}
```

One way to think about this is that we have just written the body of the
function that we defined in the Python protocol definition.

Your project should now compile successfully.

### Call the remote function from Python

For calling our new RPC function we will create a new script:

```{code-block} python
:caption: client_script.py
from compost_rpc import SerialTransport
from protocol_def import ExampleProtocol

rpc = ExampleProtocol(SerialTransport(serial_port="COM16", baudrate=921600))

adc_value = rpc.adc_read(0)
print(adc_value)
```

First you instantiate a transport - we use serial port as it is one of the
simplest ones.
First you create a connection by instantiating the class in which you
defined the remote function prototypes. Then call the Python function
which you specified in the protocol definition file:

```console
$ python client_script.py
1
```

Thats it! We called a function in Python but it was executed on an MCU.

See other Python interface usage examples in [example script](./examples/client_script).

## Deep dive

Roughly, this is what happens when you call `rpc.adc_read(0)`:

1. Python takes the argument `0`, serializes it into a Compost request message
and sends it over serial port
2. Your firmware receives the message and calls `compost_msg_process(...)` with
pointers to RX buffer containing the received message and TX buffer
3. Compost parses the message and calls your function with the passed argument
`adc_read_handler(0);`
4. Your `adc_read_handler` function returns the value `1`
5. Compost prepares the response message in the TX buffer with this return value
and `compost_msg_process()` returns
6. Your firmware sends the response message prepared in the TX buffer by
`compost_msg_process()`
7. Python receives the response message, parses it and the function
`rpc.adc_read(0)` returns `1`
