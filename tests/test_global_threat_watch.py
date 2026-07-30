"""
tests/test_global_threat_watch.py

Unit tests for GlobalThreatWatch: matches CISA KEV entries against known
knowledge-graph entities and records a world_model alert on a hit.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.event_bus import EventBus
from core.global_threat_watch import GlobalThreatWatch
from core.intel_feeds import IntelItem
from core.world_model import WorldModel


def _make_watch(kev_items, kg_entities, world_model, event_bus, otx_items=None):
    intel_feeds = MagicMock()
    intel_feeds.fetch_kev = AsyncMock(return_value=kev_items)
    # run_once() also checks OTX pulses now (see core/global_threat_watch.py);
    # default to empty so existing KEV-only tests don't need to know about it.
    intel_feeds.fetch_otx_pulses = AsyncMock(return_value=otx_items or [])
    knowledge_graph = MagicMock()
    knowledge_graph.get_all_entities = MagicMock(return_value=kg_entities)
    return GlobalThreatWatch(
        event_bus=event_bus,
        knowledge_graph=knowledge_graph,
        world_model=world_model,
        intel_feeds=intel_feeds,
    )


@pytest.mark.asyncio
async def test_kev_entry_matching_known_entity_produces_alert() -> None:
    bus = EventBus()
    await bus.start()

    with tempfile.TemporaryDirectory() as tmp:
        wm = WorldModel(data_dir=Path(tmp))

        kev_item = IntelItem(
            source="KEV", item_id="CVE-2026-12345",
            title="[KEV] CVE-2026-12345 — Docker Engine remote code execution",
            summary="A flaw in Docker Engine allows remote code execution.",
            published="2026-07-30", severity="CRITICAL",
            url="https://nvd.nist.gov/vuln/detail/CVE-2026-12345", is_kev=True,
        )
        watch = _make_watch(
            kev_items=[kev_item],
            kg_entities=[{"name": "Docker", "type": "technology", "mention_count": 5}],
            world_model=wm,
            event_bus=bus,
        )

        received = []

        async def _capture(event_name: str, payload: dict) -> None:
            received.append(payload)

        bus.subscribe("world_threat_match", _capture)

        matches = await watch.run_once()

        assert len(matches) == 1
        assert matches[0]["cve_id"] == "CVE-2026-12345"
        assert matches[0]["matched_entity"] == "Docker"
        assert len(received) == 1
        assert received[0]["cve_id"] == "CVE-2026-12345"
        assert len(wm.state["world_alerts"]) == 1
        assert "CVE-2026-12345" in wm.state["world_alerts"][0]["text"]
        assert "Docker" in wm.context_block()


@pytest.mark.asyncio
async def test_no_match_when_entity_absent_from_kev_text() -> None:
    bus = EventBus()
    await bus.start()

    with tempfile.TemporaryDirectory() as tmp:
        wm = WorldModel(data_dir=Path(tmp))

        kev_item = IntelItem(
            source="KEV", item_id="CVE-2026-99999",
            title="[KEV] CVE-2026-99999 — Some Unrelated Product",
            summary="Nothing to do with anything DEEP knows about.",
            published="2026-07-30", severity="CRITICAL",
            url="https://nvd.nist.gov/vuln/detail/CVE-2026-99999", is_kev=True,
        )
        watch = _make_watch(
            kev_items=[kev_item],
            kg_entities=[{"name": "Docker", "type": "technology", "mention_count": 5}],
            world_model=wm,
            event_bus=bus,
        )

        matches = await watch.run_once()
        assert matches == []
        assert wm.state["world_alerts"] == []


@pytest.mark.asyncio
async def test_same_match_does_not_fire_twice() -> None:
    bus = EventBus()
    await bus.start()

    with tempfile.TemporaryDirectory() as tmp:
        wm = WorldModel(data_dir=Path(tmp))

        kev_item = IntelItem(
            source="KEV", item_id="CVE-2026-11111",
            title="[KEV] CVE-2026-11111 — Docker vulnerability",
            summary="Docker again.",
            published="2026-07-30", severity="CRITICAL",
            url="https://nvd.nist.gov/vuln/detail/CVE-2026-11111", is_kev=True,
        )
        watch = _make_watch(
            kev_items=[kev_item],
            kg_entities=[{"name": "Docker", "type": "technology", "mention_count": 5}],
            world_model=wm,
            event_bus=bus,
        )

        first = await watch.run_once()
        second = await watch.run_once()

        assert len(first) == 1
        assert len(second) == 0  # already seen this cycle
        assert len(wm.state["world_alerts"]) == 1


@pytest.mark.asyncio
async def test_otx_pulse_matching_known_entity_produces_alert() -> None:
    """run_once() now checks OTX pulses too, not just KEV — same matching
    pipeline, reused via _process_items()."""
    bus = EventBus()
    await bus.start()

    with tempfile.TemporaryDirectory() as tmp:
        wm = WorldModel(data_dir=Path(tmp))

        otx_item = IntelItem(
            source="OTX", item_id="pulse-99",
            title="Campaign abusing Docker misconfigurations for initial access",
            summary="Attackers are scanning for exposed Docker APIs.",
            published="2026-07-30", severity="HIGH",
            url="https://otx.alienvault.com/pulse/pulse-99",
        )
        watch = _make_watch(
            kev_items=[], otx_items=[otx_item],
            kg_entities=[{"name": "Docker", "type": "technology", "mention_count": 5}],
            world_model=wm, event_bus=bus,
        )

        matches = await watch.run_once()

        assert len(matches) == 1
        assert matches[0]["source"] == "OTX pulse"
        assert matches[0]["matched_entity"] == "Docker"
        assert len(wm.state["world_alerts"]) == 1
        assert "pulse-99" in wm.state["world_alerts"][0]["text"]


def test_world_model_add_world_alert_bounded_and_deduped() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        wm = WorldModel(data_dir=Path(tmp))
        for i in range(WorldModel.MAX_WORLD_ALERTS + 5):
            wm.add_world_alert(f"alert {i}")
        assert len(wm.state["world_alerts"]) == WorldModel.MAX_WORLD_ALERTS
        assert wm.state["world_alerts"][-1]["text"] == f"alert {WorldModel.MAX_WORLD_ALERTS + 4}"

        wm.add_world_alert("dup")
        wm.add_world_alert("dup")  # immediate repeat should be skipped
        assert wm.state["world_alerts"][-1]["text"] == "dup"
        count_before = len(wm.state["world_alerts"])
        wm.add_world_alert("dup")
        assert len(wm.state["world_alerts"]) == count_before
