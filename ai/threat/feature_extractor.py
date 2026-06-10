"""
ai/threat/feature_extractor.py

Builds rich feature vectors from network flow data for classifier input.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, List, Optional

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from ai.anomaly.network_baseline import NetworkBaseline, NetworkFlowSnapshot
from ai.anomaly.system_baseline import SystemBaseline, SystemSnapshot

logger = logging.getLogger(__name__)

FEATURE_NAMES: list[str] = [
    # Flow volume features (0-7)
    "bytes_sent_ps", "bytes_recv_ps",
    "packets_sent_ps", "packets_recv_ps",
    # Connection features (4-7)
    "active_connections", "unique_remote_ips",
    "new_connections_ps", "connection_duration_avg",
    # DNS features (8)
    "dns_queries_ps",
    # Ratio features (9-11)
    "send_recv_ratio",
    "packet_size_avg",
    "connection_density",
    # Temporal deviation features (12-15)
    "cpu_z_score",
    "net_recv_z_score",
    "connection_z_score",
    "dns_z_score",
    # Time context features (16-20)
    "hour_sin",
    "hour_cos",
    "is_night",
    "day_of_week_sin",
    "day_of_week_cos",
]

BASE_FEATURE_NAMES = [
    "bytes_sent_ps", "bytes_recv_ps",
    "packets_sent_ps", "packets_recv_ps",
    "active_connections", "unique_remote_ips",
    "new_connections_ps", "connection_duration_avg",
    "dns_queries_ps",
]

Z_SCORE_METRICS = ["net_recv_ps", "active_connections", "dns_queries_ps"]


@dataclass
class ThreatFeatureVector:
    features: Any  # np.ndarray shape: (21,)
    feature_names: list[str]
    timestamp: str
    raw_snapshot: dict


class ThreatFeatureExtractor:
    """Extracts rich feature vectors from network flow data."""

    def __init__(self, network_baseline: NetworkBaseline) -> None:
        self.network_baseline = network_baseline

    async def extract(
        self,
        flow_snapshot: NetworkFlowSnapshot,
        system_snapshot: Optional[SystemSnapshot] = None,
    ) -> ThreatFeatureVector:
        if not NUMPY_AVAILABLE:
            raise RuntimeError("numpy not available — cannot extract features")

        # Base features from snapshot
        base = [getattr(flow_snapshot, f, 0.0) for f in BASE_FEATURE_NAMES]

        # Derived ratio features
        send_recv = flow_snapshot.bytes_sent_ps / max(flow_snapshot.bytes_recv_ps, 0.001)
        packet_size = flow_snapshot.bytes_sent_ps / max(flow_snapshot.packets_sent_ps, 0.001)
        conn_density = flow_snapshot.active_connections / max(flow_snapshot.unique_remote_ips, 1)

        # Z-score deviation from baseline
        stats = await self.network_baseline.get_baseline_stats(
            flow_snapshot.hour, flow_snapshot.day_of_week
        )

        z_scores: list[float] = []
        for metric in Z_SCORE_METRICS:
            if stats and metric in stats and stats[metric]["std"] > 0:
                z = (getattr(flow_snapshot, metric, 0) - stats[metric]["mean"]) / stats[metric]["std"]
                z_scores.append(float(np.clip(z, -10, 10)))
            else:
                z_scores.append(0.0)

        # CPU z-score
        if system_snapshot:
            cpu_z = _compute_z(
                system_snapshot.cpu_percent,
                50.0,  # default mean
                15.0,  # default std
            )
        else:
            cpu_z = 0.0

        # Cyclic time encoding
        hour = flow_snapshot.hour
        dow = flow_snapshot.day_of_week
        time_features = [
            float(np.sin(2 * np.pi * hour / 24)),
            float(np.cos(2 * np.pi * hour / 24)),
            1.0 if hour in [23, 0, 1, 2, 3, 4] else 0.0,
            float(np.sin(2 * np.pi * dow / 7)),
            float(np.cos(2 * np.pi * dow / 7)),
        ]

        full_vector = np.array(
            base + [send_recv, packet_size, conn_density, cpu_z] + z_scores + time_features,
            dtype=np.float32,
        )

        return ThreatFeatureVector(
            features=full_vector,
            feature_names=FEATURE_NAMES,
            timestamp=flow_snapshot.timestamp,
            raw_snapshot=flow_snapshot.__dict__,
        )


def _compute_z(value: float, mean: float, std: float) -> float:
    if std <= 0:
        return 0.0
    z = (value - mean) / std
    if NUMPY_AVAILABLE:
        return float(np.clip(z, -10, 10))
    return max(-10.0, min(10.0, z))
