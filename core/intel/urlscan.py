"""urlscan.io as a DEEP intelligence source.

urlscan.io fills a hole nothing else in the catalog covers. Every other source
answers questions *about* an indicator — who announces it, what ports it has,
whether a CVE affecting it is exploited. urlscan answers what a browser
actually *saw* when it loaded the page: the redirect chain, the final
destination, the certificate, the domain's age, whether anyone has tagged it
phishing. For the indicator type DEEP could not previously investigate at all
— a URL — that is the whole investigation.

**Why this module is thin.** The analysis worth trusting here is not the API
call, it is the two rules about how to read the response, and both are easy to
get quietly wrong:

* The free search tier returns *no verdict data at all*. Code that reads a
  missing verdict as "clean" reports every malicious indicator as safe.
* urlscan records the submitted URL under ``task.*`` and the post-redirect page
  under ``page.*``. Matching only ``page.*`` misses every redirector; matching
  both and then reading reputation off ``page.*`` credits the redirector with
  its destination's reputation — a day-old throwaway domain inherits
  github.com's 13-year age and top-1500 rank.

Those rules are implemented, tested and documented in the ``urlscan-mcp``
package, which DEEP also runs as an MCP server (see ``core/mcp/``). Rather than
reimplement them — and drift — this module imports the pure analysis from
there and supplies only the transport: DEEP's own :class:`IntelHTTP`, so
urlscan gets the same caching, per-host throttling, stale-fallback and failure
isolation as every other catalogued source.

If the package is not installed, :func:`available` returns False and callers
report urlscan as unconfigured with an install hint, exactly like a source
missing an API key. Nothing here raises on a missing dependency.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from core.intel.http import Fetch, IntelHTTP, shared_http

logger = logging.getLogger(__name__)

SEARCH_URL = "https://urlscan.io/api/v1/search/"
SCAN_URL = "https://urlscan.io/api/v1/scan/"
API_KEY_ENV = "URLSCAN_API_KEY"

INSTALL_HINT = (
    "urlscan intelligence needs the urlscan-mcp package: pip install urlscan-mcp "
    "(or pip install -r requirements.txt). Search works without an API key; set "
    f"{API_KEY_ENV} to also submit live scans."
)

try:  # The pure analysis. Imports no `mcp` and performs no I/O.
    from urlscan_mcp import assess as _assess
    from urlscan_mcp import query as _query
    from urlscan_mcp.shaping import summarize_result, summarize_search_hit

    _AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without the package
    _assess = _query = None  # type: ignore[assignment]
    summarize_result = summarize_search_hit = None  # type: ignore[assignment]
    _AVAILABLE = False


def available() -> bool:
    """True when the urlscan analysis package is importable."""
    return _AVAILABLE


def has_api_key() -> bool:
    """True when live scan submission is possible. Search never needs a key."""
    return bool(os.environ.get(API_KEY_ENV))


def classify(indicator: str) -> Optional[str]:
    """``domain``, ``ip``, ``url``, ``hash`` — or None when urlscan can't help."""
    if not _AVAILABLE:
        return None
    classified = _query.classify(indicator)
    return classified[0] if classified else None


class UrlscanSource:
    """Search and assessment over urlscan.io, on DEEP's HTTP stack."""

    #: Scans do not change once written, and the corpus moves slowly. An hour
    #: keeps a pivot-heavy investigation off the free tier's rate limit.
    TTL_SECONDS = 3600

    #: The search API caps a page at 100 hits, which is also what the
    #: assessment reads. Asking for more silently returns 100.
    MAX_SIZE = 100

    def __init__(self, http: Optional[IntelHTTP] = None) -> None:
        self._http = http or shared_http()

    # ── raw search ───────────────────────────────────────────────────────────

    async def search(self, query: str, size: int = 20) -> Fetch:
        """Run an ElasticSearch query string against the scan corpus."""
        size = max(1, min(int(size), self.MAX_SIZE))
        url = f"{SEARCH_URL}?q={quote(query, safe='')}&size={size}"
        return await self._http.get_json(url, ttl=self.TTL_SECONDS)

    async def search_hits(self, query: str, size: int = 20) -> tuple[List[Dict[str, Any]], Fetch]:
        """Search, returning hits already shaped down from megabytes to rows."""
        fetch = await self.search(query, size)
        if not fetch.ok or not isinstance(fetch.data, dict):
            return [], fetch
        raw = fetch.data.get("results") or []
        return [summarize_search_hit(h) for h in raw if isinstance(h, dict)], fetch

    # ── assessment ───────────────────────────────────────────────────────────

    async def assess(self, indicator: str, days: int = 180) -> Dict[str, Any]:
        """Aggregate recent scans of an indicator into one reputation picture.

        Returns the same structure ``urlscan-mcp``'s ``assess_indicator`` tool
        returns, because it is the same function — see the module docstring.
        An ``error`` key means the lookup could not be performed; it never
        means the indicator is clean.
        """
        if not _AVAILABLE:
            return {"error": INSTALL_HINT}

        classified = _query.classify(indicator)
        if classified is None:
            return {
                "error": f"urlscan cannot classify {indicator!r}. It handles "
                         "domains, IPs, URLs and SHA-256 hashes."
            }
        kind, base_query = classified
        query = base_query + (_query.time_filter(days) if kind != "hash" else "")

        hits, fetch = await self.search_hits(query, size=self.MAX_SIZE)
        if not fetch.ok:
            return {"error": f"urlscan.io search failed: {fetch.error}"}

        report = _assess.build_assessment(
            indicator,
            kind,
            hits,
            days=days,
            total_matching=(fetch.data or {}).get("total"),
        )
        if fetch.stale:
            report["freshness"] = (
                f"Served from DEEP's cache, {int(fetch.stale_age_s)}s old — "
                "urlscan.io was unreachable on this attempt."
            )
        return report

    # ── live submission ──────────────────────────────────────────────────────

    async def submit(
        self, url: str, *, visibility: str = "public", tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Submit a URL for a fresh scan. Requires an API key.

        Submission is the one urlscan operation with a side effect a user would
        care about: a public scan is permanently visible on urlscan.io, and its
        submitter is disclosed to the site owner via the referring scan. DEEP
        defaults to ``public`` because that is urlscan's own default and free
        keys cannot use anything else, but the caller is told which visibility
        was used so it can say so.
        """
        if not has_api_key():
            return {
                "error": "Submitting a scan needs a urlscan.io API key. Set "
                         f"{API_KEY_ENV} (free at https://urlscan.io/user/signup). "
                         "Searching the existing corpus works without one."
            }
        payload: Dict[str, Any] = {"url": url, "visibility": visibility}
        if tags:
            payload["tags"] = list(tags)[:10]

        fetch = await self._http.post_json(
            SCAN_URL,
            payload,
            headers={"API-Key": os.environ[API_KEY_ENV], "Content-Type": "application/json"},
            ttl=0,
        )
        if not fetch.ok:
            return {"error": f"urlscan.io rejected the submission: {fetch.error}"}
        data = fetch.data if isinstance(fetch.data, dict) else {}
        return {
            "uuid": data.get("uuid"),
            "result_url": data.get("api"),
            "report_url": data.get("result"),
            "visibility": data.get("visibility", visibility),
            "note": "The scan takes 10-30s. Fetch the result with the uuid once it finishes.",
        }

    async def result(self, uuid: str, *, full: bool = False) -> Dict[str, Any]:
        """Fetch a finished scan by UUID, summarised unless ``full``.

        Needs an API key: the result endpoint returns 403 without one, despite
        what the public docs imply.
        """
        if not _AVAILABLE:
            return {"error": INSTALL_HINT}
        headers = {"API-Key": os.environ[API_KEY_ENV]} if has_api_key() else None
        fetch = await self._http.get_json(
            f"https://urlscan.io/api/v1/result/{quote(uuid, safe='')}/",
            headers=headers,
            ttl=self.TTL_SECONDS,
        )
        if not fetch.ok:
            if fetch.status == 404:
                return {"uuid": uuid, "status": "pending",
                        "note": "Not found yet — a fresh scan is probably still running."}
            if fetch.status in (401, 403):
                return {"uuid": uuid,
                        "error": "urlscan.io refused the result document. Reading results "
                                 f"requires {API_KEY_ENV}; searching does not."}
            return {"uuid": uuid, "error": f"urlscan.io result fetch failed: {fetch.error}"}
        data = fetch.data if isinstance(fetch.data, dict) else {}
        return data if full else summarize_result(data)


_shared: Optional[UrlscanSource] = None


def shared_urlscan() -> UrlscanSource:
    """Process-wide source, sharing DEEP's HTTP session and cache."""
    global _shared
    if _shared is None:
        _shared = UrlscanSource()
    return _shared
