using DeepClient.Core;
using DeepClient.OS;
using DeepClient.UI;

namespace DeepClient;

public static class Program
{
    [STAThread]
    public static async Task Main(string[] args)
    {
        Application.SetHighDpiMode(HighDpiMode.SystemAware);
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        var config = new ConfigManager();
        var wsClient = new DeepWebSocketClient(config);
        var sysMonitor = new SystemMonitor(wsClient, config);
        var appController = new AppController(wsClient);
        var notifications = new NotificationManager(wsClient);
        var startup = new StartupManager(wsClient);
        var clipboard = new ClipboardMonitor(wsClient);

        // Wire WebSocket events to OS actions
        wsClient.OnEventReceived += evt =>
        {
            switch (evt.Type)
            {
                case "app_launch":
                    if (evt.Payload.TryGetValue("name", out var appName))
                        appController.LaunchApp(appName?.ToString() ?? "", config);
                    break;
                case "app_kill":
                    if (evt.Payload.TryGetValue("name", out var killName))
                        appController.KillApp(killName?.ToString() ?? "");
                    break;
                case "app_focus":
                    if (evt.Payload.TryGetValue("name", out var focusName))
                        appController.FocusApp(focusName?.ToString() ?? "");
                    break;
                case "show_notification":
                    notifications.ShowAlert(
                        evt.Payload.GetValueOrDefault("title", "DEEP").ToString()!,
                        evt.Payload.GetValueOrDefault("body", "").ToString()!,
                        evt.Payload.GetValueOrDefault("type", "info").ToString()!);
                    break;
                case "clipboard_get":
                    _ = wsClient.SendEvent("clipboard_text",
                        new Dictionary<string, object>
                        {
                            ["device_id"] = config.DeviceId,
                            ["text"] = Clipboard.ContainsText() ? Clipboard.GetText()[..Math.Min(Clipboard.GetText().Length, 500)] : ""
                        });
                    break;
            }
        };

        notifications.SubscribeToWebSocketEvents();

        var tray = new DeepTrayIcon(wsClient, sysMonitor, config);
        var menu = new TrayMenu(config, startup, wsClient);
        tray.SetContextMenu(menu);

        // Start background services
        _ = wsClient.ConnectAsync();
        sysMonitor.StartMonitoring();
        clipboard.StartMonitoring();

        // Keep alive
        Application.Run();

        // Shutdown
        clipboard.StopMonitoring();
        sysMonitor.StopMonitoring();
        await wsClient.DisconnectAsync();
        tray.Dispose();
    }
}
