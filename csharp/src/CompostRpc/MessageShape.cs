using System.Collections;
using System.Runtime.CompilerServices;

namespace CompostRpc;

/// <summary>
/// Wrapper for raw data of a single message.
/// </summary>
public class MessageShape : IEnumerable<Type>
{
    private readonly List<Type> _items;

    public BufferUnit Size { get; init; }

    public bool IsFixedSize { get; init; }

    public MessageShape()
    {
        IsFixedSize = true;
        Size = BufferUnit.Zero;
        _items = [];
    }

    public MessageShape(IEnumerable<Type> items)
        : this([.. items])
    {
    }

    public MessageShape(params Type[] items)
    {
        _items = [.. items];
        IsFixedSize = true;
        Size = BufferUnit.Zero;
        foreach (Type item in items)
        {
            if (!Serialization.IsTypeStatic(item))
            {
                IsFixedSize = false;
                Size = BufferUnit.Zero;
                break;
            }
            else
                Size += Serialization.GetTypeSize(item);
        }
    }

    public static MessageShape FromArguments(params object[] items)
    {
        IEnumerable<Type> objectTypes = items.Select(x => x.GetType());
        return new MessageShape([.. objectTypes]);
    }

    public Type this[int i]
    {
        get { return _items[i]; }
    }

    public IEnumerator<Type> GetEnumerator()
    {
        return _items.GetEnumerator();
    }

    IEnumerator IEnumerable.GetEnumerator()
    {
        return _items.GetEnumerator();
    }
}