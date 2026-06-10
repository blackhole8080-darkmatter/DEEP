# DEEP Windows Client (C# .NET 8)

The native Windows integration layer for DEEP v2. Runs alongside the Python core
and provides deep OS control: system tray presence, hardware monitoring, app
management, toast notifications, and a persistent WebSocket backchannel.

## Prerequisites

- .NET 8 SDK: https://dotnet.microsoft.com/download
- Visual Studio 2022 or VS Code with the C# extension
- Windows 10/11

## Project Structure

```
windows_client/
  DeepClient.sln
  config.json
  DeepClient/
    DeepClient.csproj
    Program.cs
    Core/
      WebSocketClient.cs    — connects to Python core
      EventBus.cs            — local C# pub/sub
      ConfigManager.cs       — reads config.json
    Models/
      DeepEvent.cs          — event dataclass
      SystemStats.cs         — hardware snapshot
      ProcessInfo.cs         — running process info
      AppInfo.cs             — visible window info
    OS/
      SystemMonitor.cs       — CPU/GPU/RAM/disk/network via WMI
      AppController.cs       — launch/focus/kill apps via native APIs
      NotificationManager.cs — Windows toast notifications
      StartupManager.cs      — Windows startup registry
      ClipboardMonitor.cs    — clipboard watcher
    UI/
      TrayIcon.cs            — system tray icon
      TrayMenu.cs            — right-click tray menu
```

## Build

```powershell
cd windows_client
dotnet build
```

## Run (Development)

```powershell
dotnet run --project DeepClient
```

## Build Release EXE

```powershell
dotnet publish -c Release -r win-x64 --self-contained true
# Output:
#   DeepClient/bin/Release/net8.0-windows/win-x64/publish/DeepClient.exe
```

## Configuration

Edit `config.json` before running:

| Key | Default | Description |
|---|---|---|
| `deep_ws_url` | `ws://localhost:7768/ws/deep` | WebSocket to Python core |
| `deep_hud_url` | `http://localhost:7768` | Three.js HUD |
| `stats_interval_ms` | 2000 | Hardware push frequency |
| `reconnect_interval_ms` | 5000 | WS reconnect delay |
| `app_paths` | `{...}` | Map of app names → exe paths |
| `device_id` | `""` | Auto-falls back to `MachineName` |

### Tailscale Remote Access

When connecting to DEEP on the Pi over Tailscale:

```json
{
  "deep_ws_url": "ws://100.x.x.x:7768/ws/deep",
  "deep_hud_url": "http://100.x.x.x:7768"
}
```

Replace `100.x.x.x` with the Pi's Tailscale IP.

## Capabilities

- **System Tray** — lives in the Windows tray; left-click opens HUD, right-click shows full menu
- **Hardware Monitor** — pushes CPU/GPU/RAM/disk/network stats to Python core every 2s
- **App Controller** — launch, focus, and kill apps via WebSocket commands from DEEP
- **Toast Notifications** — breakthroughs, threats, unknown devices, evil twins
- **Startup Manager** — toggle "Start with Windows" from the tray menu
- **Clipboard Integration** — sends clipboard text to DEEP for context-aware assistance

## Architecture

```
┌─────────────────────────────────────────────┐
│            Python DEEP Core                │
│  (FastAPI + WebSocket /ws/deep)            │
└──────────────┬──────────────────────────────┘
               │ WebSocket (JSON events)
┌──────────────▼──────────────────────────────┐
│          C# DeepClient.exe                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ TrayIcon │  │ AppCtrl  │  │  Notify   │  │
│  │  System  │  │   OS     │  │  Manager  │  │
│  │ Monitor  │  │          │  │           │  │
│  └──────────┘  └──────────┘  └───────────┘  │
└─────────────────────────────────────────────┘
```

## Troubleshooting

- **Notifications not showing**: Ensure "Focus assist" is off and app notifications
  are enabled for DEEP in Windows Settings.
- **WMI queries fail**: Some WMI classes (e.g., GPU) require specific drivers.
  The monitor falls back to 0 silently.
- **Tray icon missing**: The app needs `STAThread`. Already set in `Program.cs`.
