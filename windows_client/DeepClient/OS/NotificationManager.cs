using Microsoft.Toolkit.Uwp.Notifications;
using DeepClient.Core;

namespace DeepClient.OS;

/// <summary>
/// Windows 10/11 toast notifications from DEEP.
/// </summary>
public class NotificationManager
{
    private readonly DeepWebSocketClient _wsClient;

    public NotificationManager(DeepWebSocketClient wsClient)
    {
        _wsClient = wsClient;
    }

    public void ShowAlert(string title, string body, string type = "info")
    {
        var (header, icon) = type.ToLower() switch
        {
            "warning" => ("DEEP Warning", "⚠️"),
            "threat"  => ("DEEP THREAT", "🔴"),
            "success" => ("DEEP Success", "✅"),
            "deep"   => ("DEEP", "🧠"),
            _         => ("DEEP Info", "ℹ️"),
        };

        new ToastContentBuilder()
            .AddArgument("action", "viewAlert")
            .AddText($"{icon} {header}")
            .AddText(title)
            .AddText(body)
            .Show();
    }

    public void ShowBreakthrough(string domain, string summary)
    {
        new ToastContentBuilder()
            .AddArgument("action", "openHud")
            .AddText("🧠 DEEP Breakthrough Detected")
            .AddText(domain)
            .AddText(summary[..Math.Min(summary.Length, 120)])
            .AddButton(new ToastButton()
                .SetContent("Open DEEP")
                .AddArgument("action", "openHud"))
            .Show();
    }

    public void SubscribeToWebSocketEvents()
    {
        _wsClient.OnEventReceived += evt =>
        {
            switch (evt.Type)
            {
                case "breakthrough_detected":
                    ShowBreakthrough(
                        evt.Payload.GetValueOrDefault("domain", "Research").ToString()!,
                        evt.Payload.GetValueOrDefault("summary", "").ToString()!);
                    break;
                case "threat_detected":
                    ShowAlert(
                        $"Threat: {evt.Payload.GetValueOrDefault("threat_type", "unknown")}",
                        $"From {evt.Payload.GetValueOrDefault("source_ip", "unknown")}",
                        "threat");
                    break;
                case "unknown_device_detected":
                    ShowAlert(
                        "Unknown device on network",
                        $"IP: {evt.Payload.GetValueOrDefault("ip", "?")}",
                        "warning");
                    break;
                case "evil_twin_detected":
                    ShowAlert(
                        "Evil twin AP detected!",
                        $"SSID: {evt.Payload.GetValueOrDefault("ssid", "?")}",
                        "threat");
                    break;
            }
        };
    }
}
