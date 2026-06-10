"""
core/graph_analytics.py — network science over the memory graph (NetworkX).

Replaces hand-rolled JS heuristics with real algorithms at the right scale
(~hundreds of nodes — NetworkX on CPU is ideal; no GPU/WholeGraph needed):

  • PageRank            → memory IMPORTANCE (which nodes are central)
  • Greedy modularity   → real COMMUNITIES (Louvain-style)
  • Betweenness         → BRIDGE memories connecting different topics
  • Link prediction     → SUGGESTED connections (resource-allocation / Adamic-Adar):
                          memory pairs structurally close but not yet linked.
  • Graph metrics       → density, avg clustering, component/community counts.

Fail-soft: any error returns empty so the vault still serves. Runs off the event
loop (caller uses asyncio.to_thread).
"""

from __future__ import annotations

import heapq
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def analyze(entities: List[Dict[str, Any]],
            relationships: List[Dict[str, Any]],
            max_suggestions: int = 40) -> Dict[str, Any]:
    try:
        import networkx as nx
    except Exception as e:  # networkx absent → caller falls back to JS heuristics
        logger.warning(f"[graph_analytics] networkx unavailable: {e}")
        return {}

    ids = {e.get("id") for e in entities if e.get("id")}
    G = nx.Graph()
    G.add_nodes_from(ids)
    for r in relationships:
        s, t = r.get("source"), r.get("target")
        if s in ids and t in ids and s != t:
            w = float(r.get("confidence", 0.5) or 0.5)
            # keep the strongest weight if the pair appears twice
            if G.has_edge(s, t):
                G[s][t]["weight"] = max(G[s][t]["weight"], w)
            else:
                G.add_edge(s, t, weight=w)

    n = G.number_of_nodes()
    if n == 0:
        return {}

    out: Dict[str, Any] = {}
    try:
        out["pagerank"] = nx.pagerank(G, weight="weight")
    except Exception:
        out["pagerank"] = {nd: 1.0 / n for nd in G}

    # Betweenness can be O(V·E); sample pivots on bigger graphs to stay fast.
    try:
        k = min(n, 100)
        out["betweenness"] = nx.betweenness_centrality(G, k=k, weight=None, seed=7)
    except Exception:
        out["betweenness"] = {}

    # Communities via greedy modularity (Louvain-style, weighted).
    comm_of: Dict[str, int] = {}
    n_comms = 0
    try:
        comms = list(nx.community.greedy_modularity_communities(G, weight="weight"))
        comms.sort(key=len, reverse=True)
        n_comms = len(comms)
        for i, c in enumerate(comms):
            for nd in c:
                comm_of[nd] = i
    except Exception as e:
        logger.warning(f"[graph_analytics] community failed: {e}")
    out["community"] = comm_of

    # Link prediction → suggested connections (resource allocation over non-edges).
    suggestions: List[Dict[str, Any]] = []
    try:
        preds = nx.resource_allocation_index(G)   # generator over all non-edges
        top = heapq.nlargest(max_suggestions, ((p, u, v) for u, v, p in preds if p > 0),
                             key=lambda x: x[0])
        suggestions = [{"source": u, "target": v, "score": round(p, 3), "kind": "suggested"}
                       for p, u, v in top]
    except Exception as e:
        logger.warning(f"[graph_analytics] link prediction failed: {e}")
    out["suggestions"] = suggestions

    # Headline metrics for an "insights" readout.
    try:
        pr = out["pagerank"]
        top_central = sorted(pr, key=pr.get, reverse=True)[:5]
        name_of = {e["id"]: e.get("name", "?") for e in entities if e.get("id")}
        out["metrics"] = {
            "nodes": n,
            "edges": G.number_of_edges(),
            "communities": n_comms,
            "density": round(nx.density(G), 4),
            "avg_clustering": round(nx.average_clustering(G), 4),
            "components": nx.number_connected_components(G),
            "top_central": [name_of.get(i, i) for i in top_central],
        }
    except Exception:
        out["metrics"] = {"nodes": n, "edges": G.number_of_edges()}

    return out
