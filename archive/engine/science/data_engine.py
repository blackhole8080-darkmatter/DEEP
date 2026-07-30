# deep/science/data_engine.py — Data Analysis & Reporting (Bible Section 1 tree)
"""Tabular data analysis: descriptive statistics, correlation, outlier
detection, simple linear trend, and a text/markdown report generator. Works on
CSV paths or array-likes. pandas optional (numpy fallback)."""
from __future__ import annotations

import os

import numpy as np

try:
    import pandas as pd
    PANDAS = True
except Exception:  # pragma: no cover
    PANDAS = False

try:
    from .. import config
    REPORTS_DIR = str(config.REPORTS_DIR)
except Exception:  # pragma: no cover
    REPORTS_DIR = os.path.join(os.path.expanduser("~"), "deep_output", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


class DataEngine:
    def __init__(self, config=None):
        self.config = config

    def describe(self, data) -> dict:
        arr = self._as_array(data)
        stats = {"n": int(arr.shape[0]),
                 "mean": np.nanmean(arr, axis=0).tolist(),
                 "std": np.nanstd(arr, axis=0).tolist(),
                 "min": np.nanmin(arr, axis=0).tolist(),
                 "max": np.nanmax(arr, axis=0).tolist()}
        return {"stats": stats, "result": stats,
                "verbal": f"Described {stats['n']} rows × "
                          f"{arr.shape[1] if arr.ndim > 1 else 1} column(s)."}

    def correlation(self, data) -> dict:
        arr = self._as_array(data)
        if arr.ndim < 2 or arr.shape[1] < 2:
            return {"result": None, "verbal": "Need at least 2 columns for correlation, sir."}
        corr = np.corrcoef(arr, rowvar=False)
        # strongest off-diagonal pair
        c = corr.copy(); np.fill_diagonal(c, 0)
        i, j = np.unravel_index(np.argmax(np.abs(c)), c.shape)
        return {"correlation_matrix": corr.tolist(),
                "strongest_pair": (int(i), int(j), float(c[i, j])), "result": corr.tolist(),
                "verbal": f"Strongest correlation: columns {i}&{j} at r={c[i, j]:.3f}."}

    def detect_outliers(self, data, z=3.0) -> dict:
        arr = self._as_array(data).ravel().astype(float)
        mu, sd = np.nanmean(arr), np.nanstd(arr)
        outliers = np.where(np.abs(arr - mu) > z * sd)[0]
        return {"outlier_indices": outliers.tolist(), "n_outliers": len(outliers),
                "result": len(outliers),
                "verbal": f"Found {len(outliers)} outlier(s) beyond {z}σ."}

    def linear_trend(self, y, x=None) -> dict:
        y = np.asarray(y, float)
        x = np.arange(len(y)) if x is None else np.asarray(x, float)
        slope, intercept = np.polyfit(x, y, 1)
        pred = slope * x + intercept
        ss_res = np.sum((y - pred) ** 2); ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot else 0
        return {"slope": float(slope), "intercept": float(intercept), "r2": float(r2),
                "result": {"slope": float(slope), "r2": float(r2)},
                "verbal": f"Linear trend: slope {slope:.4f}, R² {r2:.3f} "
                          f"({'rising' if slope > 0 else 'falling'})."}

    def generate_report(self, data, title="DEEP Data Report") -> dict:
        desc = self.describe(data)["stats"]
        lines = [f"# {title}", "", f"- Rows analysed: {desc['n']}",
                 f"- Means: {[round(m, 3) for m in np.atleast_1d(desc['mean'])]}",
                 f"- Std dev: {[round(s, 3) for s in np.atleast_1d(desc['std'])]}", ""]
        path = os.path.join(REPORTS_DIR, "report.md")
        open(path, "w", encoding="utf-8").write("\n".join(lines))
        return {"report_path": path, "result": path,
                "verbal": f"Report written to {os.path.basename(path)}, sir."}

    @staticmethod
    def _as_array(data):
        if PANDAS and isinstance(data, str) and data.endswith(".csv"):
            return pd.read_csv(data).select_dtypes("number").to_numpy()
        if PANDAS and isinstance(data, pd.DataFrame):
            return data.select_dtypes("number").to_numpy()
        return np.asarray(data, float)

    def test(self) -> None:
        rng = np.random.default_rng(0)
        X = rng.normal(0, 1, (100, 3))
        assert self.describe(X)["stats"]["n"] == 100
        assert self.correlation(X)["result"]
        assert "slope" in self.linear_trend(np.arange(20) + rng.normal(0, 0.1, 20))
        print("data_engine.DataEngine: OK")


def test() -> None:
    DataEngine().test()


if __name__ == "__main__":
    test()
