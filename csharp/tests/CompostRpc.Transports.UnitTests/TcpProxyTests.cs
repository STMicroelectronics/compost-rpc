using System.Net.Sockets;
using System.Threading.Tasks;
using CompostRpc.Transports.UnitTests.Mocks;

namespace CompostRpc.Transports.UnitTests;

public class TcpProxyTests
{
    private static readonly int _testPort = 40000 + Environment.Version.Major * 100;

    [Fact]
    public async Task SingleClientTest()
    {
        EchoMockTransport transport = new();
        await using Session session = new(transport);
        await using TcpProxy proxy = new(session, _testPort);
        using TcpTransport client = new("localhost", _testPort);
        await using Session clientSession = new(client);

        clientSession.TransactionTimeout = TimeSpan.FromSeconds(100);
        Message resp = await clientSession.InvokeRawRpcAsync(1);
        Assert.True(resp.Header.IsUnsupportedResponse);
    }

    [Fact]
    public async Task ClientReconnectTest()
    {
        EchoMockTransport transport = new();
        await using Session session = new(transport);
        await using TcpProxy proxy = new(session, _testPort);

        using (TcpTransport client = new("localhost", _testPort))
        await using (Session clientSession = new(client))
        {
            clientSession.TransactionTimeout = TimeSpan.FromSeconds(100);
            Message resp = await clientSession.InvokeRawRpcAsync(1);
            Assert.True(resp.Header.IsUnsupportedResponse);
        }

        using (TcpTransport client = new("localhost", _testPort))
        await using (Session clientSession = new(client))
        {
            clientSession.TransactionTimeout = TimeSpan.FromSeconds(100);
            Message resp = await clientSession.InvokeRawRpcAsync(1);
            Assert.True(resp.Header.IsUnsupportedResponse);
        }
    }
}