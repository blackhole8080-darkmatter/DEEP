import requests
import json

BASE_URL = "http://127.0.0.1:7768/api/etis"

import asyncio

def test_sandbox_endpoint_refusal():
    """
    Verify the sandbox endpoint correctly refuses execution 
    when Docker is missing and DEEP_SANDBOX_ALLOW_UNSAFE != 1.
    """
    response = requests.post(f"{BASE_URL}/sandbox/execute", json={
        "code": "print('hello')",
        "language": "python"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    # The payload 'ok' is True, but the inner sandbox execution 'success' is False
    inner = data["data"]
    assert inner["success"] is False
    assert "Docker is not available" in inner["error"]
    print("test_sandbox_endpoint_refusal OK")

def test_cve_lookup():
    """Verify the CVE lookup via HTTP router, mocking the actual engine."""
    from unittest.mock import patch, AsyncMock
    with patch('domains.cybersec.cve_intel.CVEIntel.lookup', new_callable=AsyncMock) as mock_lookup:
        from domains.cybersec.cve_intel import CVERecord
        mock_lookup.return_value = CVERecord(
            cve_id="CVE-2024-3400",
            description="Mock vulnerability",
            severity="CRITICAL",
            published="2024-01-01",
            cwes=["CWE-78"],
            affected_products=["Mock OS"],
            references=[],
            is_kev=True,
            cvss_score=10.0
        )

        response = requests.get(f"{BASE_URL}/cve/CVE-2024-3400")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["ok"] is True, data
        assert data["data"]["cve_id"] == "CVE-2024-3400"
        assert data["data"]["severity"] == "CRITICAL"
        print("test_cve_lookup OK")

def test_mitre_search():
    """Verify MITRE search via HTTP router."""
    response = requests.post(f"{BASE_URL}/mitre/search", json={"query": "exploit"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["ok"] is True, data
    assert len(data["data"]) > 0
    technique_ids = [t["id"] for t in data["data"]]
    assert "T1190" in technique_ids
    print("test_mitre_search OK")

def test_mitre_map_cve():
    """Verify MITRE map_cve endpoint via HTTP router."""
    response = requests.post(f"{BASE_URL}/mitre/map-cve", json={"cve_id": "CVE-2021-44228", "description": "remote code execution"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["ok"] is True, data
    assert data["data"]["cve_id"] == "CVE-2021-44228"
    assert data["data"]["phase"] != "unknown"
    assert len(data["data"]["ttps"]) > 0
    print("test_mitre_map_cve OK")

if __name__ == "__main__":
    test_sandbox_endpoint_refusal()
    test_cve_lookup()
    test_mitre_search()
    test_mitre_map_cve()
    print("All tests passed.")
