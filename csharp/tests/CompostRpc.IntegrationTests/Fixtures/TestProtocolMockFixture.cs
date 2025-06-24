
using System.Diagnostics;
using CompostRpc.IntegrationTests.Mocks;
using CompostRpc.IntegrationTests;

namespace CompostRpc.IntegrationTests.Fixtures;

public class TestProtocolMockFixture : IAsyncDisposable
{
    public TestProtocol Protocol { get; }
    public MockTransport<TestProtocol> Mock { get; }
    public TestProtocolMockFixture()
    {
        Mock = new();
        Protocol = new TestProtocol(Mock);
        Protocol.BaseSession.TransactionTimeout = TimeSpan.FromSeconds(10);
        Mock.BindedProtocol = Protocol;
        Protocol.BaseSession.UnexpectedMessageReceived += (source, args) =>
        {
            Trace.TraceWarning($"{Mock.GetType().Name}[{Mock.GetHashCode()}] unexpected " + args.Message.ToString());
        };
    }

    public async ValueTask DisposeAsync()
    {
        await Protocol.DisposeAsync();
        GC.SuppressFinalize(this);
    }
}