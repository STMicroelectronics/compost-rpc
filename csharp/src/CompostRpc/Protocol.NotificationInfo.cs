
using System.Linq.Expressions;
using CompostRpc.Resources;

namespace CompostRpc;

public abstract partial class Protocol
{
    /// <summary>
    /// Notification wrapper
    /// </summary>
    protected class NotificationInfo
    {
        public ushort Id { get; }
        public MessageShape Shape { get; }
        public LinkedList<Delegate> EventHandlers { get; set; } = [];

        public Action<Delegate, object[]> EventHandlerInvoker { get; }
        internal NotificationInfo(ushort id, MessageShape shape, Action<Delegate, object[]> invoker)
        {
            Id = id;
            Shape = shape;
            EventHandlerInvoker = invoker;
        }

        public void ReceivedHandler(Message message)
        {
            //TODO validity checks
            BufferUnit offset = Serialization.HeaderSize;
            object[] args = [.. Shape.Select(x => Serialization.Deserialize(x, message.Buffer, ref offset))];
            foreach (Delegate d in EventHandlers)
                EventHandlerInvoker(d, args);
        }
    }
}