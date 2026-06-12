#if NETSTANDARD2_0 || NETSTANDARD2_1

namespace CompostRpc.Compatibility;

public static class QueueExtensions
{
    public static bool TryDequeue<T>(this Queue<T> queue, out T result)
    {
        if (queue.Count > 0)
        {
            result = queue.Dequeue();
            return true;
        }

        result = default!;
        return false;
    }
}

#endif
