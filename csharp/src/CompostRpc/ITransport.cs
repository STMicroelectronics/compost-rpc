using CompostRpc.Resources;
using CompostRpc.Transports;

namespace CompostRpc;

/// <summary>
/// Interface for the transport layer used by a Session instance
/// </summary>
public interface ITransport
{
    /// <summary>
    /// Writes message to a device.
    /// </summary>
    /// <param name="msg">Message to write</param>
    public void WriteMessage(Message msg);
    /// <summary>
    /// Read next message from a device into buffer.
    /// </summary>
    /// <param name="cancellationToken">Cancellation token</param>
    /// <returns>Latest message.</returns>
    public Task<Message> ReadMessageAsync(CancellationToken cancellationToken = default);
}