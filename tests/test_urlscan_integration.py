"""Tests for the urlscan.io integration.

Two things are being defended here, and they are the two ways a URL-reputation
integration goes quietly wrong:

* **A missing verdict must never read as a clean one.** urlscan's free search
  tier returns no verdict data at all. A dossier that stayed silent about that
  would let the model infer safety from an absence of findings.
* **A redirector must not inherit its destination's reputation.** urlscan
  records the submitted URL under ``task.*`` and the post-redirect page under
  ``page.*``; reading age and popularity off the latter reports a day-old
  throwaway domain as a decade-old top-ranked site.

Everything runs offline: the transport is faked at DEEP's :class:`IntelHTTP`
boundary, so the assessment logic itself — imported from ``urlscan-mcp`` — is
exercised for real.
"""
from __future__ import annotations

import pytest

from core.intel import public_apis
from core.intel.http import Fetch
from core.intel.osint_investigator import Indicator, OSINTInvestigator
from core.intel.urlscan import UrlscanSource

urlscan_mcp = pytest.importorskip(
    "urlscan_mcp", reason="urlscan intelligence needs the urlscan-mcp package"
)


class FakeHTTP:
    """Matches a URL substring to a canned payload. Mirrors test_intel_layer."""

    def __init__(self, routes: dict[str, object], fail: set[str] | None = None) -> None:
        self.routes = routes
        self.fail = fail or set()
        self.calls: list[str] = []

    def _resolve(self, url: str) -> Fetch:
        self.calls.append(url)
        for fragment in self.fail:
            if fragment in url:
                return Fetch(ok=False, error="simulated upstream failure", status=503)
        for fragment, payload in self.routes.items():
            if fragment in url:
                return Fetch(ok=True, data=payload, status=200)
        return Fetch(ok=False, error="no route", status=404)

    async def get_json(self, url, *, headers=None, ttl=None):
        return self._resolve(url)

    async def get_text(self, url, *, headers=None, ttl=None):
        return self._resolve(url)

    async def post_json(self, url, payload, *, headers=None, ttl=None):
        return self._resolve(url)


def _hit(**overrides):
    """One urlscan search hit, in the API's own (unshaped) schema."""
    hit = {
        "_id": "uuid-1",
        "task": {"url": "https://evil.test/login", "time": "2026-01-01T00:00:00Z", "tags": []},
        "page": {
            "url": "https://evil.test/login",
            "domain": "evil.test",
            "apexDomain": "evil.test",
            "country": "US",
            "asnname": "EXAMPLE-AS",
            "apexDomainAgeDays": 4000,
            "umbrellaRank": 900,
        },
        "stats": {},
    }
    for key, value in overrides.items():
        if key in ("task", "page", "verdicts", "stats"):
            hit.setdefault(key, {})
            hit[key] = {**hit.get(key, {}), **value}
        else:
            hit[key] = value
    return hit


def _search(*hits):
    return {"results": list(hits), "total": len(hits)}


def _findings(dossier, label):
    return [f for f in dossier.findings if f.label == label]


# ═══════════════════════════════════════════════════════════════════════════
# Classification — DEEP could not investigate a URL at all before this
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "target,expected",
    [
        ("https://evil.test/login", Indicator.URL),
        ("http://1.2.3.4/payload.bin", Indicator.URL),
        ("https://evil.test/a?b=c#d", Indicator.URL),
        ("evil.test", Indicator.DOMAIN),
        ("8.8.8.8", Indicator.IP),
        ("ftp://evil.test/x", None),
        ("https://", None),
    ],
)
def test_url_classification(target, expected):
    assert OSINTInvestigator.classify(target) is expected


def test_url_is_a_catalogued_indicator():
    ids = [api.id for api in public_apis.for_indicator(Indicator.URL)]
    assert "urlscan" in ids


def test_catalog_reports_why_a_source_is_unavailable():
    source = public_apis.get("urlscan_submit")
    assert source is not None
    if not source.configured:
        assert source.unavailable_reason


# ═══════════════════════════════════════════════════════════════════════════
# The two rules
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_absent_verdicts_are_reported_not_read_as_clean():
    http = FakeHTTP({"urlscan.io/api/v1/search": _search(_hit())})
    d = await OSINTInvestigator(http).investigate("https://evil.test/login")

    assert _findings(d, "verdicts_unavailable"), "the verdict gap must be stated"
    note = _findings(d, "verdicts_unavailable")[0].value
    assert "NOT a clean verdict" in note
    assert "scanned_malicious" not in d.signals


@pytest.mark.asyncio
async def test_malicious_verdicts_raise_the_risk_score():
    hit = _hit(verdicts={"overall": {"score": 90, "malicious": True}})
    http = FakeHTTP({"urlscan.io/api/v1/search": _search(hit)})
    d = await OSINTInvestigator(http).investigate("https://evil.test/login")

    assert "scanned_malicious" in d.signals
    assert d.risk_score >= 40
    assert d.risk in ("high", "critical")
    assert _findings(d, "malicious_verdicts")


@pytest.mark.asyncio
async def test_redirected_scans_do_not_lend_their_reputation():
    """The lzphy.top case: every scan bounced to github.com."""
    redirected = _hit(
        task={"url": "https://lzphy.top/", "time": "2026-01-01T00:00:00Z"},
        page={"domain": "github.com", "apexDomain": "github.com",
              "apexDomainAgeDays": 4700, "umbrellaRank": 1508},
    )
    http = FakeHTTP({"urlscan.io/api/v1/search": _search(redirected)})
    d = await OSINTInvestigator(http).investigate("lzphy.top")

    assert not _findings(d, "apex_domain_age_days"), "destination's age is not the indicator's"
    assert _findings(d, "reputation_unattributable")
    assert _findings(d, "redirects_away")
    assert "github.com" in _findings(d, "redirects_away")[0].value["destinations"]
    # And the good reputation it did not earn must not suppress the risk signal.
    assert "no_established_traffic" not in d.signals


@pytest.mark.asyncio
async def test_young_unranked_domain_is_flagged():
    hit = _hit(page={"apexDomainAgeDays": 6, "umbrellaRank": None})
    http = FakeHTTP({"urlscan.io/api/v1/search": _search(hit)})
    d = await OSINTInvestigator(http).investigate("https://evil.test/login")

    assert "very_young_domain" in d.signals
    assert "no_established_traffic" in d.signals
    assert _findings(d, "apex_domain_age_days")[0].severity == "high"


@pytest.mark.asyncio
async def test_no_scans_found_says_so_without_implying_safety():
    http = FakeHTTP({"urlscan.io/api/v1/search": _search()})
    d = await OSINTInvestigator(http).investigate("https://unknown.test/x")

    history = _findings(d, "scan_history")
    assert history and "not evidence of safety" in history[0].value
    assert d.risk != "clean" or not d.signals


# ═══════════════════════════════════════════════════════════════════════════
# Fan-out behaviour
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_url_dossier_also_investigates_the_host():
    http = FakeHTTP({
        "urlscan.io/api/v1/search": _search(_hit()),
        "cloudflare-dns.com": {"Answer": [{"data": "93.184.216.34"}]},
    })
    d = await OSINTInvestigator(http).investigate("https://evil.test/login")

    assert _findings(d, "hostname")[0].value == "evil.test"
    assert _findings(d, "a_records"), "the host must get the domain collector too"


@pytest.mark.asyncio
async def test_url_dossier_queries_urlscan_once():
    """The host lookup must not re-run the corpus and double-count the evidence."""
    http = FakeHTTP({"urlscan.io/api/v1/search": _search(_hit())})
    d = await OSINTInvestigator(http).investigate("https://evil.test/login")

    searches = [c for c in http.calls if "urlscan.io/api/v1/search" in c]
    assert len(searches) == 1
    assert d.sources_queried.count("urlscan") == 1


@pytest.mark.asyncio
async def test_urlscan_failure_degrades_rather_than_failing_the_dossier():
    http = FakeHTTP(
        {"cloudflare-dns.com": {"Answer": [{"data": "93.184.216.34"}]}},
        fail={"urlscan.io"},
    )
    d = await OSINTInvestigator(http).investigate("evil.test")

    assert "urlscan" in d.degraded
    assert _findings(d, "a_records"), "the rest of the report still renders"


@pytest.mark.asyncio
async def test_sha256_pivots_to_the_pages_serving_it():
    digest = "a" * 64
    hit = _hit(page={"domain": "cdn.evil.test", "apexDomain": "evil.test"})
    http = FakeHTTP({"urlscan.io/api/v1/search": _search(hit)})
    d = await OSINTInvestigator(http).investigate(digest)

    assert "urlscan" in d.sources_answered
    served = _findings(d, "served_by_domains")
    assert served and "cdn.evil.test" in served[0].value


@pytest.mark.asyncio
async def test_ip_lookup_includes_page_level_evidence():
    http = FakeHTTP({"urlscan.io/api/v1/search": _search(_hit())})
    d = await OSINTInvestigator(http).investigate("93.184.216.34")

    assert "urlscan" in d.sources_answered
    assert _findings(d, "scans_found")


# ═══════════════════════════════════════════════════════════════════════════
# The source adapter
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_submission_without_a_key_returns_an_error_not_an_exception(monkeypatch):
    monkeypatch.delenv("URLSCAN_API_KEY", raising=False)
    out = await UrlscanSource(FakeHTTP({})).submit("https://evil.test/")
    assert "API key" in out["error"]


@pytest.mark.asyncio
async def test_unclassifiable_indicator_is_refused_clearly():
    out = await UrlscanSource(FakeHTTP({})).assess("AS15169")
    assert "cannot classify" in out["error"]


@pytest.mark.asyncio
async def test_search_failure_is_an_error_not_an_empty_result():
    """An empty result set would read as 'never scanned' — a different claim."""
    out = await UrlscanSource(FakeHTTP({}, fail={"urlscan.io"})).assess("evil.test")
    assert "error" in out
    assert "scans_found" not in out


@pytest.mark.asyncio
async def test_stale_cache_is_labelled():
    class StaleHTTP(FakeHTTP):
        async def get_json(self, url, *, headers=None, ttl=None):
            fetch = self._resolve(url)
            fetch.stale = True
            fetch.stale_age_s = 900.0
            return fetch

    http = StaleHTTP({"urlscan.io/api/v1/search": _search(_hit())})
    out = await UrlscanSource(http).assess("evil.test")
    assert "cache" in out["freshness"]
