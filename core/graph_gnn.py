"""
core/graph_gnn.py — a real Graph Neural Network over the memory graph (CPU).

This is the genuine GNN/Graph-ML layer, right-sized for ~hundreds of nodes:

  • Builds a PyTorch-Geometric graph: node features = the entity's MiniLM
    embedding (reused from graph_enrich's cache), edges = the memory relationships.
  • A 2-layer **GraphSAGE** encoder, trained UNSUPERVISED with a link-prediction
    objective (positive edges vs. negatively-sampled non-edges, BCE) for a few
    dozen epochs — message passing fuses each node's own meaning with its
    neighbourhood, producing structure-aware embeddings.
  • From the trained embeddings: GNN-predicted "missing links" (highest-scoring
    non-edges) and KMeans clusters over the learned space.

Runs on CPU (PyTorch is CPU-only here) in a few seconds at this scale. NVIDIA
WholeGraph / cuGraph are deliberately NOT used: they require a CUDA GPU and target
billion-edge multi-GPU training — wrong tool for a personal memory graph. Fail-soft.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _node_features(entities: List[Dict[str, Any]]):
    """Reuse the MiniLM vectors graph_enrich already computed/persisted; fall back
    to a fresh embed for any entity without a cached vector."""
    import numpy as np
    from core import graph_enrich as ge

    ge._load_cache()
    vecs, missing, missing_idx = [], [], []
    dim = 384
    for i, e in enumerate(entities):
        doc = ge._doc_for(e, (e.get("context") or [""])[0])
        v = ge._VEC_CACHE.get(ge._hash(doc))
        if v is not None:
            dim = len(v); vecs.append(v)
        else:
            vecs.append(None); missing.append(doc); missing_idx.append(i)
    if missing:
        emb = ge._get_model().encode(missing, normalize_embeddings=True)
        for j, i in enumerate(missing_idx):
            vecs[i] = np.asarray(emb[j], dtype="float32")
    return np.vstack([(v if v is not None else np.zeros(dim, dtype="float32")) for v in vecs])


def run_gnn(entities: List[Dict[str, Any]],
            relationships: List[Dict[str, Any]],
            epochs: int = 60,
            dim_out: int = 64,
            top_links: int = 30) -> Dict[str, Any]:
    """Train a GraphSAGE link-predictor and return predicted links + clusters.
    Returns {} on any failure (caller keeps the NetworkX results)."""
    try:
        import torch
        import torch.nn.functional as F
        from torch_geometric.nn import SAGEConv
        from torch_geometric.utils import negative_sampling
    except Exception as e:
        logger.warning(f"[graph_gnn] torch/PyG unavailable: {e}")
        return {}

    try:
        torch.manual_seed(7)
        ids = [e.get("id") for e in entities if e.get("id")]
        idx = {nid: i for i, nid in enumerate(ids)}
        n = len(ids)
        if n < 8:
            return {}

        X = torch.tensor(_node_features(entities), dtype=torch.float32)

        src, dst = [], []
        for r in relationships:
            s, t = idx.get(r.get("source")), idx.get(r.get("target"))
            if s is not None and t is not None and s != t:
                src += [s, t]; dst += [t, s]   # undirected
        if len(src) < 4:
            return {}
        edge_index = torch.tensor([src, dst], dtype=torch.long)

        class SAGE(torch.nn.Module):
            def __init__(self, di, dh, do):
                super().__init__()
                self.c1 = SAGEConv(di, dh)
                self.c2 = SAGEConv(dh, do)
            def forward(self, x, ei):
                x = F.relu(self.c1(x, ei))
                return self.c2(x, ei)

        model = SAGE(X.size(1), 128, dim_out)
        opt = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)

        def decode(z, ei):
            return (z[ei[0]] * z[ei[1]]).sum(dim=-1)

        model.train()
        for ep in range(epochs):
            opt.zero_grad()
            z = model(X, edge_index)
            neg = negative_sampling(edge_index, num_nodes=n, num_neg_samples=edge_index.size(1))
            pos_l = decode(z, edge_index)
            neg_l = decode(z, neg)
            logits = torch.cat([pos_l, neg_l])
            labels = torch.cat([torch.ones_like(pos_l), torch.zeros_like(neg_l)])
            loss = F.binary_cross_entropy_with_logits(logits, labels)
            loss.backward(); opt.step()

        model.eval()
        with torch.no_grad():
            z = F.normalize(model(X, edge_index), dim=1)

        # GNN-predicted missing links: highest cosine non-edges (sampled for speed).
        existing = set()
        for a, b in zip(src, dst):
            existing.add((a, b))
        sims = z @ z.t()
        sims.fill_diagonal_(-2.0)
        k = min(top_links * 6, n * n)
        flat = sims.flatten()
        vals, order = torch.topk(flat, k)
        preds, seen = [], set()
        for v, o in zip(vals.tolist(), order.tolist()):
            a, b = o // n, o % n
            if a == b or (a, b) in existing:
                continue
            key = (min(a, b), max(a, b))
            if key in seen:
                continue
            seen.add(key)
            preds.append({"source": ids[a], "target": ids[b],
                          "score": round((v + 1) / 2, 3), "kind": "gnn"})
            if len(preds) >= top_links:
                break

        # KMeans clusters over the learned embedding space.
        clusters = {}
        try:
            from sklearn.cluster import KMeans
            kk = max(2, min(8, n // 12))
            lab = KMeans(n_clusters=kk, n_init=4, random_state=7).fit_predict(z.numpy())
            clusters = {ids[i]: int(lab[i]) for i in range(n)}
        except Exception:
            pass

        return {"predicted_links": preds, "clusters": clusters,
                "info": {"nodes": n, "edges": len(src) // 2, "epochs": epochs,
                         "final_loss": round(float(loss), 4), "embed_dim": dim_out,
                         "model": "GraphSAGE (2-layer, unsupervised link-pred, CPU)"}}
    except Exception as e:
        logger.warning(f"[graph_gnn] run failed: {e}")
        return {}
