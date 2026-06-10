using DeepClient.Core;
using DeepClient.OS;

namespace DeepClient.UI;

/// <summary>
/// Right-click context menu for the system tray icon.
/// </summary>
public class TrayMenu : ContextMenuStrip
{
    public TrayMenu(
        ConfigManager config,
        StartupManager startup,
        DeepWebSocketClient wsClient)
    {
        // ── Header ──
        var lblStatus = new ToolStripMenuItem("DEEP v2") { Enabled = false };
        var lblMood = new ToolStripMenuItem("Mood: —") { Enabled = false };
        Items.Add(lblStatus);
        Items.Add(lblMood);
        Items.Add(new ToolStripSeparator());

        // ── Actions ──
        var openHud = new ToolStripMenuItem("Open HUD");
        openHud.Click += (_, _) =>
            Process.Start(new ProcessStartInfo(config.GetHudUrl()) { UseShellExecute = true });
        Items.Add(openHud);

        var briefing = new ToolStripMenuItem("Morning Briefing");
        briefing.Click += async (_, _) =>
            await wsClient.SendEvent("request_briefing",
                new Dictionary<string, object> { ["device_id"] = config.DeviceId });
        Items.Add(briefing);
        Items.Add(new ToolStripSeparator());

        // ── Network ──
        var networkMenu = new ToolStripMenuItem("Network");
        networkMenu.DropDownItems.Add(CreateLink("Device List", $"{config.GetHudUrl()}/network/devices"));
        networkMenu.DropDownItems.Add(CreateLink("Threats", $"{config.GetHudUrl()}/network/threats"));
        networkMenu.DropDownItems.Add(CreateLink("Proximity", $"{config.GetHudUrl()}/network/proximity"));
        Items.Add(networkMenu);
        Items.Add(new ToolStripSeparator());

        // ── System ──
        var restartCore = new ToolStripMenuItem("Restart DEEP Core");
        restartCore.Click += async (_, _) =>
            await wsClient.SendEvent("request_restart", new Dictionary<string, object>());
        Items.Add(restartCore);

        var startupEnabled = startup.IsEnabled();
        var toggleStartup = new ToolStripMenuItem(startupEnabled ? "Stop Start with Windows" : "Start with Windows");
        toggleStartup.Click += (_, _) =>
        {
            if (startup.IsEnabled())
                startup.Disable();
            else
                startup.Enable();
            toggleStartup.Text = startup.IsEnabled() ? "Stop Start with Windows" : "Start with Windows";
        };
        Items.Add(toggleStartup);
        Items.Add(new ToolStripSeparator());

        // ── Exit ──
        var exit = new ToolStripMenuItem("Exit");
        exit.Click += async (_, _) =>
        {
            await wsClient.DisconnectAsync();
            Application.Exit();
        };
        Items.Add(exit);
    }

    private static ToolStripMenuItem CreateLink(string text, string url)
    {
        var item = new ToolStripMenuItem(text);
        item.Click += (_, _) => Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
        return item;
    }
}
