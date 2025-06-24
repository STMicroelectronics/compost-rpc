namespace CompostRpc;
/// <summary>
/// Exception related to <see cref="ITransport"/>
/// </summary>

[Serializable]
public class TransportException : Exception
{
    public TransportException()
        : base() { }
    public TransportException(string message)
        : base(message)
    { }
    public TransportException(string message, Exception innerException)
        : base(message, innerException)
    { }
}