"""core/integrations — DEEP integration stubs."""

from __future__ import annotations

from typing import Any, Optional


class _DummyIntegrationManager:
    """Fallback integration manager when real integrations are unavailable."""

    p0_loaded: bool = False
    p1_loaded: bool = False

    def get(self, name: str) -> Optional[Any]:
        return None

    def __getitem__(self, name: str) -> Any:
        raise KeyError(name)

    def __contains__(self, name: str) -> bool:
        return False


integration_manager = _DummyIntegrationManager()
