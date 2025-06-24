# Protocol definition

To make use of the Compost C# library, you first need to correctly define your set of RPC functions and notifications in a class that must inherit from [Protocol](xref:CompostRpc.Protocol). Typically, this class will be generated from the main Python definiton file, because that way it will be ensured that the generated protocol is fully compatible with the protocol generated for the firmware. However, its still helpful to understand the structure of the generated class in cases when it might be useful to modify the file directly, or even create it from scratch.

## Adding RPC function

*Python definition*
```python
class ExampleProtocol(Rpc):

    @rpc(0xC00)
    def add_int(self, a: U32, b: U32) -> U32:
        """Returns addition of two integers."""
```

*Equivalent C# code*
```csharp
using CompostRpc;

namespace MyApp.IO;

public class ExampleProtocol(ITransport transport) : Protocol(transport)
{
    /// <summary>
    /// Returns addition of two integers.
    /// </summary>
    [Rpc(0xc00, 0xc01)]
    public Task<uint> AddIntAsync (uint a, uint b)
        => InvokeRpcAsync<uint>([a, b]);
}
```

In the above example, you can see a protocol consisting of a single function that sums up two integers. To define a method as RPC call you need to annotate it with the [RpcAttribute](xref:CompostRpc.RpcAttribute) which holds the appropriate request and response IDs. The method should only call [InvokeRpcAsync](xref:CompostRpc.Protocol.InvokeRpcAsync*) and relay all parameters of RPC function in the correct order. Nothing prevents you from adding custom actions before and after [InvokeRpcAsync](xref:CompostRpc.Protocol.InvokeRpcAsync*) is called, however, the [InvokeRpcAsync](xref:CompostRpc.Protocol.InvokeRpcAsync*) must always be called within a method which was annotated with [RpcAttribute](xref:CompostRpc.RpcAttribute) and not doing so will typically result in exception. 

Generic type of [InvokeRpcAsync](xref:CompostRpc.Protocol.InvokeRpcAsync*) must match the expected return type of RPC function. However, since the call is asynchronous, the return value is wrapped in a [Task](https://learn.microsoft.com/dotnet/api/system.threading.tasks.task) object compatible with the native asynchronous features of the .NET framework. The [InvokeRpcAsync](xref:CompostRpc.Protocol.InvokeRpcAsync*) does all the heavy lifting: it serializes message header and parameters, passess the serialized data to the [Transport](xref:CompostRpc.ITransport) specified in ExampleProtocol constructor and finally awaits a response from the device. In this example, the device listening on the other side would sum up the two integers and send back the result - it obviously does not matter what the device does with the parameters, the only important thing is that it returns a correct type.

> [!NOTE]
> Technically, it cannot be determined if the recieved data have a correct type because Compost does not include type information in messages, only the data itself. So if the message has the same size as the expected type, the data will be deserialized without any warnings.

However, this method cannot be called directly outside of the class. This is a deliberate decision, because it forces the developer to create a wrapper function for it, in this case AddIntAsync. Such wrapper could technically also accept `object[]`, but the correct way is to specify parameters of the RPC function. This way, you will get a nice and simple API for your application, with type-checking of the parameters because all the public functions will have same the same signature as in the Python definition.

## Adding notification

```python
class ExampleProtocol(Rpc):

    @notification(0xe00)
    def notify_button_state(self, state: U8):
        """Returns change in a button state."""
```

*Equivalent C# code*
```csharp
using CompostRpc;

namespace MyApp.IO;

public class ExampleProtocol(ITransport transport) : Protocol(transport)
{
    /// <summary>
    /// Returns change in a button state.
    /// </summary>
    [Notification(0xe00)]
    public event Action<byte> NotifyButtonState
    {
        add => AddNotificationHandler(value);
        remove => RemoveNotificationHandler(value);
    }
}
```

Notification is a function that the device can execute asynchronously, without any involvement from the application. Therefore it is suitable to expose it as an event, that the application can subscribe to in a standard manner. Similarly to RPC calls, for every notification you need to create event annotated with [NotificationAttribute](xref:CompostRpc.NotificationAttribute). Furthermore, the `add` and `remove` methods of the event must be overloaded to pass `value` to [AddNotificationHandler](xref:CompostRpc.Protocol.AddNotificationHandler*) and [RemoveNotificationHandler](xref:CompostRpc.Protocol.RemoveNotificationHandler*) respectively. This way, the delegate is passed to the internal object that will manage the invocation of subscribed handlers. This step is unfortunately necessary, because if the handlers would be stored directly in the `ExampleProtocol` class, it would would not be possible for external class to invoke the event.