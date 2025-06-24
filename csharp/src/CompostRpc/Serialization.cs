using System.Collections;
using System.Collections.Concurrent;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using CompostRpc.Resources;

namespace CompostRpc;

/// <summary>
/// Static class used primarily to serialize/deserialize objects into their byte 
/// representation in Compost protocol. It also contains other functions and
/// constants necessary for these tasks.
/// </summary>
public static class Serialization
{
    private readonly record struct CompostStructProperty(PropertyInfo ReflectionInfo, BufferUnit? PackedSize);
    private static readonly ConcurrentDictionary<Type, BufferUnit> _typeSizeCache = new();
    private static readonly ConcurrentDictionary<Type, bool> _typeDynamicityCache = new();
    private static readonly ConcurrentDictionary<Type, CompostStructProperty[]> _compostStructPropertyCache = new();
    private static readonly Dictionary<Type, Func<byte[], object>> _primitiveTypeDeser
        = new()
    {
        {typeof(bool), (buf) => BitConverter.ToBoolean(buf, 0)},
        {typeof(short), (buf) => BitConverter.ToInt16(buf, 0)},
        {typeof(ushort), (buf) => BitConverter.ToUInt16(buf, 0)},
        {typeof(int), (buf) => BitConverter.ToInt32(buf, 0)},
        {typeof(uint), (buf) => BitConverter.ToUInt32(buf, 0)},
        {typeof(long), (buf) => BitConverter.ToInt64(buf, 0)},
        {typeof(ulong), (buf) => BitConverter.ToUInt64(buf, 0)},
        {typeof(double), (buf) => BitConverter.ToDouble(buf, 0)},
        {typeof(float), (buf) => BitConverter.ToSingle(buf, 0)},
        {typeof(char), (buf) => (char)buf[0]},
        {typeof(byte), (buf) => buf[0]},
    };

    /// <summary>
    /// Header size according to Compost protocol
    /// </summary>
    public static readonly BufferUnit HeaderSize = BufferUnit.FromBytes(4);
    /// <summary>
    /// Size of the length information in Compost slice
    /// </summary>
    public static readonly BufferUnit ListLengthSize = BufferUnit.FromBytes(2);
    /// <summary>
    /// Size of the length information in Compost slice
    /// </summary>
    public static readonly BufferUnit MessageBodyLimit = BufferUnit.FromWords(255);

    /// <summary>
    /// Check if the type is compatible with Compost struct.
    /// </summary>
    /// <param name="type">Type to check.</param>
    /// <returns>True if the Type is equivalent to Compost struct.</returns>
    public static bool IsTypeCompostStruct(Type type)
        => type.IsClass && !type.IsArray && type.BaseType == typeof(object);

    /// <summary>
    /// Check if the type is compatible with Compost list.
    /// </summary>
    /// <param name="type">Type to check.</param>
    /// <returns>True if the Type is equivalent to Compost list.</returns>
    public static bool IsTypeCompostList(Type type)
        => (type.GetInterface(nameof(IList)) != null && !type.IsArray) || type == typeof(string);

    /// <summary>
    /// Check if the type is signed integer type.
    /// </summary>
    /// <param name="type">Type to check.</param>
    /// <returns>True if the Type is signed integerss.</returns>
    public static bool IsTypeSignedInteger(Type type)
        => type == typeof(int) || type == typeof(short) || type == typeof(sbyte) || type == typeof(long);

    /// <summary>
    /// Get the type of element in the Compost list.
    /// </summary>
    /// <param name="type">Compost list type.</param>
    /// <exception cref="ProtocolException">Thrown if the Type of argument is not equivalent to Compost list.</exception>
    /// <returns>Type of the Compost list element.</returns>
    public static Type GetCompostListElementType(Type type)
    {
        if (type == typeof(string))
            return typeof(char);
        else if (type.GetInterface(nameof(IList)) != null && !type.IsArray)
            return type.GetGenericArguments()[0];
        else
            throw new SerializationException(Strings.TypeNotList());
    }

    /// <summary>
    /// Check if the length of byte representation of a Type is constant and data independent.
    /// </summary>
    /// <param name="type">Type to check.</param>
    /// <returns>True if the size of Type is static.</returns>
    public static bool IsTypeStatic(Type type)
    {
        if (IsTypeCompostList(type))
            return false;
        else if (type.IsClass)
        {
            if (_typeDynamicityCache.TryGetValue(type, out bool cached))
                return cached;
            var properties = GetCompostStructProperties(type);
            bool isClassStatic = true;
            foreach (var property in properties)
            {
                var isPropertyStatic = IsTypeStatic(property.ReflectionInfo.PropertyType);
                if (isPropertyStatic == false)
                {
                    isClassStatic = false;
                    break;
                }
            }
            _typeDynamicityCache.TryAdd(type, isClassStatic);
            return isClassStatic;
        }
        return true;
    }

    /// <summary>
    /// Get size of representation in a compost protocol for Type
    /// </summary>
    /// <param name="arg">Type</param>
    /// <exception cref="ProtocolException">Thrown when a dynamic type is passed as argument.</exception>
    /// <returns>Size of the type in the message buffer.</returns>
    public static BufferUnit GetTypeSize(Type type)
    {
        if (_typeSizeCache.TryGetValue(type, out BufferUnit cachedSize))
            return cachedSize;
        if (!IsTypeStatic(type))
            throw new SerializationException(Strings.QueriedSizeOnDynamicType());
        if (type.IsPrimitive)
        {
            int primitiveByteSize = type == typeof(bool) || type == typeof(char) ? 1 : Marshal.SizeOf(type);
            BufferUnit primitiveSize = BufferUnit.FromBytes(primitiveByteSize);
            _typeSizeCache.TryAdd(type, primitiveSize);
            return primitiveSize;
        }
        else if (type.IsEnum)
        {
            BufferUnit enumSize = BufferUnit.FromBytes(Marshal.SizeOf(Enum.GetUnderlyingType(type)));
            _typeSizeCache.TryAdd(type, enumSize);
            return enumSize;
        }
        else if (IsTypeCompostStruct(type))
        {
            BufferUnit classSize = new(0);
            var properties = GetCompostStructProperties(type);
            foreach (var property in properties)
                if (property.PackedSize is not null)
                    classSize += property.PackedSize.Value;
                else
                    classSize += GetTypeSize(property.ReflectionInfo.PropertyType);
            _typeSizeCache.TryAdd(type, classSize);
            return classSize;
        }
        else
            throw new NotSupportedException(Strings.TypeNotSupported(type.Name));
    }

    /// <summary>
    /// Get size of representation in a compost protocol for object instance
    /// </summary>
    /// <param name="arg">Any object instance</param>
    /// <returns>Size of the object instance in the message buffer.</returns>
    public static BufferUnit GetObjectSize(object? arg)
    {
        //? If applicable, isStatic is only changed to false in this method
        Type argType = arg?.GetType() ?? throw new ArgumentNullException(nameof(arg));
        if (_typeSizeCache.TryGetValue(argType, out BufferUnit cachedSize))
            return cachedSize;
        if (argType == typeof(string))
        {
            int len = (arg as string)?.Length ?? 0;
            return BufferUnit.FromBytes(len + ListLengthSize.Bytes);
        }
        else if (IsTypeCompostList(argType))
        {
            int len = (arg as IList)?.Count ?? 0;
            if (len > 0)
                return GetObjectSize((arg as IList)?[0]) * len + ListLengthSize;
            else
                return ListLengthSize;
        }
        else if (IsTypeCompostStruct(argType) && !IsTypeStatic(argType))
        {
            BufferUnit classSize = new(0);
            foreach (var property in GetCompostStructProperties(argType))
                if (property.PackedSize is not null)
                    classSize += property.PackedSize.Value;
                else
                    classSize += GetObjectSize(property.ReflectionInfo.GetValue(arg, null));
            return classSize;
        }
        else
            return GetTypeSize(argType);
    }

    /// <summary>
    /// Get size of representation in a compost protocol for collection of object instances
    /// </summary>
    /// <param name="args">Collection of objects</param>
    /// <returns>Size of the collection in the message buffer.</returns>
    public static BufferUnit GetCollectionSize(IEnumerable<object> args)
    {
        BufferUnit outSize = BufferUnit.Zero;
        foreach (var arg in args)
        {
            outSize += GetObjectSize(arg);
        }
        return outSize;
    }

    private static CompostStructProperty[] GetCompostStructProperties(Type argType)
    {
        if (!_compostStructPropertyCache.TryGetValue(argType, out CompostStructProperty[]? properties))
        {
            var propertyInfos = argType.GetProperties();
            List<CompostStructProperty> propertiesList = [];
            foreach (var info in propertyInfos)
            {
                BufferUnit? packedSize = info.GetCustomAttribute<PackAttribute>()?.Size;
                if (packedSize is not null)
                {
                    //? Test conversion to see if the attribute is on supported type;
                    long _ = IntegerToBits(Activator.CreateInstance(info.PropertyType)!, packedSize);
                }
                propertiesList.Add(new CompostStructProperty(info, packedSize));
            }
            properties = [.. propertiesList];
            _compostStructPropertyCache[argType] = properties;
            return properties;
        }
        else
            return properties;
    }

    /// <summary>
    /// Copies bytes from one array to another.
    /// </summary>
    /// <param name="src">Source array</param>
    /// <param name="srcStart">Index where the source data starts</param>
    /// <param name="dest">Destination array</param>
    /// <param name="destStart">Index where the first byte will be copied</param>
    /// <param name="length">Number of bytes to copy</param>
    /// <returns>Index that follows after copied data.</returns>
    private static int CopyBytes(ReadOnlySpan<byte> src, int srcStart, Span<byte> dest, int destStart, int length)
    {
        if (srcStart + length > src.Length || destStart + length > dest.Length)
            throw new ArgumentOutOfRangeException(nameof(length));

        int srcIdx = srcStart;
        int destIdx = destStart + length - 1;
        for (int i = 0; i < length; i++)
            dest[destIdx--] = src[srcIdx++];
        return destStart + length;
    }

    /// <summary>
    /// Copy single byte.
    /// </summary>
    /// <param name="src">Source array</param>
    /// <param name="dest">Destination array</param>
    /// <param name="destStart">Index where the byte will be copied</param>
    /// <returns>Index that follows after copied data.</returns>
    private static int CopyBytes(byte src, byte[] dest, int destStart)
    {
        dest[destStart] = src;
        return destStart + 1;
    }

    /// <summary>
    /// Serializes primitive type to byte representation.
    /// </summary>
    /// <param name="arg">Object that will be serialized</param>
    /// <param name="buffer">Output buffer</param>
    /// <param name="offset">Offset where the first byte will be copied.
    /// It will be updated with the value of next offset.
    /// </param>
    public static void SerializePrimitive(object arg, byte[] buffer, ref BufferUnit offset)
    {
        int next_offset = arg switch
        {
            bool argt => CopyBytes(BitConverter.GetBytes(argt), 0, buffer, offset.Bytes, 1),
            short argt => CopyBytes(BitConverter.GetBytes(argt), 0, buffer, offset.Bytes, sizeof(short)),
            ushort argt => CopyBytes(BitConverter.GetBytes(argt), 0, buffer, offset.Bytes, sizeof(ushort)),
            uint argt => CopyBytes(BitConverter.GetBytes(argt), 0, buffer, offset.Bytes, sizeof(uint)),
            int argt => CopyBytes(BitConverter.GetBytes(argt), 0, buffer, offset.Bytes, sizeof(int)),
            ulong argt => CopyBytes(BitConverter.GetBytes(argt), 0, buffer, offset.Bytes, sizeof(ulong)),
            long argt => CopyBytes(BitConverter.GetBytes(argt), 0, buffer, offset.Bytes, sizeof(long)),
            float argt => CopyBytes(BitConverter.GetBytes(argt), 0, buffer, offset.Bytes, sizeof(float)),
            double argt => CopyBytes(BitConverter.GetBytes(argt), 0, buffer, offset.Bytes, sizeof(double)),
            char argt => CopyBytes([(byte)argt], 0, buffer, offset.Bytes, 1),
            byte argt => CopyBytes(argt, buffer, offset.Bytes),
            _ => throw new NotSupportedException(Strings.TypeNotSupported(arg.GetType().Name))
        };
        offset = BufferUnit.FromBytes(next_offset);
    }

    /// <summary>
    /// Used to get equivalent bit representation of supported integer types with arbitrary size constraint
    /// </summary>
    /// <param name="value">Primitive value that can be represented as integer. Conversion depends on whether the type is signed or unsigned.</param>
    /// <param name="packedSize">Maximum size in buffer that the value should occupy.</param>
    /// <returns></returns>
    /// <exception cref="NotSupportedException">The type is either not an integer or it is not supported by the CompostRpc.</exception>
    /// <exception cref="OverflowException">Value falls outside of the specified size request.</exception>
    private static long IntegerToBits(object value, BufferUnit? packedSize = null)
    {
        Type argType = value.GetType();
        int sizeBits = packedSize?.Bits ?? GetTypeSize(argType).Bits;
        long rep;
        bool isSignedType = IsTypeSignedInteger(argType);
        unchecked
        {
            rep = value switch
            {
                bool x => x == true ? 1L : 0L,
                byte x => x,
                sbyte x => x,
                ushort x => x,
                short x => x,
                uint x => x,
                int x => x,
                Enum x => (long)Convert.ChangeType(x, typeof(long)),
                _ => throw new NotSupportedException(Strings.TypeNotSupported(argType.Name)),
            };
        }
        long mask = (0x1L << sizeBits) - 1;
        bool isNegativeValue = isSignedType && ((rep & (1L << (sizeBits - 1))) != 0);
        long expanded = isNegativeValue ? rep | ~mask : rep & mask;

        if (expanded != rep)
        {
            int rangeMin = isSignedType ? -(int)Math.Pow(2, sizeBits - 1) : 0;
            int rangeMax = isSignedType ? (int)Math.Pow(2, sizeBits - 1) - 1 : (int)Math.Pow(2, sizeBits) - 1;
            throw new OverflowException(Strings.PackedOverflow(rangeMin, rangeMax));
        }
        return expanded;
    }

    /// <summary>
    /// Serializes integer numeric type to specific bit offset in the buffer. The value may be packed to lower bit-size.
    /// </summary>
    /// <param name="arg">Integer value.</param>
    /// <param name="buffer">Target buffer.</param>
    /// <param name="offset">Offset in the buffer.</param>
    /// <param name="packedSize">Size of the value in the buffer</param>
    public static void SerializePackedPrimitive(object arg, byte[] buffer, ref BufferUnit offset, BufferUnit packedSize)
    {
        long val = IntegerToBits(arg, packedSize);
        int byteIndex = offset.Bits / BufferUnit.Byte.Bits;
        int bitsRemaining = packedSize.Bits;
        int bitPosition = offset.Bits;
        while (bitsRemaining > 0)
        {
            int bitsToFill = BufferUnit.Byte.Bits - (bitPosition % BufferUnit.Byte.Bits);
            int bitsToPlace = bitsRemaining <= bitsToFill ? bitsRemaining : bitsToFill;
            int shift = bitsToFill - bitsToPlace;
            long mask = (0x1L << bitsToPlace) - 1;
            long bitValue = (val >> bitsRemaining - bitsToPlace) & mask;
            buffer[byteIndex] &= (byte)~(mask << shift);
            buffer[byteIndex] |= (byte)(bitValue << shift);

            bitPosition += bitsToPlace;
            byteIndex++;
            bitsRemaining -= bitsToPlace;
        }
        offset += packedSize;
    }

    /// <summary>
    /// Deserializes arbitrary number of bits in a biuffer into specified integer numeric type.
    /// </summary>
    /// <param name="argType">Type of the return value.</param>
    /// <param name="buffer">Target buffer.</param>
    /// <param name="offset">Offset in the buffer.</param>
    /// <param name="packedSize">Size of the value in the buffer</param>
    /// <returns></returns>
    /// <exception cref="NotSupportedException"></exception>
    public static object DeserializePackedPrimitive(Type argType, ReadOnlySpan<byte> buffer, ref BufferUnit offset, BufferUnit packedSize)
    {
        long val = 0;
        int byteIndex = offset.Bits / BufferUnit.Byte.Bits;
        int bitsRemaining = packedSize.Bits;
        int bitPosition = offset.Bits;
        long mask;
        while (bitsRemaining > 0)
        {
            int bitsToFill = BufferUnit.Byte.Bits - (bitPosition % BufferUnit.Byte.Bits);
            int bitsToPlace = bitsRemaining <= bitsToFill ? bitsRemaining : bitsToFill;
            int shift = bitsToFill - bitsToPlace;
            mask = (0x1L << bitsToPlace) - 1;
            long bitValue = (buffer[byteIndex] >> shift) & mask;

            bitPosition += bitsToPlace;
            byteIndex++;
            bitsRemaining -= bitsToPlace;

            val |= bitValue << bitsRemaining;
        }
        offset += packedSize;
        Type t = argType.IsEnum ? Enum.GetUnderlyingType(argType) : argType;
        if (IsTypeSignedInteger(t))
        {
            mask = (0x1L << packedSize.Bits) - 1;
            val = (val & (0x1L << (packedSize.Bits - 1))) != 0 ? val | ~mask : val;
        }
        byte[] bytes = BitConverter.GetBytes(val);
        if (t != typeof(float) && _primitiveTypeDeser.TryGetValue(t, out var deser))
            return argType.IsEnum ? Enum.ToObject(argType, deser(bytes)) : deser(bytes);
        else
            throw new NotSupportedException(Strings.TypeNotSupported(t.Name));
    }

    /// <summary>
    /// Serializes object to byte representation.
    /// </summary>
    /// <param name="arg">Object that will be serialized</param>
    /// <param name="buffer">Output buffer</param>
    /// <param name="offset">Offset where the first byte will be copied. 
    /// It will be updated with the value of next offset.
    /// </param>
    public static void Serialize(object arg, byte[] buffer, ref BufferUnit offset)
    {
        Type argType = arg?.GetType() ?? throw new ArgumentNullException(nameof(arg));
        if (argType.IsEnum)
        {
            SerializePrimitive(Convert.ChangeType(arg, Enum.GetUnderlyingType(argType)), buffer, ref offset);
        }
        else if (argType == typeof(string))
        {
            ushort len = (ushort)((arg as string)?.Length ?? 0);
            Serialize(len, buffer, ref offset);
            char[] chars = (arg as string)?.ToCharArray() ?? throw new ArgumentNullException(nameof(arg));
            for (int i = 0; i < len; i++)
                Serialize(chars[i], buffer, ref offset);
        }
        else if (IsTypeCompostList(argType))
        {
            ushort len = (ushort)((arg as IList)?.Count ?? 0);
            ushort elemSize = len > 0 ? (ushort)GetObjectSize((arg as IList)?[0]).Bytes : (ushort)0;
            Serialize((ushort)(len * elemSize), buffer, ref offset);
            for (int i = 0; i < len; i++)
                Serialize((arg as IList)?[i] ?? throw new ArgumentNullException(nameof(arg)), buffer, ref offset);
        }
        else if (IsTypeCompostStruct(argType))
        {
            var properties = GetCompostStructProperties(argType);
            foreach (var property in properties)
            {
                object propertyValue = property.ReflectionInfo.GetValue(arg, null) ?? throw new NullReferenceException(nameof(property));
                if (property.PackedSize is null)
                    Serialize(propertyValue, buffer, ref offset);
                else
                    SerializePackedPrimitive(propertyValue, buffer, ref offset, property.PackedSize.Value);
            }
        }
        else
            SerializePrimitive(arg, buffer, ref offset);
    }

    /// <inheritdoc cref="Serialize"/>
    /// <param name="offset">Offset where the first byte will be copied</param>
    /// <returns>Offset in buffer that follows after serialized data.</returns>
    public static BufferUnit Serialize(object arg, byte[] buffer, BufferUnit offset)
    {
        BufferUnit next_offset = offset;
        Serialize(arg, buffer, ref next_offset);
        return next_offset;
    }

    /// <summary>
    /// Deserializes into a primitive type from byte representation.
    /// </summary>
    /// <param name="argType">Type of deserialized object</param>
    /// <param name="buffer">Input buffer</param>
    /// <param name="offset">Offset where the byte representation of object starts.</param>
    /// <returns>Deserialized object.</returns>
    public static object DeserializePrimitive(Type argType, ReadOnlySpan<byte> buffer, ref BufferUnit offset)
    {
        BufferUnit size = GetTypeSize(argType);
        byte[] tmp = new byte[size.Bytes];
        CopyBytes(buffer, offset.Bytes, tmp, 0, size.Bytes);

        object ret;
        if (_primitiveTypeDeser.TryGetValue(argType, out var func))
            ret = func(tmp);
        else
            throw new NotSupportedException(Strings.TypeNotSupported(argType.Name));
        offset += size;
        return ret;
    }

    /// <summary>
    /// Deserializes into an object from byte representation.
    /// </summary>
    /// <param name="buffer">Input buffer</param>
    /// <param name="offset">Offset where the byte representation of destination object starts.</param>
    /// <returns>Deserialized object.</returns>
    public static T Deserialize<T>(ReadOnlySpan<byte> buffer, ref BufferUnit offset)
    {
        return (T)Deserialize(typeof(T), buffer, ref offset);
    }

    /// <inheritdoc cref="Deserialize"/>
    /// <param name="argType">Type of object to deserialize</param>
    public static object Deserialize(Type argType, ReadOnlySpan<byte> buffer, ref BufferUnit offset)
    {
        object arg;
        if (argType.IsEnum)
        {
            arg = DeserializePrimitive(Enum.GetUnderlyingType(argType), buffer, ref offset);
        }
        else if (argType == typeof(string))
        {
            ushort len = Deserialize<ushort>(buffer, ref offset);
            StringBuilder sb = new(len);
            for (int i = 0; i < len; i++)
            {
                char tmp = Deserialize<char>(buffer, ref offset);
                sb.Append(tmp);
            }
            arg = sb.ToString();
        }
        else if (IsTypeCompostList(argType))
        {
            ushort len = Deserialize<ushort>(buffer, ref offset);
            arg = Activator.CreateInstance(argType, args: [(int)len])!;
            Type itemType = GetCompostListElementType(argType);
            len /= (ushort)GetTypeSize(itemType).Bytes;
            for (int i = 0; i < len; i++)
            {
                var tmp = Deserialize(itemType, buffer, ref offset);
                (arg as IList)?.Add(tmp);
            }
        }
        else if (IsTypeCompostStruct(argType))
        {
            var properties = GetCompostStructProperties(argType);
#if NETSTANDARD2_0
            arg = System.Runtime.Serialization.FormatterServices.GetUninitializedObject(argType);
#else
            arg = System.Runtime.CompilerServices.RuntimeHelpers.GetUninitializedObject(argType);
#endif
            foreach (var property in properties)
            {
                object? tmp;
                if (property.PackedSize is null)
                    tmp = Deserialize(property.ReflectionInfo.PropertyType, buffer, ref offset);
                else
                    tmp = DeserializePackedPrimitive(property.ReflectionInfo.PropertyType, buffer, ref offset, property.PackedSize.Value);
                property.ReflectionInfo.SetValue(arg, tmp);
            }
        }
        else
        {
            arg = DeserializePrimitive(argType, buffer, ref offset);
        }
        return arg;
    }

    /// <summary>
    /// Creates a new buffer that will fit the data of specified size.
    /// </summary>
    /// <param name="bodySize">Size of the message body (without header)</param>
    /// <exception cref="ArgumentOutOfRangeException">Thrown if the size is bigger than allowed limit.</exception>
    /// <returns></returns>
    public static byte[] InitBuffer(BufferUnit bodySize)
    {
        if (bodySize > MessageBodyLimit)
            throw new ArgumentOutOfRangeException(nameof(bodySize), Strings.MessageSizeLimitReached());
        return new byte[HeaderSize.Bytes + bodySize.Words * 4];
    }
}