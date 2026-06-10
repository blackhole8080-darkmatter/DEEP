# deep/tech/networking.py — Protocol Analysis & Network Simulation (Section 1 tree)
"""DNS resolution, latency ping, local interface info, subnet maths, and a
queueing/network-simulation model. Pure stdlib + numpy; scapy/psutil optional."""
from __future__ import annotations

import ipaddress
import socket
import time

import numpy as np

try:
    import psutil
    PSUTIL = True
except Exception:  # pragma: no cover
    PSUTIL = False


class NetworkEngine:
    def __init__(self, config=None):
        self.config = config

    def resolve(self, hostname) -> dict:
        try:
            ip = socket.gethostbyname(hostname)
            return {"hostname": hostname, "ip": ip, "result": ip,
                    "verbal": f"{hostname} resolves to {ip}, sir."}
        except Exception as e:  # noqa: BLE001
            return {"result": None, "verbal": f"Could not resolve {hostname}, sir: {e}"}

    def tcp_ping(self, host="1.1.1.1", port=443, attempts=4, timeout=2.0) -> dict:
        times = []
        for _ in range(attempts):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            t0 = time.perf_counter()
            try:
                if s.connect_ex((host, port)) == 0:
                    times.append((time.perf_counter() - t0) * 1000)
            except Exception:
                pass
            finally:
                s.close()
        if not times:
            return {"result": None, "verbal": f"{host}:{port} unreachable, sir."}
        return {"latencies_ms": times, "avg_ms": float(np.mean(times)),
                "result": float(np.mean(times)),
                "verbal": f"{host}:{port} avg latency {np.mean(times):.1f} ms "
                          f"over {len(times)} probes."}

    def subnet_info(self, cidr="192.168.1.0/24") -> dict:
        net = ipaddress.ip_network(cidr, strict=False)
        return {"network": str(net.network_address), "broadcast": str(net.broadcast_address),
                "num_hosts": net.num_addresses - 2, "netmask": str(net.netmask),
                "result": net.num_addresses - 2,
                "verbal": f"{cidr}: {net.num_addresses-2} usable hosts, "
                          f"netmask {net.netmask}."}

    def interfaces(self) -> dict:
        if not PSUTIL:
            return {"result": None, "verbal": "psutil not installed, sir."}
        addrs = psutil.net_if_addrs()
        ifaces = {name: [a.address for a in addr if a.family == socket.AF_INET]
                  for name, addr in addrs.items()}
        ifaces = {k: v for k, v in ifaces.items() if v}
        return {"interfaces": ifaces, "result": list(ifaces),
                "verbal": f"{len(ifaces)} active IPv4 interface(s): {list(ifaces)}."}

    def mm1_queue(self, arrival_rate, service_rate) -> dict:
        """M/M/1 queue steady-state metrics."""
        rho = arrival_rate / service_rate
        if rho >= 1:
            return {"result": None,
                    "verbal": f"Queue unstable (ρ={rho:.2f} ≥ 1), sir."}
        L = rho / (1 - rho)              # avg number in system
        W = 1 / (service_rate - arrival_rate)  # avg time in system
        return {"utilisation": rho, "avg_in_system": L, "avg_wait_s": W, "result": L,
                "verbal": f"M/M/1 queue: utilisation {rho:.2f}, avg {L:.2f} jobs in "
                          f"system, avg wait {W:.3f}s."}

    def test(self) -> None:
        assert self.subnet_info("10.0.0.0/24")["num_hosts"] == 254
        q = self.mm1_queue(3, 5)
        assert q["utilisation"] == 0.6
        print("networking.NetworkEngine: OK")


def test() -> None:
    NetworkEngine().test()


if __name__ == "__main__":
    test()
