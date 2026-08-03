"""Route-wiring tests for the FastAPI app.

These assert the contract the frontend depends on: that the SPA is served,
that the auth boundary is real, and that the core JSON endpoints are mounted
at the paths `interface/web/src/core/api.ts` actually calls.
"""


def test_root_serves_the_spa(client):
    """`/` is the HUD shell, not a JSON status blob."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<deep-app>" in response.text


def test_remote_requests_require_a_key(anon_client):
    """A non-loopback client with no key is rejected, not served."""
    response = anon_client.get("/api/vitals")
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


def test_wrong_key_is_rejected(anon_client):
    response = anon_client.get("/api/vitals", headers={"x-deep-key": "not-the-key"})
    assert response.status_code == 401


def test_spa_bootstrap_stays_public(anon_client):
    """The login surface has to load before a key can be supplied."""
    assert anon_client.get("/").status_code == 200


def test_vitals(client):
    response = client.get("/api/vitals")
    assert response.status_code == 200
    data = response.json()
    for key in ("cpu", "ram", "disk", "cores"):
        assert key in data


def test_system_info(client):
    response = client.get("/api/system/info")
    assert response.status_code == 200
    data = response.json()
    assert "hostname" in data
    assert "os" in data


def test_network_stats(client):
    response = client.get("/api/network/stats")
    assert response.status_code == 200


def test_security_status(client):
    response = client.get("/api/security/status")
    assert response.status_code == 200


def test_knowledge_document_list_is_mounted_where_the_ui_calls_it(client):
    """Regression: these lived at /knowledge/api/knowledge/list and 404'd."""
    response = client.get("/api/knowledge/list")
    assert response.status_code == 200
    assert "documents" in response.json()


def test_audit_stats(client):
    """Regression: this router referenced module-level names that didn't exist.

    The DB itself is only created by lifespan startup, which these tests skip,
    so a storage-level error is fine — a NameError is not.
    """
    response = client.get("/audit/stats")
    assert response.status_code == 200
    assert "is not defined" not in str(response.json().get("error", ""))


def test_audit_session_does_not_raise_nameerror(client):
    response = client.get("/audit/session")
    assert response.status_code == 200
    body = response.json()
    assert "is not defined" not in str(body.get("error", ""))


def test_retraining_status_does_not_raise_nameerror(client):
    response = client.get("/ai/retraining/status")
    assert response.status_code == 200
    body = response.json()
    assert "is not defined" not in str(body.get("error", ""))


# ── intelligence layer routes ────────────────────────────────────────────────


def test_intel_sources_catalog(client):
    response = client.get("/api/intel/sources")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 0
    assert body["keyless"] > 0
    assert all("configured" in s for s in body["sources"])


def test_intel_sources_filters_by_category(client):
    response = client.get("/api/intel/sources?category=vulnerability")
    assert response.status_code == 200
    assert {s["category"] for s in response.json()["sources"]} == {"vulnerability"}


def test_intel_classify(client):
    response = client.get("/api/intel/classify?target=CVE-2021-44228")
    assert response.status_code == 200
    body = response.json()
    assert body["indicator"] == "cve"
    assert len(body["sources"]) > 0


def test_intel_classify_unknown_indicator(client):
    response = client.get("/api/intel/classify?target=not-an-indicator-at-all")
    assert response.status_code == 200
    assert response.json()["indicator"] is None


def test_intel_investigate_rejects_garbage_with_422(client):
    """Unlike the older routers, failures here are real status codes."""
    response = client.get("/api/intel/investigate?target=%3F%3F%3F")
    assert response.status_code == 422


def test_terminal_command_catalog(client):
    response = client.get("/api/intel/terminal/commands")
    assert response.status_code == 200
    names = {c["name"] for c in response.json()["commands"]}
    assert {"help", "investigate", "cve", "kev", "stats", "scan"} <= names


def test_terminal_exec_help(client):
    response = client.post("/api/intel/terminal/exec", json={"line": "help"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "investigate" in body["text"]


def test_terminal_exec_rejects_shell_injection(client):
    response = client.post("/api/intel/terminal/exec", json={"line": "rm -rf /"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert "unknown command" in body["error"]


def test_terminal_exec_requires_a_line(client):
    assert client.post("/api/intel/terminal/exec", json={"line": ""}).status_code == 422


def test_terminal_requires_auth(anon_client):
    response = anon_client.post("/api/intel/terminal/exec", json={"line": "help"})
    assert response.status_code == 401


# ── retired surfaces ─────────────────────────────────────────────────────────


def test_removed_audio_endpoints_are_gone(client):
    """These served a hard-deleted voice subsystem and returned 500s.

    /audio/bluetooth and /audio/spatial called a stub whose __getattr__ handed
    back an async no-op, so the handler returned an un-awaited coroutine that
    FastAPI could not serialise; /audio/devices iterated None.
    """
    for path in ("/audio/bluetooth", "/audio/spatial", "/audio/devices"):
        assert client.get(path).status_code == 404, path


def test_removed_science_endpoints_are_gone(client):
    """The compute engine behind these was archived; they answered anyway."""
    for path in ("/api/chem/table", "/api/physics/constants", "/api/physics/formulas"):
        assert client.get(path).status_code == 404, path
    for path in ("/api/science/compute", "/api/math/solve"):
        assert client.post(path, json={"query": "x"}).status_code == 404, path


def test_disabled_voice_endpoints_report_503_not_200(client):
    """A disabled subsystem is a status code, not an error string inside a 200."""
    assert client.get("/api/tts?text=hello").status_code == 503


def test_investigate_without_a_target_is_422(client):
    """Was 200 with {"error": "missing target"} — indistinguishable from a result."""
    assert client.get("/api/investigate").status_code == 422


def test_no_endpoint_returns_a_server_error(client):
    """Sweep every parameterless GET; nothing may 5xx."""
    from interface.server import app

    paths = [
        p for p, ops in app.openapi()["paths"].items()
        if "get" in ops and "{" not in p
        and p not in ("/api/vision/screen", "/docs", "/redoc", "/openapi.json", "/api/tts")
    ]
    failures = [(p, r.status_code) for p in paths
                if (r := client.get(p)).status_code >= 500]
    assert not failures, f"endpoints returning 5xx: {failures}"
