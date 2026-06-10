namespace DeepClient.Models;

/// <summary>
/// Snapshot of Windows system hardware state.
/// Sent periodically to the Python core via WebSocket.
/// </summary>
public class SystemStats
{
    public float CpuPercent { get; set; }
    public float RamUsedMB { get; set; }
    public float RamTotalMB { get; set; }
    public float GpuPercent { get; set; }
    public float GpuVramMB { get; set; }
    public float DiskReadMBs { get; set; }
    public float DiskWriteMBs { get; set; }
    public float NetworkSentMBs { get; set; }
    public float NetworkRecvMBs { get; set; }
    public TimeSpan Uptime { get; set; }
    public int ActiveProcessCount { get; set; }
    public List<ProcessInfo> TopProcesses { get; set; } = new();
}
