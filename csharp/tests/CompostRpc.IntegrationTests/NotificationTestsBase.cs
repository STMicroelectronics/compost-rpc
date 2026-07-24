using System.Threading.Tasks;
using System.Threading.Tasks.Dataflow;

namespace CompostRpc.IntegrationTests;

public abstract class NotificationTestsBase
{
    private readonly TestProtocol _unit;

    public NotificationTestsBase()
    {
        _unit = GetTestProtocol();
    }

    protected abstract TestProtocol GetTestProtocol();

    protected BufferBlock<object> _notificationArgs = new();

    protected async Task<T> FetchNotificationArg<T>()
    {
        Task<object> receive = _notificationArgs.ReceiveAsync();
        Task finished = await Task.WhenAny(receive, Task.Delay(TimeSpan.FromSeconds(10)));
        if (finished == receive)
            return (T)await receive;
        else
            throw new TimeoutException("Incoming notification was expected but no data was received.");
    }

    [Fact]
    public async Task NotifyDateByTriggerRpcTest()
    {
        _unit.NotifyDate += (date) => _notificationArgs.Post(date);
        await _unit.TriggerNotificationAsync(0xe00);
        MockDate val = await FetchNotificationArg<MockDate>();
    }

    [Fact]
    public async Task NotifyVoidByTriggerRpcTest()
    {
        _unit.NotifyHeartbeat += () => _notificationArgs.Post(true);
        await _unit.TriggerNotificationAsync(0xe02);
        bool val = await FetchNotificationArg<bool>();
        Assert.IsType<bool>(val);
    }

    [Fact]
    public async Task NotifyMultipleArgsByTriggerRpcTest()
    {
        _unit.NotifyBitwiseComplement += (a, b) =>
        {
            _notificationArgs.Post(a);
            _notificationArgs.Post(b);
        };
        await _unit.TriggerNotificationAsync(0xe03);
        ulong a = await FetchNotificationArg<ulong>();
        ulong b = await FetchNotificationArg<ulong>();
        Assert.True(a == ~b);
    }

    [Fact]
    public async Task NotifyNestedBitfieldsByTriggerRpcTest()
    {
        _unit.NotifyBitfields += (a, b) => _notificationArgs.Post((a, b));
        await _unit.TriggerNotificationAsync(0xe04);

        (BitfieldStruct a, NestedBitfieldStruct b) = await FetchNotificationArg<(BitfieldStruct, NestedBitfieldStruct)>();
        Assert.Equal(0U, a.Channel);
        Assert.Equal(1U, a.Inom);
        Assert.Equal(1U, a.Tnom);
        Assert.Equal(Voltages.Mv110_92, a.Temp);
        Assert.Equal(1U, b.Leading);
        Assert.Equal(0xA5U, b.Fields.Channel);
        Assert.Equal(0x12U, b.Fields.Inom);
        Assert.Equal(0x9U, b.Fields.Hsc);
        Assert.Equal(0x155U, b.Fields.Tnom);
        Assert.Equal(Voltages.Mv63_08, b.Fields.Temp);
        Assert.Equal(0x5U, b.Fields.Ststart);
        Assert.Equal(1U, b.Fields.Ccm);
        Assert.Equal(0U, b.Fields.Set);
        Assert.Equal(1U, b.Fields.State);
        Assert.Equal(0U, b.Fields.Clear);
        Assert.Equal(Status.Warn, b.Status);
    }
}
