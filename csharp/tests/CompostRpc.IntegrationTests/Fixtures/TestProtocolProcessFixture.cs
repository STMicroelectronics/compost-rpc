
using System.Diagnostics;
using CompostRpc.IntegrationTests.Mocks;
using Xunit.Sdk;

namespace CompostRpc.IntegrationTests.Fixtures;

public class TestProtocolProcessFixture : IAsyncDisposable
{
    public TestProtocol Protocol { get; }
    public ProcessTransport Transport { get; }
    public string MockPath { get; }
    public TestProtocolProcessFixture()
    {
        string defaultMockPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "compost_mock.exe");
        MockPath = Environment.GetEnvironmentVariable("COMPOST_MOCK_PATH") ?? defaultMockPath;
        if (!File.Exists(MockPath))
            throw new FileNotFoundException($"No mock at {MockPath}! Use COMPOST_MOCK_PATH env variable to set correct path!");
        Transport = new ProcessTransport(MockPath);
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
        GC.SuppressFinalize(this);
    }
}