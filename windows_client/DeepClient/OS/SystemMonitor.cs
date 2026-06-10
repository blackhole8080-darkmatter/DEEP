using System.Diagnostics;
using System.Management;
using DeepClient.Core;
using DeepClient.Models;

namespace DeepClient.OS;

/// <summary>
/// Hardware monitoring via Windows Performance Counters and WMI.
/// </summary>
public class SystemMonitor
{
    private readonly DeepWebSocketClient _wsClient;
    private readonly ConfigManager _config;
    private readonly PerformanceCounter _cpuCounter;
    private readonly PerformanceCounter _diskReadCounter;
    private readonly PerformanceCounter _diskWriteCounter;
    private CancellationTokenSource _cts = new();
    private Task? _monitorTask;

    public SystemMonitor(DeepWebSocketClient wsClient, ConfigManager config)
    {
        _wsClient = wsClient;
        _config = config;
        _cpuCounter = new PerformanceCounter("Processor", "% Processor Time", "_Total");
        _diskReadCounter = new PerformanceCounter("PhysicalDisk", "Disk Read Bytes/sec", "_Total");
        _diskWriteCounter = new PerformanceCounter("PhysicalDisk", "Disk Write Bytes/sec", "_Total");
        // Prime the counters
        _cpuCounter.NextValue();
        _diskReadCounter.NextValue();
        _diskWriteCounter.NextValue();
    }

    public void StartMonitoring()
    {
        _cts = new CancellationTokenSource();
        _monitorTask = Task.Run(MonitorLoopAsync);
    }

    public void StopMonitoring()
    {
        _cts.Cancel();
        _monitorTask?.Wait(TimeSpan.FromSeconds(2));
    }

    private async Task MonitorLoopAsync()
    {
        var interval = _config.GetInt("stats_interval_ms", 2000);
        while (!_cts.Token.IsCancellationRequested)
        {
            try
            {
                var stats = GetStats();
                await _wsClient.SendEvent("system_stats", new Dictionary<string, object>
                {
                    ["device_id"] = _config.DeviceId,
                    ["cpu_percent"] = Math.Round(stats.CpuPercent, 1),
                    ["ram_used_mb"] = Math.Round(stats.RamUsedMB, 0),
                    ["ram_total_mb"] = Math.Round(stats.RamTotalMB, 0),
                    ["gpu_percent"] = Math.Round(stats.GpuPercent, 1),
                    ["gpu_vram_mb"] = Math.Round(stats.GpuVramMB, 0),
                    ["disk_read_mbs"] = Math.Round(stats.DiskReadMBs, 2),
                    ["disk_write_mbs"] = Math.Round(stats.DiskWriteMBs, 2),
                    ["network_sent_mbs"] = Math.Round(stats.NetworkSentMBs, 2),
                    ["network_recv_mbs"] = Math.Round(stats.NetworkRecvMBs, 2),
                    ["uptime_seconds"] = (int)stats.Uptime.TotalSeconds,
                    ["active_process_count"] = stats.ActiveProcessCount,
                    ["top_processes"] = stats.TopProcesses.Select(p => new
                    {
                        p.Name,
                        p.PID,
                        cpu_pct = Math.Round(p.CpuPercent, 1),
                        ram_mb = Math.Round(p.RamMB, 0)
                    }).ToList()
                });
            }
            catch { /* stats are best-effort */ }

            try { await Task.Delay(interval, _cts.Token); }
            catch (TaskCanceledException) { break; }
        }
    }

    public SystemStats GetStats()
    {
        var stats = new SystemStats();
        try { stats.CpuPercent = _cpuCounter.NextValue(); } catch { }
        stats.RamTotalMB = GetRamTotal();
        stats.RamUsedMB = stats.RamTotalMB - GetRamAvailable();
        stats.GpuPercent = GetGpuUsage();
        stats.GpuVramMB = GetVramUsed();
        stats.DiskReadMBs = _diskReadCounter.NextValue() / (1024f * 1024f);
        stats.DiskWriteMBs = _diskWriteCounter.NextValue() / (1024f * 1024f);
        stats.NetworkSentMBs = GetNetworkSent();
        stats.NetworkRecvMBs = GetNetworkRecv();
        stats.Uptime = GetSystemUptime();
        stats.ActiveProcessCount = Process.GetProcesses().Length;
        stats.TopProcesses = GetTopProcessesByCpu(5);
        return stats;
    }

    private static float GetRamTotal()
    {
        try
        {
            using var mc = new ManagementClass("Win32_ComputerSystem");
            foreach (ManagementObject mo in mc.GetInstances())
                return Convert.ToSingle(mo["TotalPhysicalMemory"]) / (1024f * 1024f);
        }
        catch { }
        return 0;
    }

    private static float GetRamAvailable()
    {
        try
        {
            using var mc = new ManagementClass("Win32_OperatingSystem");
            foreach (ManagementObject mo in mc.GetInstances())
                return Convert.ToSingle(mo["FreePhysicalMemory"]) / 1024f;
        }
        catch { }
        return 0;
    }

    private static float GetGpuUsage()
    {
        try
        {
            using var mc = new ManagementClass("Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine");
            var total = 0f;
            var count = 0;
            foreach (ManagementObject mo in mc.GetInstances())
            {
                var val = Convert.ToSingle(mo["UtilizationPercentage"]);
                total += val;
                count++;
            }
            return count > 0 ? total / count : 0;
        }
        catch { }
        return 0;
    }

    private static float GetVramUsed()
    {
        try
        {
            using var mc = new ManagementClass("Win32_VideoController");
            foreach (ManagementObject mo in mc.GetInstances())
            {
                var total = Convert.ToSingle(mo["AdapterRAM"] ?? 0) / (1024f * 1024f);
                return total; // Simplified; dedicated VRAM query varies by driver
            }
        }
        catch { }
        return 0;
    }

    private static float GetNetworkSent()
    {
        try
        {
            var counters = PerformanceCounterCategory.GetCategories()
                .FirstOrDefault(c => c.CategoryName == "Network Interface");
            if (counters == null) return 0;
            var instances = counters.GetInstanceNames();
            if (instances.Length == 0) return 0;
            using var pc = new PerformanceCounter("Network Interface", "Bytes Sent/sec", instances[0]);
            return pc.NextValue() / (1024f * 1024f);
        }
        catch { }
        return 0;
    }

    private static float GetNetworkRecv()
    {
        try
        {
            var counters = PerformanceCounterCategory.GetCategories()
                .FirstOrDefault(c => c.CategoryName == "Network Interface");
            if (counters == null) return 0;
            var instances = counters.GetInstanceNames();
            if (instances.Length == 0) return 0;
            using var pc = new PerformanceCounter("Network Interface", "Bytes Received/sec", instances[0]);
            return pc.NextValue() / (1024f * 1024f);
        }
        catch { }
        return 0;
    }

    private static TimeSpan GetSystemUptime()
    {
        try
        {
            using var mc = new ManagementClass("Win32_OperatingSystem");
            foreach (ManagementObject mo in mc.GetInstances())
            {
                var lastBoot = ManagementDateTimeConverter.ToDateTime(mo["LastBootUpTime"].ToString()!);
                return DateTime.Now - lastBoot;
            }
        }
        catch { }
        return TimeSpan.Zero;
    }

    private static List<ProcessInfo> GetTopProcessesByCpu(int n)
    {
        try
        {
            return Process.GetProcesses()
                .Where(p => !p.HasExited)
                .Select(p => new ProcessInfo
                {
                    Name = p.ProcessName,
                    PID = p.Id,
                    RamMB = p.WorkingSet64 / (1024f * 1024f),
                })
                .OrderByDescending(p => p.RamMB)
                .Take(n)
                .ToList();
        }
        catch { }
        return new List<ProcessInfo>();
    }
}
