using System.IO.Ports;

namespace CompostRpc.Transports;

/// <summary>
/// SerialTransport options
/// </summary>
public class SerialTransportOptions
{
    public TimeSpan Timeout { get; init; } = TimeSpan.Zero;
    public int BaudRate { get; init; } = 115200;
    public Parity Parity { get; init; } = Parity.None;
    public int DataBits { get; init; } = 8;
    public StopBits StopBits { get; init; } = StopBits.One;
    public Handshake Handshake { get; init; } = Handshake.None;
    public bool DtrEnable { get; init; } = false;
    public bool RtsEnable { get; init; } = false;
}

/// <summary>
/// Implementation of Transport for serial interface
/// </summary>
public class SerialTransport : ITransport, IDisposable
{
    private readonly SerialPort _serialPort;

    public SerialTransport(string portName, SerialTransportOptions options)
    {
        _serialPort = new SerialPort
        {
            PortName = portName,
            BaudRate = options.BaudRate,
            Parity = options.Parity,
            DataBits = options.DataBits,
            StopBits = options.StopBits,
            Handshake = options.Handshake,
            DtrEnable = options.DtrEnable,
            RtsEnable = options.RtsEnable,
            // Disable the read/write timeouts
            ReadTimeout = SerialPort.InfiniteTimeout,
            WriteTimeout = SerialPort.InfiniteTimeout
        };
        _serialPort.Open();
    }

    public SerialTransport(string portName, int baudRate, int timeoutMs = 0)
        : this(portName, new SerialTransportOptions { BaudRate = baudRate, Timeout = TimeSpan.FromMilliseconds(timeoutMs) })
    {

    }

    public void WriteMessage(Message message)
    {
        message.Write(_serialPort.BaseStream);
    }

    public Task<Message> ReadMessageAsync(CancellationToken cancellationToken = default)
    {
        return Message.FromStreamAsync(_serialPort.BaseStream, cancellationToken);
    }

    public void Dispose()
    {
        _serialPort.Dispose();
        GC.SuppressFinalize(this);
    }
}