
namespace CompostRpc;

public abstract partial class Protocol
{
    /// <summary>
    /// RPC call wrapper
    /// </summary>
    protected class RpcInfo
    {
        public ushort Identifier { get; }
        public MessageShape RequestShape { get; }
        public MessageShape ResponseShape { get; }

        internal RpcInfo(ushort id, MessageShape requestShape, MessageShape responseShape)
        {
            Identifier = id;
            RequestShape = requestShape;
            ResponseShape = responseShape;
        }
    }
}