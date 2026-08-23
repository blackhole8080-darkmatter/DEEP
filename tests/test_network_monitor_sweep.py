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
import socket
import sys
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
    """The original failure mode: one silent address, one stalled server."""
    def hangs(ip):
        time.sleep(30)
        raise AssertionError("should have been abandoned long before this")

    monkeypatch.setattr(socket, "gethostbyaddr", hangs)
    monkeypatch.setattr(nm, "HOSTNAME_TIMEOUT_S", 0.2)

    started = time.perf_counter()
    result = await monitor._resolve_hostnames(["10.0.0.7"])
    elapsed = time.perf_counter() - started

    assert result == {}, "an unresolved address must not invent a name"
    assert elapsed < 5, f"gave up after {elapsed:.1f}s; the deadline is not being applied"


@pytest.mark.asyncio
async def test_the_event_loop_keeps_running_during_resolution(monitor, monkeypatch):
    """A sweep must not be a stop-the-world pause for the rest of DEEP."""
    monkeypatch.setattr(socket, "gethostbyaddr", lambda ip: (_ for _ in ()).throw(socket.herror()))
    monkeypatch.setattr(nm, "HOSTNAME_TIMEOUT_S", 0.3)

    ticks = 0

    async def heartbeat():
        nonlocal ticks
        while True:
            ticks += 1
            await asyncio.sleep(0.01)

    beat = asyncio.create_task(heartbeat())
    await monitor._resolve_hostnames([f"10.0.0.{n}" for n in range(1, 20)])
    beat.cancel()

    assert ticks > 1, "the loop was blocked for the whole sweep"


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
