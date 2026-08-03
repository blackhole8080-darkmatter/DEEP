"""In-process tests for the cybersecurity domain endpoints.

These used to `requests.get("http://127.0.0.1:7768/...")` — they needed a
manually-started server on a port nothing binds, and patched objects in this
process while calling a different one, so the mocks never applied. Everything
here now runs against the app directly via TestClient.
"""
from unittest.mock import AsyncMock, patch

from domains.cybersec.cve_intel import CVERecord, CVSSv3


def test_sandbox_refuses_execution_without_docker(client):
    response = client.post(
        "/api/etis/sandbox/execute",
        json={"code": "print('hello')", "language": "python"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    inner = body["data"]
    assert inner["success"] is False
    assert "docker" in inner["error"].lower()


def test_cve_lookup_maps_the_record_onto_the_response(client):
    record = CVERecord(
        cve_id="CVE-2024-3400",
        description="Mock vulnerability",
        published="2024-01-01",
        modified="2024-01-02",
        cvss_v3=CVSSv3(
            score=10.0,
            severity="CRITICAL",
            vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            attack_vector="NETWORK",
            privileges_required="NONE",
            user_interaction="NONE",
            confidentiality_impact="HIGH",
            integrity_impact="HIGH",
            availability_impact="HIGH",
        ),
        cwe=["CWE-78"],
        affected_products=["Mock OS"],
        references=[],
        is_kev=True,
    )
    with patch(
        "domains.cybersec.cve_intel.CVEIntel.lookup",
        new_callable=AsyncMock,
        return_value=record,
    ):
        response = client.get("/api/etis/cve/CVE-2024-3400")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True, body
    data = body["data"]
    assert data["cve_id"] == "CVE-2024-3400"
    assert data["severity"] == "CRITICAL"
    assert data["cvss_score"] == 10.0
    assert data["is_kev"] is True


def test_cve_lookup_404s_on_unknown_id(client):
    missing = CVERecord(cve_id="CVE-0000-0000", description="not found", published="", modified="")
    with patch(
        "domains.cybersec.cve_intel.CVEIntel.lookup",
        new_callable=AsyncMock,
        return_value=missing,
    ):
        response = client.get("/api/etis/cve/CVE-0000-0000")
    assert response.status_code == 404


def test_mitre_search_finds_known_technique(client):
    """MITRE data is bundled locally, so this needs no network."""
    response = client.post("/api/etis/mitre/search", json={"query": "exploit public-facing"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True, body
    ids = [t["id"] for t in body["data"]["techniques"]]
    assert "T1190" in ids


def test_mitre_map_cve_returns_a_kill_chain(client):
    response = client.post(
        "/api/etis/mitre/map-cve",
        json={"cve_id": "CVE-2021-44228", "description": "remote code execution"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True, body
    data = body["data"]
    assert data["cve_id"] == "CVE-2021-44228"
    assert data["phase"] != "unknown"
    assert len(data["ttps"]) > 0


def test_etis_status(client):
    response = client.get("/api/etis/status")
    assert response.status_code == 200
    assert response.json()["ok"] is True
