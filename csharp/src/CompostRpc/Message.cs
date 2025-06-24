namespace CompostRpc;
#if NETSTANDARD2_0 || NETSTANDARD2_1
using CompostRpc.Compatibility;
#endif

/// <summary>
/// Wrapper for raw data of a single message.
/// </summary>
public class Message
{
    private readonly Memory<byte> _bufferMemory;
    /// <summary>
    /// Entire message buffer (includes header)
    /// </summary>
    public ReadOnlySpan<byte> Buffer { get => _bufferMemory.Span; }
    /// <summary>
    /// Message header
    /// </summary>
    public MessageHeader Header { get; private init; }
    /// <summary>
    /// Part of the buffer that holds only payload data (excludes header)
    /// </summary>
    public ReadOnlySpan<byte> Payload { get => _bufferMemory.Span.Slice(Serialization.HeaderSize.Bytes); }

    /// <summary>
    /// Get <c>Message</c> object by parsing data from stream.
    /// </summary>
    /// <param name="stream">Stream that contains message</param>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns><c>Message</c> object</returns>
    public static async Task<Message> FromStreamAsync(Stream stream, CancellationToken cancellationToken = default)
    {
        byte[] headerBuf = new byte[Serialization.HeaderSize.Bytes];
        await stream.ReadExactlyAsync(headerBuf, 0, Serialization.HeaderSize.Bytes, cancellationToken).ConfigureAwait(false);
        MessageHeader header = MessageHeader.Parse(headerBuf);
        byte[] rxBuf = new byte[Serialization.HeaderSize.Bytes + header.Len.Bytes];
        await stream.ReadExactlyAsync(rxBuf, Serialization.HeaderSize.Bytes, header.Len.Bytes, cancellationToken).ConfigureAwait(false);
        headerBuf.CopyTo(rxBuf, 0);
        return new Message(header, rxBuf);
    }

    /// <summary>
    /// Internal constructor that allows to directly set the memory buffer.
    /// Public constructors always create deep copy.
    /// </summary>
    /// <param name="header"></param>
    /// <param name="buffer"></param>
    private Message(MessageHeader header, byte[] buffer)
    {
        Header = header;
        _bufferMemory = buffer;
    }

    /// <summary>
    /// Serialize objects into a <c>Message</c>. 
    /// </summary>
    /// <param name="txn">Transaction ID</param>
    /// <param name="rpcId">Message type</param>
    /// <param name="shape">Hint to provide expected shape and payload size.
    /// This avoids repeating reflection calls.</param>
    /// <param name="args">Data that should be serialized</param>
    public Message(byte txn, ushort rpcId, bool resp, object[] args, MessageShape shape)
    {
        BufferUnit payloadSize = shape.IsFixedSize ? shape.Size : Serialization.GetCollectionSize(args);
        byte[] rawBuffer = Serialization.InitBuffer(payloadSize);
        Header = new MessageHeader { Len = payloadSize, Txn = txn, RpcId = rpcId, Resp = resp };
        Header.Write(rawBuffer);
        BufferUnit offset = Serialization.HeaderSize;
        foreach (var arg in args)
        {
            Serialization.Serialize(arg, rawBuffer, ref offset);
        }
        _bufferMemory = new Memory<byte>(rawBuffer);
    }

    public Message(byte txn, ushort rpcId, bool resp, params object[] args)
        : this(txn, rpcId, resp, args, MessageShape.FromArguments(args))
    {
    }

    public Message(byte txn, ushort rpcId, bool resp, ReadOnlySpan<byte> args)
    {
        BufferUnit payloadSize = BufferUnit.FromBytes(args.Length);
        Header = new MessageHeader { Len = payloadSize, Txn = txn, RpcId = rpcId, Resp = resp };
        byte[] rawBuffer = Serialization.InitBuffer(payloadSize);
        args.CopyTo(rawBuffer.AsSpan(Serialization.HeaderSize.Bytes));
        Header.Write(rawBuffer);
        _bufferMemory = new Memory<byte>(rawBuffer);
    }

    /// <summary>
    /// Serialize objects into a <c>Message</c>. 
    /// </summary>
    /// <param name="buffer">Buffer with message data</param>
    /// <param name="startIndex">Optional index to specify where to look for a header</param>
    public Message(byte[] buffer, int startIndex = 0)
    {
        Header = MessageHeader.Parse(buffer, startIndex);
        byte[] rawBuffer = Serialization.InitBuffer(Header.Len);
        Array.Copy(buffer, startIndex, rawBuffer, 0, rawBuffer.Length);
        _bufferMemory = new Memory<byte>(rawBuffer);
    }

    public void Write(Stream stream)
    {
        stream.Write(Buffer);
    }

    public override string ToString()
    {
        var payloadHex = BitConverter.ToString(Payload.ToArray());
        return $"{nameof(Message)} [Txn=0x{Header.Txn}, RpcId=0x{Header.RpcId:X3}, Len={Header.Len.Words} bytes, Payload={payloadHex}]";
    }
}