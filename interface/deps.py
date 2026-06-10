"""Shared service registry for DEEP API routers.

`interface/server.py` builds every service instance at import time and then
registers the ones routers need here via :func:`register`. Router modules import
this registry instead of `server.py`, which keeps the dependency arrow
one-directional (server -> routers -> deps) and avoids a circular import.

Each router reads its service lazily at request time (``services.research_engine``)
so registration order between server.py and router import does not matter.
"""

from types import SimpleNamespace

# Populated by server.py at startup. Routers reference attributes at call time.
services = SimpleNamespace()


def register(**kwargs) -> None:
    """Attach one or more shared service instances to the registry."""
    for key, value in kwargs.items():
        setattr(services, key, value)
