"""core/integrations/vision.py — screen capture for DEEP's vision."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime

_SHOT_DIR = "data/screenshots"


class VisionIntegration:
    async def take_screenshot(self) -> str:
        """Capture the primary screen to a PNG and return its path."""
        def _grab():
            from PIL import ImageGrab
            os.makedirs(_SHOT_DIR, exist_ok=True)
            path = os.path.join(_SHOT_DIR, f"shot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            img = ImageGrab.grab()
            img.save(path)
            return path
        try:
            return await asyncio.to_thread(_grab)
        except Exception as e:
            return f"Screenshot failed: {e}"
