using System.Threading.Tasks.Dataflow;
using CompostRpc.IntegrationTests.Fixtures;

namespace CompostRpc.IntegrationTests;

public class NotificationTestsOverMock(TestProtocolMockFixture fixture) : NotificationTestsBase, IClassFixture<TestProtocolMockFixture>
{
    TestProtocolMockFixture _fixture = fixture;
    TestProtocol _unit = fixture.Protocol;
    protected override TestProtocol GetTestProtocol()
    {
        return _unit;
    }

    [Fact]
    public async Task NotifyDateByTransportTest()
    {
        _unit.NotifyDate += (date) => _notificationArgs.Post(date);
        MockDate d = new()
        {
            Day = (ushort)DateTime.Now.Day,
            Month = (byte)DateTime.Now.Month,
            Year = (byte)DateTime.Now.Year
        };
        _fixture.Mock.PostNotification(0xe00, [d]);
        MockDate val = await FetchNotificationArg<MockDate>();
        Assert.Equal(d.Day, val.Day);
        Assert.Equal(d.Month, val.Month);
        Assert.Equal(d.Year, val.Year);
    }

    [Fact]
    public async Task NotifyVoidByTransportTest()
    {
        void handler()
        {
            _notificationArgs.Post(true);
        }
        _unit.NotifyHeartbeat += handler;
        _fixture.Mock.PostNotification(0xe02, []);
        bool val = await FetchNotificationArg<bool>();
        Assert.IsType<bool>(val);
    }

    [Fact]
    public async Task NotifyMultipleArgsByTransportTest()
    {
        void handler(ulong a, ulong b)
        {
            _notificationArgs.Post((a, b));
        }
        _unit.NotifyBitwiseComplement += handler;
        _fixture.Mock.PostNotification(0xe03, [0xAAAAAAAAAAAAAAAA, 0x5555555555555555]);
        (ulong a, ulong b) = await FetchNotificationArg<ValueTuple<ulong, ulong>>();
        Assert.True(a == ~b);
    }
}
