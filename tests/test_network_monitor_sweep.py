"""What one network sweep is allowed to cost.

NetworkMonitor's sweep is `async`, which used to be the only asynchronous
thing about it: every collector inside ran blocking, on the event loop, and
the hostname step resolved each address in sequence with no deadline. A sweep
measured 121s, ran every 30s, and froze the server for its whole duration —
the HUD, the API and the websocket were simply unavailable while DEEP looked
up PTR records for addresses it was about to discard.

These tests are about that cost, so they assert on *where the work goes*
rather than on scan results: that unreachable names are abandoned, that the
loop keeps running, that an answer is not asked for twice, and that addresses
the monitor does not track are never looked up at all.
"""
from __future__ import annotations

import asyncio
import contextlib
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.security import network_monitor as nm
from core.security.network_monitor import NetworkMonitor


@pytest.fixture
def monitor(tmp_path):
    return NetworkMonitor(data_dir=tmp_path)


@pytest.mark.asyncio
async def test_a_resolver_that_never_answers_does_not_stall_the_sweep(monitor, monkeypatch):
    """The original failure mode: one silent address, one stalled server.

    The stand-in blocks on an Event rather than sleeping, and the Event is set
    in `finally`. `wait_for` abandons the await but cannot stop the thread — the
    property under test — so a fixed sleep would leave a worker running after
    the assertions pass, and the interpreter joins those workers at exit. A test
    for not blocking should not itself block the shutdown.
    """
    release = threading.Event()

    def hangs(ip):
        # Raising here to signal "should never get this far" would be a guard
        # that cannot fire: the lookup body swallows every exception so a dead
        # thread cannot leak its allowance, so the assertion would never reach
        # the test. The elapsed-time check below is the real one.
        release.wait(30)
        raise socket.herror()

    monkeypatch.setattr(socket, "gethostbyaddr", hangs)
    monkeypatch.setattr(nm, "HOSTNAME_TIMEOUT_S", 0.2)

    try:
        started = time.perf_counter()
        result = await monitor._resolve_hostnames(["10.0.0.7"])
        elapsed = time.perf_counter() - started

        assert result == {}, "an unresolved address must not invent a name"
        assert elapsed < 5, f"gave up after {elapsed:.1f}s; the deadline is not being applied"
    finally:
        release.set()


@pytest.mark.asyncio
async def test_the_event_loop_keeps_running_during_resolution(monitor, monkeypatch):
    """A sweep must not be a stop-the-world pause for the rest of DEEP.

    The resolver here *blocks* rather than raising immediately. An instant
    failure proves nothing: the whole resolution then finishes inside one tick
    of the heartbeat, and the test reads a loop that was never given the chance
    to block as a loop that was blocked. Real PTR lookups against a silent
    resolver take seconds, and seconds are what this has to survive.
    """
    def slow_failure(ip):
        time.sleep(0.25)
        raise socket.herror()

    monkeypatch.setattr(socket, "gethostbyaddr", slow_failure)
    monkeypatch.setattr(nm, "HOSTNAME_TIMEOUT_S", 2.0)

    ticks = 0

    async def heartbeat():
        nonlocal ticks
        while True:
            ticks += 1
            await asyncio.sleep(0.01)

    beat = asyncio.create_task(heartbeat())
    started = time.monotonic()
    await monitor._resolve_hostnames([f"10.0.0.{n}" for n in range(1, 20)])
    elapsed = time.monotonic() - started
    beat.cancel()

    # 19 addresses that each block for 0.25s. Serially that is 4.75s of frozen
    # loop; the heartbeat should have ticked throughout instead.
    assert elapsed > 0.2, "the resolver did not actually block, so this proves nothing"
    assert ticks > 5, f"the loop only ticked {ticks} times in {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_addresses_are_resolved_together_not_one_after_another(monitor, monkeypatch):
    """Twenty slow lookups should cost about one, not twenty."""
    def slow(ip):
        time.sleep(0.2)
        raise socket.herror()

    monkeypatch.setattr(socket, "gethostbyaddr", slow)
    monkeypatch.setattr(nm, "HOSTNAME_TIMEOUT_S", 5.0)

    started = time.perf_counter()
    await monitor._resolve_hostnames([f"10.0.0.{n}" for n in range(1, 21)])
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0, f"took {elapsed:.1f}s — lookups are still running in sequence"


@pytest.mark.asyncio
async def test_an_address_with_no_name_is_not_asked_about_twice(monitor, monkeypatch):
    """Caching negatives is the difference between a 30s cycle and a stall."""
    calls = []

    def counted(ip):
        calls.append(ip)
        raise socket.herror()

    monkeypatch.setattr(socket, "gethostbyaddr", counted)
    await monitor._resolve_hostnames(["10.0.0.5"])
    await monitor._resolve_hostnames(["10.0.0.5"])
    assert len(calls) == 1, f"re-resolved a known-nameless address: {calls}"


@pytest.mark.asyncio
async def test_a_resolved_name_is_reused_and_returned(monitor, monkeypatch):
    calls = []

    def named(ip):
        calls.append(ip)
        return ("router.lan", [], [ip])

    monkeypatch.setattr(socket, "gethostbyaddr", named)
    first = await monitor._resolve_hostnames(["192.168.1.1"])
    second = await monitor._resolve_hostnames(["192.168.1.1"])

    assert first == {"192.168.1.1": "router.lan"}
    assert second == first, "a cached name must still be reported, not dropped"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_internet_addresses_are_never_looked_up(monitor, monkeypatch):
    """The sweep discards non-local addresses, so it must not resolve them first.

    Every open browser tab puts a public IP in the ARP table. Resolving those
    was 25 of the 29 lookups in a real sweep, and every answer was thrown away
    on the next line.
    """
    looked_up = []

    def record(ip):
        looked_up.append(ip)
        raise socket.herror()

    monkeypatch.setattr(socket, "gethostbyaddr", record)
    monkeypatch.setattr(nm, "HOSTNAME_TIMEOUT_S", 0.2)
    monkeypatch.setattr(
        monitor, "_get_arp_table",
        lambda: [
            {"ip": "192.168.1.50", "mac": "aa:bb:cc:dd:ee:01", "type": "dynamic"},
            {"ip": "142.250.190.78", "mac": "aa:bb:cc:dd:ee:02", "type": "dynamic"},
        ],
    )
    monkeypatch.setattr(monitor, "_get_connection_peers", lambda: [])

    await monitor._do_scan()

    assert "142.250.190.78" not in looked_up, "resolved a public address it does not track"


@pytest.mark.asyncio
async def test_starting_the_monitor_does_not_wait_for_a_sweep(monitor, monkeypatch):
    """Boot must not be held hostage by the network being slow.

    uvicorn opens the port only once startup returns, so a sweep awaited here
    is time the server spends unreachable.
    """
    async def slow_sweep():
        await asyncio.sleep(10)

    monkeypatch.setattr(monitor, "_do_scan", slow_sweep)

    started = time.perf_counter()
    await monitor.start()
    elapsed = time.perf_counter() - started

    assert elapsed < 1.0, f"start() blocked for {elapsed:.1f}s on the first sweep"
    assert monitor._scan_task is not None, "the background sweep was never scheduled"
    await monitor.stop()


@pytest.mark.asyncio
async def test_the_baseline_is_established_by_whichever_sweep_lands_first(monitor):
    """Deferring the sweep must not quietly disable anomaly detection."""
    monitor.device_registry["aa:bb:cc:dd:ee:01"] = nm.NetworkDevice(
        mac="aa:bb:cc:dd:ee:01", ip="192.168.1.50"
    )
    assert not monitor.baseline_established

    monitor._establish_baseline()

    assert monitor.baseline_established
    assert monitor.baseline_device_count == 1


@pytest.mark.asyncio
async def test_establishing_the_baseline_twice_does_not_move_it(monitor):
    monitor.device_registry["aa:bb:cc:dd:ee:01"] = nm.NetworkDevice(
        mac="aa:bb:cc:dd:ee:01", ip="192.168.1.50"
    )
    monitor._establish_baseline()
    monitor.device_registry["aa:bb:cc:dd:ee:02"] = nm.NetworkDevice(
        mac="aa:bb:cc:dd:ee:02", ip="192.168.1.51"
    )
    monitor._establish_baseline()
    assert monitor.baseline_device_count == 1, "the baseline drifted to match the anomaly"


# ── what a stalled lookup is allowed to block ────────────────────────────────
#
# asyncio.wait_for abandons the await; it cannot stop a gethostbyaddr already
# inside the C library. So the deadline bounds how long the *sweep* waits, not
# how long the thread stays busy — and on asyncio's shared default pool those
# stragglers accumulate until everything else that calls to_thread waits behind
# them, including the collectors in this same sweep.


@pytest.mark.asyncio
async def test_a_stalled_lookup_does_not_occupy_the_shared_executor(monitor, monkeypatch):
    release = threading.Event()

    def hangs(ip):
        release.wait(10)
        raise socket.herror()

    monkeypatch.setattr(socket, "gethostbyaddr", hangs)
    monkeypatch.setattr(nm, "HOSTNAME_TIMEOUT_S", 0.05)
    try:
        await monitor._resolve_hostnames([f"10.0.0.{n}" for n in range(1, 9)])

        # Eight lookups are still wedged in the resolver's own threads. Work on
        # the default executor — where the ARP and connection collectors run —
        # must be unaffected.
        began = time.monotonic()
        assert await asyncio.wait_for(
            asyncio.to_thread(lambda: "collector"), timeout=2
        ) == "collector"
        assert time.monotonic() - began < 1.0
    finally:
        release.set()


@pytest.mark.asyncio
async def test_the_resolver_is_bounded(monitor, monkeypatch):
    """Unbounded would mean one sweep of a /24 spawning 254 threads.

    Asserted by watching how many lookups are in flight, not by inspecting
    whichever object does the bounding, so the guarantee outlives the
    mechanism.
    """
    live = 0
    peak = 0
    lock = threading.Lock()

    def slow(ip):
        nonlocal live, peak
        with lock:
            live += 1
            peak = max(peak, live)
        time.sleep(0.15)
        with lock:
            live -= 1
        raise socket.herror()

    monkeypatch.setattr(socket, "gethostbyaddr", slow)
    monkeypatch.setattr(nm, "HOSTNAME_TIMEOUT_S", 5.0)
    await monitor._resolve_hostnames([f"10.3.{n // 256}.{n % 256}" for n in range(60)])

    assert peak <= nm.HOSTNAME_RESOLVER_THREADS, f"{peak} lookups ran at once"


@pytest.mark.asyncio
async def test_a_stalled_lookup_cannot_hold_the_interpreter_open(monitor, monkeypatch):
    """Why these are daemon threads and not a ThreadPoolExecutor's workers.

    Those are not daemons on 3.9+, and concurrent.futures joins them from an
    atexit hook, so `shutdown(wait=False)` returns at once while the process
    still waits out the lookup. Measured: stop() returned in 0.16s, the process
    exited 3.17s later — the freeze this module removed from the sweep, moved
    to shutdown. A daemon thread is never joined.
    """
    seen = []
    release = threading.Event()

    def slow(ip):
        seen.append(threading.current_thread())
        release.wait(10)
        raise socket.herror()

    monkeypatch.setattr(socket, "gethostbyaddr", slow)
    monkeypatch.setattr(nm, "HOSTNAME_TIMEOUT_S", 0.05)
    try:
        await monitor._resolve_hostnames(["10.0.0.1"])
        assert seen, "the lookup never ran"
        assert all(t.daemon for t in seen), "a non-daemon lookup will be joined at exit"
    finally:
        release.set()


@pytest.mark.asyncio
async def test_lookups_stay_bounded_across_stop_and_start(monitor, monkeypatch):
    """A stop/start cycle must not be able to double the number in flight.

    Handing out a fresh allowance on stop looks tidier and is wrong: a
    `gethostbyaddr` already inside the C library keeps running whatever we do,
    so a new allowance would permit a second full set alongside the stalled
    first. Repeat the cycle and the bound is gone. The allowance therefore
    lives as long as the monitor.
    """
    bound = nm.HOSTNAME_RESOLVER_THREADS
    live = 0
    peak = 0
    lock = threading.Lock()
    release = threading.Event()

    def hangs(ip):
        nonlocal live, peak
        with lock:
            live += 1
            peak = max(peak, live)
        release.wait(10)
        with lock:
            live -= 1          # count concurrency, not arrivals
        raise socket.herror()

    monkeypatch.setattr(socket, "gethostbyaddr", hangs)
    monkeypatch.setattr(nm, "HOSTNAME_TIMEOUT_S", 0.05)
    try:
        # Wedge the whole allowance, then stop — the cycle in question.
        await monitor._resolve_hostnames([f"10.0.0.{n}" for n in range(1, bound + 1)])
        assert peak == bound
        await monitor.stop()

        # The second sweep must not be able to proceed while the first set is
        # still wedged. Run it alongside a pause rather than awaiting it, so a
        # bound that has been widened shows up as extra lookups in flight.
        second = asyncio.create_task(
            monitor._resolve_hostnames([f"10.0.1.{n}" for n in range(1, bound + 1)])
        )
        await asyncio.sleep(0.5)

        assert peak <= bound, f"{peak} lookups in flight — the cycle widened the bound"
        assert not second.done(), "the second sweep ignored the allowance entirely"
    finally:
        release.set()
        with contextlib.suppress(asyncio.TimeoutError, Exception):
            await asyncio.wait_for(second, 10)


@pytest.mark.asyncio
async def test_expired_entries_leave_the_cache(monitor, monkeypatch):
    """Skipping an expired entry is not the same as removing it.

    A monitor runs for weeks and sees every address the machine has spoken to.
    Entries that are merely ignored still have to be walked, so the cost of a
    sweep grows with everything the host has ever contacted rather than with
    what is on the network now.
    """
    monkeypatch.setattr(socket, "gethostbyaddr", lambda ip: (_ for _ in ()).throw(socket.herror()))
    monitor._hostname_cache["10.0.0.99"] = ("stale.lan", time.monotonic() - nm.HOSTNAME_CACHE_TTL_S - 1)
    monitor._hostname_cache["10.0.0.98"] = ("current.lan", time.monotonic())

    await monitor._resolve_hostnames(["10.0.0.1"])

    assert "10.0.0.99" not in monitor._hostname_cache, "expired entry was kept"
    assert "10.0.0.98" in monitor._hostname_cache, "a live entry was evicted with it"


@pytest.mark.asyncio
async def test_an_unexpected_lookup_failure_does_not_leak_its_allowance(monitor, monkeypatch):
    """The allowance must come back however the lookup ends.

    `deliver` hands the slot back, so a lookup that dies before reaching it
    keeps its slot forever. Enough of those and `acquire()` never returns —
    every later sweep blocks indefinitely, which is the freeze this module
    exists to remove, made permanent rather than merely long.

    `gethostbyaddr` does raise outside the socket family: a PTR record that is
    not valid UTF-8 arrives as UnicodeDecodeError, and on a hostile LAN that
    record is the attacker's to choose.
    """
    def malformed_ptr(ip):
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr(socket, "gethostbyaddr", malformed_ptr)
    monkeypatch.setattr(nm, "HOSTNAME_TIMEOUT_S", 0.2)

    count = nm.HOSTNAME_RESOLVER_THREADS
    assert await monitor._resolve_hostnames(
        [f"10.0.0.{n}" for n in range(1, count + 1)]
    ) == {}

    # Every thread has to have finished dying before the allowance is counted.
    for _ in range(50):
        if monitor._resolver_gate._value == count:
            break
        await asyncio.sleep(0.02)
    assert monitor._resolver_gate._value == count, "the allowance was not returned"

    # And the real proof: a later sweep still resolves rather than blocking.
    monkeypatch.setattr(socket, "gethostbyaddr", lambda ip: ("host.lan", [], [ip]))
    assert await asyncio.wait_for(
        monitor._resolve_hostnames(["10.0.1.1"]), timeout=5
    ) == {"10.0.1.1": "host.lan"}
