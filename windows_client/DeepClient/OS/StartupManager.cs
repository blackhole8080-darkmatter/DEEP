using Microsoft.Win32;
using DeepClient.Core;

namespace DeepClient.OS;

/// <summary>
/// Manages DEEP Windows startup registration.
/// </summary>
public class StartupManager
{
    private const string RunKey =
        @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string AppName = "DEEP";
    private readonly DeepWebSocketClient _wsClient;
    private readonly string _exePath;

    public StartupManager(DeepWebSocketClient wsClient)
    {
        _wsClient = wsClient;
        _exePath = System.Reflection.Assembly.GetExecutingAssembly().Location;
        if (_exePath.EndsWith(".dll"))
        {
            _exePath = _exePath[..^4] + ".exe";
        }
    }

    public bool IsEnabled()
    {
        using var key = Registry.CurrentUser.OpenSubKey(RunKey, false);
        return key?.GetValue(AppName) != null;
    }

    public void Enable()
    {
        using var key = Registry.CurrentUser.OpenSubKey(RunKey, true);
        key?.SetValue(AppName, $"\"{_exePath}\"");
        _ = _wsClient.SendEvent("startup_enabled",
            new Dictionary<string, object> { ["device_id"] = Environment.MachineName });
    }

    public void Disable()
    {
        using var key = Registry.CurrentUser.OpenSubKey(RunKey, true);
        if (key?.GetValue(AppName) != null)
        {
            key.DeleteValue(AppName);
        }
        _ = _wsClient.SendEvent("startup_disabled",
            new Dictionary<string, object> { ["device_id"] = Environment.MachineName });
    }
}
