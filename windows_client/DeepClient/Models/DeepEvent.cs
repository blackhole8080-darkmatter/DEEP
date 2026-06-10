namespace DeepClient.Models;

/// <summary>
/// Unified event format used across the C# client and Python core.
/// Mirrors the Python EventBus payload structure.
/// </summary>
public class DeepEvent
{
    public string Type { get; set; } = string.Empty;
    public Dictionary<string, object> Payload { get; set; } = new();
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;

    public static DeepEvent FromJson(string json)
    {
        return Newtonsoft.Json.JsonConvert.DeserializeObject<DeepEvent>(json)
            ?? new DeepEvent();
    }

    public string ToJson()
    {
        return Newtonsoft.Json.JsonConvert.SerializeObject(this);
    }
}
