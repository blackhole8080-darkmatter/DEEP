"""urlscan.io as catalogued source 21.

Two rules here are not obvious, and both were established against the live API
by `blackhole8080-darkmatter/urlscan-mcp` rather than read out of the docs.
They are the whole reason this is a module and not three inline lines:

1. A domain lookup must match `task.*` as well as `page.*`, or every indicator
   that redirects away — which is what shorteners and phishing redirectors do —
   reads as "never scanned".
2. Having widened the query, reputation must NOT then be read off a redirected
   scan, whose `page.*` fields describe the destination. Doing so credits the
   indicator with a stranger's domain age and popularity rank.

Both failures produce a *reassuring* wrong answer, which is the dangerous
direction for a security console.
"""

from __future__ import annotations

import pytest

from core.intel import public_apis
from core.intel.urlscan import (
    escape,
    partition,
    risk_signals,
    search_query,
    submitted_or_final,
    summarise,
)


def _hit(domain, *, age=None, rank=None, tags=(), country="US"):
    return {
        "page": {
            "domain": domain,
            "apexDomainAgeDays": age,
            "umbrellaRank": rank,
            "country": country,
        },
        "task": {"tags": list(tags)},
    }


# ═══════════════════════════════════════════════════════════════════════════
# The catalog entry
# ═══════════════════════════════════════════════════════════════════════════


def test_urlscan_is_catalogued_and_keyless():
    api = public_apis.get("urlscan")
    assert api is not None
    assert api.configured is True, "search must work on a fresh clone"
    assert {i.value for i in api.indicators} == {"domain", "ip", "hash"}


def test_the_catalog_entry_warns_that_a_missing_verdict_is_not_clean():
    """`/api/intel/sources` renders this text; the caveat has to travel with it."""
    description = public_apis.get("urlscan").description.lower()
    assert "clean" in description and "no data" in description


@pytest.mark.parametrize("kind", ["domain", "ip", "hash"])
def test_urlscan_is_offered_for_each_indicator_it_covers(kind):
    from core.intel.public_apis import Indicator

    ids = {a.id for a in public_apis.for_indicator(Indicator(kind))}
    assert "urlscan" in ids


# ═══════════════════════════════════════════════════════════════════════════
# Rule 1 — match the submitted URL as well as the final page
# ═══════════════════════════════════════════════════════════════════════════


def test_a_domain_query_matches_both_submitted_and_final():
    """page.domain:lzphy.top returns 0 hits; task.domain:lzphy.top finds the
    scan, because the page redirected to github.com."""
    query = search_query("domain", "lzphy.top", days=None)
    assert "page.domain:lzphy.top" in query
    assert "task.domain:lzphy.top" in query
    assert " OR " in query


def test_an_ip_query_does_not_invent_a_task_field():
    """An address is where a scan landed — it is never the submitted value."""
    query = search_query("ip", "45.33.32.156", days=None)
    assert query == "page.ip:45.33.32.156"


def test_a_hash_query_uses_the_resource_hash_field():
    digest = "a" * 64
    assert search_query("hash", digest, days=None) == f"hash:{digest}"


def test_the_time_window_is_appended_when_asked():
    assert "date:>now-30d" in search_query("domain", "example.com", days=30)
    assert "date:" not in search_query("domain", "example.com", days=None)


def test_an_unsupported_indicator_is_refused_rather_than_guessed():
    with pytest.raises(ValueError):
        search_query("cve", "CVE-2021-44228")


def test_query_syntax_in_an_indicator_is_escaped():
    """Otherwise a colon or quote in a hostile indicator rewrites the query."""
    assert escape('evil.com" OR page.domain:*') == 'evil.com\\" OR page.domain\\:\\*'
    assert "\\:" in submitted_or_final("domain", "a:b")


# ═══════════════════════════════════════════════════════════════════════════
# Rule 2 — do not read reputation off a scan that landed somewhere else
# ═══════════════════════════════════════════════════════════════════════════


def test_a_redirected_scan_is_separated_from_one_that_landed():
    hits = [_hit("lzphy.top"), _hit("github.com")]
    landed, redirected = partition(hits, "domain", "lzphy.top")
    assert len(landed) == 1 and len(redirected) == 1
    assert redirected[0]["page"]["domain"] == "github.com"


def test_a_subdomain_counts_as_having_landed():
    landed, redirected = partition([_hit("login.example.com")], "domain", "example.com")
    assert len(landed) == 1 and not redirected


def test_a_lookalike_suffix_does_not_count_as_landed():
    """`evil-example.com` ends with `example.com` but is a different domain."""
    landed, redirected = partition([_hit("evil-example.com")], "domain", "example.com")
    assert not landed and len(redirected) == 1


def test_partition_is_case_insensitive():
    landed, _ = partition([_hit("EXAMPLE.com")], "domain", "example.COM")
    assert len(landed) == 1


def test_ip_and_hash_lookups_cannot_redirect_so_everything_landed():
    for kind in ("ip", "hash"):
        landed, redirected = partition([_hit("anything.test")], kind, "x")
        assert len(landed) == 1 and not redirected


def test_reputation_is_not_inherited_from_the_redirect_destination():
    """The exact failure: lzphy.top inherited github.com's 13-year age and
    rank 1508, which then suppressed the "no established traffic" signal."""
    hits = [_hit("github.com", age=4800, rank=1508)]  # redirected away
    summary = summarise(hits, "domain", "lzphy.top")

    assert summary["scans_landed"] == 0
    assert summary["scans_redirected_away"] == 1
    assert summary["min_apex_domain_age_days"] is None, "age belongs to github.com"
    assert summary["best_umbrella_rank"] is None
    assert summary["ranked_in_umbrella"] is False
    assert summary["reputation_attributable"] is False
    assert "github.com" in summary["redirect_destinations"]


def test_unattributable_reputation_says_so_rather_than_going_quiet():
    summary = summarise(
        [_hit("github.com", age=4800, rank=1508)], "domain", "lzphy.top"
    )
    signals = risk_signals(summary)
    assert any("no reputation can be attributed" in s for s in signals)
    # And it must not emit the age/popularity signals it has no basis for.
    assert not any("young" in s or "Umbrella" in s for s in signals)


def test_reputation_is_read_from_scans_that_did_land():
    hits = [_hit("evil.test", age=6), _hit("github.com", age=4800, rank=1508)]
    summary = summarise(hits, "domain", "evil.test")
    assert summary["scans_landed"] == 1
    assert summary["min_apex_domain_age_days"] == 6
    assert summary["ranked_in_umbrella"] is False, "the rank was the destination's"


# ═══════════════════════════════════════════════════════════════════════════
# Rule 3 — a missing verdict is never a clean verdict
# ═══════════════════════════════════════════════════════════════════════════


def test_verdicts_are_always_reported_as_unavailable():
    """Search returns no verdict data on the free tier, key or not. Reading
    that absence as 'no findings' reports every malicious indicator as safe."""
    summary = summarise(
        [_hit("example.com", age=4000, rank=500)], "domain", "example.com"
    )
    assert summary["verdicts_available"] is False


def test_a_clean_looking_indicator_produces_no_reassuring_signal():
    summary = summarise(
        [_hit("example.com", age=4000, rank=500)], "domain", "example.com"
    )
    signals = risk_signals(summary)
    assert not any("clean" in s.lower() or "safe" in s.lower() for s in signals)


def test_a_young_unranked_domain_raises_both_signals():
    summary = summarise([_hit("phish.test", age=6)], "domain", "phish.test")
    signals = risk_signals(summary)
    assert any("very young (6 days)" in s for s in signals)
    assert any("Umbrella" in s for s in signals)


def test_submitter_tags_surface():
    summary = summarise(
        [_hit("phish.test", age=400, rank=9000, tags=["phishing", "banking"])],
        "domain",
        "phish.test",
    )
    assert "phishing" in summary["tags"]
    assert any("phishing" in s for s in risk_signals(summary))


def test_an_indicator_with_no_scans_is_empty_not_an_error():
    summary = summarise([], "domain", "never-scanned.test")
    assert summary["scans_found"] == 0
    assert summary["reputation_attributable"] is False
    assert risk_signals(summary) == []


# ═══════════════════════════════════════════════════════════════════════════
# Investigator wiring
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_the_investigator_queries_urlscan_for_every_covered_indicator():
    """Regression guard: the collector is easy to add for one indicator and
    forget for the other two."""
    import inspect

    from core.intel.osint_investigator import OSINTInvestigator

    for method, kind in (
        ("_collect_domain", "domain"),
        ("_collect_ip", "ip"),
        ("_collect_hash", "hash"),
    ):
        source = inspect.getsource(getattr(OSINTInvestigator, method))
        assert f'self._urlscan("{kind}"' in source, f"{method} never asks urlscan"


@pytest.mark.asyncio
async def test_an_unreachable_urlscan_lands_in_degraded_not_a_crash(monkeypatch):
    from core.intel.osint_investigator import Dossier, OSINTInvestigator

    investigator = OSINTInvestigator()
    dossier = Dossier(target="example.com", indicator="domain")
    await investigator._urlscan("domain", "example.com", dossier)

    assert "urlscan" in dossier.sources_queried
    # No network in the test environment, so it must degrade rather than raise.
    assert "urlscan" in dossier.degraded or "urlscan" in dossier.sources_answered
