using System;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Reflection;
using CompostRpc.IntegrationTests.Utils;
using CompostRpc.IntegrationTests.Mocks;

namespace CompostRpc.IntegrationTests;

public partial class TestProtocol : Protocol
{
    /// <summary>
    /// RPC function not implemented in the protocol, to test the error response
    /// </summary>
    [Rpc(0x222)]
    public Task<uint> AddIntUnimplementedAsync(uint a, uint b)
        => InvokeRpcAsync<uint>([a, b]);
    
    [RpcImplementation(nameof(TriggerNotificationAsync))]
    public void TriggerNotificationImpl (ushort rpcId)
    {
        object[]? data = rpcId switch 
        {
            0xe00 => [EpochToDateImpl((int)DateTimeOffset.Now.ToUnixTimeSeconds())],
            0xe02 => [true],
            0xe03 => [0xAAAAAAAAAAAAAAAA, 0x5555555555555555],
            _ => throw new NotImplementedException($"Trigger for {rpcId} not defined.")
        };
        ITransport? _baseTransport = (ITransport?)BaseSession?.GetType().GetField("_transport", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(BaseSession);
        switch (_baseTransport)
        {
            case MockTransport<TestProtocol> a:
                a.PostNotification(rpcId, data, true);
                break;
            default:
                throw new InvalidOperationException($"{nameof(TriggerNotificationImpl)} must only be called when device is set to {nameof(MockTransport<TestProtocol>)} instance.");
        }
    }

    [RpcImplementation(nameof(AddIntAsync))]
    public static int AddIntImpl(int a, int b) => a + b;

    [RpcImplementation(nameof(SumListAsync))]
    public static int SumListImpl(List<int> b)
    {
        return b.Sum();
    }

    [RpcImplementation(nameof(VoidReturnAsync))]
    public static void VoidReturnImpl(short x)
    {
        return;
    }

    [RpcImplementation(nameof(VoidFullAsync))]
    public static void VoidFullImpl()
    {
        return;
    }

    [RpcImplementation(nameof(DivideFloatAsync))]
    public static float DivideFloatImpl(float a, float b)
    {
        return a/b;
    }

    [RpcImplementation(nameof(CaesarCipherAsync))]
    public static string CaesarCipherImpl(string str, byte offset)
    {
        var enc = new string(str.Select(c => (char)(c + offset)).ToArray());
        return enc ?? "";
    }

    [RpcImplementation(nameof(SortBytesAsync))]
    public static List<byte> SortBytesImpl(List<byte> data)
    {
        data.Sort();
        return data;
    }

    private static T CalculateMinMax<T> (List<short> data) where T : new()
    {
        T ret = new();
        var retType = typeof(T);
        retType.GetProperty("Min", BindingFlags.Public | BindingFlags.Instance)?.SetValue(ret, data.Min());
        retType.GetProperty("Max", BindingFlags.Public | BindingFlags.Instance)?.SetValue(ret, data.Max());
        retType.GetProperty("Data", BindingFlags.Public | BindingFlags.Instance)?.SetValue(ret, data);
        return ret;
    }

    [RpcImplementation(nameof(ListFirstAttrAsync))]
    public static ListFirstAttr ListFirstAttrImpl (List<short> data)
    {
        return CalculateMinMax<ListFirstAttr>(data);
    }

    [RpcImplementation(nameof(ListMidAttrAsync))]
    public static ListMidAttr ListMidAttrImpl (List<short> data)
    {
        return CalculateMinMax<ListMidAttr>(data);
    }

    [RpcImplementation(nameof(ListLastAttrAsync))]
    public static ListLastAttr ListLastAttrImpl (List<short> data)
    {
        return CalculateMinMax<ListLastAttr>(data);
    }

    [RpcImplementation(nameof(TwoListAttrAsync))]
    public static TwoListAttr TwoListAttrImpl (List<short> data_a, List<short> data_b)
    {
        return new TwoListAttr()
        {
            AvgA = (float)data_a.Select(i => (int)i).Average(),
            AvgB = (float)data_b.Select(i => (int)i).Average(),
            AvgMerge = (float)data_a.Concat(data_b).Select(i => (int)i).Average(),
            DataA = data_a,
            DataB = data_b
        };
    }
    
    [RpcImplementation(nameof(EpochToDateAsync))]
    public static MockDate EpochToDateImpl (int epoch)
    {
        var dt = DateTimeOffset.FromUnixTimeSeconds(epoch);
        MockDate ret = new()
        {
            Year = dt.Year,
            Month = (byte)dt.Month,
            Day = (ushort)dt.Day,
            AsText = dt.ToString("ddMMyyyy")
        };
        ret.AsDigits = ret.AsText.Select(x => (byte)(x - '0')).ToList();
        return ret;
    }
}