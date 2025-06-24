
using System.Net.Sockets;

namespace CompostRpc.Transports;

/// <summary>
/// Implementation of Transport for TCP network protocol
/// </summary>
public class TcpTransport : ITransport, IDisposable
{
    private readonly TcpClient _client;
    private readonly NetworkStream _stream;

    public TcpTransport(string host = "localhost", int port = 50051)
    {
        _client = new TcpClient(host, port);
        _stream = _client.GetStream();
    }

    public Task<Message> ReadMessageAsync(CancellationToken cancellationToken = default)
    {
        return Message.FromStreamAsync(_stream, cancellationToken);
    }

    public void WriteMessage(Message msg)
    {
        msg.Write(_stream);
    }

    public void Dispose()
    {
        _stream.Dispose();
        _client.Dispose();
        GC.SuppressFinalize(this);
    }
}