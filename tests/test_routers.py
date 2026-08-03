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
