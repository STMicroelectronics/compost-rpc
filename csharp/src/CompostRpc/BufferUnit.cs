
namespace CompostRpc;

public readonly record struct BufferUnit
{
    private const int _byteBits = 8;
    private const int _wordBits = 32;
    /// <summary>
    /// Represents zero unit.
    /// </summary>
    public static readonly BufferUnit Zero = new(0);
    /// <summary>
    /// Represents a single byte unit.
    /// </summary>
    public static readonly BufferUnit Byte = new(_byteBits);
    /// <summary>
    /// Represents a single word unit.
    /// </summary>
    public static readonly BufferUnit Word = new(_wordBits);

    /// <summary>
    /// Number of bits.
    /// </summary>
    public int Bits { get; }
    /// <summary>
    /// Number of bytes, rounded up.
    /// </summary>
    public int Bytes { get; }
    /// <summary>
    /// Number of words, rounded up.
    /// </summary>
    public int Words { get; }

    /// <summary>
    /// True if the number of bits is aligned to bytes.
    /// </summary>
    public bool IsByteAligned { get => Bits % Byte.Bits == 0; }
    /// <summary>
    /// True if the number of bits is aligned to words.
    /// </summary>
    public bool IsWordAligned { get => Words % Word.Bits == 0; }

    public BufferUnit(int bits)
    {
        Bits = bits;
        Bytes = (bits + _byteBits - 1) / _byteBits;
        Words = (bits + _wordBits - 1) / _wordBits;
    }

    /// <summary>
    /// Create instance from number of bytes.
    /// </summary>
    /// <param name="bytes">Number of bytes.</param>
    /// <returns></returns>
    public static BufferUnit FromBytes(int bytes)
        => new(bytes * Byte.Bits);

    /// <summary>
    /// Create instance from number of words.
    /// </summary>
    /// <param name="bytes">Number of words.</param>
    /// <returns></returns>
    public static BufferUnit FromWords(int words)
        => new(words * Word.Bits);

    /// <summary>
    /// Creates instance with bit value aligned to bytes.
    /// </summary>
    public BufferUnit AlignToBytes()
    {
        return FromBytes(Bytes);
    }

    /// <summary>
    /// Creates instance with bit value aligned to words.
    /// </summary>
    public BufferUnit AlignToWords()
    {
        return FromWords(Words);
    }

    public static BufferUnit operator +(BufferUnit a, BufferUnit b)
        => new(a.Bits + b.Bits);

    public static BufferUnit operator -(BufferUnit a, BufferUnit b)
        => new(a.Bits - b.Bits);

    public static BufferUnit operator *(BufferUnit a, int b)
        => new(a.Bits * b);

    public static BufferUnit operator *(int b, BufferUnit a)
        => new(a.Bits * b);

    public static bool operator >(BufferUnit a, BufferUnit b)
        => a.Bits > b.Bits;

    public static bool operator <(BufferUnit a, BufferUnit b)
        => a.Bits < b.Bits;
}