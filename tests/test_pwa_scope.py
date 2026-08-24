"""The PWA's root scope, and the wiring that was missing from it.

The service worker shipped for a long time doing nothing at all, in three
compounding ways: nothing called `navigator.serviceWorker.register()`, the
script was only reachable at `/static/sw.js` — where its scope would have been
`/static/*`, not the app it exists to cache — and its precache list named six
paths that no longer resolved, which `addAll` discards atomically.

`_PUBLIC_PATHS` had listed `/manifest.webmanifest`, `/sw.js` and `/favicon.ico`
at the root the whole time, so the auth layer already believed in routes that
did not exist. These tests pin the three facts that make it real.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from interface.server import app, _PUBLIC_PATHS

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "interface" / "static"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_every_public_root_path_is_actually_served(client):
    """The auth layer exempted these from authentication. Nothing served them,
    so the exemption described routes that returned 404."""
    for path in sorted(_PUBLIC_PATHS):
        response = client.get(path)
        assert response.status_code == 200, f"{path} -> {response.status_code}"


def test_the_worker_is_allowed_the_scope_it_needs(client):
    """A worker's scope is capped by the directory it is served from unless the
    response says otherwise — the reason /static/sw.js could never have worked."""
    response = client.get("/sw.js")
    assert response.headers.get("service-worker-allowed") == "/"
    assert "javascript" in response.headers["content-type"]
    # A cached worker cannot ship its own replacement.
    assert "no-cache" in response.headers.get("cache-control", "")


def test_the_manifest_declares_the_scope_the_server_grants(client):
    manifest = client.get("/manifest.webmanifest").json()
    assert manifest["scope"] == "/"
    assert manifest["start_url"] == "/app"
    for icon in manifest["icons"]:
        assert client.get(icon["src"]).status_code == 200, icon["src"]


def test_the_page_asks_for_the_worker():
    """The registration call, in the built bundle rather than only in source —
    editing main.ts without rebuilding leaves the served app unchanged."""
    built = sorted((STATIC / "app-dist" / "assets").glob("index-*.js"))
    assert built, "no built bundle"
    assert any("serviceWorker" in b.read_text(encoding="utf-8", errors="ignore")
               for b in built), "the bundle never registers the worker"

    index = (STATIC / "app-dist" / "index.html").read_text(encoding="utf-8")
    assert 'rel="manifest"' in index, "the app is not installable without this"


def test_everything_the_worker_precaches_resolves(client):
    """`addAll` is atomic: one 404 in this list discards the entire precache,
    which is exactly how the cache came to be empty while looking populated."""
    source = (STATIC / "sw.js").read_text(encoding="utf-8")
    block = re.search(r"const SHELL = \[(.*?)\]", source, re.S)
    assert block, "SHELL list not found"
    shell = re.findall(r"'([^']+)'", block.group(1))
    assert shell, "SHELL is empty"

    for path in shell:
        assert client.get(path).status_code == 200, f"precached {path} is a 404"


def test_the_offline_fallback_is_not_offered_to_assets():
    """Handing index.html to an uncached script is worse than the network error
    it replaces: the browser gets text/html where it asked for JavaScript."""
    source = (STATIC / "sw.js").read_text(encoding="utf-8")
    assert "e.request.mode === 'navigate'" in source
