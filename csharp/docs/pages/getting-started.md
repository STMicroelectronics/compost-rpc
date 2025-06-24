# Getting Started

## Generate protocol file

Follow the tutorial to define the functions for the application protocol and to integrate compost into a firmware of a device.

```python
if __name__ == "__main__":
    import sys

    with Generator(MyProtocol) as gen:
        gen.csharp.generate()
```

In this example, `MyProtocol.cs` will be generated in the current working directory, as well as `MyProtocolTypes` if the protocol uses user-defined enums and structs. You can then add these files to your codebase. 

## Using the library

First you need to create some [Transport](xref:CompostRpc.ITransport) and connect to it. 
The library provides implementation to several popular transports - here I will use [SerialTransport](xref:CompostRpc.Transports.SerialTransport).
Note the `using` statement, that ensures Transport will be automatically closed and disposed at the end of current scope.

```csharp
//                   (port, baudRate, timeoutMs)
using SerialTransport comm = new ("COM5", 115200, 500);
```

Then you just need to create instance of your protocol (here called `MyProtocol`) and point it to the `comm` in the constructor. 
Now you can start calling your functions or subscribe to notifications!

```csharp
MyProtocol protocol = new (comm);
//Call the RPC functions. All calls are by their nature asynchronous
//and should be awaited.
await protocol.MyRpcFunction();
//You can use standard Event syntax to subscribe to notifications.
protocol.MyNotification += MyHandler;
//Dispose protocol correctly on application exit
protocol.Dispose();
```