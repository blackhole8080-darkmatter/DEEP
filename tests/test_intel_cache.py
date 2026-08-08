"""The intel cache's durable tier and the feed pre-warmer.

The in-memory cache made every restart cold: the first console load after a
boot blocked on four multi-megabyte feeds, and restarting twice in a minute
re-downloaded the same CISA catalog twice. These tests pin the properties that
make the disk tier worth having — and the ones that keep it honest.
"""
from __future__ import annotations

import asyncio
import sqlite3

import pytest

from core.intel.cache_store import IntelCacheStore, cache_key, redact
from core.intel.http import Fetch, IntelHTTP


@pytest.fixture
def store(tmp_path):
    return IntelCacheStore(tmp_path / "cache.db")


# ═══════════════════════════════════════════════════════════════════════════
# The store
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_a_stored_response_survives_a_new_store_object(tmp_path):
    """This is the whole point: a restart must not re-download the KEV catalog."""
    path = tmp_path / "cache.db"
    first = IntelCacheStore(path)
    await first.put("k", label="GET https://example.test/kev",
                    payload={"vulnerabilities": [1, 2, 3]}, status=200, ttl_s=600)

    reborn = IntelCacheStore(path)          # a fresh process would do exactly this
    entry = await reborn.get("k")
    assert entry is not None
    assert entry.fresh
    assert entry.payload == {"vulnerabilities": [1, 2, 3]}


@pytest.mark.asyncio
async def test_expiry_is_wall_clock_not_monotonic(store):
    """Monotonic time restarts with the process, so it cannot be written down."""
    await store.put("k", label="l", payload="x", status=200, ttl_s=-1)
    entry = await store.get("k")
    assert entry is not None, "an expired entry is still readable as a stale fallback"
    assert entry.fresh is False


@pytest.mark.asyncio
async def test_entries_past_the_stale_grace_are_gone(tmp_path):
    store = IntelCacheStore(tmp_path / "cache.db", stale_grace_s=60)
    await store.put("k", label="l", payload="x", status=200, ttl_s=-3600)
    assert await store.get("k") is None


@pytest.mark.asyncio
async def test_no_url_or_credential_is_written_to_disk(tmp_path):
    """Several catalogued sources take their key in the query string."""
    path = tmp_path / "cache.db"
    store = IntelCacheStore(path)
    url = "https://api.example.test/v1/lookup?apikey=SUPERSECRET&ip=1.1.1.1"
    await store.put(cache_key("GET", url), label=redact("GET", url),
                    payload={"ok": True}, status=200, ttl_s=600)

    blob = path.read_bytes()
    assert b"SUPERSECRET" not in blob
    assert b"apikey" not in blob
    # The label is still useful for an operator reading the table.
    with sqlite3.connect(str(path)) as conn:
        (label,) = conn.execute("SELECT label FROM intel_cache").fetchone()
    assert label == "GET https://api.example.test/v1/lookup"


def test_the_key_is_a_digest_of_the_whole_request():
    assert cache_key("GET", "https://a.test") != cache_key("GET", "https://b.test")
    assert cache_key("GET", "https://a.test") != cache_key("POST", "https://a.test")
    assert (cache_key("POST", "https://a.test", {"x": 1})
            != cache_key("POST", "https://a.test", {"x": 2}))
    # Body key order must not change the identity of the request.
    assert (cache_key("POST", "https://a.test", {"a": 1, "b": 2})
            == cache_key("POST", "https://a.test", {"b": 2, "a": 1}))
    assert len(cache_key("GET", "https://a.test")) == 64


@pytest.mark.asyncio
async def test_the_database_is_owner_only(tmp_path):
    path = tmp_path / "cache.db"
    store = IntelCacheStore(path)
    await store.put("k", label="l", payload="x", status=200, ttl_s=60)
    assert path.stat().st_mode & 0o077 == 0, "responses from keyed sources live here"


@pytest.mark.asyncio
async def test_an_oversized_payload_is_skipped_not_stored(tmp_path):
    store = IntelCacheStore(tmp_path / "cache.db", max_entry_bytes=100)
    stored = await store.put("k", label="l", payload="x" * 500, status=200, ttl_s=60)
    assert stored is False
    assert await store.get("k") is None


@pytest.mark.asyncio
async def test_an_unserialisable_payload_is_skipped_not_raised(store):
    stored = await store.put("k", label="l", payload={1, 2, 3}, status=200, ttl_s=60)
    assert stored is False


@pytest.mark.asyncio
async def test_a_broken_database_disables_the_cache_rather_than_deep(tmp_path):
    """A bad disk should make the console slow, not broken."""
    path = tmp_path / "cache.db"
    path.write_bytes(b"this is not a sqlite database")
    store = IntelCacheStore(path)

    assert await store.get("k") is None
    assert await store.put("k", label="l", payload="x", status=200, ttl_s=60) is False
    assert (await store.stats())["enabled"] is False


@pytest.mark.asyncio
async def test_prune_drops_only_what_is_past_the_grace(tmp_path):
    store = IntelCacheStore(tmp_path / "cache.db", stale_grace_s=60)
    await store.put("fresh", label="l", payload="a", status=200, ttl_s=600)
    await store.put("stale", label="l", payload="b", status=200, ttl_s=-30)  # in grace
    await store.put("ancient", label="l", payload="c", status=200, ttl_s=-600)

    assert await store.prune() == 1
    assert await store.get("fresh") is not None
    assert await store.get("stale") is not None
    assert await store.get("ancient") is None


@pytest.mark.asyncio
async def test_prune_enforces_the_size_budget_oldest_first(tmp_path):
    store = IntelCacheStore(tmp_path / "cache.db", max_total_bytes=400)
    for i in range(6):
        await store.put(f"k{i}", label="l", payload="x" * 100, status=200, ttl_s=600)
        await asyncio.sleep(0.002)  # distinct stored_at, so "oldest" is well defined

    assert await store.prune() > 0
    stats = await store.stats()
    assert stats["bytes"] <= 400
    assert await store.get("k0") is None, "oldest write should go first"
    assert await store.get("k5") is not None


@pytest.mark.asyncio
async def test_rewriting_a_key_replaces_rather_than_accumulates(store):
    await store.put("k", label="l", payload="first", status=200, ttl_s=600)
    await store.put("k", label="l", payload="second", status=200, ttl_s=600)
    entry = await store.get("k")
    assert entry.payload == "second"
    assert (await store.stats())["entries"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# IntelHTTP against the store
# ═══════════════════════════════════════════════════════════════════════════


async def _seed(http: IntelHTTP, url: str, payload, ttl: int):
    """Put a payload in the durable tier the way a previous process would have."""
    await http._store.put(
        cache_key("GET", url, None), label=redact("GET", url),
        payload=payload, status=200, ttl_s=ttl,
    )


@pytest.mark.asyncio
async def test_a_cold_process_serves_the_previous_run_from_disk(tmp_path):
    """No aiohttp call at all — the disk answer is returned before the network."""
    store = IntelCacheStore(tmp_path / "cache.db")
    http = IntelHTTP(store=store)
    url = "https://kev.test/catalog.json"
    await _seed(http, url, {"vulnerabilities": []}, ttl=600)

    result = await http.get_json(url)
    assert result.ok and result.cached
    assert result.data == {"vulnerabilities": []}
    assert http.stats()["disk_hits"] == 1
    assert http.stats()["requests"] == 0, "a disk hit must not touch the network"
    assert result.fresh_for_s > 0
    await http.close()


@pytest.mark.asyncio
async def test_a_disk_hit_is_promoted_into_memory(tmp_path):
    store = IntelCacheStore(tmp_path / "cache.db")
    http = IntelHTTP(store=store)
    url = "https://kev.test/catalog.json"
    await _seed(http, url, {"v": 1}, ttl=600)

    await http.get_json(url)
    await http.get_json(url)
    assert http.stats()["disk_hits"] == 1, "second read should not go back to disk"
    assert http.stats()["cache_hits"] == 1
    await http.close()


@pytest.mark.asyncio
async def test_an_expired_disk_entry_is_not_served_as_fresh(tmp_path):
    """It stays around as a fallback, but only after a failed fetch."""
    store = IntelCacheStore(tmp_path / "cache.db")
    http = IntelHTTP(store=store)
    url = "https://kev.test/catalog.json"
    await _seed(http, url, {"v": 1}, ttl=-30)

    result = await http.get_json(url)
    # No network in the test environment, so the fetch fails and the stale
    # fallback is what comes back — flagged, not disguised.
    assert result.stale is True
    assert result.stale_age_s > 0
    assert result.data == {"v": 1}
    assert http.stats()["stale_served"] == 1
    await http.close()


@pytest.mark.asyncio
async def test_a_failed_fetch_with_no_cached_answer_still_fails(tmp_path):
    """The fallback must never invent an all-clear out of an empty cache."""
    http = IntelHTTP(store=IntelCacheStore(tmp_path / "cache.db"))
    result = await http.get_json("https://nothing-here.invalid/x")
    assert result.ok is False
    assert result.data is None
    assert result.stale is False
    await http.close()


@pytest.mark.asyncio
async def test_refresh_bypasses_both_tiers(tmp_path):
    """Otherwise 'refreshing' would just re-read what is already cached."""
    store = IntelCacheStore(tmp_path / "cache.db")
    http = IntelHTTP(store=store)
    url = "https://kev.test/catalog.json"
    await _seed(http, url, {"v": 1}, ttl=600)

    assert (await http.get_json(url)).cached is True
    assert http.stats()["requests"] == 0, "a cached read must not hit the network"

    result = await http.get_json(url, refresh=True)
    assert http.stats()["requests"] == 1, "refresh must issue a real request"
    # The request fails here (no network), so the still-valid cached copy comes
    # back — as current data, since it has not expired, but carrying the error.
    assert result.ok and result.stale is False
    assert result.error, "the caller must be able to tell the source was unreachable"
    await http.close()


@pytest.mark.asyncio
async def test_short_lived_responses_are_not_written_to_disk(tmp_path):
    """A 30s failure TTL is not worth the write amplification."""
    store = IntelCacheStore(tmp_path / "cache.db")
    http = IntelHTTP(store=store)
    assert http.PERSIST_MIN_TTL >= 60
    await http.get_json("https://nothing-here.invalid/x", ttl=5)
    assert (await store.stats())["writes"] == 0
    await http.close()


@pytest.mark.asyncio
async def test_persistence_can_be_switched_off(tmp_path):
    http = IntelHTTP(store=None)
    stats = await http.cache_stats()
    assert stats["disk"] == {"enabled": False}
    assert http.stats()["persistent"] is False
    assert await http.prune_cache() == 0
    await http.close()


@pytest.mark.asyncio
async def test_clearing_the_cache_clears_both_tiers(tmp_path):
    store = IntelCacheStore(tmp_path / "cache.db")
    http = IntelHTTP(store=store)
    url = "https://kev.test/catalog.json"
    await _seed(http, url, {"v": 1}, ttl=600)
    await http.get_json(url)

    await http.clear_persistent_cache()
    assert http.stats()["cache_entries"] == 0
    assert (await store.stats())["entries"] == 0
    await http.close()


# ═══════════════════════════════════════════════════════════════════════════
# The pre-warmer
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_every_hot_feed_names_a_real_catalog_source():
    """The cadence comes from the catalog; a typo'd id would silently mean 1h."""
    from core.intel import public_apis
    from core.intel.refresher import HOT_FEEDS

    for feed in HOT_FEEDS:
        api = public_apis.get(feed.source_id)
        assert api is not None, f"{feed.source_id} is not in the catalog"
        assert feed.ttl_s == api.ttl_seconds


@pytest.mark.asyncio
async def test_hot_feed_urls_are_the_ones_the_console_actually_reads():
    """Warming a URL nothing reads would be pure waste."""
    from core.intel import live_stats
    from core.intel.refresher import HOT_FEEDS

    console_urls = {
        live_stats.KEV_URL,
        live_stats.EPSS_TOP.format(limit=20),
        live_stats.FEODO_URL,
        live_stats.TOR_EXITS,
        live_stats.ISC_TOP_SOURCES.format(limit=100),
    }
    assert {f.url for f in HOT_FEEDS} == console_urls


@pytest.mark.asyncio
async def test_a_warm_cache_makes_the_boot_pass_free(tmp_path):
    """A restart with a warm disk cache should issue no network traffic."""
    from core.intel.refresher import HOT_FEEDS, IntelRefresher

    store = IntelCacheStore(tmp_path / "cache.db")
    http = IntelHTTP(store=store)
    for feed in HOT_FEEDS:
        await store.put(cache_key("GET", feed.url, None), label=redact("GET", feed.url),
                        payload={"warm": True}, status=200, ttl_s=feed.ttl_s)

    refresher = IntelRefresher(http=http, stagger_s=0)
    await refresher.refresh_once(force=False)

    assert http.stats()["requests"] == 0
    assert http.stats()["disk_hits"] == len(HOT_FEEDS)
    await http.close()


@pytest.mark.asyncio
async def test_a_warm_up_hit_is_rescheduled_off_its_remaining_life(tmp_path):
    """Scheduling off the full TTL would let a half-expired entry lapse."""
    from core.intel.refresher import Feed, IntelRefresher

    feed = Feed("cisa_kev", "https://kev.test/x.json", "KEV")
    store = IntelCacheStore(tmp_path / "cache.db")
    http = IntelHTTP(store=store)
    # Six-hour TTL source, but this cached copy has only ten minutes left.
    await store.put(cache_key("GET", feed.url, None), label="l",
                    payload={"v": 1}, status=200, ttl_s=600)

    refresher = IntelRefresher(http=http, feeds=[feed], tick_s=1, stagger_s=0)
    await refresher.refresh_once(force=False)

    due = refresher.status()["feeds"][0]["due_in_s"]
    assert 0 < due <= 600, f"next refresh in {due}s — should be inside the cached life"
    await http.close()


@pytest.mark.asyncio
async def test_a_failing_feed_backs_off_instead_of_spinning(tmp_path):
    from core.intel.refresher import Feed, IntelRefresher

    feed = Feed("cisa_kev", "https://nothing-here.invalid/kev.json", "KEV")
    http = IntelHTTP(store=None)
    refresher = IntelRefresher(http=http, feeds=[feed], tick_s=1, stagger_s=0)

    delays = []
    for _ in range(3):
        await refresher.refresh_once()
        state = refresher.status()["feeds"][0]
        delays.append(state["last"]["next_in_s"])
        refresher._due[feed.source_id] = 0.0   # force the next attempt

    assert refresher.status()["feeds"][0]["consecutive_failures"] == 3
    assert delays == sorted(delays), f"backoff must not shrink: {delays}"
    assert delays[-1] > delays[0]
    assert max(delays) <= feed.ttl_s, "backoff is capped at the feed's own cadence"
    await http.close()


@pytest.mark.asyncio
async def test_a_failed_refresh_onto_unexpired_data_is_not_called_stale(tmp_path):
    """The refresher fires at 85% of TTL, so this is the common failure case.

    The cached copy has not expired — it is still current, and flagging it
    stale would put a false alarm on the console. The source is still down
    though, so the refresher must not treat it as a successful pass.
    """
    from core.intel.refresher import Feed, IntelRefresher

    feed = Feed("cisa_kev", "https://nothing-here.invalid/kev.json", "KEV")
    store = IntelCacheStore(tmp_path / "cache.db")
    http = IntelHTTP(store=store)
    await store.put(cache_key("GET", feed.url, None), label="l",
                    payload={"v": 1}, status=200, ttl_s=600)

    refresher = IntelRefresher(http=http, feeds=[feed], tick_s=1, stagger_s=0)
    await refresher.refresh_once()

    state = refresher.status()["feeds"][0]
    assert state["last"]["ok"] is False, "the source is down; do not reset the backoff"
    assert state["last"]["stale"] is False, "unexpired data must not be flagged stale"
    assert state["consecutive_failures"] == 1

    # And a console read still gets the data, presented as current.
    served = await http.get_json(feed.url, ttl=600)
    assert served.ok and served.data == {"v": 1}
    assert served.stale is False
    await http.close()


@pytest.mark.asyncio
async def test_a_stale_fallback_does_not_count_as_a_successful_refresh(tmp_path):
    """The source is still down; treating it as fine would freeze the backoff."""
    from core.intel.refresher import Feed, IntelRefresher

    feed = Feed("cisa_kev", "https://nothing-here.invalid/kev.json", "KEV")
    store = IntelCacheStore(tmp_path / "cache.db")
    http = IntelHTTP(store=store)
    await store.put(cache_key("GET", feed.url, None), label="l",
                    payload={"v": 1}, status=200, ttl_s=-30)

    refresher = IntelRefresher(http=http, feeds=[feed], tick_s=1, stagger_s=0)
    await refresher.refresh_once()

    last = refresher.status()["feeds"][0]["last"]
    assert last["ok"] is False
    assert last["stale"] is True
    assert refresher.status()["feeds"][0]["consecutive_failures"] == 1
    await http.close()


@pytest.mark.asyncio
async def test_feeds_that_are_not_due_are_left_alone(tmp_path):
    from core.intel.refresher import Feed, IntelRefresher

    feed = Feed("cisa_kev", "https://nothing-here.invalid/kev.json", "KEV")
    http = IntelHTTP(store=None)
    refresher = IntelRefresher(http=http, feeds=[feed], tick_s=1, stagger_s=0)

    first = await refresher.refresh_once()
    assert feed.source_id in first["refreshed"]
    second = await refresher.refresh_once()
    assert second["refreshed"] == {}, "a feed just refreshed must not refresh again"
    await http.close()


@pytest.mark.asyncio
async def test_the_loop_starts_and_stops_cleanly(monkeypatch, tmp_path):
    from core.intel.refresher import IntelRefresher

    monkeypatch.setenv("DEEP_INTEL_REFRESH", "1")
    http = IntelHTTP(store=None)
    refresher = IntelRefresher(http=http, feeds=[], initial_delay_s=10, tick_s=10)

    assert await refresher.start() is True
    assert refresher.running is True
    await refresher.stop()
    assert refresher.running is False
    await http.close()


@pytest.mark.asyncio
async def test_the_loop_is_opt_out(monkeypatch):
    from core.intel.refresher import IntelRefresher

    monkeypatch.setenv("DEEP_INTEL_REFRESH", "0")
    refresher = IntelRefresher(http=IntelHTTP(store=None), feeds=[])
    assert await refresher.start() is False
    assert refresher.running is False


# ═══════════════════════════════════════════════════════════════════════════
# Honest degradation
# ═══════════════════════════════════════════════════════════════════════════


def test_stale_ages_are_reported_per_source():
    from core.intel.live_stats import _stale_ages

    fresh = Fetch(ok=True, data={}, status=200)
    old = Fetch(ok=True, data={}, status=200, stale=True, stale_age_s=7200)
    assert _stale_ages(cisa_kev=fresh, feodo=old) == {"feodo": 7200}
    assert _stale_ages(cisa_kev=fresh) == {}
    # A gathered exception must not blow up the reporter.
    assert _stale_ages(epss=RuntimeError("boom")) == {}


def test_the_terminal_surfaces_staleness_rather_than_hiding_it():
    """Stale data shown as current is worse than no data at all."""
    import inspect

    from core.intel.ops_terminal import OpsTerminal

    source = inspect.getsource(OpsTerminal._cmd_stats)
    assert 'stats.get("stale")' in source
    assert "STALE" in source
