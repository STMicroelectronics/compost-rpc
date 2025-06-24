using System.Collections.Concurrent;
using System.Threading.Tasks.Dataflow;

namespace CompostRpc.Transports.UnitTests.Mocks;

public class EchoMockTransport : ITransport
{
    private readonly BufferBlock<byte> _txns = new();

    public async Task<Message> ReadMessageAsync(CancellationToken cancellationToken = default)
    {
        byte txn = await _txns.ReceiveAsync(cancellationToken);
        return new Message(txn, MessageHeader.UnsupportedResponseRpcId, true);
    }

    public void WriteMessage(Message msg)
    {
        _txns.Post(msg.Header.Txn);
    }
}