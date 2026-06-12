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
    /// Task that will be completed when <see cref="TrySetResponse"/> is called.
    /// </summary>
    public Task<Message> Response { get => _txnTask.Task; }
    public bool IsCompleted { get => _txnTask.Task.IsCompleted; }

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
    /// Tries to assign response message as the transaction result.
    /// </summary>
    /// <param name="response">Message with the response.</param>
    /// <returns>True when response was assigned.</returns>
    public bool TrySetResponse(Message response)
    {
        return _txnTask.TrySetResult(response);
    }

    /// <summary>
    /// Tries to assign exception to the request.
    /// </summary>
    /// <param name="exception">Exception that failed the transaction.</param>
    /// <returns>True when exception was assigned.</returns>
    public bool TrySetException(Exception exception)
    {
        return _txnTask.TrySetException(exception);
    }

    /// <summary>
    /// Cancels the pending transaction.
    /// </summary>
    public void Cancel()
    {
        _txnTask.TrySetCanceled();
    }
}