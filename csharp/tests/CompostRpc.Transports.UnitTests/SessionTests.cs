using CompostRpc.Transports.UnitTests.Mocks;

namespace CompostRpc.Transports.UnitTests;

public class SessionTests
{
    [Fact]
    public async Task SessionDisposalTest()
    {
        EchoMockTransport transport = new();
        await using Session session = new(transport);
        session.TransactionTimeout = TimeSpan.FromSeconds(100);
        Message resp1 = await session.InvokeRawRpcAsync(1);
        Message resp2 = await session.InvokeRawRpcAsync(1);
        Assert.True(resp1.Header.IsUnsupportedResponse);
        Assert.True(resp1.Header.IsUnsupportedResponse);
    }
}