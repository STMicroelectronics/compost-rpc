namespace CompostRpc;

/// <summary>
/// Exception related to serialization/deserialization of Compost messages
/// and other data related errors during RPC calls and notification processing.
/// </summary>

[Serializable]
public class SerializationException : Exception
{
    public SerializationException()
        : base() { }
    public SerializationException(string message)
        : base(message)
    { }
    public SerializationException(string message, Exception innerException)
        : base(message, innerException)
    { }
}