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
}
