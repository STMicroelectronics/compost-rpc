namespace CompostRpc;

/// <summary>
/// Struct that represents header of a Compost message.
/// </summary>
public readonly struct MessageHeader
{
    /// <summary>
    /// Message type that signals an error when processing request
    /// </summary>
    public const ushort ErrorResponseRpcId = 0xfee;
    /// <summary>
    /// Message type that signals that the request is not supported by the target
    /// </summary>
    public const ushort UnsupportedResponseRpcId = 0xfef;
    /// <summary>
    /// Size of the message data.
    /// </summary>
    public BufferUnit Len { get; init; }
    /// <summary>
    /// Transaction ID. Used to pair response with request. Is 0 for notification.
    /// </summary>
    public byte Txn { get; init; }
    /// <summary>
    /// Value that identifies the function call. Depends on the specific protocol.
    /// </summary>
    public ushort RpcId { get; init; }
    /// <summary>
    /// Identifies requests/notifications from responses.
    /// </summary>
    public bool Resp { get; init; }

    public bool IsErrorResponse => Resp && RpcId == ErrorResponseRpcId;
    public bool IsUnsupportedResponse => Resp && RpcId == UnsupportedResponseRpcId;

    /// <summary>
    /// Read Compost header information from the beginning of a buffer.
    /// </summary>
    /// <param name="buffer">Buffer with header</param>
    /// <param name="offset">Position of header, defaults to 0</param>
    /// <returns>Header object</returns>
    public static MessageHeader Parse(byte[] buffer, int offset = 0)
    {
        return new MessageHeader
        {
            Len = BufferUnit.FromWords(buffer[offset]),
            Txn = buffer[offset + 1],
            RpcId = (ushort)(((buffer[offset + 2] & 0xF) << 8) | buffer[offset + 3]),
            Resp = ((buffer[offset + 2] >> 4) & 0x1) != 0
        };
    }

    /// <summary>
    /// Writes Compost header to a buffer.
    /// </summary>
    /// <param name="buffer"></param>
    /// <param name="offset"></param>
    public void Write(byte[] buffer, int offset = 0)
    {
        if (buffer is null || buffer.Length < offset + Serialization.HeaderSize.Bytes)
            return;

        buffer[0] = (byte)Len.Words;
        buffer[1] = Txn;
        buffer[2] = (byte)((RpcId >> 8) & 0x0F);
        buffer[2] |= (byte)((Resp ? 0b1 : 0b0) << 4);
        buffer[3] = (byte)(RpcId & 0xFF);
    }

    public override string ToString()
    {
        return $"{nameof(MessageHeader)} [Txn={Txn}, RpcId=0x{RpcId:X3}, Len={Len.Words} words, Resp={Resp}]";
    }
}