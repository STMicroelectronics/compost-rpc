
namespace CompostRpc.IntegrationTests.Utils;

[AttributeUsage(AttributeTargets.Method)]
public class RpcImplementationAttribute(string rpcName) : System.Attribute
{
    public string RpcName { get; set; } = rpcName;
}