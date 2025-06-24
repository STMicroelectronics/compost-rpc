using System.Net;
using System.Net.Sockets;
using System.Threading.Tasks;

namespace CompostRpc.Transports;

public class TcpProxy : IAsyncDisposable
{
    private readonly Session _session;
    private readonly int _port;
    private CancellationTokenSource _listenerCts;
    private CancellationTokenSource _clientCts;
    private NetworkStream? _connectedStream;
    private readonly object _connectedStreamLock = new();
    private TcpListener _listener;
    TcpClient? _connectedClient = null;
    private Task _listenerTask;
    private Task? _handleClientTask;

    public TcpProxy(Protocol protocol, int port = 50051)
        : this(protocol.BaseSession, port)
    {
    }

    public TcpProxy(Session session, int port = 50051)
    {
        _session = session;
        _port = port;
        _listenerCts = new CancellationTokenSource();
        _clientCts = new CancellationTokenSource();
        _listener = new(IPAddress.Any, _port);
        _listener.Start();
        _listenerTask = StartAsync(_listenerCts.Token);
    }

    /// <summary>
    /// Starts listening for new TCP connections on the specified port.
    /// </summary>
    private async Task StartAsync(CancellationToken cancellationToken)
    {
        _session.NotificationReceived += OnTransportNotificationReceived;
        Task<TcpClient>? acceptClientTask = null;

        while (!cancellationToken.IsCancellationRequested)
        {
#pragma warning disable CA2016 // Forward the 'CancellationToken' parameter to methods
            //? .NET 5.0 does not implement the cancellation token parameter, so the cancellation is handled in StartAsync() directly
            acceptClientTask ??= _listener.AcceptTcpClientAsync();
#pragma warning restore CA2016 // Forward the 'CancellationToken' parameter to methods
            Task completed = await Task.WhenAny(acceptClientTask, Task.Delay(500, cancellationToken)).ConfigureAwait(false);
            if (completed == acceptClientTask)
            {
                if (_handleClientTask != null)
                    await CloseClientConnection().ConfigureAwait(false);
                OpenClientConnection(acceptClientTask.Result);
                acceptClientTask = null;
            }
            if (cancellationToken.IsCancellationRequested)
            {
                await CloseClientConnection().ConfigureAwait(false);
                break;
            }
        }
    }

    private void OpenClientConnection(TcpClient client)
    {
        _connectedClient = client;
        lock (_connectedStreamLock)
        {
            _connectedStream = client.GetStream();
        }
        _clientCts = new CancellationTokenSource();
        _handleClientTask = HandleClientAsync(_clientCts.Token);
    }

    private async Task CloseClientConnection()
    {
        lock (_connectedStreamLock)
        {
            _connectedStream?.Close();
            _connectedStream = null;
        }
        _clientCts.Cancel();
        _connectedClient?.Dispose();
        _connectedClient = null;
        try
        {
            if (_handleClientTask is not null)
                await _handleClientTask.ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
        }
        catch (EndOfStreamException)
        {
        }
        _handleClientTask = null;
    }

    /// <summary>
    /// Handles individual client connections and passes data to the given Transport.
    /// </summary>
    private async Task HandleClientAsync(CancellationToken cancellationToken)
    {
        if (_connectedClient is null || _connectedStream is null)
            throw new NullReferenceException();
        while (!cancellationToken.IsCancellationRequested && _connectedClient.Connected)
        {
            Message req = await Message.FromStreamAsync(_connectedStream, cancellationToken).ConfigureAwait(false);
            Message resp = await _session.InvokeRawRpcAsync(req.Header.RpcId, req.Payload).ConfigureAwait(false);
            MessageHeader pairedHeader = new()
            {
                Len = resp.Header.Len,
                RpcId = resp.Header.RpcId,
                Txn = req.Header.Txn,
                Resp = true
            };
            var respBuf = resp.Buffer.ToArray();
            pairedHeader.Write(respBuf);
            _connectedStream.Write(respBuf, 0, respBuf.Length);
        }
    }

    /// <summary>
    /// Handles notifications received by the Transport and forwards them to the client.
    /// </summary>
    private void OnTransportNotificationReceived(object? sender, MessageReceivedEventArgs e)
    {
        lock (_connectedStreamLock)
        {
            if (_connectedStream is not null)
                e.Message.Write(_connectedStream);
        }
    }

    public async ValueTask DisposeAsync()
    {
        _listenerCts.Cancel();
        _session.NotificationReceived -= OnTransportNotificationReceived;
        await _listenerTask.ConfigureAwait(false);
        _listener.Stop();
        _clientCts.Dispose();
        _listenerCts.Dispose();
        GC.SuppressFinalize(this);
    }
}