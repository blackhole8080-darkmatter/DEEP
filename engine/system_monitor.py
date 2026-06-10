# deep/system_monitor.py — System Monitoring (Bible Section 26.1)
"""Hardware snapshot, temperatures, process control, CPU benchmark. psutil
core; pynvml optional for NVIDIA GPU."""
from __future__ import annotations

import time

try:
    import psutil
    PSUTIL = True
except Exception:  # pragma: no cover
    PSUTIL = False

try:
    import pynvml
    pynvml.nvmlInit()
    PYNVML = True
except Exception:  # pragma: no cover
    PYNVML = False


class SystemMonitor:
    def __init__(self, config=None):
        self.config = config

    def get_hardware_status(self) -> dict:
        if not PSUTIL:
            return {"result": None, "verbal": "psutil is not installed, sir."}
        cpu = {"percent": psutil.cpu_percent(interval=0.3),
               "per_core": psutil.cpu_percent(interval=0.0, percpu=True),
               "freq_mhz": getattr(psutil.cpu_freq(), "current", None),
               "cores": psutil.cpu_count(logical=True)}
        vm = psutil.virtual_memory()
        ram = {"total_gb": round(vm.total / 1e9, 2), "used_gb": round(vm.used / 1e9, 2),
               "percent": vm.percent}
        disk = []
        for p in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(p.mountpoint)
                disk.append({"device": p.device, "percent": u.percent,
                             "free_gb": round(u.free / 1e9, 1)})
            except Exception:
                pass
        net = psutil.net_io_counters()
        battery = None
        try:
            b = psutil.sensors_battery()
            if b:
                battery = {"percent": b.percent, "plugged": b.power_plugged}
        except Exception:
            pass
        gpu = self._gpu()
        verbal = (f"CPU at {cpu['percent']:.0f}% across {cpu['cores']} cores, "
                  f"RAM {ram['percent']:.0f}% ({ram['used_gb']}/{ram['total_gb']} GB)")
        if battery:
            verbal += f", battery {battery['percent']:.0f}%"
        if gpu:
            verbal += f", GPU {gpu['util']}%"
        verbal += ", sir."
        return {"cpu": cpu, "ram": ram, "gpu": gpu, "disk": disk,
                "network": {"sent_mb": round(net.bytes_sent / 1e6, 1),
                            "recv_mb": round(net.bytes_recv / 1e6, 1)},
                "battery": battery, "result": {"cpu": cpu["percent"], "ram": ram["percent"]},
                "verbal": verbal}

    def _gpu(self):
        if not PYNVML:
            return None
        try:
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            return {"util": util.gpu, "vram_used_gb": round(mem.used / 1e9, 2)}
        except Exception:
            return None

    def get_temperatures(self) -> dict:
        if not PSUTIL or not hasattr(psutil, "sensors_temperatures"):
            return {"result": None, "verbal": "Temperature sensors unavailable, sir."}
        temps = psutil.sensors_temperatures()
        out = {k: [t.current for t in v] for k, v in temps.items()}
        hottest = max(((max(v), k) for k, v in out.items() if v), default=(None, None))
        return {"temperatures": out, "hottest_component": hottest[1], "result": out,
                "verbal": (f"Hottest component: {hottest[1]} at {hottest[0]:.0f}°C, sir."
                           if hottest[1] else "No temperature data, sir.")}

    def benchmark_cpu(self, duration=2.0) -> dict:
        import numpy as np
        start = time.time(); ops = 0
        while time.time() - start < duration:
            np.linalg.svd(np.random.rand(64, 64)); ops += 1
        return {"single_thread_score": ops, "n_cores": psutil.cpu_count() if PSUTIL else None,
                "result": ops,
                "verbal": f"CPU benchmark: {ops} SVD ops in {duration:.0f}s."}

    def kill_process(self, pid_or_name) -> dict:
        if not PSUTIL:
            return {"result": None, "verbal": "psutil not installed, sir."}
        for p in psutil.process_iter(["pid", "name"]):
            if str(p.info["pid"]) == str(pid_or_name) or p.info["name"] == pid_or_name:
                try:
                    p.terminate()
                    return {"success": True, "result": True,
                            "verbal": f"Terminated process {p.info['name']} (PID {p.info['pid']}), sir."}
                except Exception as e:
                    return {"success": False, "verbal": f"Could not terminate: {e}"}
        return {"success": False, "verbal": "No such process, sir."}

    def test(self) -> None:
        if PSUTIL:
            s = self.get_hardware_status()
            assert "cpu" in s and s["cpu"]["cores"] >= 1
        print("system_monitor.SystemMonitor: OK")


_engine = SystemMonitor()


def report(text: str = "") -> dict:
    low = text.lower()
    if "temp" in low:
        return _engine.get_temperatures()
    if "benchmark" in low:
        return _engine.benchmark_cpu()
    return _engine.get_hardware_status()


def test() -> None:
    SystemMonitor().test()


if __name__ == "__main__":
    test()
