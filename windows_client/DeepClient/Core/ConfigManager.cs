using Newtonsoft.Json.Linq;

namespace DeepClient.Core;

/// <summary>
/// Reads windows_client/config.json and provides typed access.
/// </summary>
public class ConfigManager
{
    private readonly JObject _config;

    public ConfigManager(string path = "config.json")
    {
        var fullPath = Path.Combine(AppContext.BaseDirectory, path);
        if (!File.Exists(fullPath))
            fullPath = Path.Combine(AppContext.BaseDirectory, "..", path);
        var json = File.Exists(fullPath) ? File.ReadAllText(fullPath) : "{}";
        _config = JObject.Parse(json);
    }

    public string Get(string key, string defaultValue = "")
    {
        var token = _config.SelectToken(key);
        return token?.ToString() ?? defaultValue;
    }

    public int GetInt(string key, int defaultValue = 0)
    {
        var token = _config.SelectToken(key);
        return token?.Value<int>() ?? defaultValue;
    }

    public string GetWsUrl()
    {
        var url = Get("deep_ws_url", "ws://localhost:7768/ws/deep");
        return url;
    }

    public string GetHudUrl()
    {
        return Get("deep_hud_url", "http://localhost:7768");
    }

    public string? GetAppPath(string appName)
    {
        var paths = _config.SelectToken("app_paths") as JObject;
        var path = paths?.
            SelectToken(appName)?.ToString();
        if (path != null && path.Contains("%USER%"))
        {
            path = path.Replace("%USER%", Environment.UserName);
        }
        return path;
    }

    public string DeviceId
    {
        get
        {
            var id = Get("device_id", "");
            if (string.IsNullOrEmpty(id))
                id = Environment.MachineName;
            return id;
        }
    }

    public string DeviceName
    {
        get
        {
            var name = Get("device_name", "");
            if (string.IsNullOrEmpty(name))
                name = Environment.MachineName;
            return name;
        }
    }
}
