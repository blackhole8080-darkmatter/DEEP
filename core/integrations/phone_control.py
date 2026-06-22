"""
core/integrations/phone_control.py

Phone Control for DEEP — let DEEP see and drive your mobile while it sits on a
stand/desk facing you.

Two backends behind one interface:

  • AndroidBackend  — full control via ADB (tap / swipe / type / key / launch app
                      / screencap). No root needed; just USB-debugging on.
  • IPhoneBackend   — iOS blocks programmatic touch injection on a stock device,
                      so "control" = trigger Siri Shortcuts over a webhook the
                      phone listens for. Seeing the screen is handled by DEEP's
                      existing vision tools on a mirrored frame.

ADB resolution order:
  1. $DEEP_ADB_PATH (explicit override)
  2. `adb` on PATH
  3. ASUS GlideX's bundled adb (ships on this machine)

The vision-guided loop is intentionally NOT baked in here — the brain already
owns vision (LLaVA). A typical autonomous step is:
    phone_screenshot -> (LLaVA reads UI) -> phone_tap/phone_text -> repeat
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Where captured phone frames land (under the project data dir).
_SCREEN_DIR = Path(__file__).resolve().parents[2] / "data" / "phone_frames"

# Common Android keyevent aliases so the LLM/user can say "back" not "KEYCODE_BACK".
_KEY_ALIASES = {
    "home": "KEYCODE_HOME",
    "back": "KEYCODE_BACK",
    "enter": "KEYCODE_ENTER",
    "menu": "KEYCODE_MENU",
    "power": "KEYCODE_POWER",
    "wake": "KEYCODE_WAKEUP",
    "sleep": "KEYCODE_SLEEP",
    "recents": "KEYCODE_APP_SWITCH",
    "appswitch": "KEYCODE_APP_SWITCH",
    "volup": "KEYCODE_VOLUME_UP",
    "voldown": "KEYCODE_VOLUME_DOWN",
    "mute": "KEYCODE_VOLUME_MUTE",
    "search": "KEYCODE_SEARCH",
    "tab": "KEYCODE_TAB",
    "del": "KEYCODE_DEL",
    "delete": "KEYCODE_DEL",
    "space": "KEYCODE_SPACE",
}

# Fallback location for ASUS GlideX's adb on Windows.
_GLIDEX_ADB = r"C:\Program Files\ASUS\GlideX\adb.exe"


def _resolve_adb() -> Optional[str]:
    """Find a usable adb binary. Returns its path or None."""
    override = os.getenv("DEEP_ADB_PATH")
    if override and Path(override).exists():
        return override
    found = shutil.which("adb")
    if found:
        return found
    if Path(_GLIDEX_ADB).exists():
        return _GLIDEX_ADB
    return None


class AndroidBackend:
    """ADB-driven control. Stateless wrapper around the adb CLI."""

    def __init__(self, adb_path: str, serial: Optional[str] = None):
        self.adb_path = adb_path
        # Optional device serial (for when several phones are attached).
        self.serial = serial or os.getenv("DEEP_ADB_SERIAL") or None

    async def _adb(self, *args: str, timeout: int = 30,
                   binary: bool = False) -> Tuple[int, bytes, bytes]:
        cmd = [self.adb_path]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += list(args)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return -1, b"", b"adb command timed out"
        return proc.returncode, out, err

    async def _shell(self, *args: str, timeout: int = 30) -> Tuple[int, str, str]:
        rc, out, err = await self._adb("shell", *args, timeout=timeout)
        return rc, out.decode("utf-8", "replace").strip(), err.decode("utf-8", "replace").strip()

    async def devices(self) -> List[dict]:
        rc, out, _ = await self._adb("devices", "-l")
        if rc != 0:
            return []
        devices = []
        for line in out.decode("utf-8", "replace").splitlines()[1:]:
            line = line.strip()
            if not line or "\t" not in line and " " not in line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                devices.append({"serial": parts[0], "state": parts[1],
                                "info": " ".join(parts[2:])})
        return devices

    async def connect(self, address: str) -> Tuple[bool, str]:
        """Connect to a wireless device, e.g. '192.168.1.42:5555'. Pins it as the
        active serial so subsequent taps/screens target the phone."""
        rc, out, err = await self._adb("connect", address, timeout=20)
        text = (out.decode("utf-8", "replace") + err.decode("utf-8", "replace")).strip()
        ok = rc == 0 and "connected" in text.lower() and "cannot" not in text.lower() \
            and "failed" not in text.lower()
        if ok:
            self.serial = address
        return ok, text or f"connect {address}"

    async def pair(self, address: str, code: str) -> Tuple[bool, str]:
        """Android 11+ wireless pairing (one-time). `address` is the host:port shown
        under Settings → Wireless debugging → Pair device with pairing code."""
        rc, out, err = await self._adb("pair", address, code, timeout=25)
        text = (out.decode("utf-8", "replace") + err.decode("utf-8", "replace")).strip()
        ok = rc == 0 and "success" in text.lower()
        return ok, text or f"pair {address}"

    async def tcpip(self, port: int = 5555) -> Tuple[bool, str]:
        """Switch a USB-attached device into wireless mode (Android <=10 path)."""
        rc, out, err = await self._adb("tcpip", str(port), timeout=20)
        text = (out.decode("utf-8", "replace") + err.decode("utf-8", "replace")).strip()
        return rc == 0, text or f"tcpip {port}"

    async def screenshot(self) -> Tuple[bool, str]:
        """Capture the phone screen to a PNG. Returns (ok, path_or_error)."""
        _SCREEN_DIR.mkdir(parents=True, exist_ok=True)
        path = _SCREEN_DIR / f"phone_{int(time.time() * 1000)}.png"
        # exec-out keeps the PNG bytes binary-clean (no CRLF mangling).
        rc, out, err = await self._adb("exec-out", "screencap", "-p", binary=True, timeout=30)
        if rc != 0 or not out:
            return False, f"screencap failed: {err.decode('utf-8','replace') or 'no output'}"
        try:
            path.write_bytes(out)
        except Exception as e:  # noqa: BLE001
            return False, f"could not write frame: {e}"
        return True, str(path)

    async def tap(self, x: int, y: int) -> Tuple[bool, str]:
        rc, _, err = await self._shell("input", "tap", str(x), str(y))
        return rc == 0, err or f"tapped ({x}, {y})"

    async def swipe(self, x1: int, y1: int, x2: int, y2: int,
                    duration_ms: int = 300) -> Tuple[bool, str]:
        rc, _, err = await self._shell(
            "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms))
        return rc == 0, err or f"swiped ({x1},{y1})->({x2},{y2})"

    async def text(self, value: str) -> Tuple[bool, str]:
        # adb input text needs spaces as %s and chokes on some punctuation.
        escaped = value.replace(" ", "%s")
        rc, _, err = await self._shell("input", "text", escaped)
        return rc == 0, err or f"typed {len(value)} chars"

    async def key(self, key: str) -> Tuple[bool, str]:
        code = _KEY_ALIASES.get(key.strip().lower(), key.strip())
        rc, _, err = await self._shell("input", "keyevent", code)
        return rc == 0, err or f"keyevent {code}"

    async def open_app(self, package: str) -> Tuple[bool, str]:
        # monkey is the most reliable no-activity-name launcher.
        rc, out, err = await self._shell(
            "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")
        ok = rc == 0 and "No activities found" not in (out + err)
        return ok, (out or err) if not ok else f"launched {package}"


class IPhoneBackend:
    """
    iOS: no raw touch injection on a stock device. We trigger Siri Shortcuts via
    a webhook the phone exposes (e.g. a Pushcut server, or a self-hosted relay the
    user runs a Shortcuts automation against). Configure DEEP_IPHONE_SHORTCUT_WEBHOOK.

    Seeing the iPhone screen is done with DEEP's normal vision tools pointed at a
    QuickTime/AirPlay mirror — not handled here.
    """

    def __init__(self):
        self.webhook = os.getenv("DEEP_IPHONE_SHORTCUT_WEBHOOK")

    async def run_shortcut(self, name: str, payload: str = "") -> Tuple[bool, str]:
        if not self.webhook:
            return False, ("No iPhone shortcut webhook configured. Set "
                           "DEEP_IPHONE_SHORTCUT_WEBHOOK to a URL your phone listens "
                           "on (Pushcut / a Shortcuts automation), then retry.")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=20) as c:
                r = await c.post(self.webhook, json={"shortcut": name, "input": payload})
            return r.status_code < 400, f"Triggered shortcut '{name}' (HTTP {r.status_code})."
        except Exception as e:  # noqa: BLE001
            return False, f"Failed to trigger shortcut '{name}': {e}"


class PhoneControl:
    """Unified phone-control facade used by the tool registry."""

    def __init__(self):
        self.adb_path = _resolve_adb()
        self.android = AndroidBackend(self.adb_path) if self.adb_path else None
        self.iphone = IPhoneBackend()

    # ─── status ──────────────────────────────────────────────────────────────

    async def status(self) -> str:
        lines = []
        if not self.adb_path:
            lines.append("Android: adb NOT found. Install platform-tools or set "
                         "DEEP_ADB_PATH. (ASUS GlideX bundles one if installed.)")
        else:
            devs = await self.android.devices()
            ready = [d for d in devs if d["state"] == "device"]
            if not devs:
                lines.append(f"Android: adb OK ({self.adb_path}), but NO device "
                             "connected. Plug in via USB with USB-debugging on, or "
                             "pair wirelessly (adb tcpip 5555).")
            elif not ready:
                lines.append(f"Android: device(s) seen but not authorised: "
                             f"{', '.join(d['serial']+'='+d['state'] for d in devs)}. "
                             "Accept the 'Allow USB debugging' prompt on the phone.")
            else:
                lines.append("Android: ready — " +
                             ", ".join(d["serial"] + " (" + d["info"] + ")" for d in ready))
        if self.iphone.webhook:
            lines.append(f"iPhone: shortcut webhook configured ({self.iphone.webhook}).")
        else:
            lines.append("iPhone: command-only via Siri Shortcuts — set "
                         "DEEP_IPHONE_SHORTCUT_WEBHOOK to enable.")
        return "\n".join(lines)

    # ─── android passthroughs (with a friendly missing-adb guard) ──────────────

    def _need_android(self) -> Optional[str]:
        if not self.android:
            return ("No adb available. Install Android platform-tools or set "
                    "DEEP_ADB_PATH, then connect the phone.")
        return None
