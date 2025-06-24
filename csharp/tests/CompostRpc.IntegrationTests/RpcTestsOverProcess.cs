using CompostRpc.IntegrationTests.Fixtures;

namespace CompostRpc.IntegrationTests;

[Trait("Category", "External")]
public class RpcTestsOverProcess(TestProtocolProcessFixture fixture) : RpcTestsBase, IClassFixture<TestProtocolProcessFixture>
{
    TestProtocolProcessFixture _fixture = fixture;

    protected override TestProtocol GetTestProtocol()
    {
        return _fixture.Protocol;
    }
}