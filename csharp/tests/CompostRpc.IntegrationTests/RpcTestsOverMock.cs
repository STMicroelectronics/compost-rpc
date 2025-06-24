using CompostRpc.IntegrationTests.Fixtures;

namespace CompostRpc.IntegrationTests;

public class RpcTestsOverMock(TestProtocolMockFixture fixture) : RpcTestsBase, IClassFixture<TestProtocolMockFixture>
{
    TestProtocolMockFixture _fixture = fixture;

    protected override TestProtocol GetTestProtocol()
    {
        return _fixture.Protocol;
    }
}
