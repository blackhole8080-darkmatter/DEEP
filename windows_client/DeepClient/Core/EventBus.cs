using DeepClient.Models;

namespace DeepClient.Core;

/// <summary>
/// In-process pub/sub for the C# client.
/// Mirrors Python EventBus semantics for the local side.
/// </summary>
public class EventBus
{
    private readonly Dictionary<string, List<Action<DeepEvent>>> _subscribers = new();

    public void Subscribe(string eventType, Action<DeepEvent> handler)
    {
        if (!_subscribers.ContainsKey(eventType))
            _subscribers[eventType] = new List<Action<DeepEvent>>();
        _subscribers[eventType].Add(handler);
    }

    public void Unsubscribe(string eventType, Action<DeepEvent> handler)
    {
        if (_subscribers.TryGetValue(eventType, out var list))
            list.Remove(handler);
    }

    public void Publish(string eventType, Dictionary<string, object> payload)
    {
        var evt = new DeepEvent { Type = eventType, Payload = payload };
        Publish(evt);
    }

    public void Publish(DeepEvent evt)
    {
        if (_subscribers.TryGetValue(evt.Type, out var handlers))
        {
            foreach (var h in handlers.ToList())
            {
                try { h(evt); }
                catch { /* subscriber exceptions should not crash bus */ }
            }
        }
        // Wildcard subscriber
        if (_subscribers.TryGetValue("*", out var wildcards))
        {
            foreach (var h in wildcards.ToList())
            {
                try { h(evt); }
                catch { }
            }
        }
    }
}
