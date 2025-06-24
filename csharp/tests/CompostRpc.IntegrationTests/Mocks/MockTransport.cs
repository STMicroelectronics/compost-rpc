using System.Collections.Specialized;
using System.Data;
using System.Diagnostics;
using System.Reflection;
using System.Threading.Tasks.Dataflow;
using CompostRpc.IntegrationTests.Utils;
using CompostRpc.Transports;

namespace CompostRpc.IntegrationTests.Mocks;

public class MockTransport<T> : ITransport
{
    private readonly BufferBlock<Message> _mem = new();
    private readonly Queue<Message> _defereredNotifs = new();
    private readonly Dictionary<ushort, MethodInfo> _implementations = [];
    public T? BindedProtocol { get; set; }

    public MockTransport()
    {
        Type protocolType = typeof(T);
        var impls = protocolType.GetMethods()
            .Where(x => Attribute.IsDefined(x, typeof(RpcImplementationAttribute)));
        int count = impls.Count();
        foreach (var impl in impls)
        {
            RpcImplementationAttribute attr = impl.GetCustomAttribute<RpcImplementationAttribute>()!;
            var rpcAttr = (protocolType.GetMethod(attr.RpcName)?.GetCustomAttribute<RpcAttribute>()) ?? throw new InvalidOperationException($"{attr.RpcName} function is missing RPC attribute.");
            if (_implementations.ContainsKey(rpcAttr.RpcId))
                throw new ArgumentException($"{attr.RpcName} is duplicate implementation.");
            _implementations[rpcAttr.RpcId] = impl;
        }
    }

    public void PostNotification(ushort rpcId, object[] args, bool postAfterRpc = false)
    {
        Message notif = new(0, rpcId, false, args);
        if (postAfterRpc)
            _defereredNotifs.Enqueue(notif);
        else
            _mem.Post(notif);
    }

    public async Task<Message> ReadMessageAsync(CancellationToken cancellationToken = default)
    {
        Message msg = await _mem.ReceiveAsync(cancellationToken);
        Trace.TraceInformation($"{this.GetType().Name}[{this.GetHashCode()}] reading " + msg.ToString());
        return msg;
    }

    public void WriteMessage(Message msg)
    {
        Trace.TraceInformation($"{this.GetType().Name}[{this.GetHashCode()}] writing " + msg.ToString());
        InvokeImplementation(msg);
    }

    private void InvokeImplementation(Message message)
    {
        if (message.Header.Resp)
            throw new ArgumentException("Cannot invoke based on response message", nameof(message));
        MessageHeader reqHeader = message.Header;
        ushort respId = reqHeader.RpcId;
        object? result;

        if (!_implementations.TryGetValue(reqHeader.RpcId, out MethodInfo? rpc))
        {
            respId = MessageHeader.UnsupportedResponseRpcId;
            result = null;
        }
        else
        {
            ParameterInfo[] args = rpc.GetParameters();
            List<object> argvals = [];
            BufferUnit offset = Serialization.HeaderSize;
            foreach (var arg in args)
            {
                object tmp = Serialization.Deserialize(arg.ParameterType, message.Buffer, ref offset);
                argvals.Add(tmp);
            }

            result = rpc.Invoke(BindedProtocol, [.. argvals]);
            //? Check if the result is null because the RPC returns void
            if (result == null && rpc.ReturnType != typeof(void))
                throw new Exception("RPC implementation likely is not static.");
        }
        Message resp = result is null ?
            new Message(reqHeader.Txn, respId, true)
            : new Message(reqHeader.Txn, respId, true, result);
        _mem.Post(resp);
        while (_defereredNotifs.Count > 0)
        {
            Message notif = _defereredNotifs.Dequeue();
            _mem.Post(notif);
        }
    }
}