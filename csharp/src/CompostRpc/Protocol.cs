using System.Runtime.CompilerServices;
using System.Reflection;
using CompostRpc.Transports;
using CompostRpc.Resources;
using System.Linq.Expressions;

namespace CompostRpc;

/// <summary>
/// Base class for user Compost implementations.
/// </summary>
public abstract partial class Protocol : IAsyncDisposable
{
    private readonly Dictionary<string, NotificationInfo> _notificationInfoCache;
    private readonly Dictionary<string, RpcInfo> _rpcInfoCache;

    /// <summary>
    /// Transport assigned during object initialization.
    /// </summary>
    public Session BaseSession { get; }

    /// <summary>
    /// Constructor called by a derived class.
    /// </summary>
    /// <param name="device">Transport used for RPC calls and receiving notifications.</param>
    public Protocol(ITransport transport)
    {
        BaseSession = new Session(transport);
        _notificationInfoCache = [];
        _rpcInfoCache = [];

        Type type = this.GetType();
        MethodInfo[] methods = type.GetMethods(BindingFlags.Public | BindingFlags.Instance);
        foreach (MethodInfo method in methods)
        {
            RpcAttribute? rpcAttr = method.GetCustomAttribute<RpcAttribute>();
            if (rpcAttr is null)
                continue;
            MessageShape requestShape = new([.. method.GetParameters().Select(x => x.ParameterType)]);
            if (method.ReturnType.GetInterface(nameof(IAsyncResult)) is null)
                throw new ProtocolException(Strings.RpcReturnTypeInvalid(method.Name));
            Type? returnType = method.ReturnType.GenericTypeArguments.FirstOrDefault();
            MessageShape responseShape = returnType is null ? new() : new(returnType);
            _rpcInfoCache[method.Name] = new RpcInfo(rpcAttr.RpcId, requestShape, responseShape);
        }
        EventInfo[] events = type.GetEvents(BindingFlags.Public | BindingFlags.Instance);
        Type notificationInfoGenericType = typeof(NotificationInfo);
        foreach (EventInfo ev in events)
        {
            NotificationAttribute? notifAttr = ev.GetCustomAttribute<NotificationAttribute>();
            if (notifAttr is null)
                continue;
            IEnumerable<Type> eventParameters = ev.EventHandlerType?.GetMethod("Invoke")?.GetParameters().Select(x => x.ParameterType)
             ?? throw new InvalidOperationException(Strings.NotificationTypeInvalid());
            var eventHandlerInvoker = CreateEventHandlerInvoker(ev);
            NotificationInfo notifInfo = new(notifAttr.RpcId, new MessageShape(eventParameters), eventHandlerInvoker);
            _notificationInfoCache[ev.Name] = notifInfo;
            BaseSession.AddNotificationHandler(notifAttr.RpcId, notifInfo.ReceivedHandler);
        }
    }

    /// <summary>
    /// Based on the definition of event, create a compiled Invoker, that will cast
    /// any delegate to the type of event handler and invoke it as if it was delegate
    /// of the same type.
    /// </summary>
    /// <remarks>
    /// This resulting invoker can only be used when it is certain that delegate is 
    /// of the same type as event handler from which it was created!
    /// </remarks>
    /// <returns>Invoker delegate</returns>
    private static Action<Delegate, object[]> CreateEventHandlerInvoker(EventInfo eventInfo)
    {
        var delegateParameter = Expression.Parameter(typeof(Delegate), "delegate");
        var argsParameter = Expression.Parameter(typeof(object[]), "args");

        Type eventHandlerType = eventInfo.EventHandlerType
            ?? throw new ArgumentException(Strings.IsNull(nameof(eventInfo.EventHandlerType)), nameof(eventInfo));
        var castedDelegate = Expression.Convert(delegateParameter, eventHandlerType);

        var invokeMethod = eventHandlerType.GetMethod("Invoke")
            ?? throw new ArgumentException(Strings.DelegateWithoutInvoke(), nameof(eventInfo));
        var invokeParams = invokeMethod.GetParameters();
        var invokeCallParameters = new Expression[invokeParams.Length];
        for (int i = 0; i < invokeParams.Length; i++)
        {
            var arg = Expression.ArrayIndex(argsParameter, Expression.Constant(i));
            invokeCallParameters[i] = Expression.Convert(arg, invokeParams[i].ParameterType);
        }

        var invokeCall = Expression.Call(castedDelegate, invokeMethod, invokeCallParameters);
        return Expression.Lambda<Action<Delegate, object[]>>(invokeCall, delegateParameter, argsParameter).Compile();
    }

    /// <summary>
    /// Retrieves information about the RPC function based on the caller name and invokes it
    /// on Compost device with selected arguments, expecting void.
    /// </summary>
    /// <param name="rpcName">Name of the RPC function</param>
    /// <param name="args">Arguments of a RPC function</param>
    /// <exception cref="TransportException"></exception>
    /// <exception cref="ProtocolException"></exception>
    /// <exception cref="TimeoutException"></exception>
    /// <returns><see cref="Task"/> with no value.</returns>
    protected async Task InvokeRpcAsync(object[]? args = null, [CallerMemberName] string? rpcName = null)
    {
        await InvokeRpcAsync<object>(args, rpcName);
    }


    /// <summary>
    /// Retrieves information about the RPC function based on the caller name and invokes it
    /// on Compost device with selected arguments, expecting specified return type.
    /// </summary>
    /// <param name="rpcName">Name of the RPC function</param>
    /// <param name="args">Arguments of a RPC function</param>
    /// <typeparam name="TResult">Return value type</typeparam>
    /// <exception cref="TransportException"></exception>
    /// <exception cref="ProtocolException"></exception>
    /// <exception cref="TimeoutException"></exception>
    /// <returns><see cref="Task"/> with RPC call result.</returns>
    protected async Task<TResult> InvokeRpcAsync<TResult>(object[]? args = null, [CallerMemberName] string? rpcName = null)
    {
        if (rpcName is null)
            throw new ProtocolException(Strings.CallerNameIsNull());
        if (!_rpcInfoCache.TryGetValue(rpcName, out RpcInfo? rpc))
            throw new ProtocolException(Strings.RpcCallerNameInvalid(rpcName));

        Message resp = await BaseSession.InvokeRawRpcAsync(rpc.Identifier, args ?? [], rpc.RequestShape);
        if (resp.Header.IsErrorResponse)
            throw new ProtocolException(Strings.RpcError(rpc.Identifier));
        else if (resp.Header.IsUnsupportedResponse)
            throw new ProtocolException(Strings.UnsupportedRequest(rpc.Identifier));
        else if (resp.Header.RpcId != rpc.Identifier)
            throw new ProtocolException(Strings.IncorrectResponseRpcId(rpc.Identifier, resp.Header.RpcId));

        TResult? ret;
        BufferUnit offset = Serialization.HeaderSize;
        //TODO Response message size check with the T type
        if (typeof(TResult) != typeof(object))
        {
            ret = Serialization.Deserialize<TResult>(resp.Buffer, ref offset);
            return ret;
        }
        else
            return (TResult)new object();
    }

    private LinkedList<Delegate> FetchNotificationEventHandlers(string? notifName = null)
    {
        if (notifName is null)
            throw new ProtocolException(Strings.CallerNameIsNull());
        return _notificationInfoCache[notifName].EventHandlers;
    }

    protected void AddNotificationHandler<T>(T handler, [CallerMemberName] string? notifName = null) where T : Delegate
    {
        LinkedList<Delegate> handlers = FetchNotificationEventHandlers(notifName);
        if (handlers.Contains(handler))
            return;
        Delegate prev = handlers.LastOrDefault() ?? handler;
        if (prev.GetType() == handler.GetType())
            handlers.AddLast(handler);
        else
            throw new ProtocolException(Strings.NotificationHandlerInvalid());
    }

    protected void RemoveNotificationHandler<T>(T handler, [CallerMemberName] string? notifName = null) where T : Delegate
    {
        LinkedList<Delegate> handlers = FetchNotificationEventHandlers(notifName);
        handlers.Remove(handler);
    }

    public async ValueTask DisposeAsync()
    {
        foreach (var notificationInfo in _notificationInfoCache.Values)
            BaseSession.RemoveNotificationHandler(notificationInfo.Id, notificationInfo.ReceivedHandler);
        await BaseSession.DisposeAsync();
        _rpcInfoCache.Clear();
        _notificationInfoCache.Clear();
        GC.SuppressFinalize(this);
    }
}