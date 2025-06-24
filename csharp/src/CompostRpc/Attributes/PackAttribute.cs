
namespace CompostRpc;

[System.AttributeUsage(System.AttributeTargets.Property)]
public class PackAttribute : System.Attribute
{
    public BufferUnit Size { get; init; }

    public PackAttribute(BufferUnit size)
    {
        Size = size;
    }

    public PackAttribute(int bitSize)
    {
        Size = new BufferUnit(bitSize);
    }
}