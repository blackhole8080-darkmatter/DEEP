"""
core/integrations/vision_llava.py — DEEP's eyes.

Real multimodal vision via a local LLaVA model served by Ollama (default
llava:13b). Fully local — images never leave the machine. Accepts an image file
path (or raw base64) and returns a natural-language analysis.
"""
from __future__ import annotations

import asyncio
import base64
import os

_OLLAMA = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
_MODEL = os.environ.get("VISION_MODEL", "llava:13b")


class _LlavaVision:
    def _to_b64(self, image: str) -> str | None:
        if not image:
            return None
        try:
            if os.path.exists(image):
                with open(image, "rb") as f:
                    return base64.b64encode(f.read()).decode("ascii")
        except Exception:
            return None
        # assume it's already base64 (strip a data-URL prefix if present)
        return image.split(",", 1)[-1] if "," in image[:40] else image

    async def _ask(self, image: str, prompt: str) -> str:
        b64 = self._to_b64(image)
        if not b64:
            return f"No image found at '{image}'."

        def _call():
            import requests
            r = requests.post(
                f"{_OLLAMA}/api/generate",
                json={"model": _MODEL, "prompt": prompt, "images": [b64], "stream": False},
                timeout=180,
            )
            r.raise_for_status()
            return (r.json().get("response") or "").strip()
        try:
            out = await asyncio.to_thread(_call)
            return out or "(vision model returned no description)"
        except Exception as e:
            return f"Vision analysis failed ({type(e).__name__}: {e}). Is Ollama running with {_MODEL}?"

    async def analyze_image(self, image_path: str, question: str = "Describe this image in detail.") -> str:
        return await self._ask(image_path, question)

    async def debug_ui(self, image_path: str) -> str:
        return await self._ask(image_path,
            "You are a senior UI/UX engineer. Analyze this interface screenshot: describe the layout "
            "and key elements, then identify any visual bugs — misalignment, overlap, low contrast, "
            "clipped or broken elements, inconsistent spacing — and give concrete fixes.")

    async def analyze_circuit(self, image_path: str) -> str:
        return await self._ask(image_path,
            "You are an electronics expert. Analyze this circuit or schematic: identify the visible "
            "components and how they connect, infer the circuit's purpose, and flag anything that looks wrong.")


llava_vision = _LlavaVision()
