"""Tests for the human-in-the-loop gate and the approvals endpoints.

The gate had a hole worth naming: tools have been parking actions in
``core/pending_actions`` and telling the user to approve them in a panel — but
nothing listed the queue or ran anything out of it, so a parked action stayed
parked and the message promising otherwise was false. These cover both the gate
and the endpoints that make it real.

What is being defended:

* publishing never happens without an explicit approval, and the model cannot
  approve on the user's behalf by passing the flag itself
* an approval applies to the action that was shown to the user, not to
  arguments supplied at approval time
* consent expires, and rejecting is as available as approving
"""
from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core import pending_actions
from core.domain.models import ToolResult
from core.tools.registry import TOOL_SPECS
from interface import deps
from interface.routers import actions as actions_router


@pytest.fixture(autouse=True)
def empty_queue():
    pending_actions.clear()
    yield
    pending_actions.clear()


class FakeRegistry:
    """Stands in for DeepToolRegistry, recording what approval re-ran."""

    def __init__(self, result=None):
        self.calls: list[tuple[str, dict]] = []
        self._result = result or ToolResult(True, "done", "tool")

    async def execute_tool(self, name, args):
        self.calls.append((name, dict(args)))
        return self._result


@pytest.fixture
def client(monkeypatch):
    registry = FakeRegistry()
    monkeypatch.setattr(deps.services, "deep_tools", registry, raising=False)
    app = FastAPI()
    app.include_router(actions_router.router)
    test_client = TestClient(app)
    test_client.registry = registry
    return test_client


# ── the queue ────────────────────────────────────────────────────────────────


def test_enqueue_strips_a_caller_supplied_approval_flag():
    """Otherwise a tool could park itself pre-approved, defeating the gate."""
    aid = pending_actions.enqueue("t", {"url": "https://x.test", "_approved": True}, "label")
    assert "_approved" not in pending_actions.get(aid)["args"]
    assert pending_actions.approved_args(pending_actions.get(aid))["_approved"] is True


def test_consent_expires():
    aid = pending_actions.enqueue("t", {}, "label", ttl_s=-1)
    assert pending_actions.get(aid) is None
    assert pending_actions.list_pending() == []


def test_the_queue_is_bounded():
    for i in range(pending_actions.MAX_PENDING + 10):
        pending_actions.enqueue("t", {"i": i}, f"label {i}")
        time.sleep(0)
    assert pending_actions.count() <= pending_actions.MAX_PENDING


def test_popping_twice_yields_nothing_the_second_time():
    aid = pending_actions.enqueue("t", {}, "label")
    assert pending_actions.pop(aid) is not None
    assert pending_actions.pop(aid) is None


# ── the endpoints ────────────────────────────────────────────────────────────


def test_pending_lists_what_is_waiting(client):
    pending_actions.enqueue("url_scan_submit", {"url": "https://x.test"}, "Publish a scan")
    body = client.get("/api/actions/pending").json()

    assert body["count"] == 1
    assert body["pending"][0]["label"] == "Publish a scan"
    assert body["pending"][0]["expires_in_s"] > 0


def test_approving_reruns_the_tool_with_the_stored_arguments(client):
    aid = pending_actions.enqueue(
        "url_scan_submit", {"url": "https://x.test", "visibility": "public"}, "Publish"
    )
    body = client.post(f"/api/actions/{aid}/approve").json()

    assert body["ok"] is True
    assert client.registry.calls == [
        ("url_scan_submit", {"url": "https://x.test", "visibility": "public", "_approved": True})
    ]


def test_approving_twice_runs_the_action_once(client):
    aid = pending_actions.enqueue("url_scan_submit", {"url": "https://x.test"}, "Publish")

    assert client.post(f"/api/actions/{aid}/approve").status_code == 200
    assert client.post(f"/api/actions/{aid}/approve").status_code == 404
    assert len(client.registry.calls) == 1


def test_an_unknown_or_expired_action_is_a_404_not_a_silent_run(client):
    response = client.post("/api/actions/deadbeef/approve")

    assert response.status_code == 404
    assert "expired" in response.json()["detail"]
    assert client.registry.calls == []


def test_rejecting_drops_the_action_without_running_it(client):
    aid = pending_actions.enqueue("url_scan_submit", {"url": "https://x.test"}, "Publish")
    body = client.post(f"/api/actions/{aid}/reject").json()

    assert body["rejected"] is True
    assert client.registry.calls == []
    assert pending_actions.count() == 0


# ── the gated tool ───────────────────────────────────────────────────────────


async def _submit(args, monkeypatch, *, has_key=True, submit_result=None):
    from core.tools import intel as intel_tools

    monkeypatch.setattr(intel_tools, "urlscan_has_key", lambda: has_key)

    class FakeSource:
        def __init__(self):
            self.submitted = []

        async def submit(self, url, *, visibility="public", tags=None):
            self.submitted.append((url, visibility))
            return submit_result or {
                "uuid": "u1", "report_url": "https://urlscan.io/result/u1/",
                "visibility": visibility, "note": "takes 10-30s",
            }

    source = FakeSource()
    monkeypatch.setattr(intel_tools, "shared_urlscan", lambda: source)
    result = await TOOL_SPECS["url_scan_submit"].handler(None, args)
    return result, source


@pytest.mark.asyncio
async def test_an_unapproved_submission_publishes_nothing(monkeypatch):
    result, source = await _submit({"url": "https://x.test"}, monkeypatch)

    assert source.submitted == [], "the gate must run before anything is published"
    assert result.ok is True          # not a failure — a request for consent
    assert "confirmation" in result.content
    assert pending_actions.count() == 1


@pytest.mark.asyncio
async def test_the_parked_action_names_what_will_be_published(monkeypatch):
    await _submit({"url": "https://x.test/login"}, monkeypatch)
    entry = pending_actions.list_pending()[0]

    assert "https://x.test/login" in entry["label"]
    assert "permanently visible" in entry["detail"]
    assert entry["args"] == {"url": "https://x.test/login", "visibility": "public"}


@pytest.mark.asyncio
async def test_approval_lets_the_submission_through(monkeypatch):
    result, source = await _submit(
        {"url": "https://x.test", "visibility": "public", "_approved": True}, monkeypatch
    )

    assert source.submitted == [("https://x.test", "public")]
    assert result.ok is True
    assert "urlscan.io/result/u1" in result.content


@pytest.mark.asyncio
async def test_a_missing_key_is_reported_before_asking_for_consent(monkeypatch):
    """Do not ask a user to authorise something that cannot happen anyway."""
    result, source = await _submit({"url": "https://x.test"}, monkeypatch, has_key=False)

    assert result.ok is False
    assert "API key" in result.content
    assert pending_actions.count() == 0
    assert source.submitted == []


@pytest.mark.asyncio
async def test_a_malformed_url_never_reaches_the_queue(monkeypatch):
    result, _ = await _submit({"url": "javascript:alert(1)"}, monkeypatch)

    assert result.ok is False
    assert pending_actions.count() == 0


@pytest.mark.asyncio
async def test_an_unknown_visibility_falls_back_to_public(monkeypatch):
    """Never quietly upgrade to a weaker visibility than the user will see named."""
    await _submit({"url": "https://x.test", "visibility": "sneaky"}, monkeypatch)
    entry = pending_actions.list_pending()[0]

    assert entry["args"]["visibility"] == "public"
    assert "public" in entry["label"]


def test_an_unreachable_tool_registry_does_not_burn_the_approval(monkeypatch):
    """A 503 means nothing ran, so the user's answer must survive it."""
    monkeypatch.delattr(deps.services, "deep_tools", raising=False)
    app = FastAPI()
    app.include_router(actions_router.router)
    bare = TestClient(app)

    aid = pending_actions.enqueue("url_scan_submit", {"url": "https://x.test"}, "Publish")
    assert bare.post(f"/api/actions/{aid}/approve").status_code == 503
    assert pending_actions.get(aid) is not None, "the approval must still be actionable"


# ── the HUD notifier ─────────────────────────────────────────────────────────


def test_the_queue_announces_changes_so_the_hud_need_not_wait_for_a_poll():
    seen: list[tuple[str, dict]] = []
    pending_actions.set_notifier(lambda event, payload: seen.append((event, payload)))
    try:
        aid = pending_actions.enqueue("url_scan_submit", {"url": "https://x.test"}, "Publish")
        assert seen[0][0] == "approval_pending"
        assert seen[0][1]["id"] == aid
        assert seen[0][1]["pending"] == 1

        pending_actions.pop(aid)
        assert seen[1][0] == "approval_resolved"
        assert seen[1][1]["pending"] == 0
    finally:
        pending_actions.set_notifier(None)


def test_a_broken_notifier_does_not_break_the_gate():
    """The queue reports to the HUD; it must not depend on the HUD."""
    def boom(event, payload):
        raise RuntimeError("no listener")

    pending_actions.set_notifier(boom)
    try:
        aid = pending_actions.enqueue("t", {}, "label")
        assert pending_actions.get(aid) is not None
        assert pending_actions.pop(aid) is not None
    finally:
        pending_actions.set_notifier(None)
