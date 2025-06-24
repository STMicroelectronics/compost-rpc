using CompostRpc.IntegrationTests.Fixtures;

namespace CompostRpc.IntegrationTests;

public class RpcTestsOverTcp(TestProtocolTcpFixture fixture) : RpcTestsBase, IClassFixture<TestProtocolTcpFixture>
{
    TestProtocolTcpFixture _fixture = fixture;

    protected override TestProtocol GetTestProtocol()
    {
        return _fixture.Protocol;
    }
}