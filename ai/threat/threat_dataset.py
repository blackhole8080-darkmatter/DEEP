"""
ai/threat/threat_dataset.py

Builds labelled training data by combining normal traffic, real threats, and synthetic attacks.
"""

from __future__ import annotations

import logging
import random
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from sklearn.utils import resample
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from core.config import Settings
except ImportError:
    from config import Settings

from ai.anomaly.network_baseline import NetworkFlowSnapshot
from ai.threat.feature_extractor import ThreatFeatureExtractor

logger = logging.getLogger(__name__)


class ThreatLabel(IntEnum):
    NORMAL = 0
    PORT_SCAN = 1
    BRUTE_FORCE = 2
    ARP_SPOOF = 3
    DEAUTH = 4
    EXFILTRATION = 5
    UNKNOWN_THREAT = 6


THREAT_TYPE_MAP: dict[str, ThreatLabel] = {
    "port_scan": ThreatLabel.PORT_SCAN,
    "brute_force": ThreatLabel.BRUTE_FORCE,
    "arp_spoof": ThreatLabel.ARP_SPOOF,
    "deauth": ThreatLabel.DEAUTH,
    "exfiltration": ThreatLabel.EXFILTRATION,
    "unknown": ThreatLabel.UNKNOWN_THREAT,
}


@dataclass
class ThreatSample:
    features: Any  # np.ndarray
    label: int
    threat_type: str
    timestamp: str
    is_synthetic: bool = False


@dataclass
class ThreatDataset:
    X: Any  # np.ndarray
    y: Any  # np.ndarray
    n_normal: int = 0
    n_real_threats: int = 0
    n_synthetic: int = 0
    class_distribution: dict[str, int] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.class_distribution is None:
            self.class_distribution = {}


class ThreatDatasetBuilder:
    """Builds labelled dataset for threat classifier training."""

    def __init__(
        self,
        network_baseline: Any,
        anomaly_db_path: Optional[str] = None,
    ) -> None:
        self.network_baseline = network_baseline
        self.settings = Settings()
        self._anomaly_db_path = Path(
            anomaly_db_path or getattr(self.settings, "anomaly_db_path", "logs/anomaly/deep_anomaly.db")
        )
        self._synthetic_per_class = int(getattr(self.settings, "synthetic_samples_per_class", 100))
        self._feature_extractor = ThreatFeatureExtractor(network_baseline)

    async def build_dataset(self) -> ThreatDataset:
        if not NUMPY_AVAILABLE:
            logger.error("numpy not available — cannot build dataset")
            return ThreatDataset(X=np.array([]), y=np.array([]))

        # 1. Normal traffic samples
        normal_flows = await self._load_normal_flows()
        normal_samples = await self._flows_to_samples(normal_flows, ThreatLabel.NORMAL, is_synthetic=False)

        # 2. Real threat events
        threat_flows = await self._load_threat_flows()
        threat_samples = await self._flows_to_samples(threat_flows, None, is_synthetic=False)

        # 3. Synthetic attack patterns
        synthetic_samples = self._generate_synthetic_attacks(self._synthetic_per_class)

        # Combine
        all_samples = normal_samples + threat_samples + synthetic_samples
        if not all_samples:
            logger.warning("[ThreatDatasetBuilder] No samples available — returning empty dataset")
            return ThreatDataset(X=np.array([]), y=np.array([]))

        # Balance classes
        balanced = self._balance_classes(all_samples)

        X = np.array([s.features for s in balanced])
        y = np.array([s.label for s in balanced])

        class_dist: dict[str, int] = {}
        for s in balanced:
            name = ThreatLabel(s.label).name
            class_dist[name] = class_dist.get(name, 0) + 1

        return ThreatDataset(
            X=X,
            y=y,
            n_normal=len(normal_samples),
            n_real_threats=len(threat_samples),
            n_synthetic=len(synthetic_samples),
            class_distribution=class_dist,
        )

    async def _load_normal_flows(self) -> List[NetworkFlowSnapshot]:
        """Load flows where no anomaly was detected within +/- 5 minutes."""
        if not self._anomaly_db_path.exists():
            return []

        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        with sqlite3.connect(str(self._anomaly_db_path)) as conn:
            conn.row_factory = sqlite3.Row
            # Get timestamps of anomalies
            anomaly_times = [
                r["timestamp"]
                for r in conn.execute(
                    "SELECT timestamp FROM anomalies WHERE anomaly_type = 'network' AND timestamp >= ?",
                    (cutoff,),
                ).fetchall()
            ]

            rows = conn.execute(
                "SELECT * FROM network_baseline WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 2000",
                (cutoff,),
            ).fetchall()

        flows = []
        for r in rows:
            ts = r["timestamp"]
            # Skip if anomaly within 5 min
            skip = False
            for ats in anomaly_times:
                try:
                    t1 = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(ats.replace("Z", "+00:00"))
                    if abs((t1 - t2).total_seconds()) < 300:
                        skip = True
                        break
                except Exception:
                    pass
            if not skip:
                flows.append(NetworkFlowSnapshot(**{k: r[k] for k in r.keys() if k in NetworkFlowSnapshot.__dataclass_fields__}))
        return flows

    async def _load_threat_flows(self) -> List[tuple[NetworkFlowSnapshot, ThreatLabel]]:
        """Load flows that coincide with threat_detected events from audit trail."""
        if not self._anomaly_db_path.exists():
            return []

        # Try to join with audit_log if it exists in the same DB
        try:
            with sqlite3.connect(str(self._anomaly_db_path)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT nb.*, a.threat_type
                    FROM network_baseline nb
                    JOIN audit_log a ON (
                        a.entry_type = 'THREAT_DETECTED'
                        AND a.timestamp BETWEEN datetime(nb.timestamp, '-5 minutes')
                                           AND datetime(nb.timestamp, '+5 minutes')
                    )
                    WHERE nb.timestamp >= datetime('now', '-30 days')
                    ORDER BY nb.timestamp DESC
                    LIMIT 500
                    """
                ).fetchall()
        except Exception:
            # Fallback: just load recent flows with no threat labels
            return []

        result = []
        for r in rows:
            flow = NetworkFlowSnapshot(**{k: r[k] for k in r.keys() if k in NetworkFlowSnapshot.__dataclass_fields__})
            threat_type = r.get("threat_type", "unknown")
            label = THREAT_TYPE_MAP.get(threat_type, ThreatLabel.UNKNOWN_THREAT)
            result.append((flow, label))
        return result

    async def _flows_to_samples(
        self,
        flows: List[Any],
        default_label: Optional[ThreatLabel],
        is_synthetic: bool = False,
    ) -> List[ThreatSample]:
        samples = []
        for item in flows:
            if isinstance(item, tuple):
                flow, label = item
            else:
                flow = item
                label = default_label
            try:
                vec = await self._feature_extractor.extract(flow)
                samples.append(
                    ThreatSample(
                        features=vec.features,
                        label=int(label) if label is not None else 0,
                        threat_type=ThreatLabel(label).name if label else "NORMAL",
                        timestamp=flow.timestamp,
                        is_synthetic=is_synthetic,
                    )
                )
            except Exception as exc:
                logger.debug(f"Feature extraction error: {exc}")
        return samples

    def _generate_synthetic_attacks(self, n_per_class: int) -> List[ThreatSample]:
        """Generate synthetic attack samples by perturbing normal patterns."""
        if not NUMPY_AVAILABLE:
            return []

        samples: List[ThreatSample] = []
        rng = np.random.RandomState(42)

        for label in [ThreatLabel.PORT_SCAN, ThreatLabel.BRUTE_FORCE, ThreatLabel.EXFILTRATION]:
            for _ in range(n_per_class):
                base = self._random_normal_flow(rng)
                perturbed = self._apply_attack_signature(base, label, rng)
                try:
                    # Build feature vector manually for synthetic data
                    features = self._build_synthetic_features(perturbed, label)
                    samples.append(
                        ThreatSample(
                            features=features,
                            label=int(label),
                            threat_type=label.name,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            is_synthetic=True,
                        )
                    )
                except Exception as exc:
                    logger.debug(f"Synthetic generation error: {exc}")
        return samples

    def _random_normal_flow(self, rng: Any) -> dict[str, float]:
        """Generate a plausible normal network flow."""
        return {
            "bytes_sent_ps": rng.uniform(1, 100),
            "bytes_recv_ps": rng.uniform(1, 100),
            "packets_sent_ps": rng.uniform(1, 50),
            "packets_recv_ps": rng.uniform(1, 50),
            "active_connections": rng.randint(5, 50),
            "unique_remote_ips": rng.randint(3, 20),
            "new_connections_ps": rng.uniform(0.1, 2.0),
            "connection_duration_avg": rng.uniform(10, 300),
            "dns_queries_ps": rng.uniform(0.5, 5.0),
            "hour": rng.randint(0, 23),
            "day_of_week": rng.randint(0, 6),
        }

    def _apply_attack_signature(
        self,
        base: dict[str, float],
        label: ThreatLabel,
        rng: Any,
    ) -> dict[str, float]:
        p = dict(base)
        noise = lambda: rng.normal(0, 0.1)

        if label == ThreatLabel.PORT_SCAN:
            p["unique_remote_ips"] = rng.randint(50, 200)
            p["new_connections_ps"] = rng.uniform(10, 50)
            p["bytes_sent_ps"] = rng.uniform(0.1, 5.0)
            p["connection_duration_avg"] = rng.uniform(0.1, 0.5)

        elif label == ThreatLabel.BRUTE_FORCE:
            p["unique_remote_ips"] = 1
            p["new_connections_ps"] = rng.uniform(20, 100)
            p["active_connections"] = rng.randint(20, 80)
            p["connection_duration_avg"] = rng.uniform(0.5, 2.0)

        elif label == ThreatLabel.EXFILTRATION:
            p["bytes_sent_ps"] = rng.uniform(500, 2000)
            p["bytes_recv_ps"] = rng.uniform(1, 10)
            p["connection_duration_avg"] = rng.uniform(600, 1800)
            p["hour"] = rng.choice([23, 0, 1, 2, 3, 4])

        # Add Gaussian noise for variety
        for k in p:
            if isinstance(p[k], float):
                p[k] = max(0, p[k] + noise() * p[k])
        return p

    def _build_synthetic_features(
        self, flow: dict[str, float], label: ThreatLabel
    ) -> Any:
        """Build a feature vector from a synthetic flow dict."""
        base = [flow.get(f, 0.0) for f in [
            "bytes_sent_ps", "bytes_recv_ps",
            "packets_sent_ps", "packets_recv_ps",
            "active_connections", "unique_remote_ips",
            "new_connections_ps", "connection_duration_avg",
            "dns_queries_ps",
        ]]

        send_recv = flow["bytes_sent_ps"] / max(flow["bytes_recv_ps"], 0.001)
        packet_size = flow["bytes_sent_ps"] / max(flow["packets_sent_ps"], 0.001)
        conn_density = flow["active_connections"] / max(flow["unique_remote_ips"], 1)

        cpu_z = 0.0
        net_z = 0.0
        conn_z = 0.0
        dns_z = 0.0

        hour = int(flow["hour"])
        dow = int(flow["day_of_week"])
        time_features = [
            float(np.sin(2 * np.pi * hour / 24)),
            float(np.cos(2 * np.pi * hour / 24)),
            1.0 if hour in [23, 0, 1, 2, 3, 4] else 0.0,
            float(np.sin(2 * np.pi * dow / 7)),
            float(np.cos(2 * np.pi * dow / 7)),
        ]

        return np.array(
            base + [send_recv, packet_size, conn_density, cpu_z, net_z, conn_z, dns_z] + time_features,
            dtype=np.float32,
        )

    def _balance_classes(self, samples: List[ThreatSample]) -> List[ThreatSample]:
        """Oversample minority classes to match majority."""
        if not SKLEARN_AVAILABLE:
            return samples

        from collections import Counter

        counts = Counter(s.label for s in samples)
        if not counts:
            return samples

        max_count = max(counts.values())
        balanced: List[ThreatSample] = []
        for label in counts:
            class_samples = [s for s in samples if s.label == label]
            if not class_samples:
                continue
            oversampled = resample(
                class_samples,
                n_samples=max_count,
                replace=True,
                random_state=42,
            )
            balanced.extend(oversampled)

        random.shuffle(balanced)
        return balanced
