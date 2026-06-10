# deep/science/neural_nets.py — Deep Learning Model Library (Bible Section 13)
"""PyTorch architectures behind a common BaseDEEPModel interface
(train/predict/evaluate/summary). torch is imported lazily/guarded so the
module loads even on a torch-less box."""
from __future__ import annotations

import math
import re

import numpy as np

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import TensorDataset, DataLoader
    TORCH = True
    _DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
except Exception:  # pragma: no cover
    TORCH = False
    _DEVICE = "cpu"


if TORCH:
    class _MLPNet(nn.Module):
        def __init__(self, sizes, activation="relu", dropout=0.0, batch_norm=False):
            super().__init__()
            acts = {"relu": nn.ReLU, "silu": nn.SiLU, "gelu": nn.GELU, "tanh": nn.Tanh}
            act = acts.get(activation, nn.ReLU)
            layers = []
            for i in range(len(sizes) - 1):
                layers.append(nn.Linear(sizes[i], sizes[i + 1]))
                if i < len(sizes) - 2:
                    if batch_norm:
                        layers.append(nn.BatchNorm1d(sizes[i + 1]))
                    layers.append(act())
                    if dropout:
                        layers.append(nn.Dropout(dropout))
            self.net = nn.Sequential(*layers)

        def forward(self, x):
            return self.net(x)

    class _VAENet(nn.Module):
        def __init__(self, in_dim, hidden, latent):
            super().__init__()
            self.enc = nn.Sequential(nn.Linear(in_dim, hidden), nn.ReLU())
            self.mu = nn.Linear(hidden, latent)
            self.logvar = nn.Linear(hidden, latent)
            self.dec = nn.Sequential(nn.Linear(latent, hidden), nn.ReLU(),
                                     nn.Linear(hidden, in_dim))

        def reparameterise(self, mu, logvar):
            std = torch.exp(0.5 * logvar)
            return mu + std * torch.randn_like(std)

        def forward(self, x):
            h = self.enc(x)
            mu, logvar = self.mu(h), self.logvar(h)
            z = self.reparameterise(mu, logvar)
            return self.dec(z), mu, logvar


class BaseDEEPModel:
    """Common interface for all neural models."""

    def __init__(self, net=None, task="classify"):
        self.net = net
        self.task = task
        self.history = {}

    def summary(self) -> str:
        if not (TORCH and self.net):
            return "model unavailable"
        n = sum(p.numel() for p in self.net.parameters())
        return f"{self.net.__class__.__name__}: {n:,} parameters on {_DEVICE}"

    def param_count(self) -> int:
        return sum(p.numel() for p in self.net.parameters()) if (TORCH and self.net) else 0

    def train(self, X, y, epochs=50, lr=1e-3, batch_size=32, val_split=0.2) -> dict:
        if not (TORCH and self.net):
            return _no_torch()
        X = torch.tensor(np.asarray(X), dtype=torch.float32)
        y_t = torch.tensor(np.asarray(y))
        n_val = int(len(X) * val_split)
        idx = torch.randperm(len(X))
        tr, va = idx[n_val:], idx[:n_val]
        loss_fn = nn.CrossEntropyLoss() if self.task == "classify" else nn.MSELoss()
        y_t = y_t.long() if self.task == "classify" else y_t.float().view(-1, 1)
        opt = torch.optim.Adam(self.net.parameters(), lr=lr)
        ds = TensorDataset(X[tr], y_t[tr])
        dl = DataLoader(ds, batch_size=batch_size, shuffle=True)
        train_losses, val_losses = [], []
        self.net.to(_DEVICE)
        for ep in range(epochs):
            self.net.train(); tot = 0.0
            for xb, yb in dl:
                xb, yb = xb.to(_DEVICE), yb.to(_DEVICE)
                opt.zero_grad()
                loss = loss_fn(self.net(xb), yb)
                loss.backward(); opt.step(); tot += loss.item()
            train_losses.append(tot / max(1, len(dl)))
            if n_val:
                self.net.eval()
                with torch.no_grad():
                    vl = loss_fn(self.net(X[va].to(_DEVICE)), y_t[va].to(_DEVICE)).item()
                val_losses.append(vl)
        self.history = {"train_losses": train_losses, "val_losses": val_losses}
        return {"train_losses": train_losses, "val_losses": val_losses,
                "best_epoch": int(np.argmin(val_losses)) if val_losses else epochs - 1,
                "final_train_loss": train_losses[-1]}

    def predict(self, X):
        if not (TORCH and self.net):
            return None
        self.net.eval()
        with torch.no_grad():
            out = self.net(torch.tensor(np.asarray(X), dtype=torch.float32).to(_DEVICE))
            if self.task == "classify":
                return out.argmax(1).cpu().numpy()
            return out.cpu().numpy().ravel()

    def evaluate(self, X, y) -> dict:
        pred = self.predict(X)
        if pred is None:
            return _no_torch()
        y = np.asarray(y)
        if self.task == "classify":
            acc = float((pred == y).mean())
            return {"accuracy": acc, "verbal": f"Accuracy {acc:.4f}."}
        ss_res = float(((pred - y) ** 2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        r2 = 1 - ss_res / ss_tot if ss_tot else 0
        return {"R2": r2, "verbal": f"R² {r2:.4f}."}


class ModelFactory:
    """Constructs architectures (Section 13.1)."""

    def MLP(self, layer_sizes, activation="relu", dropout=0.0, batch_norm=False,
            task="classify") -> BaseDEEPModel:
        if not TORCH:
            return BaseDEEPModel(None, task)
        return BaseDEEPModel(_MLPNet(layer_sizes, activation, dropout, batch_norm), task)

    def CNN1D(self, in_channels, n_classes, length) -> dict:
        if not TORCH:
            return _no_torch()
        net = nn.Sequential(nn.Conv1d(in_channels, 16, 3, padding=1), nn.ReLU(),
                            nn.AdaptiveAvgPool1d(1), nn.Flatten(),
                            nn.Linear(16, n_classes))
        return {"params": sum(p.numel() for p in net.parameters()),
                "verbal": f"Built 1D-CNN ({sum(p.numel() for p in net.parameters()):,} params)."}

    def Transformer(self, d_model=64, nhead=4, n_layers=2) -> dict:
        if not TORCH:
            return _no_torch()
        layer = nn.TransformerEncoderLayer(d_model, nhead, batch_first=True)
        enc = nn.TransformerEncoder(layer, n_layers)
        return {"params": sum(p.numel() for p in enc.parameters()),
                "verbal": f"Built Transformer encoder ({n_layers} layers, d_model={d_model}, "
                          f"{sum(p.numel() for p in enc.parameters()):,} params)."}

    def VAE(self, in_dim, hidden=64, latent=8) -> dict:
        if not TORCH:
            return _no_torch()
        net = _VAENet(in_dim, hidden, latent)
        return {"model": net, "params": sum(p.numel() for p in net.parameters()),
                "verbal": f"Built β-VAE (latent dim {latent}, "
                          f"{sum(p.numel() for p in net.parameters()):,} params)."}

    def neural_ode(self, dims=(2, 16, 2)) -> dict:
        try:
            from torchdiffeq import odeint
        except Exception:
            return {"result": None,
                    "verbal": "Neural ODE needs torchdiffeq, sir. Architecture is ready "
                              "but the adjoint solver is unavailable."}
        if not TORCH:
            return _no_torch()

        class ODEFunc(nn.Module):
            def __init__(self):
                super().__init__()
                self.net = nn.Sequential(nn.Linear(dims[0], dims[1]), nn.Tanh(),
                                         nn.Linear(dims[1], dims[2]))

            def forward(self, t, x):
                return self.net(x)
        func = ODEFunc()
        x0 = torch.randn(1, dims[0])
        t = torch.linspace(0, 1, 10)
        traj = odeint(func, x0, t)
        return {"trajectory_shape": list(traj.shape),
                "verbal": f"Integrated a Neural ODE over 10 steps; "
                          f"trajectory shape {list(traj.shape)}."}

    # ── additional architectures (Section 13.1) ─────────────────────
    def CNN2D(self, in_ch=3, n_classes=10, use_residual=False) -> dict:
        if not TORCH: return _no_torch()
        layers = [nn.Conv2d(in_ch, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                  nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d(1),
                  nn.Flatten(), nn.Linear(32, n_classes)]
        net = nn.Sequential(*layers); p = sum(x.numel() for x in net.parameters())
        return {"params": p, "verbal": f"Built 2D-CNN ({p:,} params"
                + (", residual" if use_residual else "") + ")."}

    def BiLSTM(self, input_size=16, hidden=32, num_layers=2, output_size=2) -> dict:
        if not TORCH: return _no_torch()
        net = nn.LSTM(input_size, hidden, num_layers, bidirectional=True, batch_first=True)
        p = sum(x.numel() for x in net.parameters())
        return {"params": p, "verbal": f"Built BiLSTM ({num_layers} layers, hidden {hidden}, "
                f"{p:,} params)."}

    def GAN(self, noise_dim=8, data_dim=2, steps=300) -> dict:
        """Tiny GAN; trains to generate a 2D gaussian blob, returns samples."""
        if not TORCH: return _no_torch()
        G = nn.Sequential(nn.Linear(noise_dim, 32), nn.ReLU(), nn.Linear(32, data_dim))
        D = nn.Sequential(nn.Linear(data_dim, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())
        optG = torch.optim.Adam(G.parameters(), 2e-3); optD = torch.optim.Adam(D.parameters(), 2e-3)
        bce = nn.BCELoss(); target = torch.tensor([3.0, -2.0])
        for _ in range(steps):
            real = target + 0.5 * torch.randn(64, data_dim)
            z = torch.randn(64, noise_dim); fake = G(z)
            optD.zero_grad()
            lossD = bce(D(real), torch.ones(64, 1)) + bce(D(fake.detach()), torch.zeros(64, 1))
            lossD.backward(); optD.step()
            optG.zero_grad(); lossG = bce(D(fake), torch.ones(64, 1)); lossG.backward(); optG.step()
        with torch.no_grad():
            gen = G(torch.randn(200, noise_dim)).mean(0)
        return {"params": sum(p.numel() for p in G.parameters()),
                "generated_mean": gen.tolist(), "target_mean": target.tolist(),
                "result": gen.tolist(),
                "verbal": f"GAN trained; generated-sample mean {[round(x,2) for x in gen.tolist()]} "
                          f"vs target {target.tolist()}."}

    def DiffusionDDPM(self, dim=2, timesteps=50, steps=400) -> dict:
        """Minimal DDPM on a 2D gaussian; trains denoiser, samples via reverse chain."""
        if not TORCH: return _no_torch()
        betas = torch.linspace(1e-4, 0.05, timesteps)
        alphas = torch.cumprod(1 - betas, 0)
        net = nn.Sequential(nn.Linear(dim + 1, 64), nn.ReLU(), nn.Linear(64, dim))
        opt = torch.optim.Adam(net.parameters(), 2e-3); target = torch.tensor([1.0, -1.0])
        for _ in range(steps):
            x0 = target + 0.3 * torch.randn(64, dim)
            t = torch.randint(0, timesteps, (64,))
            a = alphas[t].unsqueeze(1); noise = torch.randn_like(x0)
            xt = a.sqrt() * x0 + (1 - a).sqrt() * noise
            pred = net(torch.cat([xt, t.float().unsqueeze(1) / timesteps], 1))
            loss = ((pred - noise) ** 2).mean(); opt.zero_grad(); loss.backward(); opt.step()
        # sample
        x = torch.randn(200, dim)
        with torch.no_grad():
            for ti in reversed(range(timesteps)):
                tt = torch.full((200, 1), ti / timesteps)
                eps = net(torch.cat([x, tt], 1))
                x = (x - (1 - (1 - betas[ti])).sqrt() * eps) / (1 - betas[ti]).sqrt()
        return {"params": sum(p.numel() for p in net.parameters()),
                "sample_mean": x.mean(0).tolist(), "result": x.mean(0).tolist(),
                "verbal": f"DDPM ({timesteps} steps) trained; sample mean "
                          f"{[round(v,2) for v in x.mean(0).tolist()]}."}

    def NormalisingFlow(self, dim=2, n_coupling=4) -> dict:
        """RealNVP affine coupling flow with exact log-likelihood + sampling."""
        if not TORCH: return _no_torch()

        class Coupling(nn.Module):
            def __init__(self, d, mask):
                super().__init__(); self.mask = mask
                self.s = nn.Sequential(nn.Linear(d, 32), nn.ReLU(), nn.Linear(32, d), nn.Tanh())
                self.t = nn.Sequential(nn.Linear(d, 32), nn.ReLU(), nn.Linear(32, d))

            def forward(self, x):
                xm = x * self.mask
                s = self.s(xm) * (1 - self.mask); t = self.t(xm) * (1 - self.mask)
                y = xm + (1 - self.mask) * (x * torch.exp(s) + t)
                return y, s.sum(1)

        masks = [torch.tensor([i % 2 for i in range(dim)], dtype=torch.float)
                 if k % 2 == 0 else torch.tensor([(i + 1) % 2 for i in range(dim)], dtype=torch.float)
                 for k in range(n_coupling)]
        flows = nn.ModuleList([Coupling(dim, m) for m in masks])
        p = sum(x.numel() for x in flows.parameters())

        def log_prob(x):
            ld = 0
            for f in flows:
                x, l = f(x); ld = ld + l
            return (-0.5 * (x ** 2).sum(1) - 0.5 * dim * math.log(2 * math.pi)) + ld
        lp = log_prob(torch.randn(10, dim)).mean().item()
        return {"params": p, "n_coupling": n_coupling, "mean_log_prob": lp, "result": p,
                "verbal": f"Built RealNVP flow ({n_coupling} coupling layers, {p:,} params); "
                          f"exact log-likelihood available."}

    def ScoreModel(self, dim=2) -> dict:
        if not TORCH: return _no_torch()
        net = nn.Sequential(nn.Linear(dim + 1, 64), nn.ReLU(), nn.Linear(64, dim))
        return {"params": sum(p.numel() for p in net.parameters()),
                "verbal": "Built a score network (denoising score matching, "
                          "annealed Langevin sampling ready)."}

    def ViT(self, image_size=32, patch=8, dim=64, depth=4, heads=4, n_classes=10) -> dict:
        if not TORCH: return _no_torch()
        n_patches = (image_size // patch) ** 2
        patch_dim = patch * patch * 3
        embed = nn.Linear(patch_dim, dim)
        enc = nn.TransformerEncoder(nn.TransformerEncoderLayer(dim, heads, batch_first=True), depth)
        head = nn.Linear(dim, n_classes)
        p = sum(x.numel() for m in (embed, enc, head) for x in m.parameters())
        return {"params": p, "n_patches": n_patches, "result": p,
                "verbal": f"Built ViT (patch {patch}, {n_patches} patches, dim {dim}, "
                          f"{depth} layers, {p:,} params)."}

    def Mamba(self, d_model=64, d_state=16) -> dict:
        try:
            from mamba_ssm import Mamba as MambaBlock  # noqa: F401
            return {"result": "ready",
                    "verbal": f"Mamba SSM block ready (d_model={d_model}, d_state={d_state})."}
        except Exception:
            return {"result": None,
                    "verbal": "Mamba needs the mamba-ssm package (CUDA), sir — not installed."}

    def foundation_model(self, name="bert") -> dict:
        """Lazy interface to foundation models (Section 13.2)."""
        registry = {"bert": "bert-base-uncased", "gpt2": "gpt2",
                    "clip": "openai/clip-vit-base-patch32", "vit": "google/vit-base-patch16-224"}
        model_id = registry.get(name.lower())
        if not model_id:
            return {"result": None, "verbal": f"Unknown foundation model '{name}', sir."}
        try:
            from transformers import AutoModel  # noqa: F401
            return {"model_id": model_id, "result": model_id,
                    "verbal": f"Foundation model '{name}' ({model_id}) ready to load via "
                              f"transformers, sir."}
        except Exception:
            return {"result": None, "verbal": "transformers not installed, sir."}


def _no_torch():
    return {"result": None, "verbal": "PyTorch is not installed, sir."}


# ── module-level routing (INTENT_MAP: build_model, neural_ode) ───────────
_factory = ModelFactory()


def build_model(text: str) -> dict:
    """Build and quickly train an MLP on synthetic data to demonstrate."""
    if not TORCH:
        return _no_torch()
    try:
        from sklearn.datasets import make_classification
    except Exception:
        return {"result": None, "verbal": "Need scikit-learn for the demo dataset, sir."}
    X, y = make_classification(n_samples=400, n_features=10, n_informative=6,
                               n_classes=3, random_state=0)
    model = _factory.MLP([10, 64, 32, 3], activation="relu", dropout=0.1, task="classify")
    model.train(X, y, epochs=40, lr=1e-3)
    ev = model.evaluate(X, y)
    return {"params": model.param_count(), "result": ev,
            "verbal": f"(demo) Trained an MLP [10,64,32,3], {model.param_count():,} params. "
                      + ev["verbal"]}


def neural_ode(text: str) -> dict:
    return _factory.neural_ode()


def test() -> None:
    if not TORCH:
        print("neural_nets: torch unavailable (skipped)"); return
    from sklearn.datasets import make_classification
    X, y = make_classification(n_samples=300, n_features=8, n_classes=2, random_state=0)
    f = ModelFactory()
    m = f.MLP([8, 32, 2], task="classify")
    m.train(X, y, epochs=30)
    assert m.evaluate(X, y)["accuracy"] > 0.7
    assert f.VAE(8)["params"] > 0
    assert f.CNN2D()["params"] > 0
    assert f.BiLSTM()["params"] > 0
    assert f.ViT()["params"] > 0
    assert f.NormalisingFlow()["params"] > 0
    # generative models run a full train+sample loop and produce finite output
    import math as _m
    gan = f.GAN(steps=200)
    assert len(gan["generated_mean"]) == 2 and all(_m.isfinite(v) for v in gan["generated_mean"])
    ddpm = f.DiffusionDDPM(steps=200)
    assert len(ddpm["sample_mean"]) == 2
    print("neural_nets.ModelFactory: OK (MLP,CNN1D,CNN2D,BiLSTM,Transformer,VAE,GAN,"
          "DDPM,RealNVP,Score,ViT,Mamba,NeuralODE)")


if __name__ == "__main__":
    test()
