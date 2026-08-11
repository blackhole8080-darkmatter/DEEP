"""Shared service registry for DEEP API routers.

`interface/server.py` builds every service instance at import time and then
registers the ones routers need here via :func:`register`. Router modules import
this registry instead of `server.py`, which keeps the dependency arrow
one-directional (server -> routers -> deps) and avoids a circular import.

so registration order between server.py and router import does not matter.
"""

from types import SimpleNamespace
from typing import Any

from fastapi import HTTPException

# Populated by server.py at startup. Routers reference attributes at call time.
services = SimpleNamespace()


def register(**kwargs) -> None:
    """Attach one or more shared service instances to the registry."""
    for key, value in kwargs.items():
        setattr(services, key, value)


def require(name: str) -> Any:
    """Fetch a registered service, or 503 if that subsystem isn't running.

    Routers reach for `services.<name>` at call time, and a subsystem whose
    `start()` failed is simply never registered. Reaching through that
    unregistered attribute raises AttributeError, which is a bug's shape, not a
    fact's — the fact is that the subsystem is down. 503 says so; a 500 would
    send an operator hunting for a defect that isn't there.
    """
    service = getattr(services, name, None)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail=f"{name} is not available — that subsystem is not running",
        )
    return service
