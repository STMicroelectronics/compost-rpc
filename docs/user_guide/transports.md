# Transports

Compost messages can be transported over any medium. Some transports are
provided with the implementations, except for C where you need to implement
the plumbing to selected transport by yourself.

Transports must transport all the messages correctly - there are no protection
mechanisms built in to Compost itself. If your medium is unreliable you have
to provide the protections yourself. Compost expects only valid messages.

## Serial port

Raw messages sent over serial port. There is no encapsulation.
Python implementation needs pyserial to be able to use the serial transport.

## UDP

For UDP user needs to set destination address and port. The UDP payload
always contains one Compost message.

## Stdio

Raw messages are sent over standard input/output. This can be useful for simple
communication with another executable/process on the same PC.
This transport is used for testing Compost implementations for different
languages against each other.
