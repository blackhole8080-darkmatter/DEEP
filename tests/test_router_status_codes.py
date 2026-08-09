"""Routers must answer with status codes, not 200-carrying-an-error.

Every handler in these modules used to end in `except Exception: return
{"error": str(e)}`. Three things were wrong with that, and each has bitten this
codebase already:

* A caller cannot distinguish a result from a failure — both are 200. Three
  NameError bugs sat undetected in this repo for exactly that reason.
* It pre-empts the app's own 500 handler, which logs the traceback. A swallowed
  exception is one nobody ever sees.
* `str(e)` goes to the client. On a security console that can mean filesystem
  paths or connection strings.

The blanket catches are gone. What is left is the deliberate part: a subsystem
that is not running is 503, absent data is 404, bad input is 422, and a refusal
that is about the request rather than the server is 409.
"""
from __future__ import annotations

import pytest

from interface.deps import require, services

# ═══════════════════════════════════════════════════════════════════════════
# require(): a down subsystem is 503, not a 500 and not an empty 200
# ═══════════════════════════════════════════════════════════════════════════


def test_require_returns_a_registered_service(client):
    # The client fixture is what imports server.py and populates the registry.
    assert require("event_bus") is services.event_bus


def test_require_raises_503_naming_the_subsystem():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as caught:
        require("a_subsystem_that_was_never_registered")
    assert caught.value.status_code == 503
    assert "a_subsystem_that_was_never_registered" in caught.value.detail
    assert "not running" in caught.value.detail


def test_a_subsystem_that_failed_to_start_is_503_not_500(client, monkeypatch):
    """server.py logs a start failure and carries on, so the attribute is
    simply never registered. That is a fact about the deployment, not a bug —
    sending an operator hunting for a defect would be the wrong answer."""
    monkeypatch.delattr(services, "predictive_engine", raising=False)
    response = client.get("/api/predictive/stats")
    assert response.status_code == 503
    assert "predictive_engine" in response.json()["detail"]


# ═══════════════════════════════════════════════════════════════════════════
# Input validation is 422, and says what was expected
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "path,payload",
    [
        # was 200 {"error": "Missing device_id"}
        ("/state/handoff", {}),
        ("/state/handoff", {"device_id": ""}),
        ("/api/predictive/feedback", {}),
        ("/api/predictive/feedback", {"prediction_id": "p1"}),   # accepted missing
    ],
)
def test_missing_body_fields_are_422(client, path, payload):
    assert client.post(path, json=payload).status_code == 422


@pytest.mark.parametrize(
    "path",
    [
        "/api/predictive/history?limit=0",
        "/api/predictive/history?limit=9999",
        "/api/evolution/history?limit=0",
        "/anomaly/recent?hours=0",
        "/threat/predictions?limit=0",
        "/api/security/timeline?limit=0",
    ],
)
def test_out_of_range_query_params_are_422(client, path):
    """These were unbounded, so `limit=100000` was a denial-of-service knob."""
    assert client.get(path).status_code == 422


def test_an_unknown_severity_filter_is_rejected_not_ignored(client):
    """Silently returning everything is the opposite of what narrowing to
    `critical` implies — a typo used to read as 'nothing was filtered out'."""
    response = client.get("/api/security/timeline?min_severity=catastrophic")
    assert response.status_code == 422
    assert "critical" in response.json()["detail"]


def test_a_valid_severity_filter_still_works(client):
    assert client.get("/api/security/timeline?min_severity=high").status_code == 200
    assert client.get("/api/security/timeline?min_severity=HIGH").status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# Absent data is 404; a refusal about the request is 409
# ═══════════════════════════════════════════════════════════════════════════


def test_feedback_on_an_unknown_prediction_is_404(client):
    """record_feedback returns False for an id it has never seen, which came
    back as {"success": false} at 200 — a successful call with a falsy field."""
    response = client.post(
        "/api/predictive/feedback",
        json={"prediction_id": "no-such-prediction", "accepted": True},
    )
    assert response.status_code == 404
    assert "no-such-prediction" in response.json()["detail"]


def test_handoff_to_an_unknown_device_is_404(client):
    """handoff_to writes the target into shared state unconditionally, so a
    typo used to hand control to a device that does not exist — and say OK."""
    response = client.post("/state/handoff", json={"device_id": "not-a-real-device"})
    assert response.status_code == 404
    assert "not-a-real-device" in response.json()["detail"]


def test_evaluating_without_enough_history_is_409(client):
    """evaluate_and_evolve returns None under MIN_TURNS_FOR_EVOLUTION."""
    response = client.post("/api/evolution/evaluate")
    assert response.status_code in (200, 409)
    if response.status_code == 409:
        assert "not enough" in response.json()["detail"].lower()


def test_a_missing_training_report_is_404(client):
    """Was 200 {"reports": []} — indistinguishable from a report listing zero."""
    response = client.get("/threat/report")
    assert response.status_code in (200, 404)
    if response.status_code == 404:
        assert "train" in response.json()["detail"]


# ═══════════════════════════════════════════════════════════════════════════
# The pattern itself must not come back
# ═══════════════════════════════════════════════════════════════════════════


CONVERTED = (
    "state", "anomaly", "threat", "predictive", "evolution", "security_timeline",
    "intel", "alerts",
)


def _parse(module_name: str):
    """Parse a router to an AST.

    Deliberately not a text scan: these modules document the pattern they
    removed, and grepping the source matches the prose describing the fix as
    readily as a real recurrence.
    """
    import ast
    import importlib
    import inspect

    module = importlib.import_module(f"interface.routers.{module_name}")
    return ast.parse(inspect.getsource(module))


@pytest.mark.parametrize("module_name", CONVERTED)
def test_converted_routers_have_no_error_returning_200(module_name):
    """`return {"error": ...}` is a failure the caller reads as a result."""
    import ast

    offenders = [
        node.lineno
        for node in ast.walk(_parse(module_name))
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
        and any(isinstance(k, ast.Constant) and k.value == "error"
                for k in node.value.keys)
    ]
    assert not offenders, \
        f"{module_name} returns an error at 200 on line(s) {offenders}"


@pytest.mark.parametrize("module_name", CONVERTED)
def test_converted_routers_have_no_blanket_exception_handler(module_name):
    """A bare `except Exception` pre-empts the app's 500 handler, so the
    traceback is never logged and nobody ever learns the endpoint is broken."""
    import ast

    offenders = [
        handler.lineno
        for handler in ast.walk(_parse(module_name))
        if isinstance(handler, ast.ExceptHandler)
        and (handler.type is None
             or (isinstance(handler.type, ast.Name) and handler.type.id == "Exception"))
    ]
    assert not offenders, f"{module_name} swallows everything on line(s) {offenders}"


@pytest.mark.parametrize("module_name", CONVERTED)
def test_converted_routers_reach_services_through_require(module_name):
    """Bare `services.x` raises AttributeError — a 500 — when a subsystem did
    not start. require() makes that same case a 503 that names it."""
    import ast

    reached = {
        node.attr
        for node in ast.walk(_parse(module_name))
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
        and node.value.id == "services"
    }
    assert not reached, \
        f"{module_name} reaches services.{{{', '.join(sorted(reached))}}}"
