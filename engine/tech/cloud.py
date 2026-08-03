# deep/tech/cloud.py — Cloud & Distributed Systems (Bible Section 24)
"""Federated learning (FedAvg), model quantisation, ONNX export, edge
benchmarking, FastAPI serving stubs. numpy core; torch/onnx/docker optional."""
from __future__ import annotations

import time

import numpy as np

try:
    import torch  # noqa: F401
    TORCH = True
except Exception:  # pragma: no cover
    TORCH = False


class CloudEngine:
    def __init__(self, config=None):
        self.config = config

    # ── federated learning ──────────────────────────────────────────
    def fed_avg(self, client_weights, client_sizes=None) -> dict:
        """Federated averaging of model weight vectors (FedAvg)."""
        weights = [np.asarray(w, float) for w in client_weights]
        n = len(weights)
        sizes = np.asarray(client_sizes if client_sizes else [1] * n, float)
        sizes = sizes / sizes.sum()
        agg = sum(s * w for s, w in zip(sizes, weights))
        divergence = float(np.mean([np.linalg.norm(w - agg) for w in weights]))
        return {"global_weights": agg.tolist(), "client_divergence": divergence,
                "result": {"divergence": divergence},
                "verbal": f"FedAvg aggregated {n} client models; mean client "
                          f"divergence {divergence:.4f}."}

    # ── quantisation ────────────────────────────────────────────────
    def quantise(self, weights, bits=8) -> dict:
        w = np.asarray(weights, float)
        qmax = 2 ** (bits - 1) - 1
        scale = np.abs(w).max() / qmax if w.size else 1.0
        q = np.round(w / scale).astype(int)
        deq = q * scale
        err = float(np.mean((w - deq) ** 2))
        compression = 32 / bits
        return {"scale": scale, "mse": err, "compression_ratio": compression,
                "result": {"compression": compression, "mse": err},
                "verbal": f"Quantised to int{bits}: {compression:.0f}× smaller, "
                          f"reconstruction MSE {err:.2e}."}

    # ── ONNX export (guarded) ───────────────────────────────────────
    def onnx_export(self, model=None) -> dict:
        try:
            import onnx  # noqa: F401
        except Exception:
            return {"result": None,
                    "verbal": "ONNX export needs the onnx package, sir — not installed."}
        return {"result": "ready",
                "verbal": "ONNX exporter ready; pass a torch.nn.Module and sample input, sir."}

    # ── edge benchmark ──────────────────────────────────────────────
    def edge_benchmark(self, matrix_size=512, iterations=5) -> dict:
        times = []
        for _ in range(iterations):
            A = np.random.randn(matrix_size, matrix_size)
            B = np.random.randn(matrix_size, matrix_size)
            t0 = time.perf_counter()
            A @ B
            times.append(time.perf_counter() - t0)
        avg = float(np.mean(times))
        gflops = (2 * matrix_size**3) / avg / 1e9
        return {"avg_time_s": avg, "gflops": gflops, "result": {"gflops": gflops},
                "verbal": f"Edge benchmark: {matrix_size}×{matrix_size} matmul in "
                          f"{avg*1000:.1f} ms ({gflops:.1f} GFLOP/s)."}

    def serve_info(self) -> dict:
        return {"result": None,
                "verbal": "FastAPI model serving: POST /predict with a JSON feature vector; "
                          "Docker/K8s deployment configs are generated on request, sir."}

    def test(self) -> None:
        fa = self.fed_avg([[1, 2, 3], [3, 2, 1], [2, 2, 2]])
        assert abs(fa["global_weights"][0] - 2.0) < 1e-9
        q = self.quantise(np.random.randn(1000), 8)
        assert q["compression_ratio"] == 4
        b = self.edge_benchmark(128, 2)
        assert b["gflops"] > 0
        print("cloud.CloudEngine: OK")


_engine = CloudEngine()


def execute(text: str) -> dict:
    low = text.lower()
    if "quantis" in low or "quantiz" in low or "compress" in low:
        return _engine.quantise(np.random.randn(1000), 8)
    if "onnx" in low or "export" in low:
        return _engine.onnx_export()
    if "benchmark" in low or "edge" in low:
        return _engine.edge_benchmark()
    if "serve" in low or "api" in low or "deploy" in low or "docker" in low or "kubernetes" in low:
        return _engine.serve_info()
    return _engine.edge_benchmark()


def distributed_ml(text: str) -> dict:
    low = text.lower()
    if "federated" in low or "fedavg" in low:
        return _engine.fed_avg([np.random.randn(10) for _ in range(5)])
    return _engine.fed_avg([np.random.randn(10) for _ in range(5)])


def test() -> None:
    CloudEngine().test()


if __name__ == "__main__":
    test()
