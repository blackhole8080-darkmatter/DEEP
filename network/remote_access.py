"""
network/remote_access.py

Configures DEEP FastAPI to be safely reachable over Tailscale
from any device. Generates QR codes, persists access info, and
publishes events when remote access becomes available.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default path for remote access info JSON
_DEFAULT_INFO_PATH = Path("network/remote_access_info.json")
_DEFAULT_QR_PATH = Path("network/deep_qr.png")

# Ensure the network/ directory exists
_DEFAULT_INFO_PATH.parent.mkdir(parents=True, exist_ok=True)


class RemoteAccessManager:
    """
    Manages remote-access metadata when Tailscale connects.

    Lifecycle: __init__ -> start() -> ... -> stop() -> status()
    """

    def __init__(self, event_bus: Any, tailscale: Any) -> None:
        self._event_bus = event_bus
        self._tailscale = tailscale
        self._started = False
        self._info_path: Path = _DEFAULT_INFO_PATH
        self._qr_path: Path = _DEFAULT_QR_PATH

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Subscribe to tailscale_connected and prepare for remote access."""
        self._started = True
        self._event_bus.subscribe("tailscale_connected", self._on_tailscale_connected)
        logger.info("RemoteAccessManager started")

    async def stop(self) -> None:
        """Clean up subscriptions."""
        self._started = False
        # Note: EventBus unsubscribe is available per v1 API
        try:
            self._event_bus.unsubscribe("tailscale_connected", self._on_tailscale_connected)
        except Exception:
            pass
        logger.info("RemoteAccessManager stopped")

    def status(self) -> dict[str, Any]:
        """Return current operational status."""
        info_exists = self._info_path.exists()
        qr_exists = self._qr_path.exists()
        url: str | None = None
        if info_exists:
            try:
                with open(self._info_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                url = data.get("deep_url")
            except Exception:
                pass

        return {
            "accessible_remotely": info_exists and url is not None,
            "url": url,
            "qr_generated": qr_exists,
        }

    # ------------------------------------------------------------------
    # Event handler
    # ------------------------------------------------------------------

    async def _on_tailscale_connected(self, event_name: str, payload: dict) -> None:
        """Called when Tailscale connects."""
        await self._configure_remote_access()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    async def _configure_remote_access(self) -> None:
        """
        1. Get Tailscale IP
        2. Write remote_access_info.json
        3. Generate QR code for the DEEP URL
        4. Log and publish remote_access_ready
        """
        tailscale_ip = await self._tailscale.get_ip()
        if not tailscale_ip:
            logger.warning("Tailscale connected but no IP available — skipping remote access config")
            return

        deep_url = f"http://{tailscale_ip}:7768"
        ws_url = f"ws://{tailscale_ip}:7768/ws/deep"
        timestamp = datetime.now(timezone.utc).isoformat()

        info = {
            "tailscale_ip": tailscale_ip,
            "deep_url": deep_url,
            "ws_url": ws_url,
            "last_updated": timestamp,
        }

        # Persist JSON
        try:
            with open(self._info_path, "w", encoding="utf-8") as f:
                json.dump(info, f, indent=2)
        except Exception as exc:
            logger.error(f"Failed to write remote access info: {exc}")

        # Generate QR code
        try:
            import qrcode

            qr = qrcode.make(deep_url)
            qr.save(str(self._qr_path))
            logger.info(f"QR code saved to {self._qr_path}")
        except Exception as exc:
            logger.warning(f"QR code generation failed: {exc}")

        logger.info(f"DEEP reachable at {deep_url}")

        await self._event_bus.publish(
            "remote_access_ready",
            {
                "url": deep_url,
                "ws_url": ws_url,
                "tailscale_ip": tailscale_ip,
                "qr_path": str(self._qr_path),
            },
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_access_info(self) -> dict[str, Any]:
        """Return contents of remote_access_info.json or not_connected."""
        if not self._info_path.exists():
            return {"status": "not_connected"}

        try:
            with open(self._info_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.error(f"Failed to read remote access info: {exc}")
            return {"status": "not_connected", "error": str(exc)}
