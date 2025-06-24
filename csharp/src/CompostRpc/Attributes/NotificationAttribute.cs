
namespace CompostRpc;

[System.AttributeUsage(System.AttributeTargets.Event)]
public class NotificationAttribute(ushort rpcId) : System.Attribute
{
    public ushort RpcId { get; init; } = rpcId;
}