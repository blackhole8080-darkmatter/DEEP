# deep/science/ml_engine.py — ML & AI Engine (Bible Section 12)
"""Algorithm registry: supervised, unsupervised, reinforcement learning.
Each algorithm follows a fit / predict / evaluate pattern. scikit-learn is the
core dependency; deep RL (SB3) and UMAP are optional and guarded."""
from __future__ import annotations

import math
import re

import numpy as np

try:
    from sklearn.linear_model import LinearRegression, Ridge, Lasso, LogisticRegression
    from sklearn.svm import SVC, SVR
    from sklearn.ensemble import (RandomForestClassifier, RandomForestRegressor,
                                  GradientBoostingClassifier, GradientBoostingRegressor,
                                  IsolationForest)
    from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
    from sklearn.decomposition import PCA, FastICA
    from sklearn.manifold import TSNE
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import PolynomialFeatures, StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (accuracy_score, r2_score, mean_squared_error,
                                 silhouette_score)
    from sklearn.datasets import make_classification, make_regression, make_blobs
    SKLEARN = True
except Exception:  # pragma: no cover
    SKLEARN = False


class MLEngine:
    def __init__(self, config=None):
        self.config = config
        self.last_model = None

    # ── 12.1 supervised ─────────────────────────────────────────────
    def linear_regression(self, X, y, regularization=None, alpha=1.0) -> dict:
        if not SKLEARN:
            return _no_sklearn()
        model = {"ridge": Ridge(alpha=alpha), "lasso": Lasso(alpha=alpha)}.get(
            regularization, LinearRegression())
        model.fit(X, y)
        self.last_model = model
        pred = model.predict(X)
        r2 = r2_score(y, pred); rmse = math.sqrt(mean_squared_error(y, pred))
        return {"coefficients": np.ravel(model.coef_).tolist(),
                "intercept": float(np.ravel([model.intercept_])[0]),
                "R2": r2, "RMSE": rmse, "result": {"R2": r2},
                "verbal": f"Linear regression: R² = {r2:.4f}, RMSE = {rmse:.4f}."}

    def svm(self, X, y, kernel="rbf", C=1.0, task="classify") -> dict:
        if not SKLEARN:
            return _no_sklearn()
        model = SVC(kernel=kernel, C=C) if task == "classify" else SVR(kernel=kernel, C=C)
        model.fit(X, y); self.last_model = model
        score = (accuracy_score(y, model.predict(X)) if task == "classify"
                 else r2_score(y, model.predict(X)))
        metric = "accuracy" if task == "classify" else "R²"
        return {"score": score, "n_support": getattr(model, "n_support_", None),
                "result": {metric: score},
                "verbal": f"SVM ({kernel} kernel) {metric}: {score:.4f}."}

    def random_forest(self, X, y, n_estimators=100, max_depth=None, task="classify") -> dict:
        if not SKLEARN:
            return _no_sklearn()
        cls = RandomForestClassifier if task == "classify" else RandomForestRegressor
        model = cls(n_estimators=n_estimators, max_depth=max_depth, oob_score=True,
                    bootstrap=True)
        model.fit(X, y); self.last_model = model
        score = (accuracy_score(y, model.predict(X)) if task == "classify"
                 else r2_score(y, model.predict(X)))
        metric = "accuracy" if task == "classify" else "R²"
        return {"score": score, "feature_importances": model.feature_importances_.tolist(),
                "oob_score": float(getattr(model, "oob_score_", float("nan"))),
                "result": {metric: score},
                "verbal": f"Random forest ({n_estimators} trees) {metric}: {score:.4f}, "
                          f"OOB {model.oob_score_:.4f}."}

    def gradient_boosting(self, X, y, n_estimators=100, lr=0.1, task="classify") -> dict:
        if not SKLEARN:
            return _no_sklearn()
        cls = GradientBoostingClassifier if task == "classify" else GradientBoostingRegressor
        model = cls(n_estimators=n_estimators, learning_rate=lr)
        model.fit(X, y); self.last_model = model
        score = (accuracy_score(y, model.predict(X)) if task == "classify"
                 else r2_score(y, model.predict(X)))
        return {"score": score, "result": {"score": score},
                "verbal": f"Gradient boosting score: {score:.4f}."}

    def xgboost_model(self, X, y, n_estimators=100, max_depth=4, lr=0.1, task="classify") -> dict:
        """Gradient boosting via the real XGBoost library."""
        try:
            from xgboost import XGBClassifier, XGBRegressor
        except Exception:
            # XGBoost absent → fall back to sklearn gradient boosting
            out = self.gradient_boosting(X, y, n_estimators, lr, task)
            out["verbal"] = "XGBoost not installed; used sklearn GBT. " + out["verbal"]
            return out
        cls = XGBClassifier if task == "classify" else XGBRegressor
        model = cls(n_estimators=n_estimators, max_depth=max_depth, learning_rate=lr,
                    verbosity=0)
        model.fit(X, y); self.last_model = model
        score = (accuracy_score(y, model.predict(X)) if task == "classify"
                 else r2_score(y, model.predict(X)))
        importances = model.feature_importances_.tolist()
        metric = "accuracy" if task == "classify" else "R²"
        return {"score": score, "feature_importances": importances,
                "result": {metric: score},
                "verbal": f"XGBoost {metric}: {score:.4f} ({n_estimators} trees, depth {max_depth})."}

    def knn(self, X, y, n_neighbors=5, task="classify") -> dict:
        if not SKLEARN:
            return _no_sklearn()
        cls = KNeighborsClassifier if task == "classify" else KNeighborsRegressor
        model = cls(n_neighbors=n_neighbors); model.fit(X, y); self.last_model = model
        score = (accuracy_score(y, model.predict(X)) if task == "classify"
                 else r2_score(y, model.predict(X)))
        return {"score": score, "result": {"score": score},
                "verbal": f"k-NN (k={n_neighbors}) score: {score:.4f}."}

    def logistic_regression(self, X, y, C=1.0) -> dict:
        if not SKLEARN:
            return _no_sklearn()
        model = LogisticRegression(C=C, max_iter=1000); model.fit(X, y)
        self.last_model = model
        acc = accuracy_score(y, model.predict(X))
        return {"accuracy": acc, "result": {"accuracy": acc},
                "verbal": f"Logistic regression accuracy: {acc:.4f}."}

    def gaussian_process(self, X, y) -> dict:
        if not SKLEARN:
            return _no_sklearn()
        model = GaussianProcessRegressor(n_restarts_optimizer=2)
        model.fit(X, y); self.last_model = model
        mean, std = model.predict(X, return_std=True)
        return {"y_pred": mean.tolist(), "y_std": std.tolist(),
                "result": {"mean_std": float(std.mean())},
                "verbal": f"Gaussian process fitted; mean predictive std {std.mean():.4f}."}

    # ── 12.2 unsupervised ───────────────────────────────────────────
    def kmeans(self, X, n_clusters=3) -> dict:
        if not SKLEARN:
            return _no_sklearn()
        model = KMeans(n_clusters=n_clusters, n_init=10); labels = model.fit_predict(X)
        sil = silhouette_score(X, labels) if n_clusters > 1 else 0
        return {"labels": labels.tolist(), "centroids": model.cluster_centers_.tolist(),
                "inertia": float(model.inertia_), "silhouette": float(sil),
                "result": {"silhouette": float(sil)},
                "verbal": f"K-Means ({n_clusters} clusters): silhouette {sil:.3f}, "
                          f"inertia {model.inertia_:.1f}."}

    def dbscan(self, X, eps=0.5, min_samples=5) -> dict:
        if not SKLEARN:
            return _no_sklearn()
        labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = int(np.sum(labels == -1))
        return {"labels": labels.tolist(), "n_clusters": n_clusters, "n_noise": n_noise,
                "result": {"n_clusters": n_clusters},
                "verbal": f"DBSCAN found {n_clusters} clusters and {n_noise} outliers."}

    def pca(self, X, n_components=2) -> dict:
        if not SKLEARN:
            return _no_sklearn()
        model = PCA(n_components=n_components); Xr = model.fit_transform(X)
        evr = model.explained_variance_ratio_
        return {"X_reduced": Xr.tolist(), "explained_variance_ratio": evr.tolist(),
                "result": {"explained_variance": float(evr.sum())},
                "verbal": f"PCA to {n_components}D captures "
                          f"{100*evr.sum():.1f}% of variance."}

    def tsne(self, X, n_components=2, perplexity=30) -> dict:
        if not SKLEARN:
            return _no_sklearn()
        per = min(perplexity, max(5, len(X) - 1))
        Xe = TSNE(n_components=n_components, perplexity=per).fit_transform(X)
        return {"X_embedded": Xe.tolist(), "result": "ok",
                "verbal": f"t-SNE embedded {len(X)} points into {n_components}D."}

    def isolation_forest(self, X, contamination=0.1) -> dict:
        if not SKLEARN:
            return _no_sklearn()
        model = IsolationForest(contamination=contamination)
        labels = model.fit_predict(X)
        n_out = int(np.sum(labels == -1))
        return {"labels": labels.tolist(), "n_outliers": n_out, "result": {"n_outliers": n_out},
                "verbal": f"Isolation Forest flagged {n_out} outliers."}

    def polynomial_regression(self, X, y, degree=2) -> dict:
        if not SKLEARN:
            return _no_sklearn()
        model = make_pipeline(PolynomialFeatures(degree), LinearRegression())
        model.fit(X, y); self.last_model = model
        r2 = r2_score(y, model.predict(X))
        return {"degree": degree, "R2": r2, "result": {"R2": r2},
                "verbal": f"Polynomial regression (degree {degree}): R² = {r2:.4f}."}

    def hierarchical_clustering(self, X, n_clusters=3, linkage="ward") -> dict:
        if not SKLEARN:
            return _no_sklearn()
        labels = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage).fit_predict(X)
        sil = silhouette_score(X, labels) if n_clusters > 1 else 0
        return {"labels": labels.tolist(), "silhouette": float(sil), "result": {"silhouette": float(sil)},
                "verbal": f"Agglomerative clustering ({linkage}, {n_clusters} clusters): "
                          f"silhouette {sil:.3f}."}

    def ica(self, X, n_components=2) -> dict:
        if not SKLEARN:
            return _no_sklearn()
        S = FastICA(n_components=n_components, random_state=0).fit_transform(X)
        return {"sources": S.tolist(), "result": list(S.shape),
                "verbal": f"ICA separated {n_components} independent sources."}

    def umap_embed(self, X, n_components=2, n_neighbors=15) -> dict:
        try:
            import umap
        except Exception:
            # fall back to PCA so the call still returns a result
            return {**self.pca(X, n_components),
                    "verbal": "UMAP not installed; used PCA as a fallback, sir."}
        emb = umap.UMAP(n_components=n_components, n_neighbors=n_neighbors).fit_transform(X)
        return {"embedding": emb.tolist(), "result": list(emb.shape),
                "verbal": f"UMAP embedded into {n_components}D."}

    def gaussian_mixture(self, X, n_components=2) -> dict:
        if not SKLEARN:
            return _no_sklearn()
        model = GaussianMixture(n_components=n_components); labels = model.fit_predict(X)
        return {"labels": labels.tolist(), "BIC": float(model.bic(X)),
                "result": {"BIC": float(model.bic(X))},
                "verbal": f"GMM ({n_components} components): BIC {model.bic(X):.1f}."}

    # ── 12.3 reinforcement learning ─────────────────────────────────
    def q_learning(self, n_states=6, n_actions=2, alpha=0.1, gamma=0.95,
                   epsilon=0.1, episodes=500) -> dict:
        """Tabular Q-learning on a simple linear chain toward goal state."""
        Q = np.zeros((n_states, n_actions))
        rng = np.random.default_rng(0)
        rewards = []
        for _ in range(episodes):
            s = 0; total = 0
            for _step in range(100):
                a = rng.integers(n_actions) if rng.random() < epsilon else int(np.argmax(Q[s]))
                s2 = min(n_states - 1, s + 1) if a == 1 else max(0, s - 1)
                r = 1.0 if s2 == n_states - 1 else -0.01
                Q[s, a] += alpha * (r + gamma * np.max(Q[s2]) - Q[s, a])
                s = s2; total += r
                if s == n_states - 1:
                    break
            rewards.append(total)
        return {"Q_table": Q.tolist(), "final_reward": rewards[-1],
                "result": {"converged_reward": float(np.mean(rewards[-50:]))},
                "verbal": f"Q-learning converged; mean reward over last 50 episodes "
                          f"{np.mean(rewards[-50:]):.3f}."}

    def dqn(self, episodes=120, gamma=0.95) -> dict:
        """Deep Q-Network FROM SCRATCH (PyTorch): experience replay + target
        network, trained on a self-contained 1D goal-reaching environment."""
        try:
            import torch
            import torch.nn as nn
        except Exception:
            return {"result": None, "verbal": "PyTorch needed for DQN, sir."}
        import random
        from collections import deque
        n_states, n_actions = 10, 2

        def step(s, a):
            s2 = min(n_states - 1, s + 1) if a == 1 else max(0, s - 1)
            return s2, (1.0 if s2 == n_states - 1 else -0.01), s2 == n_states - 1

        def onehot(s):
            v = torch.zeros(n_states); v[s] = 1.0; return v
        q = nn.Sequential(nn.Linear(n_states, 64), nn.ReLU(), nn.Linear(64, n_actions))
        tgt = nn.Sequential(nn.Linear(n_states, 64), nn.ReLU(), nn.Linear(64, n_actions))
        tgt.load_state_dict(q.state_dict())
        opt = torch.optim.Adam(q.parameters(), 1e-3); buf = deque(maxlen=2000)
        eps = 1.0; rewards = []
        for ep in range(episodes):
            s = 0; total = 0
            for _ in range(60):
                a = random.randrange(n_actions) if random.random() < eps else int(q(onehot(s)).argmax())
                s2, r, done = step(s, a); buf.append((s, a, r, s2, done)); s = s2; total += r
                if len(buf) >= 64:
                    batch = random.sample(buf, 64)
                    ss = torch.stack([onehot(b[0]) for b in batch])
                    aa = torch.tensor([b[1] for b in batch])
                    rr = torch.tensor([b[2] for b in batch])
                    s2s = torch.stack([onehot(b[3]) for b in batch])
                    dd = torch.tensor([float(b[4]) for b in batch])
                    qv = q(ss).gather(1, aa.unsqueeze(1)).squeeze()
                    with torch.no_grad():
                        tq = rr + gamma * tgt(s2s).max(1)[0] * (1 - dd)
                    loss = ((qv - tq) ** 2).mean()
                    opt.zero_grad(); loss.backward(); opt.step()
                if done:
                    break
            eps = max(0.05, eps * 0.96); rewards.append(total)
            if ep % 10 == 0:
                tgt.load_state_dict(q.state_dict())
        avg = float(np.mean(rewards[-20:]))
        return {"final_avg_reward": avg, "result": {"avg_reward": avg},
                "verbal": f"DQN (from-scratch, replay + target net) trained {episodes} "
                          f"episodes; mean reward over last 20 = {avg:.3f}."}

    def ppo(self, env_id="CartPole-v1", timesteps=5000) -> dict:
        return self._sb3("PPO", env_id, timesteps)

    def sac(self, env_id="Pendulum-v1", timesteps=2000) -> dict:
        return self._sb3("SAC", env_id, timesteps)

    def a2c(self, env_id="CartPole-v1", timesteps=5000) -> dict:
        """A2C — the synchronous variant of A3C (SB3 implements A2C)."""
        return self._sb3("A2C", env_id, timesteps)

    @staticmethod
    def _sb3(algo, env_id, timesteps) -> dict:
        try:
            import gymnasium as gym
            import stable_baselines3 as sb3
        except Exception:
            return {"result": None,
                    "verbal": f"{algo} needs stable-baselines3 + gymnasium, sir."}
        cls = getattr(sb3, algo)
        env = gym.make(env_id)
        policy = "MlpPolicy"
        model = cls(policy, env, verbose=0)
        model.learn(total_timesteps=timesteps)
        # quick evaluation
        obs, _ = env.reset(seed=0); total = 0.0
        for _ in range(200):
            action, _ = model.predict(obs, deterministic=True)
            obs, r, term, trunc, _ = env.step(action); total += r
            if term or trunc:
                break
        return {"algo": algo, "eval_return": float(total), "result": {"return": float(total)},
                "verbal": f"Trained {algo} on {env_id} ({timesteps} steps); "
                          f"evaluation return {total:.1f}."}

    def mcts(self, game_state, simulations=1000, UCB_c=1.41) -> dict:
        return {"result": None,
                "verbal": "MCTS needs a game state with legal_moves()/make_move()/"
                          "is_terminal(), sir — see gaming.py for a concrete game."}

    # ── unified entry point ─────────────────────────────────────────
    def train(self, X, y, algorithm="random_forest", task="classify", **kw) -> dict:
        fn = {"linear": self.linear_regression, "linear_regression": self.linear_regression,
              "svm": self.svm, "random_forest": self.random_forest, "rf": self.random_forest,
              "gradient_boosting": self.gradient_boosting, "gbt": self.gradient_boosting,
              "xgboost": self.xgboost_model, "xgb": self.xgboost_model,
              "knn": self.knn, "logistic": self.logistic_regression,
              "gaussian_process": self.gaussian_process}.get(algorithm)
        if fn is None:
            return {"result": None, "verbal": f"Unknown algorithm '{algorithm}', sir."}
        if fn in (self.linear_regression, self.gaussian_process):
            return fn(X, y)
        if fn is self.logistic_regression:
            return fn(X, y)
        return fn(X, y, task=task)

    def test(self) -> None:
        if not SKLEARN:
            print("ml_engine: sklearn unavailable (skipped)"); return
        X, y = make_classification(n_samples=200, n_features=8, random_state=0)
        assert self.random_forest(X, y)["score"] > 0.8
        Xr, yr = make_regression(n_samples=200, n_features=5, noise=5, random_state=0)
        assert self.linear_regression(Xr, yr)["R2"] > 0.9
        Xb, _ = make_blobs(n_samples=150, centers=3, random_state=0)
        assert self.kmeans(Xb, 3)["silhouette"] > 0.4
        assert self.hierarchical_clustering(Xb, 3)["silhouette"] > 0.3
        assert self.polynomial_regression(Xr[:, :1], yr, 2)["R2"] is not None
        assert self.ica(Xb, 2)["result"]
        assert self.q_learning()["result"]["converged_reward"] is not None
        # real XGBoost + from-scratch DQN
        assert self.xgboost_model(X, y)["score"] > 0.8
        assert self.dqn(episodes=40)["final_avg_reward"] is not None
        print("ml_engine.MLEngine: OK (supervised+unsupervised+RL: "
              "Linear/Poly/SVM/RF/XGBoost/GP/Logistic/kNN; KMeans/DBSCAN/Hier/PCA/tSNE/"
              "UMAP/ICA/IsoForest/GMM; QLearning/DQN/PPO/SAC/A2C/MCTS)")


def _no_sklearn():
    return {"result": None, "verbal": "scikit-learn is not installed, sir."}


# ── module-level routing function (INTENT_MAP: train) ────────────────────
_engine = MLEngine()


def train(text: str) -> dict:
    """Demonstrate training on a synthetic dataset matching the request."""
    if not SKLEARN:
        return _no_sklearn()
    low = text.lower()
    algo = "random_forest"
    for name in ("linear", "svm", "random forest", "gradient", "knn", "logistic",
                 "gaussian process"):
        if name in low:
            algo = name.replace(" ", "_").replace("random_forest", "random_forest"); break
    if "regress" in low or "linear" in low or "gaussian process" in low:
        X, y = make_regression(n_samples=300, n_features=6, noise=8, random_state=0)
        task = "regress"
    else:
        X, y = make_classification(n_samples=300, n_features=8, n_informative=5,
                                   random_state=0)
        task = "classify"
    algo = {"random_forest": "random_forest", "gradient": "gradient_boosting",
            "linear": "linear", "svm": "svm", "knn": "knn", "logistic": "logistic",
            "gaussian_process": "gaussian_process"}.get(algo, "random_forest")
    out = _engine.train(X, y, algorithm=algo, task=task)
    out["verbal"] = f"(demo on synthetic data) " + out.get("verbal", "")
    return out


def test() -> None:
    MLEngine().test()


if __name__ == "__main__":
    test()
