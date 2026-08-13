"""urlscan.io — what a page actually *did* when somebody loaded it.

Every other source in DEEP's catalog describes an indicator from the outside:
who owns the address, which CVEs affect the product, whether a blocklist names
it. urlscan is the only one that reports observed behaviour — the redirect
chain a URL took, the resources it pulled, the servers it contacted, and how
old and how popular the domain serving it actually is.

Search is keyless, which is why this is worth having: it works on a fresh clone.

Two correctness rules here are not obvious, and both were established by
`blackhole8080-darkmatter/urlscan-mcp` against the live API rather than from
the documentation:

**Match both the submitted URL and the final page.** urlscan records what was
submitted under ``task.*`` and where the scan actually landed under ``page.*``.
Querying ``page.domain`` alone returns *zero* hits for a domain that redirects
away — and redirecting away is exactly what link shorteners, phishing
redirectors and traffic distribution systems do. Verified: ``page.domain:
lzphy.top`` finds nothing while ``task.domain:lzphy.top`` finds the scan,
because the page redirected to github.com. Reporting "never seen" for an
indicator that has been scanned turns a gap in the query into an apparent
absence of findings.

**Then do not read reputation off a redirected scan.** Its ``page.*`` fields
describe the *destination*, so apex-domain age and Umbrella rank belong to
whoever it redirected to. lzphy.top inherited github.com's 13-year age and
rank 1508 — which then suppressed the "no established traffic" signal that
should have fired. Reputation is therefore derived only from scans that landed
on the indicator itself, and scans that redirected away are reported
separately.

**A missing verdict is not a clean verdict.** The search API returns no verdict
data on the free tier, key or not. Treating that absence as "no findings" would
report every malicious indicator on earth as safe, so nothing here infers
safety from silence — the observable signals (domain age, popularity rank,
submitter tags) are used instead, and their absence is stated.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

SEARCH_URL = "https://urlscan.io/api/v1/search/"

#: Lucene syntax that would otherwise change a query's meaning. A colon or a
#: quote inside an indicator must be data, not structure.
_RESERVED = r'+-=&|><!(){}[]^"~*?:\/'

#: Scans older than this tell you little about an indicator's current state.
DEFAULT_DAYS = 180


def escape(value: str) -> str:
    """Neutralise query syntax so an indicator cannot rewrite the query."""
    return "".join(f"\\{c}" if c in _RESERVED else c for c in str(value))


def submitted_or_final(field: str, value: str) -> str:
    """Match what was submitted *and* where the scan landed. See module docstring."""
    rendered = escape(value)
    return f"(page.{field}:{rendered} OR task.{field}:{rendered})"


def search_query(kind: str, value: str, days: Optional[int] = DEFAULT_DAYS) -> str:
    """Build the search query for one indicator kind."""
    if kind == "domain":
        base = submitted_or_final("domain", value)
    elif kind == "ip":
        # An address is where a scan landed; it is never "submitted", so there
        # is no task.ip field to widen to.
        base = f"page.ip:{escape(value)}"
    elif kind == "hash":
        base = f"hash:{escape(value)}"
    else:
        raise ValueError(f"urlscan lookup does not cover {kind!r}")
    window = f" AND date:>now-{int(days)}d" if days and days > 0 else ""
    return base + window


def _apex_matches(hit_domain: str, indicator: str) -> bool:
    """True when a scan landed on the indicator itself, or a subdomain of it."""
    domain = (hit_domain or "").lower().rstrip(".")
    target = (indicator or "").lower().rstrip(".")
    if not domain or not target:
        return False
    # Suffix comparison alone matches `evil-example.com` against `example.com`,
    # so the boundary has to be a label separator.
    return domain == target or domain.endswith("." + target)


def partition(hits: List[Dict[str, Any]], kind: str, value: str) -> Tuple[list, list]:
    """Split hits into those that landed on the indicator and those that left.

    Only meaningful for domain lookups — an IP or resource-hash query cannot
    match via a redirect in the first place, so everything counts as landed.
    """
    if kind != "domain":
        return list(hits), []
    landed, redirected = [], []
    for hit in hits:
        page = hit.get("page") or {}
        (landed if _apex_matches(page.get("domain", ""), value) else redirected).append(
            hit
        )
    return landed, redirected


def summarise(hits: List[Dict[str, Any]], kind: str, value: str) -> Dict[str, Any]:
    """Turn raw search hits into an attributable picture of the indicator."""
    landed, redirected = partition(hits, kind, value)

    ages: List[int] = []
    ranks: List[int] = []
    tags: List[str] = []
    countries: List[str] = []
    destinations: List[str] = []

    for hit in landed:
        page = hit.get("page") or {}
        task = hit.get("task") or {}
        age = page.get("apexDomainAgeDays")
        if isinstance(age, int):
            ages.append(age)
        rank = page.get("umbrellaRank")
        if isinstance(rank, int):
            ranks.append(rank)
        if page.get("country"):
            countries.append(str(page["country"]))
        tags.extend(str(t).lower() for t in (task.get("tags") or []))

    for hit in redirected:
        destination = (hit.get("page") or {}).get("domain")
        if destination and destination not in destinations:
            destinations.append(str(destination))

    return {
        "scans_found": len(hits),
        "scans_landed": len(landed),
        "scans_redirected_away": len(redirected),
        "redirect_destinations": destinations[:10],
        "min_apex_domain_age_days": min(ages) if ages else None,
        "best_umbrella_rank": min(ranks) if ranks else None,
        "ranked_in_umbrella": bool(ranks),
        "countries": sorted(set(countries))[:10],
        "tags": sorted(set(tags))[:12],
        # Never populated by the free-tier search API. Stated so that no caller
        # — human or model — reads the absence as an all-clear.
        "verdicts_available": False,
        "reputation_attributable": bool(landed),
    }


def risk_signals(summary: Dict[str, Any]) -> List[str]:
    """Observable signals, available even when no verdict is.

    Domain age and popularity catch freshly-registered phishing that no verdict
    engine has scored yet — which is most of it, at the point it matters.
    """
    signals: List[str] = []
    if not summary.get("reputation_attributable"):
        # Every scan redirected away, so nothing observed describes *this*
        # indicator. Saying so beats crediting it with a stranger's reputation.
        if summary.get("scans_redirected_away"):
            where = ", ".join(summary.get("redirect_destinations") or ["elsewhere"])
            signals.append(
                f"All {summary['scans_redirected_away']} scan(s) redirected away "
                f"to {where} — no reputation can be attributed to this indicator."
            )
        return signals

    age = summary.get("min_apex_domain_age_days")
    if isinstance(age, int):
        if age < 30:
            signals.append(
                f"Apex domain is very young ({age} days) — common in phishing."
            )
        elif age < 180:
            signals.append(f"Apex domain is relatively new ({age} days).")
    if not summary.get("ranked_in_umbrella"):
        signals.append(
            "Not in the Umbrella popularity ranking — no established traffic."
        )
    for marker in ("phishing", "malicious", "malware", "credential", "scam"):
        if any(marker in tag for tag in summary.get("tags", [])):
            signals.append(f"Submitters tagged scans with '{marker}'.")
            break
    if summary.get("scans_redirected_away"):
        signals.append(
            f"{summary['scans_redirected_away']} scan(s) redirected away "
            f"({', '.join(summary.get('redirect_destinations') or [])}) — "
            "behaves like a redirector."
        )
    return signals
