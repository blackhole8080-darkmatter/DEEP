"""DEEP public-API intelligence layer.

Three pieces:

* :mod:`core.intel.public_apis` — the declarative catalog of upstream sources.
* :mod:`core.intel.http` — the shared async transport (cache, throttle, timeouts).
* :mod:`core.intel.osint_investigator` — the pivot engine that turns one
  indicator into an attributed dossier.
* :mod:`core.intel.live_stats` — rolled-up live cyber statistics and the geo
  intelligence map feed.
"""
from core.intel.http import Fetch, IntelHTTP, shared_http
from core.intel.osint_investigator import Dossier, Finding, OSINTInvestigator
from core.intel.public_apis import CATALOG, Auth, Category, Indicator, PublicAPI

__all__ = [
    "CATALOG",
    "Auth",
    "Category",
    "Dossier",
    "Fetch",
    "Finding",
    "Indicator",
    "IntelHTTP",
    "OSINTInvestigator",
    "PublicAPI",
    "shared_http",
]
