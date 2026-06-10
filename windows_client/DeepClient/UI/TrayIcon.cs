using DeepClient.Core;
using DeepClient.OS;

namespace DeepClient.UI;

/// <summary>
/// DEEP system tray presence on Windows.
/// </summary>
public class DeepTrayIcon : IDisposable
{
    private readonly NotifyIcon _trayIcon;
    private readonly DeepWebSocketClient _wsClient;
    private readonly SystemMonitor _sysMonitor;
    private readonly ConfigManager _config;
    private readonly System.Windows.Forms.Timer _tooltipTimer;
    private DateTime _threatIconUntil = DateTime.MinValue;

    public DeepTrayIcon(DeepWebSocketClient wsClient, SystemMonitor sysMonitor, ConfigManager config)
    {
        _wsClient = wsClient;
        _sysMonitor = sysMonitor;
        _config = config;

        _trayIcon = new NotifyIcon
        {
            Text = "DEEP v2 — Initialising...",
            Visible = true,
            Icon = SystemIcons.Application // fallback; replace with embedded resources
        };

        // Wire events
        _wsClient.OnConnected += () => UpdateIcon("idle");
        _wsClient.OnDisconnected += () => UpdateIcon("disconnected");
        _wsClient.OnEventReceived += OnDeepEvent;

        _trayIcon.Click += (_, e) =>
        {
            if (e is MouseEventArgs me && me.Button == MouseButtons.Left)
            {
                OpenHud();
            }
        };

        // Tooltip updater
        _tooltipTimer = new System.Windows.Forms.Timer { Interval = 5000 };
        _tooltipTimer.Tick += (_, _) => UpdateTooltip();
        _tooltipTimer.Start();
    }

    public void SetContextMenu(ContextMenuStrip menu)
    {
        _trayIcon.ContextMenuStrip = menu;
    }

    private void OnDeepEvent(DeepEvent evt)
    {
        switch (evt.Type)
        {
            case "wake_word_detected":
                UpdateIcon("active");
                break;
            case "tts_complete":
                UpdateIcon("idle");
                break;
            case "threat_detected":
                UpdateIcon("threat");
                _threatIconUntil = DateTime.Now.AddSeconds(5);
                break;
            case "tailscale_connected":
                _trayIcon.BalloonTipTitle = "DEEP Remote Access";
                _trayIcon.BalloonTipText = "VPN connected. DEEP is reachable from anywhere.";
                _trayIcon.ShowBalloonTip(3000);
                break;
        }
    }

    private void UpdateIcon(string state)
    {
        // In production: swap _trayIcon.Icon to embedded .ico resources
        // deep_idle.ico, deep_active.ico, deep_alert.ico, deep_threat.ico
        // For now we rely on text/tooltip differentiation.
    }

    private void UpdateTooltip()
    {
        if (DateTime.Now > _threatIconUntil && _threatIconUntil != DateTime.MinValue)
        {
            UpdateIcon("idle");
        }

        var stats = _sysMonitor.GetStats();
        var status = _wsClient.IsConnected ? "Online" : "Offline";
        _trayIcon.Text = $"DEEP — {status} | CPU {stats.CpuPercent:F0}% | RAM {stats.RamUsedMB:F0}/{stats.RamTotalMB:F0} MB";
    }

    private void OpenHud()
    {
        var url = _config.GetHudUrl();
        Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
    }

    public void Dispose()
    {
        _tooltipTimer?.Stop();
        _tooltipTimer?.Dispose();
        _trayIcon?.Dispose();
    }
}
