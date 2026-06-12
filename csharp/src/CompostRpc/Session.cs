using CompostRpc.Resources;
#if NETSTANDARD2_0
using CompostRpc.Compatibility;
#endif

namespace CompostRpc;

/// <summary>
/// Class that represents the current state of communication with some
/// Transport. It holds pending transactions and handles distribution of Txn
/// identifiers in a thread-safe manner.
/// </summary>
public class Session : IAsyncDisposable
{
    private readonly ITransport _transport;
    private readonly SynchronizationContext _synchronizationContext;
    private readonly object _txnDictMutex;
    private readonly object _txnCounterMutex;
    private readonly object _notifMutex;
    private readonly object _streamWriteMutex;
    private readonly CancellationTokenSource _readCts;
    private readonly Task _readTask;
    private readonly Transaction?[] _txnDict;
    private readonly Queue<Transaction> _queue;
    private readonly Dictionary<ushort, Action<Message>> _notifDict;
    private uint _concurrencyLimit = 1;
    private uint _concurrentTransactionCount;
    /// <summary>
    /// Timeout for <see cref="InvokeRawRpcAsync"/>
    /// </summary>
    /// <value>Timeout is disabled by setting it to zero.</value>
    public TimeSpan TransactionTimeout { get; set; }

    /// <summary>
    /// Limits how many transactions can be concurrently processed by the server.
    /// Allowed range is 1 to 255 (inclusive).
    /// </summary>
    public uint ConcurrencyLimit
    {
        get => _concurrencyLimit;
        set
        {
            if (value < 1 || value > 255)
                throw new ArgumentOutOfRangeException(nameof(ConcurrencyLimit),
                    $"{nameof(ConcurrencyLimit)} must be between 1 and 255.");
            _concurrencyLimit = value;
        }
    }

    /// <summary>
    /// Limits how many transactions can be pending
    /// </summary>
    public uint PendingTransactionLimit { get; set; } = 255;

    /// <summary>
    /// Number of transactions currently held by the session.
    /// </summary>
    public uint PendingTransactionCount
    {
        get
        {
            lock (_txnDictMutex)
            {
                return (uint)_queue.Count + _concurrentTransactionCount;
            }
        }
    }

    /// <summary>
    /// Expected transaction ID of next RPC call 
    /// </summary>
    private byte _txnCounter = 1;

    public event EventHandler<MessageReceivedEventArgs>? UnexpectedMessageReceived;
    public event EventHandler<MessageReceivedEventArgs>? NotificationReceived;

    public Session(ITransport transport)
    {
        _transport = transport;
        _synchronizationContext = SynchronizationContext.Current ?? new SynchronizationContext();
        _txnDictMutex = new object();
        _txnCounterMutex = new object();
        _notifMutex = new object();
        _streamWriteMutex = new object();
        _txnDict = new Transaction?[byte.MaxValue + 1];
        _queue = [];
        _notifDict = [];

        _readCts = new CancellationTokenSource();
        _readTask = ReadMessagesAsync(_readCts.Token);
    }

    /// <summary>
    /// Processes Compost RPC call. 
    /// Payload is sent to a device and than a valid response will be awaited,
    /// at most for the duration specified by <see cref="TransactionTimeout"/>.
    /// Device must be connected
    /// when this method called.
    /// </summary>
    /// <param name="requestId">Message type of the request</param>
    /// <param name="responseId">Message type of the response</param>
    /// <param name="requestArgs">Data to send in the request</param>
    /// <param name="requestShape">Request shape. Avoids reflection calls if provided.</param>
    /// <exception cref="TransportException"></exception>
    /// <exception cref="TimeoutException"></exception>
    /// 
    public Task<Message> InvokeRawRpcAsync(ushort requestId, object[] requestArgs, MessageShape requestShape)
    {
        Message request = new(AquireNextTxnId(), requestId, false, requestArgs, requestShape);
        return InvokeRawRpcAsync(request);
    }

    public Task<Message> InvokeRawRpcAsync(ushort requestId, params object[] requestArgs)
    {
        return InvokeRawRpcAsync(requestId, requestArgs, MessageShape.FromArguments(requestArgs));
    }

    public Task<Message> InvokeRawRpcAsync(ushort requestId, ReadOnlySpan<byte> serializedRequestArgs)
    {
        Message request = new(AquireNextTxnId(), requestId, false, serializedRequestArgs);
        return InvokeRawRpcAsync(request);
    }

    private bool TrySendTransactionRequest(Transaction txn)
    {
        try
        {
            lock (_streamWriteMutex)
            {
                _transport.WriteMessage(txn.Request);
            }
            return true;
        }
        catch (Exception e)
        {
            FetchAndRemoveTransaction(txn.TxnID);
            txn.TrySetException(e);
            return false;
        }
    }

    private bool TryTransactionDispatchFromQueue()
    {
        Transaction? txn;
        lock (_txnDictMutex)
        {
            if (_concurrentTransactionCount >= ConcurrencyLimit)
                return false;

            do
            {
                if (!_queue.TryDequeue(out txn) || txn is null)
                    return false;
            } while (txn.IsCompleted);

            AddTransaction(txn);
        }

        return TrySendTransactionRequest(txn);
    }

    private void EnqueueTransaction(Transaction txn)
    {
        bool sendRequestDirectly = false;

        lock (_txnDictMutex)
        {
            if ((_concurrentTransactionCount + _queue.Count + 1) > PendingTransactionLimit)
                throw new TransportException(Strings.TransactionLimitReached());

            // Fast path: if there is free concurrency capacity and no backlog,
            // dispatch this request immediately without touching the queue.
            if (_queue.Count == 0 && _concurrentTransactionCount < ConcurrencyLimit)
            {
                AddTransaction(txn);
                sendRequestDirectly = true;
            }
            else
            {
                _queue.Enqueue(txn);
            }
        }

        if (sendRequestDirectly)
        {
            TrySendTransactionRequest(txn);
        }
        else
        {
            TryTransactionDispatchFromQueue();
        }
    }

    /// <summary>
    /// This is a private base function for the InvokeRawRPCAsync that accepts
    /// already processed Message. It is not exposed because user might use any
    /// TxnID and it must be managed by the Transport directly.
    /// </summary>
    /// <param name="request"></param>
    /// <returns></returns>
    /// <exception cref="TransportException"></exception>
    /// <exception cref="TimeoutException"></exception>
    private async Task<Message> InvokeRawRpcAsync(Message request)
    {
        Transaction txn = new(request);
        EnqueueTransaction(txn);

        try
        {
            Task finished;
            if (TransactionTimeout.TotalMilliseconds > 0)
                finished = await Task.WhenAny(txn.Response, Task.Delay(TransactionTimeout)).ConfigureAwait(false);
            else
                finished = await Task.WhenAny(txn.Response).ConfigureAwait(false);

            if (finished != txn.Response)
            {
                TimeoutException timeout = new();
                if (txn.TrySetException(timeout))
                {
                    FetchAndRemoveTransaction(txn.TxnID);
                    throw timeout;
                }
            }

            return await txn.Response.ConfigureAwait(false);
        }
        finally
        {
            TryTransactionDispatchFromQueue();
        }
    }

    /// <summary>
    /// Registers handler for incoming notifications.
    /// <remark>Called by a Compost implementation.</remark>
    /// </summary>
    /// <param name="rpcId">Notification message type</param>
    /// <param name="handler">Handler for processing the message byte array</param>
    public void AddNotificationHandler(ushort rpcId, Action<Message> handler)
    {
        lock (_notifMutex)
        {
            if (!_notifDict.TryGetValue(rpcId, out Action<Message>? added))
                _notifDict[rpcId] = handler;
            else
            {
                if (!added.GetInvocationList().Contains(handler))
                    _notifDict[rpcId] = added + handler;
            }
        }
    }

    /// <summary>
    /// Removes previously registed handler for incoming notifications.
    /// <remark>Called by a Compost implementation.</remark>
    /// </summary>
    /// <param name="rpcId">Notification message type</param>
    /// <param name="handler">Handler for processing the message byte array</param>
    public void RemoveNotificationHandler(ushort rpcId, Action<Message> handler)
    {
        lock (_notifMutex)
        {
            if (_notifDict.TryGetValue(rpcId, out Action<Message>? added))
            {
                var afterRemove = added - handler;
                if (afterRemove is null)
                    _notifDict.Remove(rpcId);
                else
                    _notifDict[rpcId] = afterRemove;
            }
        }
    }

    /// <summary>
    /// Read task. Runs while the device is connected.
    /// </summary>
    /// <returns>Reference to a task</returns>
    private async Task ReadMessagesAsync(CancellationToken cancellationToken)
    {
        while (!cancellationToken.IsCancellationRequested)
        {
            Message msg;
            try
            {
                msg = await _transport.ReadMessageAsync(cancellationToken).ConfigureAwait(false);
            }
            catch (AggregateException e)
            {
                if (e.InnerException is not OperationCanceledException)
                    throw;
                return;
            }
            catch (OperationCanceledException)
            {
                return;
            }
            bool isNotification = CheckNotificationExists(msg.Header.RpcId) && !msg.Header.Resp;
            Transaction? txn = null;
            if (!isNotification && msg.Header.Resp)
            {
                txn = FetchAndRemoveTransaction(msg.Header.Txn);
                if (txn == null)
                {
                    UnexpectedMessageReceived?.Invoke(this, new MessageReceivedEventArgs(msg));
                    continue;
                }
            }

            if (isNotification)
                TryInvokeNotification(msg);
            else
                txn?.TrySetResponse(msg);
        }
    }

    protected byte AquireNextTxnId()
    {
        lock (_txnCounterMutex)
        {
            byte current = _txnCounter;
            _txnCounter = (byte)(_txnCounter + 1 == 0 ? 1 : _txnCounter + 1);
            return current;
        }
    }

    /// <summary>
    /// Stores transaction so it can be retrieved by the read task when
    /// matching response is received.
    /// </summary>
    /// <param name="txn">CompostTransaction object</param>
    protected void AddTransaction(Transaction txn)
    {
        lock (_txnDictMutex)
        {
            //* Creates buffer for response (so that the reading thread
            //* knows this respID is valid)
            if (_txnDict[txn.TxnID] != null)
                throw new TransportException(Strings.TransactionWrapAround());
            _txnDict[txn.TxnID] = txn;
            _concurrentTransactionCount += 1;
        }
    }

    /// <summary>
    /// Used to retrieve pending transaction by the response and transaction IDs.
    /// If it is found, it is returned and also deleted from the database.
    /// </summary>
    /// <param name="respId">Response message type</param>
    /// <param name="txnId">Transaction ID</param>
    /// <returns>Null if no transaction is found.</returns>
    protected Transaction? FetchAndRemoveTransaction(byte txnId)
    {
        lock (_txnDictMutex)
        {
            var txn = _txnDict[txnId];
            _txnDict[txnId] = null;
            if (txn != null)
                _concurrentTransactionCount -= 1;
            return txn;
        }
    }

    /// <summary>
    /// Clears database with pending transactions.
    /// </summary>
    protected void ClearTransactions()
    {
        lock (_txnDictMutex)
        {
            for (int i = 0; i < _txnDict.Length; i++)
            {
                _txnDict[i]?.Cancel();
                _txnDict[i] = null;
            }
            foreach (var queuedTxn in _queue)
                queuedTxn.Cancel();
            _queue.Clear();
            _concurrentTransactionCount = 0;
        }
    }

    /// <summary>
    /// Checks if Compost notification with specified message type
    /// is implemented in the protocol.
    /// </summary>
    /// <param name="rpcId">Message type of the notification</param>
    /// <returns></returns>
    protected bool CheckNotificationExists(ushort rpcId)
    {
        lock (_notifMutex)
        {
            return _notifDict.ContainsKey(rpcId);
        }
    }

    /// <summary>
    /// If the message type is valid (<seealso cref="CheckNotificationExists"/>),
    /// invoke subscribed handlers.
    /// </summary>
    /// <param name="notification">Notification message</param>
    /// <returns></returns>
    protected void TryInvokeNotification(Message notification)
    {
        lock (_notifMutex)
        {
            if (_notifDict.TryGetValue(notification.Header.RpcId, out Action<Message>? handlers))
            {
                NotificationReceived?.Invoke(this, new MessageReceivedEventArgs(notification));
                _synchronizationContext.Post(_ =>
                {
                    handlers.Invoke(notification);
                }, null);
            }
        }
    }

    public async ValueTask DisposeAsync()
    {
        _readCts.Cancel();
        var completedTask = await Task.WhenAny(_readTask, Task.Delay(1000));
        if (completedTask != _readTask)
            throw new TimeoutException(
                $"Pending read operation over {_transport.GetType().Name} did not finish gracefully. " +
                $"Ensure implementation of {nameof(ITransport.ReadMessageAsync)} respects cancellation token.");
        _readCts.Dispose();
        ClearTransactions();
        GC.SuppressFinalize(this);
    }
}