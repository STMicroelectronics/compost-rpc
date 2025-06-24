
using System.Diagnostics;

namespace CompostRpc.IntegrationTests.Mocks;

public class ProcessTransport : ITransport, IDisposable
{
    readonly Process _proc = new();

    public ProcessTransport(string mockPath)
    {
        _proc.StartInfo.UseShellExecute = false;
        _proc.StartInfo.RedirectStandardInput = true;
        _proc.StartInfo.RedirectStandardOutput = true;
        _proc.StartInfo.RedirectStandardError = true;
        _proc.StartInfo.FileName = mockPath;
        //_proc.StartInfo.Arguments = "Write-Error Test";
        _proc.StartInfo.CreateNoWindow = false;
        _proc.Start();
    }

    public async Task<Message> ReadMessageAsync(CancellationToken cancellationToken = default)
    {
        Message msg = await Message.FromStreamAsync(_proc.StandardOutput.BaseStream, cancellationToken);
        Trace.TraceInformation($"{this.GetType().Name}[{this.GetHashCode()}] reading " + msg.ToString());
        return msg;
    }

    public void WriteMessage(Message msg)
    {
        Trace.TraceInformation($"{this.GetType().Name}[{this.GetHashCode()}] writing " + msg.ToString());
        msg.Write(_proc.StandardInput.BaseStream);
        _proc.StandardInput.Flush();
    }

    public void Dispose()
    {
        _proc.Dispose();
        GC.SuppressFinalize(this);
    }
}