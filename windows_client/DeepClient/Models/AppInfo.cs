namespace DeepClient.Models;

/// <summary>
/// Information about a visible application window.
/// </summary>
public class AppInfo
{
    public string Name { get; set; } = string.Empty;
    public int PID { get; set; }
    public string Title { get; set; } = string.Empty;
    public bool IsResponding { get; set; }
}
