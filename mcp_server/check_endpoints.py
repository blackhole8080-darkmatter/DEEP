#!/usr/bin/env python3
"""Verify every endpoint mcp_server/deep_mcp.py depends on is actually live.

Two bugs shipped because nothing checked this: the MCP server defaulted to port
7768 while the API bound 5174, and `deep_research` called
`/api/research/findings`, which does not exist. Both would have been caught the
first time this ran.

Usage:  python mcp_server/check_endpoints.py
Exit 0 if every endpoint answers, 1 otherwise.
"""
from __future__ import annotations

import asyncio
import os
import sys

import httpx

DEFAULT_PORT = os.environ.get("DEEP_PORT", "5174")
BASE = os.environ.get("DEEP_BASE_URL", f"http://localhost:{DEFAULT_PORT}").rstrip("/")

# (method, path, params) — every endpoint deep_mcp.py touches.
ENDPOINTS: list[tuple[str, str, dict]] = [
    ("GET", "/api/status", {}),
    ("GET", "/api/investigate", {"target": "1.1.1.1"}),
    ("GET", "/network/proximity", {}),
    ("GET", "/network/proximity/wifi", {}),
    ("GET", "/network/proximity/bt", {}),
    ("GET", "/api/knowledge/search", {"q": "test", "limit": 1}),
    ("GET", "/api/etis/intel/feed", {"days_back": 7}),
    ("GET", "/api/security/status", {}),
    ("GET", "/audit/stats", {}),
]

# POST endpoints are listed but not called — deep_remember writes to the
# knowledge graph, and a health check must not mutate state.
WRITE_ONLY = ["/api/knowledge/ingest"]


async def main() -> int:
    print(f"Checking DEEP endpoints at {BASE}\n")
    failures: list[str] = []

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            await client.get(f"{BASE}/api/status")
        except Exception as exc:
            print(f"  FAIL  cannot reach {BASE} — is DEEP running?  ({exc})")
            print(f"\nStart it with:  python interface/server.py")
            print(f"If it listens elsewhere, set DEEP_PORT or DEEP_BASE_URL.")
            return 1

        for method, path, params in ENDPOINTS:
            try:
                r = await client.request(method, f"{BASE}{path}", params=params)
                size = len(r.content)
                if r.status_code == 200:
                    flag = "  (large — shape this)" if size > 10_000 else ""
                    print(f"  ok    {path:<34} {r.status_code}  {size:>7,} B{flag}")
                else:
                    print(f"  FAIL  {path:<34} {r.status_code}")
                    failures.append(f"{path} -> HTTP {r.status_code}")
            except Exception as exc:
                print(f"  FAIL  {path:<34} {type(exc).__name__}")
                failures.append(f"{path} -> {exc}")

    for path in WRITE_ONLY:
        print(f"  skip  {path:<34} (write endpoint, not exercised)")

    if failures:
        print(f"\n{len(failures)} endpoint(s) broken:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"\nAll {len(ENDPOINTS)} endpoints healthy.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
