
using System.Diagnostics;
using CompostRpc.IntegrationTests.Mocks;
using CompostRpc.Transports;

namespace CompostRpc.IntegrationTests.Fixtures;

public class TestProtocolTcpFixture : IAsyncDisposable
{
    public TestProtocol Protocol { get; }
    public TcpTransport Transport { get; }
    public TestProtocol ProxiedProtocol { get; }
    public MockTransport<TestProtocol> ProxiedTransport { get; }
    private TcpProxy Proxy { get; }
    public TestProtocolTcpFixture()
    {
        // ? Avoid port collisions between parallel tests across .NET versions
        int testPort = 50000 + Environment.Version.Major * 100;
        //? Setup basic mocked transport
        ProxiedTransport = new MockTransport<TestProtocol>();
        ProxiedProtocol = new TestProtocol(ProxiedTransport);
        ProxiedProtocol.BaseSession.TransactionTimeout = TimeSpan.FromSeconds(10);
        ProxiedProtocol.BaseSession.UnexpectedMessageReceived += (source, args) =>
        {
            Trace.TraceWarning($"ProxyMockTransport[{ProxiedTransport.GetHashCode()}] unexpected " + args.Message.ToString());
        };
        ProxiedTransport.BindedProtocol = Protocol;

        //? Setup proxy over mocked Transport
        Proxy = new TcpProxy(ProxiedProtocol, testPort);

        //? Connect to a proxy
        Transport = new TcpTransport("localhost", testPort);
        Protocol = new TestProtocol(Transport);
        Protocol.BaseSession.TransactionTimeout = TimeSpan.FromSeconds(10);
        Protocol.BaseSession.UnexpectedMessageReceived += (source, args) =>
        {
            Trace.TraceWarning($"{Transport.GetType().Name}[{Transport.GetHashCode()}] unexpected " + args.Message.ToString());
        };
    }

    public async ValueTask DisposeAsync()
    {
        await Protocol.DisposeAsync();
        Transport.Dispose();
        await Proxy.DisposeAsync();
        await ProxiedProtocol.DisposeAsync();
        GC.SuppressFinalize(this);
    }
}