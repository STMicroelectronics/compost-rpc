# Creating custom Transport

If you want to use Compost with a transport that is not yet supported, you can do that very easily. Compost is designed to be transport-agnostic, allowing you to communicate over any medium (serial, TCP, USB, CAN etc.) by implementing your own transport class.


## Implementing the ITransport interface

If you selected a medium and you can work with it from C# (read&write bytes from it), using it with Compost is just a matter of implementing the [`ITransport`](xref:CompostRpc.ITransport) interface:

```csharp
public interface ITransport
{
    void WriteMessage(Message msg);
    Task<Message> ReadMessageAsync(CancellationToken cancellationToken = default);
}
```

- **WriteMessage**: Sends a message to the device.
- **ReadMessageAsync**: Reads the next message from the device asynchronously.


> [!NOTE]
> Look at the [SerialTransport](xref:CompostRpc.Transports.SerialTransport) implementation for a real-world example.

### Handle Message Serialization

There are some helper methods in [Message](xref:CompostRpc.Message) to serialize and deserialize data. For example, if you can represent your Transport as a stream, you can implement reading and writing like this:

```csharp
// To write:
msg.Write(stream);

// To read:
var message = await Message.FromStreamAsync(stream, cancellationToken);
```

Also, if your transport uses unmanaged resources (like sockets or file handles), implement `IDisposable` to ensure proper cleanup.

### Using the custom Transport

Once your transport is ready, use it just like any other transport:

```csharp
using var transport = new CustomTransport();
var protocol = new MyProtocol(transport);
// Now you can use protocol as usual
```

## Expected behavior of Transport

The [`ITransport`](xref:CompostRpc.ITransport) interface makes only a single assumption about your implementation - when it is passed into your [Protocol](xref:CompostRpc.Protocol) or [Session](xref:CompostRpc.Session), it must be fully initialized and it is expected that connection is open and data can be read. In case the connection breaks (disconnected cable, power loss etc.), exception will be thrown to callers of the RPC methods and the connection must be checked and reestablished by creating a new [Protocol](xref:CompostRpc.Protocol) or [Session](xref:CompostRpc.Session) instance.