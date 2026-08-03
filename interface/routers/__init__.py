"""DEEP API routers.

Cohesive, single-service endpoint groups extracted from the former
`server.py` monolith. Each module exposes a `router` (FastAPI APIRouter) that
server.py mounts via `app.include_router(...)`.
"""

from interface.routers import (
    predictive, evolution, knowledge_graph, threat, workspace, reference, security,
    etis, knowledge, state, network, audit, anomaly, security_timeline,
)

ROUTERS = [
    predictive.router,
    evolution.router,
    knowledge_graph.router,
    threat.router,
    workspace.router,
    reference.router,
    security.router,
    etis.router,
    knowledge.router,
    knowledge.docs_router,
    state.router,
    network.router,
    audit.router,
    anomaly.router,
    security_timeline.router,
]

from interface.ws import router as ws_router
ROUTERS.append(ws_router.router)

__all__ = ["ROUTERS"]

