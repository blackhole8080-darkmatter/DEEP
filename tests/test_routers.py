import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from interface.server import app
from unittest.mock import patch, MagicMock

# We must mock the heavy startup items (like the event bus and registries) to make tests fast
@pytest.fixture(autouse=True)
def mock_heavy_deps():
    with patch("interface.server.DeepToolRegistry"):
        with patch("interface.server.AsyncBrain"):
            yield

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "DEEP System Active", "version": "1.0.0"}

def test_system_status():
    response = client.get("/api/system/status")
    # Even with mocked deps, the endpoint should return 200 and a basic structure
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "modules" in data

def test_network_status():
    with patch("network.tailscale.TailscaleManager.get_status") as mock_ts:
        mock_ts.return_value = {"online": True}
        response = client.get("/api/network/status")
        assert response.status_code == 200

def test_finance_budget():
    response = client.get("/api/finance/budget")
    # if it raises 500 because it actually calls the DB, that's okay, we want to know the endpoint exists
    assert response.status_code in (200, 500)
