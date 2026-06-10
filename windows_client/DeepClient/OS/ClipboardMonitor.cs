using System.Windows.Forms;
using DeepClient.Core;

namespace DeepClient.OS;

/// <summary>
/// Monitors the Windows clipboard for content that DEEP may want to
/// act on (e.g., copied URLs, text, etc.).
/// </summary>
public class ClipboardMonitor : Form
{
    private readonly DeepWebSocketClient _wsClient;
    private string _lastText = string.Empty;
    private readonly System.Windows.Forms.Timer _timer;

    public ClipboardMonitor(DeepWebSocketClient wsClient)
    {
        _wsClient = wsClient;
        WindowState = FormWindowState.Minimized;
        ShowInTaskbar = false;
        Opacity = 0;
        Size = new System.Drawing.Size(1, 1);

        _timer = new System.Windows.Forms.Timer { Interval = 1000 };
        _timer.Tick += async (_, _) => await CheckClipboardAsync();
    }

    public void StartMonitoring()
    {
        _timer.Start();
    }

    public void StopMonitoring()
    {
        _timer.Stop();
    }

    private async Task CheckClipboardAsync()
    {
        try
        {
            if (Clipboard.ContainsText())
            {
                var text = Clipboard.GetText();
                if (!string.IsNullOrEmpty(text) && text != _lastText && text.Length < 5000)
                {
                    _lastText = text;
                    await _wsClient.SendEvent("clipboard_text", new Dictionary<string, object>
                    {
                        ["text"] = text[..Math.Min(text.Length, 500)],
                        ["device_id"] = Environment.MachineName,
                        ["timestamp"] = DateTime.UtcNow.ToString("O")
                    });
                }
            }
        }
        catch { /* clipboard may be locked by another app */ }
    }
}
