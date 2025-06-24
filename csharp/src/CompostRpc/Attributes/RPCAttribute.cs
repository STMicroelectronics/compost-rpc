
namespace CompostRpc;

[System.AttributeUsage(System.AttributeTargets.Method)]
public class RpcAttribute(ushort rpcId) : System.Attribute
{
    public ushort RpcId { get; init; } = rpcId;
}