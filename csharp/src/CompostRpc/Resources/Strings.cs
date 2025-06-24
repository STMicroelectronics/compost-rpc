namespace CompostRpc.Resources
{
    internal static class Strings
    {
        internal static string IsNull(string param) => $"{param} is null.";
        internal static string NotInstantiated(string name) => $"{name} could not be instantiated.";
        internal static string TransportNotConnected() =>
            "Transport is not connected. Before you use the Protocol functions, open the Transport with Connect().";
        internal static string CallerNameIsNull() =>
            "Caller name is null. This indicates incorrect usage, please refer to documentation.";
        internal static string RpcCallerNameInvalid(string method) =>
            $"{method} method was not annotated with RPC attribute or it does not exist.";
        internal static string RpcReturnTypeNotInstantiated() =>
            "Return type of RPC function could not be instantiated.";
        internal static string RpcReturnTypeInvalid(string method) =>
            $"{method} method annotated with RPC attribute must return value as IAsyncResult.";
        internal static string NotificationTypeInvalid() =>
            "Notification argument types could not be resolved.";
        internal static string NotificationTypeNotInstantiated() =>
            "Notification argument could not be instantiated.";
        internal static string NotificationHandlerInvalid() =>
            "Registered notification handler is not valid.";
        internal static string FetchedWrongNotificationHandler() =>
            "Notification cache contained unexpected type of notification listener. This indicates incorrect usage, please refer to documentation.";
        internal static string MessageSizeLimitReached() =>
            "Message size in bytes exceeds maximum allowed by the Compost protocol.";
        internal static string TypeNotSupported(string type) => $"Type {type} is not supported";
        internal static string TypeNotList() => "Type is not equivalent to Compost list";
        internal static string DelegateWithoutInvoke() => "Delegate does not define an Invoke method.";
        internal static string QueriedSizeOnDynamicType() => "Can't get byte size because the type is dynamic";
        internal static string TransactionWrapAround() =>
            "Transaction buffer wrap-around detected. Too many hanging transactions.";
        internal static string UnexpectedTransactionId(int txn) =>
            $"Received message with transaction {txn}, but no pending transaction with the same ID could be found.";
        internal static string UnsupportedRequest(int rpcId) =>
            $"Request {rpcId:X} is not supported by the Compost target.";
        internal static string RpcError(int rpcId) =>
            $"Compost target replied with error header to request {rpcId:X}.";
        internal static string IncorrectResponseRpcId(int requestId, int responseId) =>
            $"Compost target replied to request {requestId:X} with incorrect response {responseId:X}. This indicates protocol mismatch.";
        internal static string PackedOverflow(long min, long max) =>
            $"Value is outside of requested packed range of {min} to {max}.";
    }
}
