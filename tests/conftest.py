"""Shared pytest fixtures for the DEEP suite.

The one thing every HTTP test needs is a client that gets past the security
middleware. `TestClient` reports its client host as "testclient", which is
deliberately *not* loopback, so unauthenticated requests correctly 401. Tests
therefore authenticate the same way a real remote client would: with the key.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="session")
def api_key() -> str:
    from core.config import Settings

    return Settings().deep_api_key


@pytest.fixture(scope="session")
def client(api_key: str):
    """Authenticated TestClient bound to the real FastAPI app.

    Built without triggering lifespan startup: the tests exercise route
    wiring and handler logic, not the full boot sequence (which starts
    scanners, schedulers and background loops).
    """
    from fastapi.testclient import TestClient

    from interface.server import app

    return TestClient(app, headers={"x-deep-key": api_key})


@pytest.fixture(scope="session")
def anon_client():
    """Unauthenticated client, for asserting the auth boundary itself."""
    from fastapi.testclient import TestClient

    from interface.server import app

    return TestClient(app)
