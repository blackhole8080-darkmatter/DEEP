"""One place the server's address is written down.

The port drifted once already and took four features with it. It moved to 5174
while `network/remote_access.py` handed out Tailscale URLs on 7768, the Windows
client's defaults pointed at 7768, `core/tools/legacy.py` posted the approvals
queue's own security actions to 7768, and `mcp_server/deep_mcp.py` bridged
DEEP's tools to 7768. Every one of them connected to nothing, and each failed
quietly in a different way.

These tests are about the shape that allowed it: a value written out at every
call site drifts, a value derived from one setting cannot. So they assert on
*where the number lives* rather than on what it currently is — 5174 is not the
point, and changing it should not break them.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from core.config import Settings

ROOT = Path(__file__).resolve().parent.parent


def test_the_address_comes_from_one_setting():
    settings = Settings()
    assert settings.base_url() == f"http://{settings.deep_host}:{settings.deep_port}"
    assert settings.ws_url() == f"ws://{settings.deep_host}:{settings.deep_port}/ws/deep"


def test_a_remote_host_keeps_the_configured_port():
    """Remote access substitutes the host and nothing else — the bug was a
    correct Tailscale address carrying a port nobody was listening on."""
    settings = Settings()
    assert settings.base_url("100.64.0.1") == f"http://100.64.0.1:{settings.deep_port}"
    assert settings.ws_url(host="100.64.0.1") == f"ws://100.64.0.1:{settings.deep_port}/ws/deep"


def test_moving_the_port_moves_every_derived_url():
    """The property the old shape lacked: one change, everything follows.

    Run in a subprocess because `Settings` reads the environment into dataclass
    defaults at import, so an override has to be in place before `core.config`
    is imported — which is how it is actually used (a shell export, or `.env`
    loaded at startup), and not something monkeypatch can reproduce in-process.
    """
    import subprocess
    import sys

    env = {**os.environ, "DEEP_PORT": "9999", "DEEP_HOST": "0.0.0.0"}
    proof = subprocess.run(
        [sys.executable, "-c",
         "from core.config import Settings as S; s = S();"
         "print(s.base_url()); print(s.ws_url()); print(s.base_url('100.64.0.1'))"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    assert proof.returncode == 0, proof.stderr
    base, socket_url, remote = proof.stdout.strip().splitlines()[-3:]
    assert base == "http://0.0.0.0:9999"
    assert socket_url == "ws://0.0.0.0:9999/ws/deep"
    assert remote == "http://100.64.0.1:9999"


#: The dead port may still be *named* in a comment explaining the drift — that
#: is the record of why this file exists. It may not appear in code. The
#: distinction is drawn per line rather than per file, because a file-level
#: exemption would let any module that documents the bug quietly reintroduce it,
#: which is exactly what the first version of this test allowed.
_PROSE_FILES = {
    # A module docstring recording what these tests used to do.
    "tests/test_etis_domains.py",
    # This file, which names the port throughout.
    "tests/test_server_address.py",
}

_SEARCHED = ("*.py", "*.json", "*.bat", "*.cs")
_SKIP_DIRS = {".git", "node_modules", "app-dist", "__pycache__", "archive", ".venv"}


def _searchable_files():
    for pattern in _SEARCHED:
        for path in ROOT.rglob(pattern):
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            if path.name in {"world.json", "package-lock.json"}:
                continue
            yield path


#: Comment syntax per file type. `//` belongs to C# alone here — treating it as
#: universal is what broke the first version of this guard: `http://host:7768`
#: contains `//`, so every URL looked like a comment and the check passed while
#: the bug sat in plain sight.
_COMMENT_MARKERS = {
    ".py": ("#",),
    ".cs": ("//",),
    ".bat": ("REM", "rem", "::"),
    ".json": (),  # JSON has no comments; a mention there is data.
}


def _is_comment(line: str, suffix: str) -> bool:
    markers = _COMMENT_MARKERS.get(suffix, ())
    if not markers:
        return False
    stripped = line.strip()
    if stripped.startswith(markers):
        return True
    # A trailing comment: the mention sits after a marker that is not itself
    # part of a URL scheme.
    for marker in markers:
        index = 0
        while (index := line.find(marker, index)) != -1:
            if marker == "//" and index and line[index - 1] == ":":
                index += len(marker)
                continue
            if re.search(r"\b7768\b", line[index:]) and not re.search(
                r"\b7768\b", line[:index]
            ):
                return True
            index += len(marker)
    return False


def test_the_dead_port_is_gone_from_live_code():
    """7768 is bound by nothing. Any surviving reference in code is a broken
    caller; a mention in a comment is the explanation of why."""
    offenders = []
    for path in _searchable_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in _PROSE_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if re.search(r"\b7768\b", line) and not _is_comment(line, path.suffix):
                offenders.append(f"{rel}:{number}: {line.strip()}")
    assert not offenders, "the dead port is still in code:\n" + "\n".join(offenders)


def test_the_windows_client_points_at_the_server():
    """It is a separate codebase that cannot import Settings, so its defaults
    are checked against them instead of left to drift."""
    settings = Settings()
    config = json.loads((ROOT / "windows_client" / "config.json").read_text())
    for key in ("deep_ws_url", "deep_hud_url", "deep_api_url"):
        assert f":{settings.deep_port}" in config[key], f"{key} is {config[key]!r}"


def test_the_server_binds_what_settings_say():
    """Read as text: importing interface.server starts the whole application."""
    source = (ROOT / "interface" / "server.py").read_text(encoding="utf-8")
    assert "uvicorn.run(app, host=settings.deep_host, port=settings.deep_port" in source
    assert not re.search(r"uvicorn\.run\([^)]*port=\d", source), "a literal port is back"
