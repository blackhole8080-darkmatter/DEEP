using System.Net.WebSockets;
using System.Text;
using DeepClient.Models;

namespace DeepClient.Core;

/// <summary>
/// Persistent WebSocket connection to the Python DEEP core.
/// </summary>
public class DeepWebSocketClient
{
    private ClientWebSocket? _ws;
    private readonly ConfigManager _config;
    private CancellationTokenSource _cts = new();
    private readonly string _uri;
    private Task? _receiveTask;

    public event Action<DeepEvent>? OnEventReceived;
    public event Action? OnConnected;
    public event Action? OnDisconnected;

    public bool IsConnected => _ws?.State == WebSocketState.Open;

    public DeepWebSocketClient(ConfigManager config)
    {
        _config = config;
        _uri = config.GetWsUrl();
    }

    public async Task ConnectAsync()
    {
        var reconnectMs = _config.GetInt("reconnect_interval_ms", 5000);
        while (!_cts.Token.IsCancellationRequested)
        {
            try
            {
                _ws = new ClientWebSocket();
                await _ws.ConnectAsync(new Uri(_uri), _cts.Token);
                OnConnected?.Invoke();

                // Send registration event
                var reg = new DeepEvent
                {
                    Type = "device_register",
                    Payload = new Dictionary<string, object>
                    {
                        ["device_id"] = _config.DeviceId,
                        ["device_name"] = _config.DeviceName,
                        ["platform"] = "windows",
                        ["version"] = "v2"
                    }
                };
                await SendRawAsync(reg.ToJson());

                _receiveTask = ReceiveLoopAsync();
                await _receiveTask; // blocks until disconnect
            }
            catch (Exception ex)
            {
                OnDisconnected?.Invoke();
            }

            if (_cts.Token.IsCancellationRequested) break;
            try { await Task.Delay(reconnectMs, _cts.Token); }
            catch (TaskCanceledException) { break; }
        }
    }

    private async Task ReceiveLoopAsync()
    {
        if (_ws == null) return;
        var buffer = new byte[8192];
        while (_ws.State == WebSocketState.Open && !_cts.Token.IsCancellationRequested)
        {
            try
            {
                var result = await _ws.ReceiveAsync(new ArraySegment<byte>(buffer), _cts.Token);
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
                    break;
                }
                var json = Encoding.UTF8.GetString(buffer, 0, result.Count);
                var evt = DeepEvent.FromJson(json);
                OnEventReceived?.Invoke(evt);
            }
            catch (WebSocketException)
            {
                break;
            }
            catch (TaskCanceledException)
            {
                break;
            }
        }
    }

    public async Task SendEvent(string type, Dictionary<string, object> payload)
    {
        var evt = new DeepEvent { Type = type, Payload = payload };
        await SendRawAsync(evt.ToJson());
    }

    private async Task SendRawAsync(string json)
    {
        if (_ws == null || _ws.State != WebSocketState.Open) return;
        var bytes = Encoding.UTF8.GetBytes(json);
        await _ws.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, _cts.Token);
    }

    public async Task DisconnectAsync()
    {
        _cts.Cancel();
        if (_ws != null && _ws.State == WebSocketState.Open)
        {
            await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "Client shutdown", CancellationToken.None);
        }
        _ws?.Dispose();
    }
}
