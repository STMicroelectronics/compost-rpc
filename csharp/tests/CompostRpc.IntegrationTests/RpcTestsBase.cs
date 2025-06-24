namespace CompostRpc.IntegrationTests;

public abstract class RpcTestsBase
{
    private readonly TestProtocol _unit;

    public RpcTestsBase()
    {
        _unit = GetTestProtocol();
    }

    protected abstract TestProtocol GetTestProtocol();

    [Fact]
    public async Task AddNumbersAsync()
    {
        Assert.Equal((uint)7, await _unit.AddIntAsync(5, 2));
    }

    [Fact]
    public async Task AddNumbersWithoutTimeoutAsync()
    {
        TimeSpan tmp = _unit.BaseSession.TransactionTimeout;
        _unit.BaseSession.TransactionTimeout = TimeSpan.Zero;
        Assert.Equal((uint)5000, await _unit.AddIntAsync(3223, 1777));
        _unit.BaseSession.TransactionTimeout = tmp;
    }

    [Fact]
    public async Task CallUnimplementedRpcFunction()
    {
        await Assert.ThrowsAsync<ProtocolException>(async () => await _unit.AddIntUnimplementedAsync(5, 2));
    }

    [InlineData(new uint[] { 5, 10, 15 }, 30)]
    [InlineData(new uint[] { 1, 2, 3 }, 6)]
    [InlineData(new uint[] { 1, 2, 3, 4, 5, 5, 5, 5 }, 30)]
    [Theory]
    public async Task SumListsIncreasingInSize(uint[] numbers, int sum)
    {
        Assert.True((await _unit.SumListAsync([.. numbers])) == sum);
        Assert.True((await _unit.SumListAsync([.. numbers, .. numbers])) == 2 * sum);
    }

    [Fact]
    public async Task ReturnVoidAsync()
    {
        await _unit.VoidReturnAsync(5);
        await _unit.VoidFullAsync();
    }

    [InlineData(9, 4)]
    [Theory]
    public async Task DivideFloatsAsync(float a, float b)
    {
        Assert.True((await _unit.DivideFloatAsync(a, b)) == a / b);
    }

    [InlineData("ahoj", 1, "bipk")]
    [Theory]
    public async Task CaesarCipherAsync(string str, byte offset, string res)
    {
        Assert.True((await _unit.CaesarCipherAsync(str, offset)) == res);
    }

    [InlineData(new byte[] { 4, 3, 2 }, new byte[] { 2, 3, 4 })]
    [InlineData(new byte[] { 96, 8, 3, 65, 255, 129 }, new byte[] { 3, 8, 65, 96, 129, 255 })]
    [Theory]
    public async Task SortBytesAsync(byte[] bytes, byte[] ordered)
    {
        Assert.Equal(await _unit.SortBytesAsync(bytes.ToList()), ordered.ToList());
    }

    [InlineData(new short[] { 96, 8, 3, 65, 255, 129 }, 3, 255)]
    [Theory]
    public async Task ListPositionInStructTest(short[] data, short min, short max)
    {
        ListFirstAttr f = await _unit.ListFirstAttrAsync(data.ToList());
        Assert.Equal(f.Data, data);
        Assert.Equal(f.Min, min);
        Assert.Equal(f.Max, max);
        ListMidAttr m = await _unit.ListMidAttrAsync(data.ToList());
        Assert.Equal(m.Data, data);
        Assert.Equal(m.Min, min);
        Assert.Equal(m.Max, max);
        ListLastAttr l = await _unit.ListLastAttrAsync(data.ToList());
        Assert.Equal(l.Data, data);
        Assert.Equal(l.Min, min);
        Assert.Equal(l.Max, max);
    }

    [Fact]
    public async Task TwoListsInStructTest()
    {
        List<short> a = [2, 4, 6];
        List<short> b = [3, 5, 10];
        TwoListAttr t = await _unit.TwoListAttrAsync(a, b);
        Assert.Equal(t.DataA, a);
        Assert.Equal(t.DataB, b);
        Assert.Equal(4, t.AvgA);
        Assert.Equal(6, t.AvgB);
        Assert.Equal(5, t.AvgMerge);
    }

    [InlineData(1706531829)]
    [Theory]
    public async Task EpochToDateTest(int epoch)
    {
        DateTimeOffset expected = DateTimeOffset.FromUnixTimeSeconds(epoch);
        string expected_str = expected.ToString("ddMMyyyy");
        MockDate dt = await _unit.EpochToDateAsync(epoch);
        Assert.Equal(expected.Year, dt.Year);
        Assert.Equal(expected.Month, dt.Month);
        Assert.Equal(expected.Day, dt.Day);
        Assert.Equal(expected_str, dt.AsText);
        Assert.Equal(expected_str.Select(x => (byte)(x - '0')).ToList(), dt.AsDigits);
    }
}