"""DEEP API routers.

Cohesive, single-service endpoint groups extracted from the former
`server.py` monolith. Each module exposes a `router` (FastAPI APIRouter) that
server.py mounts via `app.include_router(...)`.
"""

from interface.routers import (
    research, predictive, evolution, knowledge_graph, threat, workspace, reference, system, security,
    etis, finance, email, missions,
)

ROUTERS = [
    research.router,
    predictive.router,
    evolution.router,
    knowledge_graph.router,
    threat.router,
    workspace.router,
    reference.router,
    system.router,
    security.router,
    etis.router,
    finance.router,
    email.router,
    missions.router,
]

__all__ = ["ROUTERS"]

