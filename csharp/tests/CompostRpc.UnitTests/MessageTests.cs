namespace CompostRpc.UnitTests;

public class MessageTests
{
    private readonly byte[] mockResponseMessageHeaderBytes = [0x11, 0x22, 0x1D, 0xDD];
    private readonly MessageHeader mockResponseMessageHeader = new()
    {

        Resp = true,
        Len = BufferUnit.FromWords(0x11),
        Txn = 0x22,
        RpcId = 0xDDD
    };

    [Fact]
    public void ResponseMessageHeaderParseTest()
    {
        MessageHeader parsedHeader = MessageHeader.Parse(mockResponseMessageHeaderBytes);
        Assert.Equal(mockResponseMessageHeader, parsedHeader);
    }

    [Fact]
    public void ResponseMessageHeaderWriteTest()
    {
        byte[] buffer = new byte[Serialization.HeaderSize.Bytes];
        mockResponseMessageHeader.Write(buffer);
        Assert.Equal(mockResponseMessageHeaderBytes, buffer);
    }
}