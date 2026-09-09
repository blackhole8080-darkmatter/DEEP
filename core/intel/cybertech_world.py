"""Read-only projection for the Cybertech World dashboard.

This module deliberately contains no scanners and no synthetic events. It reshapes
outputs that DEEP already collected into one bounded, UI-friendly contract.
Unavailable or stale upstream data stays visible as a degraded state instead of
being converted into a reassuring zero.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable


WORLD_LAYER_DEFINITIONS = (
    {"id": "threats", "label": "Threat feeds", "description": "Geolocated indicators attributed to their source."},
    {"id": "local", "label": "Local estate", "description": "Observed devices and network entities from DEEP's graph."},
    {"id": "entities", "label": "Entity graph", "description": "Relationships DEEP has stored or inferred."},
    {"id": "alerts", "label": "Security events", "description": "The bounded security timeline."},
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any, fallback: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def _severity(value: Any) -> str:
    candidate = _text(value, "info").lower()
    return candidate if candidate in {"info", "low", "medium", "high", "critical", "warning"} else "info"


def _normalise_node(raw: Any, index: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    ip = _text(raw.get("ip"))
    if not ip:
        return None
    try:
        lat = float(raw.get("lat"))
        lon = float(raw.get("lon"))
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    detail = raw.get("detail") if isinstance(raw.get("detail"), dict) else {}
    return {
        "id": f"indicator:{ip}",
        "layer": "threats",
        "kind": "indicator",
        "label": ip,
        "lat": lat,
        "lon": lon,
        "country": _text(raw.get("country")),
        "city": _text(raw.get("city")),
        "source": _text(raw.get("source"), "unknown source"),
        "classification": _text(raw.get("classification"), "unclassified"),
        "severity": _severity(raw.get("severity")),
        "detail": detail,
        "rank": index,
    }


def _normalise_event(raw: Any, index: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    summary = _text(raw.get("summary"), "Security event")
    return {
        "id": _text(raw.get("id"), f"event:{index}"),
        "source": _text(raw.get("source"), "security timeline"),
        "kind": _text(raw.get("kind"), "security_event"),
        "severity": _severity(raw.get("severity")),
        "timestamp": _text(raw.get("timestamp")),
        "summary": summary,
        "techniques": raw.get("techniques") if isinstance(raw.get("techniques"), list) else [],
        "related_cves": raw.get("related_cves") if isinstance(raw.get("related_cves"), list) else [],
    }


def _iter_sources(summary: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(summary, dict):
        return ()
    sources = summary.get("sources")
    return (item for item in sources if isinstance(item, dict)) if isinstance(sources, list) else ()


def build_world_snapshot(
    *,
    map_payload: Any,
    timeline_items: Any,
    graph_payload: Any,
    source_summary: Any,
) -> dict[str, Any]:
    """Build the stable response consumed by the Cybertech World view."""
    raw_nodes = map_payload.get("nodes", []) if isinstance(map_payload, dict) else []
    nodes = [node for i, raw in enumerate(raw_nodes) if (node := _normalise_node(raw, i))]

    raw_events = timeline_items if isinstance(timeline_items, list) else []
    events = [event for i, raw in enumerate(raw_events) if (event := _normalise_event(raw, i))]

    graph = graph_payload if isinstance(graph_payload, dict) else {}
    graph_nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    graph_edges = graph.get("edges") if isinstance(graph.get("edges"), list) else []
    local_count = sum(1 for item in graph_nodes if isinstance(item, dict) and item.get("layer") in {"lan", "wifi", "bluetooth", "vpn", "internet", "dns"})

    source_states = []
    for source in _iter_sources(source_summary):
        source_states.append({
            "id": _text(source.get("id") or source.get("name"), "source"),
            "label": _text(source.get("label") or source.get("name"), "Unnamed source"),
            "category": _text(source.get("category")),
            "available": bool(source.get("configured", source.get("available", source.get("live", False)))),
            "reason": _text(source.get("unavailable_reason") or source.get("reason") or source.get("error")),
        })

    degraded: dict[str, Any] = {}
    if isinstance(map_payload, dict):
        if isinstance(map_payload.get("degraded"), dict):
            degraded.update(map_payload["degraded"])
        if isinstance(map_payload.get("stale"), dict):
            degraded["stale"] = map_payload["stale"]

    counts = {
        "threats": len(nodes),
        "local": local_count,
        "entities": len(graph_nodes),
        "alerts": len(events),
    }
    layers = [
        {**definition, "count": counts[definition["id"]], "enabled": True}
        for definition in WORLD_LAYER_DEFINITIONS
    ]

    return {
        "generated_at": _text(map_payload.get("generated_at") if isinstance(map_payload, dict) else "", _now()),
        "layers": layers,
        "nodes": nodes,
        "edges": graph_edges[:500],
        "events": events,
        "sources": source_states,
        "stats": {
            "threat_nodes": len(nodes),
            "security_events": len(events),
            "graph_entities": len(graph_nodes),
            "graph_edges": len(graph_edges),
            "available_sources": sum(1 for source in source_states if source["available"]),
            "total_sources": len(source_states),
        },
        "degraded": degraded,
    }
