namespace CompostRpc;
/// <summary>
/// Exception related to <see cref="ITransport"/>
/// </summary>

[Serializable]
public class SessionException : Exception
{
    public SessionException()
        : base() { }
    public SessionException(string message)
        : base(message)
    { }
    public SessionException(string message, Exception innerException)
        : base(message, innerException)
    { }
}