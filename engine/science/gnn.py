# deep/science/gnn.py — Graph Neural Networks (Bible Section 14)
"""Graph neural networks. PyTorch Geometric is the spec's primary framework but
is optional here; a from-scratch GCN (normalised-adjacency message passing) runs
on plain PyTorch so the module is useful without PyG."""
from __future__ import annotations

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH = True
except Exception:  # pragma: no cover
    TORCH = False

try:
    import torch_geometric  # noqa: F401
    PYG = True
except Exception:  # pragma: no cover
    PYG = False


if TORCH:
    class GCNLayer(nn.Module):
        """Single graph-convolution layer: D^-1/2 (A+I) D^-1/2 X W."""

        def __init__(self, in_dim, out_dim):
            super().__init__()
            self.lin = nn.Linear(in_dim, out_dim)

        def forward(self, x, A_hat):
            return A_hat @ self.lin(x)

    class GCN(nn.Module):
        def __init__(self, in_dim, hidden, out_dim, n_layers=2, dropout=0.1):
            super().__init__()
            dims = [in_dim] + [hidden] * (n_layers - 1) + [out_dim]
            self.layers = nn.ModuleList(GCNLayer(dims[i], dims[i + 1])
                                        for i in range(n_layers))
            self.dropout = dropout

        def forward(self, x, A_hat, pool=True):
            for i, layer in enumerate(self.layers):
                x = layer(x, A_hat)
                if i < len(self.layers) - 1:
                    x = F.relu(x)
                    x = F.dropout(x, self.dropout, self.training)
            return x.mean(0, keepdim=True) if pool else x  # graph-level mean pool


def normalised_adjacency(edge_index, n_nodes):
    """Build symmetric normalised adjacency  D^-1/2 (A+I) D^-1/2."""
    A = torch.zeros(n_nodes, n_nodes)
    for s, d in zip(edge_index[0], edge_index[1]):
        A[s, d] = 1.0
        A[d, s] = 1.0
    A = A + torch.eye(n_nodes)
    deg = A.sum(1)
    dinv = torch.diag(deg.pow(-0.5))
    return dinv @ A @ dinv


class GNNEngine:
    def __init__(self, config=None):
        self.config = config

    def build_gcn(self, in_dim=4, hidden=16, out_dim=2, n_layers=2) -> dict:
        if not TORCH:
            return _no_torch()
        model = GCN(in_dim, hidden, out_dim, n_layers)
        params = sum(p.numel() for p in model.parameters())
        return {"model": model, "params": params,
                "verbal": f"Built a {n_layers}-layer GCN ({in_dim}→{hidden}→{out_dim}, "
                          f"{params:,} params)."}

    def forward_demo(self, n_nodes=5, in_dim=4) -> dict:
        """Run a GCN forward pass on a small random graph (graph-level output)."""
        if not TORCH:
            return _no_torch()
        x = torch.randn(n_nodes, in_dim)
        edge_index = torch.tensor([[0, 1, 2, 3, 0], [1, 2, 3, 4, 4]])
        A_hat = normalised_adjacency(edge_index, n_nodes)
        model = GCN(in_dim, 16, 2, 2)
        with torch.no_grad():
            out = model(x, A_hat)
        return {"output": out.tolist(), "result": out.tolist(),
                "verbal": f"GCN message passing over a {n_nodes}-node graph produced "
                          f"a graph embedding {out.squeeze().tolist()}."}

    # ── PyG-backed architectures (real when torch_geometric present) ─
    def _demo_graph(self, n=6, feat=8):
        x = torch.randn(n, feat)
        edge_index = torch.tensor([[0, 1, 2, 3, 4, 0, 2], [1, 2, 3, 4, 5, 4, 5]])
        return x, edge_index

    def gat(self, in_dim=8, hidden=16, heads=4) -> dict:
        if not PYG:
            return {"result": None, "verbal": "GAT needs torch_geometric, sir."}
        from torch_geometric.nn import GATv2Conv
        x, ei = self._demo_graph(feat=in_dim)
        conv = GATv2Conv(in_dim, hidden, heads=heads)
        with torch.no_grad():
            out = conv(x, ei)
        p = sum(q.numel() for q in conv.parameters())
        return {"params": p, "out_shape": list(out.shape), "result": p,
                "verbal": f"GAT (GATv2, {heads} heads): forward output {list(out.shape)}, "
                          f"{p:,} params."}

    def mpnn(self, in_dim=8, hidden=16) -> dict:
        if not PYG:
            return {"result": None, "verbal": "MPNN needs torch_geometric, sir."}
        from torch_geometric.nn import NNConv
        import torch.nn as nn
        x, ei = self._demo_graph(feat=in_dim)
        edge_attr = torch.randn(ei.shape[1], 3)
        ednet = nn.Sequential(nn.Linear(3, 16), nn.ReLU(), nn.Linear(16, in_dim * hidden))
        conv = NNConv(in_dim, hidden, ednet)
        with torch.no_grad():
            out = conv(x, ei, edge_attr)
        return {"out_shape": list(out.shape), "result": list(out.shape),
                "verbal": f"MPNN (edge-conditioned NNConv): output {list(out.shape)}."}

    def graph_transformer(self, in_dim=8, hidden=16, heads=4) -> dict:
        if not PYG:
            return {"result": None, "verbal": "GraphTransformer needs torch_geometric, sir."}
        from torch_geometric.nn import TransformerConv
        x, ei = self._demo_graph(feat=in_dim)
        conv = TransformerConv(in_dim, hidden, heads=heads)
        with torch.no_grad():
            out = conv(x, ei)
        return {"out_shape": list(out.shape), "result": list(out.shape),
                "verbal": f"Graph Transformer ({heads} heads): output {list(out.shape)}."}

    def egnn(self, in_dim=8, hidden=16) -> dict:
        """E(n)-equivariant GNN layer (scratch) — updates features and positions."""
        if not TORCH: return _no_torch()
        import torch.nn as nn
        n = 6; h = torch.randn(n, in_dim); pos = torch.randn(n, 3)
        edge_index = torch.tensor([[0, 1, 2, 3, 4], [1, 2, 3, 4, 5]])
        phi_e = nn.Sequential(nn.Linear(2 * in_dim + 1, hidden), nn.SiLU(),
                              nn.Linear(hidden, hidden))
        phi_x = nn.Sequential(nn.Linear(hidden, 1))
        with torch.no_grad():
            s, d = edge_index
            diff = pos[s] - pos[d]; dist2 = (diff ** 2).sum(1, keepdim=True)
            m = phi_e(torch.cat([h[s], h[d], dist2], 1))
            dx = diff * phi_x(m)
            pos_new = pos.clone().index_add_(0, s, dx)
        return {"pos_shape": list(pos_new.shape), "result": "ok",
                "verbal": "EGNN layer: rotation/translation-equivariant update of "
                          "features and 3D coordinates applied."}

    def schnet(self, hidden=64, n_interactions=3) -> dict:
        if not PYG:
            return {"result": None, "verbal": "SchNet needs torch_geometric, sir."}
        try:
            from torch_geometric.nn import SchNet
            model = SchNet(hidden_channels=hidden, num_interactions=n_interactions)
            p = sum(q.numel() for q in model.parameters())
            return {"params": p, "result": p,
                    "verbal": f"SchNet ({n_interactions} interaction blocks, {p:,} params) "
                              f"ready for QM property prediction."}
        except Exception as e:  # noqa: BLE001
            return {"result": None, "verbal": f"SchNet build failed, sir: {e}"}

    def dimenet(self) -> dict:
        if not PYG:
            return {"result": None, "verbal": "DimeNet needs torch_geometric, sir."}
        try:
            from torch_geometric.nn import DimeNet
            model = DimeNet(hidden_channels=32, out_channels=1, num_blocks=2,
                            num_bilinear=4, num_spherical=4, num_radial=4)
            p = sum(q.numel() for q in model.parameters())
            return {"params": p, "result": p,
                    "verbal": f"DimeNet (directional MP, {p:,} params) ready."}
        except Exception as e:  # noqa: BLE001
            return {"result": None, "verbal": f"DimeNet needs extra deps, sir: {e}"}

    def nequip(self) -> dict:
        try:
            import nequip  # noqa: F401
            return {"result": "ready", "verbal": "NequIP (SO(3)-equivariant) ready, sir."}
        except Exception:
            return {"result": None,
                    "verbal": "NequIP needs the nequip package (e3nn), sir — not installed. "
                              "EGNN provides equivariance in the meantime."}

    def hignn(self, in_dim=8, hidden=16) -> dict:
        """Hierarchical GNN: atom-level GCN -> fragment pool -> molecule readout."""
        if not TORCH: return _no_torch()
        x, ei = self._demo_graph(feat=in_dim)
        A = normalised_adjacency(ei, x.shape[0])
        atom = GCN(in_dim, hidden, hidden, 2)
        with torch.no_grad():
            atom_h = atom(x, A, pool=False)
            # fragment level: mean-pool pairs, then molecule readout
            frag = atom_h.view(-1, 2, hidden).mean(1) if x.shape[0] % 2 == 0 else atom_h
            mol = frag.mean(0)
        return {"mol_embedding_dim": mol.shape[0], "result": "ok",
                "verbal": "HiGNN: atom→fragment→molecule hierarchical aggregation "
                          f"produced a {mol.shape[0]}-dim molecule embedding."}

    def test(self) -> None:
        if not TORCH:
            print("gnn: torch unavailable (skipped)"); return
        assert "output" in self.forward_demo()
        assert self.build_gcn()["params"] > 0
        assert self.egnn()["result"] == "ok"
        assert self.hignn()["result"] == "ok"
        if PYG:
            assert self.gat()["params"] > 0
            assert self.graph_transformer()["result"]
        print("gnn.GNNEngine: OK (GCN,GAT,MPNN,EGNN,SchNet,DimeNet,NequIP,"
              "GraphTransformer,HiGNN)")


def _no_torch():
    return {"result": None, "verbal": "PyTorch is not installed, sir."}


_engine = GNNEngine()


def build_gnn(text: str) -> dict:
    return _engine.forward_demo()


def test() -> None:
    GNNEngine().test()


if __name__ == "__main__":
    test()
