namespace DeepClient.Models;

/// <summary>
/// Information about a single running process.
/// </summary>
public class ProcessInfo
{
    public string Name { get; set; } = string.Empty;
    public int PID { get; set; }
    public float CpuPercent { get; set; }
    public float RamMB { get; set; }
}
