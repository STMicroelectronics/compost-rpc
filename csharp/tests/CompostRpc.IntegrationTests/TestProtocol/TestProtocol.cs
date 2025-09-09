
/******************************************************************************/
/*                     G E N E R A T E D   P R O T O C O L                    */
/******************************************************************************/
using System;
using System.Threading.Tasks;
using System.Collections.Generic;
using CompostRpc;

namespace CompostRpc.IntegrationTests;

public partial class TestProtocol(ITransport transport) : Protocol(transport)
{
    /// <summary>
    /// Send request for notification with selected msg_id.
    /// </summary>
    [Rpc(0xb00)]
    public Task TriggerNotificationAsync(ushort rpcId)
        => InvokeRpcAsync([rpcId]);

    /// <summary>
    /// Returns addition of two integers.
    /// </summary>
    [Rpc(0xc00)]
    public Task<uint> AddIntAsync(uint a, uint b)
        => InvokeRpcAsync<uint>([a, b]);

    /// <summary>
    /// Sums up numbers in a list of integers.
    /// </summary>
    [Rpc(0xc01)]
    public Task<uint> SumListAsync(List<uint> a)
        => InvokeRpcAsync<uint>([a]);

    /// <summary>
    /// Sends number and expects no response data.
    /// </summary>
    [Rpc(0xc02)]
    public Task VoidReturnAsync(short x)
        => InvokeRpcAsync([x]);

    /// <summary>
    /// Sends nothing, expects nothing.
    /// </summary>
    [Rpc(0xc03)]
    public Task VoidFullAsync()
        => InvokeRpcAsync();

    /// <summary>
    /// Divide two floats.
    /// </summary>
    [Rpc(0xc04)]
    public Task<float> DivideFloatAsync(float a, float b)
        => InvokeRpcAsync<float>([a, b]);

    /// <summary>
    /// Offset all characters in a string by certain offset
    /// </summary>
    [Rpc(0xc05)]
    public Task<string> CaesarCipherAsync(string str, byte offset)
        => InvokeRpcAsync<string>([str, offset]);

    /// <summary>
    /// Sorts array of bytes in ascending order
    /// </summary>
    [Rpc(0xc06)]
    public Task<List<byte>> SortBytesAsync(List<byte> data)
        => InvokeRpcAsync<List<byte>>([data]);

    /// <summary>
    /// Get attributes of the list (tests struct with list at the beginning)
    /// </summary>
    [Rpc(0xc07)]
    public Task<ListFirstAttr> ListFirstAttrAsync(List<short> data)
        => InvokeRpcAsync<ListFirstAttr>([data]);

    /// <summary>
    /// Get attributes of the list (tests struct with list between members)
    /// </summary>
    [Rpc(0xc08)]
    public Task<ListMidAttr> ListMidAttrAsync(List<short> data)
        => InvokeRpcAsync<ListMidAttr>([data]);

    /// <summary>
    /// Get attributes of the list (tests struct with list at the end)
    /// </summary>
    [Rpc(0xc09)]
    public Task<ListLastAttr> ListLastAttrAsync(List<short> data)
        => InvokeRpcAsync<ListLastAttr>([data]);

    /// <summary>
    /// Get attributes of two lists merged. (tests struct with multiple lists)
    /// </summary>
    [Rpc(0xc0a)]
    public Task<TwoListAttr> TwoListAttrAsync(List<short> dataA, List<short> dataB)
        => InvokeRpcAsync<TwoListAttr>([dataA, dataB]);

    /// <summary>
    /// Convert seconds from epoch to date.
    /// </summary>
    [Rpc(0xc0b)]
    public Task<MockDate> EpochToDateAsync(int epoch)
        => InvokeRpcAsync<MockDate>([epoch]);

    /// <summary>
    /// Send emoji, receive emoji.
    /// </summary>
    [Rpc(0xc0c)]
    public Task<string> EmojiAsync(string text)
        => InvokeRpcAsync<string>([text]);

    /// <summary>
    /// Concatenate two lists into one.
    /// </summary>
    [Rpc(0xc0d)]
    public Task<List<uint>> CatListsAsync(List<uint> listA, List<uint> listB)
        => InvokeRpcAsync<List<uint>>([listA, listB]);

    /// <summary>
    /// Get a pseudorandom 64-bit value.
    ///     Uses a very simple and deterministic algorithm which
    ///     you can read about here: https://en.wikipedia.org/wiki/Linear-feedback_shift_register
    /// </summary>
    [Rpc(0xc0e)]
    public Task<MockLfsr> GetRandomNumberAsync(ulong seed, byte iter)
        => InvokeRpcAsync<MockLfsr>([seed, iter]);

    /// <summary>
    /// Send structure in parameter.
    /// </summary>
    [Rpc(0xc0f)]
    public Task StructInParamAsync(ListFirstAttr structure)
        => InvokeRpcAsync([structure]);

    /// <summary>
    /// Notifies a current date.
    /// </summary>
    [Notification(0xe00)]
    public event Action<MockDate> NotifyDate
    {
        add => AddNotificationHandler(value);
        remove => RemoveNotificationHandler(value);
    }

    /// <summary>
    /// Notifies a arbitrary string message.
    /// </summary>
    [Notification(0xe01)]
    public event Action<MockLogMessage> NotifyLog
    {
        add => AddNotificationHandler(value);
        remove => RemoveNotificationHandler(value);
    }

    /// <summary>
    /// Signal that remote is alive.
    /// </summary>
    [Notification(0xe02)]
    public event Action NotifyHeartbeat
    {
        add => AddNotificationHandler(value);
        remove => RemoveNotificationHandler(value);
    }

    /// <summary>
    /// Notifies a value and its bitwise complement.
    /// </summary>
    [Notification(0xe03)]
    public event Action<ulong, ulong> NotifyBitwiseComplement
    {
        add => AddNotificationHandler(value);
        remove => RemoveNotificationHandler(value);
    }
}