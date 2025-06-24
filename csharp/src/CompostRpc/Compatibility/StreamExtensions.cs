namespace CompostRpc.Compatibility;

public static class StreamExtensions
{
    public static ValueTask ReadExactlyAsync(this Stream stream, byte[] buffer, int offset, int count, System.Threading.CancellationToken cancellationToken = default)
    {
        return new ValueTask(Task.Run(async () =>
        {
            int read;
            while (count > 0)
            {
#pragma warning disable CA1835 // Do not suggest 'Memory'-based overloads for 'ReadAsync' and 'WriteAsync'
                read = await stream.ReadAsync(buffer, offset, count, cancellationToken).ConfigureAwait(false);
#pragma warning restore CA1835
                if (read == 0)
                    throw new EndOfStreamException();
                offset += read;
                count -= read;
            }
        }, cancellationToken));
    }

    public static void Write(this Stream stream, ReadOnlySpan<byte> buffer)
    {
        stream.Write(buffer.ToArray(), 0, buffer.Length);
    }
}