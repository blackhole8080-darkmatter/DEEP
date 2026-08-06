"""
core/network_topology_graph.py — Unified multi-layer network graph

SQLite-backed graph storing LAN hosts, WiFi APs, Bluetooth devices,
VPN peers, DNS domains, internet endpoints, and LLM providers as nodes
with typed edges linking them across layers.

Schema:
  nodes         — id, layer, label, metadata_json, x, y, first_seen, last_seen
  edges         — source_id, target_id, layer, relation_type, strength, metadata_json
  observations  — timestamp, node_id, metric, value
  inferences    — timestamp, node_id, inference_type, confidence, explanation
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

import logging

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _DATA_DIR / "network_graph.db"

LAYERS = ["lan", "wifi", "bluetooth", "vpn", "internet", "dns", "ai"]
NODE_TYPES = {
    "lan": ["host", "gateway", "router"],
    "wifi": ["ap", "client"],
    "bluetooth": ["bt_device", "beacon"],
    "vpn": ["tailscale_peer", "exit_node"],
    "internet": ["external_ip", "asn", "country"],
    "dns": ["domain", "nameserver"],
    "ai": ["llm_provider", "model"],
}


@dataclass
class GraphNode:
    id: str
    layer: str
    node_type: str
    label: str
    metadata: dict
    x: float = 0.0
    y: float = 0.0
    first_seen: str = ""
    last_seen: str = ""


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    layer: str
    relation_type: str
    strength: float = 1.0
    metadata: dict = None  # type: ignore[assignment]


class NetworkTopologyGraph:
    """Persistent multi-layer network graph for DEEP."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db = db_path or str(_DB_PATH)
        self._init_schema()

    def _init_schema(self) -> None:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    layer TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    metadata_json TEXT DEFAULT '{}',
                    x REAL DEFAULT 0,
                    y REAL DEFAULT 0,
                    first_seen TEXT DEFAULT (datetime('now')),
                    last_seen TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_nodes_layer ON nodes(layer);
                CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);

                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    layer TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    strength REAL DEFAULT 1.0,
                    metadata_json TEXT DEFAULT '{}',
                    first_seen TEXT DEFAULT (datetime('now')),
                    last_seen TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(source_id);
                CREATE INDEX IF NOT EXISTS idx_edges_tgt ON edges(target_id);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_edges_pair ON edges(source_id, target_id, relation_type);

                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT (datetime('now')),
                    node_id TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL,
                    context_json TEXT DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_obs_node ON observations(node_id);
                CREATE INDEX IF NOT EXISTS idx_obs_time ON observations(timestamp);

                CREATE TABLE IF NOT EXISTS inferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT (datetime('now')),
                    node_id TEXT NOT NULL,
                    inference_type TEXT NOT NULL,
                    confidence REAL,
                    explanation TEXT,
                    context_json TEXT DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_inf_node ON inferences(node_id);
                """
            )

    # ── Node CRUD ─────────────────────────────────────────────────────────────
    def upsert_node(self, node_id: str, layer: str, node_type: str, label: str, metadata: Optional[dict] = None, x: float = 0.0, y: float = 0.0) -> None:
        now = datetime.now(timezone.utc).isoformat()
        meta = json.dumps(metadata or {})
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                """
                INSERT INTO nodes (id, layer, node_type, label, metadata_json, x, y, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    layer=excluded.layer,
                    node_type=excluded.node_type,
                    label=excluded.label,
                    metadata_json=excluded.metadata_json,
                    x=excluded.x,
                    y=excluded.y,
                    last_seen=excluded.last_seen
                """,
                (node_id, layer, node_type, label, meta, x, y, now, now),
            )

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        if not row:
            return None
        return GraphNode(
            id=row["id"], layer=row["layer"], node_type=row["node_type"], label=row["label"],
            metadata=json.loads(row["metadata_json"]), x=row["x"], y=row["y"],
            first_seen=row["first_seen"], last_seen=row["last_seen"],
        )

    def list_nodes(self, layer: Optional[str] = None, node_type: Optional[str] = None, limit: int = 1000) -> List[GraphNode]:
        sql = "SELECT * FROM nodes"
        params: List[Any] = []
        where = []
        if layer:
            where.append("layer = ?")
            params.append(layer)
        if node_type:
            where.append("node_type = ?")
            params.append(node_type)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += f" ORDER BY last_seen DESC LIMIT {limit}"
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        return [
            GraphNode(
                id=r["id"], layer=r["layer"], node_type=r["node_type"], label=r["label"],
                metadata=json.loads(r["metadata_json"]), x=r["x"], y=r["y"],
                first_seen=r["first_seen"], last_seen=r["last_seen"],
            )
            for r in rows
        ]

    def delete_node(self, node_id: str) -> None:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", (node_id, node_id))
            conn.execute("DELETE FROM observations WHERE node_id = ?", (node_id,))
            conn.execute("DELETE FROM inferences WHERE node_id = ?", (node_id,))
            conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))

    # ── Edge CRUD ────────────────────────────────────────────────────────────
    def upsert_edge(self, source_id: str, target_id: str, layer: str, relation_type: str, strength: float = 1.0, metadata: Optional[dict] = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        meta = json.dumps(metadata or {})
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                """
                INSERT INTO edges (source_id, target_id, layer, relation_type, strength, metadata_json, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, relation_type) DO UPDATE SET
                    layer=excluded.layer,
                    strength=excluded.strength,
                    metadata_json=excluded.metadata_json,
                    last_seen=excluded.last_seen
                """,
                (source_id, target_id, layer, relation_type, strength, meta, now, now),
            )

    def get_edges(self, node_id: Optional[str] = None, layer: Optional[str] = None) -> List[GraphEdge]:
        sql = "SELECT * FROM edges"
        params: List[Any] = []
        where = []
        if node_id:
            where.append("(source_id = ? OR target_id = ?)")
            params.extend([node_id, node_id])
        if layer:
            where.append("layer = ?")
            params.append(layer)
        if where:
            sql += " WHERE " + " AND ".join(where)
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        return [
            GraphEdge(
                source_id=r["source_id"], target_id=r["target_id"], layer=r["layer"],
                relation_type=r["relation_type"], strength=r["strength"],
                metadata=json.loads(r["metadata_json"]),
            )
            for r in rows
        ]

    # ── Observations (time-series) ──────────────────────────────────────────
    def add_observation(self, node_id: str, metric: str, value: float, context: Optional[dict] = None) -> None:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "INSERT INTO observations (node_id, metric, value, context_json) VALUES (?, ?, ?, ?)",
                (node_id, metric, value, json.dumps(context or {})),
            )

    def get_observations(self, node_id: str, metric: Optional[str] = None, hours: int = 24) -> List[dict]:
        sql = "SELECT * FROM observations WHERE node_id = ? AND timestamp >= datetime('now', ?)"
        params: List[Any] = [node_id, f"-{hours} hours"]
        if metric:
            sql += " AND metric = ?"
            params.append(metric)
        sql += " ORDER BY timestamp DESC"
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ── Inferences (AI-generated) ───────────────────────────────────────────
    def add_inference(self, node_id: str, inference_type: str, confidence: float, explanation: str, context: Optional[dict] = None) -> None:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "INSERT INTO inferences (node_id, inference_type, confidence, explanation, context_json) VALUES (?, ?, ?, ?, ?)",
                (node_id, inference_type, confidence, explanation, json.dumps(context or {})),
            )

    def get_inferences(self, node_id: str, inference_type: Optional[str] = None, limit: int = 20) -> List[dict]:
        sql = "SELECT * FROM inferences WHERE node_id = ?"
        params: List[Any] = [node_id]
        if inference_type:
            sql += " AND inference_type = ?"
            params.append(inference_type)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ── Full graph export ───────────────────────────────────────────────────
    def export_graph(self, layer: Optional[str] = None) -> dict:
        nodes = self.list_nodes(layer=layer)
        edges = self.get_edges(layer=layer) if layer else self.get_edges()
        return {
            "nodes": [{"id": n.id, "layer": n.layer, "node_type": n.node_type, "label": n.label,
                       "metadata": n.metadata, "x": n.x, "y": n.y, "last_seen": n.last_seen} for n in nodes],
            "edges": [{"source": e.source_id, "target": e.target_id, "layer": e.layer,
                       "relation": e.relation_type, "strength": e.strength, "metadata": e.metadata} for e in edges],
        }

    def export_subgraph(self, centre_id: str, depth: int = 1) -> dict:
        """Export nodes within N hops of centre_id."""
        visited = {centre_id}
        frontier = {centre_id}
        all_edges = []
        for _ in range(depth):
            next_frontier = set()
            for nid in frontier:
                edges = self.get_edges(node_id=nid)
                for e in edges:
                    all_edges.append(e)
                    other = e.source_id if e.target_id == nid else e.target_id
                    if other not in visited:
                        visited.add(other)
                        next_frontier.add(other)
            frontier = next_frontier
        nodes = [n for n in [self.get_node(i) for i in visited] if n]
        return {
            "nodes": [{"id": n.id, "layer": n.layer, "node_type": n.node_type, "label": n.label,
                       "metadata": n.metadata, "x": n.x, "y": n.y, "last_seen": n.last_seen} for n in nodes],
            "edges": [{"source": e.source_id, "target": e.target_id, "layer": e.layer,
                       "relation": e.relation_type, "strength": e.strength, "metadata": e.metadata} for e in all_edges],
        }

    # ── Statistics ──────────────────────────────────────────────────────────
    def stats(self) -> dict:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            node_counts = {row["layer"]: row["c"] for row in conn.execute("SELECT layer, COUNT(*) as c FROM nodes GROUP BY layer").fetchall()}
            edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            obs_count = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
            inf_count = conn.execute("SELECT COUNT(*) FROM inferences").fetchone()[0]
        return {"nodes_by_layer": node_counts, "edges": edge_count, "observations": obs_count, "inferences": inf_count}


# ── singleton ────────────────────────────────────────────────────────────────
_graph: Optional[NetworkTopologyGraph] = None


def get_network_graph() -> NetworkTopologyGraph:
    global _graph
    if _graph is None:
        _graph = NetworkTopologyGraph()
    return _graph


if __name__ == "__main__":
    g = NetworkTopologyGraph()
    g.upsert_node("gw_001", "lan", "gateway", "Home Router", {"ip": "192.168.1.1", "mac": "AA:BB:CC:11:22:33"})
    g.upsert_node("host_001", "lan", "host", "Aryan's Laptop", {"ip": "192.168.1.45", "mac": "AA:BB:CC:44:55:66"})
    g.upsert_edge("host_001", "gw_001", "lan", "connected_via", 1.0, {"interface": "eth0"})
    print(g.export_graph())
