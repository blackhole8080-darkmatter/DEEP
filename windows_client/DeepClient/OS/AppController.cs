using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using DeepClient.Core;
using DeepClient.Models;

namespace DeepClient.OS;

/// <summary>
/// Launch, focus, and kill applications using native Windows APIs.
/// Goes beyond what Python subprocess can do — includes window management.
/// </summary>
public class AppController
{
    private readonly DeepWebSocketClient _wsClient;

    public AppController(DeepWebSocketClient wsClient)
    {
        _wsClient = wsClient;
    }

    // P/Invoke declarations
    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();

    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    private const int SW_RESTORE = 9;

    public bool LaunchApp(string appName, ConfigManager config)
    {
        var path = config.GetAppPath(appName);
        if (string.IsNullOrEmpty(path)) return false;

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = path,
                UseShellExecute = true
            };
            var proc = Process.Start(psi);
            if (proc != null)
            {
                _ = _wsClient.SendEvent("app_launched", new Dictionary<string, object>
                {
                    ["name"] = appName,
                    ["pid"] = proc.Id,
                    ["device_id"] = config.DeviceId
                });
                return true;
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"LaunchApp error: {ex.Message}");
        }
        return false;
    }

    public bool KillApp(string appName)
    {
        try
        {
            var procs = Process.GetProcessesByName(appName);
            foreach (var p in procs)
            {
                p.Kill();
            }
            _ = _wsClient.SendEvent("app_killed", new Dictionary<string, object>
            {
                ["name"] = appName
            });
            return true;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"KillApp error: {ex.Message}");
            return false;
        }
    }

    public bool FocusApp(string appName)
    {
        try
        {
            var procs = Process.GetProcessesByName(appName);
            if (procs.Length == 0) return false;
            var targetPid = (uint)procs[0].Id;

            IntPtr found = IntPtr.Zero;
            EnumWindows((hWnd, _) =>
            {
                if (!IsWindowVisible(hWnd)) return true;
                GetWindowThreadProcessId(hWnd, out var pid);
                if (pid == targetPid)
                {
                    found = hWnd;
                    return false;
                }
                return true;
            }, IntPtr.Zero);

            if (found != IntPtr.Zero)
            {
                ShowWindow(found, SW_RESTORE);
                SetForegroundWindow(found);
                _ = _wsClient.SendEvent("app_focused", new Dictionary<string, object>
                {
                    ["name"] = appName
                });
                return true;
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"FocusApp error: {ex.Message}");
        }
        return false;
    }

    public string GetForegroundApp()
    {
        try
        {
            var hwnd = GetForegroundWindow();
            var sb = new StringBuilder(256);
            GetWindowText(hwnd, sb, 256);
            GetWindowThreadProcessId(hwnd, out var pid);
            using var proc = Process.GetProcessById((int)pid);
            return $"{proc.ProcessName} | {sb}";
        }
        catch
        {
            return "unknown";
        }
    }

    public List<AppInfo> GetRunningApps()
    {
        var apps = new List<AppInfo>();
        var seenPids = new HashSet<int>();
        EnumWindows((hWnd, _) =>
        {
            if (!IsWindowVisible(hWnd)) return true;
            var sb = new StringBuilder(256);
            GetWindowText(hWnd, sb, 256);
            if (string.IsNullOrWhiteSpace(sb.ToString())) return true;

            GetWindowThreadProcessId(hWnd, out var pid);
            if (seenPids.Contains((int)pid)) return true;
            seenPids.Add((int)pid);

            try
            {
                using var proc = Process.GetProcessById((int)pid);
                apps.Add(new AppInfo
                {
                    Name = proc.ProcessName,
                    PID = (int)pid,
                    Title = sb.ToString(),
                    IsResponding = proc.Responding
                });
            }
            catch { }
            return true;
        }, IntPtr.Zero);
        return apps;
    }
}
