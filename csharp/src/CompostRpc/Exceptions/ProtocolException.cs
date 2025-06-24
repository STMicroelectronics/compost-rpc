namespace CompostRpc;

/// <summary>
/// Exception related to incorrect usage of Protocol functions
/// or incorrect Protocol definition.
/// </summary>

[Serializable]
public class ProtocolException : Exception
{
    public ProtocolException()
        : base() { }
    public ProtocolException(string message)
        : base(message)
    { }
    public ProtocolException(string message, Exception innerException)
        : base(message, innerException)
    { }
}