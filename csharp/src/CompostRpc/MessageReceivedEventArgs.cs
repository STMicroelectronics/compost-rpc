namespace CompostRpc;

/// <summary>
/// Argument for events raised when message is received by <see cref="ITransport"/> changes.
/// </summary>
public class MessageReceivedEventArgs(Message msg) : EventArgs
{
    public Message Message { get; } = msg;
}