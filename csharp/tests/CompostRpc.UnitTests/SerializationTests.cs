namespace CompostRpc.UnitTests;

public class SerializationTests
{
    [InlineData(4)]
    [InlineData(127)]
    [Theory]
    public void BufferAllocationTest(int words)
    {
        byte[] buffer = Serialization.InitBuffer(BufferUnit.FromWords(words));
        Assert.True(buffer.Length == (words + 1) * 4);
    }

    [Fact]
    public void BufferAllocationOverLimitTest()
    {
        Serialization.InitBuffer(BufferUnit.FromWords(255));
        Assert.ThrowsAny<ArgumentOutOfRangeException>(() => Serialization.InitBuffer(BufferUnit.FromWords(256)));
    }

    public static TheoryData<object, int, int, byte[]> PackedPrimitiveTestData => new()
    {
        {-1, 0, 4, [0xF0,0,0,0]},
        {-8, 0, 4, [0x80,0,0,0]},
        {0xFU, 6, 4, [0x03,0xC0,0,0]},
        {0xFU, 1, 4, [0x78,0,0,0]},
        {0xFU, 0, 4, [0xF0,0,0,0]},
        {0xFU, 4, 4, [0x0F,0,0,0]},
        {0b101U, 6, 4, [1,64,0,0]},
        {0x3FFCU, 4, 16, [0x03,0xFF,0xC0,0x00]},
        {int.MinValue, 0, 32, [128,0,0,0]}
    };

    [MemberData(nameof(PackedPrimitiveTestData))]
    [Theory]
    public void PackedPrimitiveSerializationTest(object val, int bitOffset, int bitSize, byte[] expected)
    {
        byte[] bytes = [0, 0, 0, 0];
        BufferUnit offset = new(bitOffset);
        Serialization.SerializePackedPrimitive(val, bytes, ref offset, new BufferUnit(bitSize));
        Assert.Equal(expected, bytes);
    }

    [MemberData(nameof(PackedPrimitiveTestData))]
    [Theory]
    public void PackedPrimitiveDeserializationTest(object expected, int bitOffset, int bitSize, byte[] buffer)
    {
        BufferUnit offset = new(bitOffset);
        object value = Serialization.DeserializePackedPrimitive(expected.GetType(), buffer, ref offset, new BufferUnit(bitSize));
        Assert.Equal(expected, value);
    }

    [InlineData(22U, 6, 4)]
    [InlineData(-17, 6, 4)]
    [InlineData(-500000, 12, 8)]
    [Theory]
    public void PackedPrimitiveOverflowSerializationTest(object val, int bitOffset, int bitSize)
    {
        byte[] bytes = [0, 0, 0, 0];
        BufferUnit offset = new(bitOffset);
        Assert.ThrowsAny<OverflowException>(() => Serialization.SerializePackedPrimitive(val, bytes, ref offset, new BufferUnit(bitSize)));
    }

    enum Status
    {
        Ok,
        Warn,
        Fail = 255 //To test overflow
    };
    [Fact]
    public void PackedEnumSerializationTest()
    {
        byte[] buffer = [0, 0, 0, 0];
        BufferUnit offset = BufferUnit.Zero;
        BufferUnit size = new(4);
        Serialization.SerializePackedPrimitive(Status.Warn, buffer, ref offset, size);
        offset = BufferUnit.Zero;
        object value = Serialization.DeserializePackedPrimitive(typeof(Status), buffer, ref offset, size);
        Assert.Equal(Status.Warn, value);
        offset = BufferUnit.Zero;
        Assert.ThrowsAny<OverflowException>(() => Serialization.SerializePackedPrimitive(Status.Fail, buffer, ref offset, size));
    }
}