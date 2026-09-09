from core.intel.cybertech_world import build_world_snapshot


def test_world_snapshot_normalises_real_nodes_and_preserves_degraded_state():
    snapshot = build_world_snapshot(
        map_payload={
            "generated_at": "2026-09-09T12:00:00+00:00",
            "nodes": [
                {
                    "ip": "203.0.113.10",
                    "lat": 52.5,
                    "lon": 13.4,
                    "country": "Germany",
                    "city": "Berlin",
                    "source": "test-feed",
                    "classification": "scanner",
                    "severity": "high",
                    "detail": {"attacks": 12},
                },
                {"ip": "not-geolocated", "lat": None, "lon": 1},
            ],
            "degraded": {"geo": "test outage"},
            "stale": {"feed": 42},
        },
        timeline_items=[{
            "id": "evt-1",
            "source": "timeline",
            "kind": "threat",
            "severity": "critical",
            "timestamp": "2026-09-09T11:59:00+00:00",
            "summary": "Known event",
        }],
        graph_payload={
            "nodes": [{"id": "host-1", "layer": "lan"}],
            "edges": [{"source": "host-1", "target": "gw-1"}],
        },
        source_summary={"sources": [{"id": "test", "name": "Test feed", "available": True}]},
    )

    assert snapshot["stats"]["threat_nodes"] == 1
    assert snapshot["stats"]["security_events"] == 1
    assert snapshot["stats"]["graph_entities"] == 1
    assert snapshot["layers"][0]["id"] == "threats"
    assert snapshot["nodes"][0]["severity"] == "high"
    assert snapshot["degraded"]["geo"] == "test outage"
    assert snapshot["degraded"]["stale"]["feed"] == 42


def test_world_snapshot_does_not_turn_missing_sources_into_healthy_sources():
    snapshot = build_world_snapshot(
        map_payload={"nodes": []},
        timeline_items=[],
        graph_payload={},
        source_summary={"sources": [{"id": "down", "name": "Down feed", "available": False, "error": "offline"}]},
    )

    assert snapshot["stats"]["available_sources"] == 0
    assert snapshot["stats"]["total_sources"] == 1
    assert snapshot["sources"][0]["available"] is False
    assert snapshot["sources"][0]["reason"] == "offline"
