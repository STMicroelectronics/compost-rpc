using System;
using System.Diagnostics.CodeAnalysis;
using System.Runtime.InteropServices;
using System.Threading.Tasks;

namespace CompostRpc;

/// <summary>
/// Represents a single Compost transaction (pair of request/response).
/// </summary>
public class Transaction
{
    private TaskCompletionSource<Message> _txnTask;
    public Message Request { get; private set; }
    public byte TxnID { get => Request.Header.Txn; }
    /// <summary>
    /// Task that will be completed when <see cref="SetResponse"/> is called.
    /// </summary>
    public Task<Message> Response { get => _txnTask.Task; }

    /// <summary>
    /// Creates an object that represents pending Compost transaction.
    /// </summary>
    /// <param name="request">Message with the request payload. 
    /// </param>
    public Transaction(Message request)
    {
        _txnTask = new TaskCompletionSource<Message>();
        Request = request;
    }

    /// <summary>
    /// Assigns response to the request.
    /// </summary>
    /// <param name="respBuffer">Buffer with the response.
    /// </param>
    public void SetResponse(Message response)
    {
        _txnTask.TrySetResult(response);
    }

    /// <summary>
    /// Cancels the pending transaction.
    /// </summary>
    public void Cancel()
    {
        _txnTask.TrySetCanceled();
    }
}