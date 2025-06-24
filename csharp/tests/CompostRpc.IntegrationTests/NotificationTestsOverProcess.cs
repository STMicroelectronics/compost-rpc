using CompostRpc.IntegrationTests.Fixtures;

namespace CompostRpc.IntegrationTests;

[Trait("Category", "External")]
public class NotificationTestsOverProcess(TestProtocolProcessFixture fixture) : NotificationTestsBase, IClassFixture<TestProtocolProcessFixture>
{
    TestProtocolProcessFixture _fixture = fixture;
    protected override TestProtocol GetTestProtocol()
    {
        return _fixture.Protocol;
    }
}
