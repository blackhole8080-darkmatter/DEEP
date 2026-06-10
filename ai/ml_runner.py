"""
ml_runner.py - Layer 2 of the Deep ML capability stack.

This is where the algorithms in ml_catalog.py become *real*: Deep can train a
model, score it, persist it, and predict with it by calling the actual
scikit-learn implementations. No hand-rolled math - we call the battle-tested
library named in each catalog entry.

Pure by design: every function takes a pandas DataFrame. Data-source resolution
(CSV files vs. Deep's own internal data) lives in the ToolBox handler, so this
module stays testable in isolation.

Scope (v1): the scikit-learn-backed algorithms that are installed and runnable
today - supervised classification/regression, clustering, anomaly detection,
and dimensionality reduction. XGBoost / deep learning / RL are advise-only until
their libraries land (see ml_catalog.py).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, f1_score, r2_score, mean_absolute_error, silhouette_score,
)


# ---------------------------------------------------------------------------
# Algorithm registry: catalog key -> how to build & what kind of task it is.
# Estimators are imported lazily inside factories so a missing optional lib
# only breaks that one algorithm, never the whole module.
# ---------------------------------------------------------------------------

KIND_CLASSIFIER = "classifier"
KIND_REGRESSOR = "regressor"
KIND_CLUSTER = "cluster"
KIND_ANOMALY = "anomaly"
KIND_REDUCE = "reduce"


@dataclass(frozen=True, slots=True)
class Spec:
    kind: str
    factory: Callable[[dict[str, Any]], Any]
    scale: bool = False  # wrap in StandardScaler pipeline (distance/margin models)


def _spec_registry() -> dict[str, Spec]:
    from sklearn.linear_model import LinearRegression, LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import (
        RandomForestClassifier, GradientBoostingClassifier,
        AdaBoostClassifier, IsolationForest,
    )
    from sklearn.svm import SVC
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.naive_bayes import GaussianNB
    from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
    from sklearn.decomposition import PCA
    from sklearn.manifold import TSNE

    registry = {
        # supervised
        "linear_regression": Spec(KIND_REGRESSOR, lambda p: LinearRegression(**p)),
        "logistic_regression": Spec(KIND_CLASSIFIER, lambda p: LogisticRegression(max_iter=1000, **p), scale=True),
        "decision_tree": Spec(KIND_CLASSIFIER, lambda p: DecisionTreeClassifier(**p)),
        "random_forest": Spec(KIND_CLASSIFIER, lambda p: RandomForestClassifier(**p)),
        "svm": Spec(KIND_CLASSIFIER, lambda p: SVC(**p), scale=True),
        "knn": Spec(KIND_CLASSIFIER, lambda p: KNeighborsClassifier(**p), scale=True),
        "naive_bayes": Spec(KIND_CLASSIFIER, lambda p: GaussianNB(**p)),
        "gradient_boosting": Spec(KIND_CLASSIFIER, lambda p: GradientBoostingClassifier(**p)),
        "adaboost": Spec(KIND_CLASSIFIER, lambda p: AdaBoostClassifier(**p)),
        # unsupervised
        "kmeans": Spec(KIND_CLUSTER, lambda p: KMeans(n_init="auto", **p), scale=True),
        "hierarchical_clustering": Spec(KIND_CLUSTER, lambda p: AgglomerativeClustering(**p), scale=True),
        "dbscan": Spec(KIND_CLUSTER, lambda p: DBSCAN(**p), scale=True),
        "isolation_forest": Spec(KIND_ANOMALY, lambda p: IsolationForest(random_state=42, **p)),
        "pca": Spec(KIND_REDUCE, lambda p: PCA(**p)),
        "tsne": Spec(KIND_REDUCE, lambda p: TSNE(**p)),
    }

    # XGBoost is an optional dependency; only register it if installed.
    try:
        from xgboost import XGBClassifier
        registry["xgboost"] = Spec(
            KIND_CLASSIFIER,
            lambda p: XGBClassifier(eval_metric="logloss", **p),
        )
    except ImportError:
        pass

    return registry


def runnable_algorithms() -> list[str]:
    """Catalog keys this runner can actually execute today."""
    return sorted(_spec_registry().keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _numeric_features(df: pd.DataFrame, drop: Optional[list[str]] = None) -> pd.DataFrame:
    drop = drop or []
    feats = df.drop(columns=[c for c in drop if c in df.columns], errors="ignore")
    num = feats.select_dtypes(include=[np.number])
    return num.dropna(axis=1, how="all")


def _wrap(spec: Spec, params: dict[str, Any]) -> Any:
    est = spec.factory(params)
    if spec.scale:
        return Pipeline([("scaler", StandardScaler()), ("model", est)])
    return est


# ---------------------------------------------------------------------------
# Train / predict
# ---------------------------------------------------------------------------

def train(
    df: pd.DataFrame,
    algorithm: str,
    target: Optional[str] = None,
    params: Optional[dict[str, Any]] = None,
    save_as: Optional[str] = None,
    models_dir: Optional[str] = None,
) -> str:
    """Train `algorithm` on `df` and return a human-readable report."""
    params = params or {}
    algo = (algorithm or "").strip().lower().replace("-", "_").replace(" ", "_")
    specs = _spec_registry()
    if algo not in specs:
        return (
            f"'{algorithm}' is not runnable in Layer 2 yet. Runnable now: "
            f"{', '.join(runnable_algorithms())}. "
            f"(XGBoost / deep learning / RL are advise-only until their libs are installed.)"
        )

    spec = specs[algo]
    if df is None or df.empty:
        return "No data: the provided dataset is empty."

    try:
        if spec.kind in (KIND_CLASSIFIER, KIND_REGRESSOR):
            if not target or target not in df.columns:
                return f"This algorithm is supervised - specify a valid target column. Columns: {list(df.columns)}"
            X = _numeric_features(df, drop=[target])
            if X.shape[1] == 0:
                return "No numeric feature columns found to train on."
            y = df[target]
            X = X.fillna(X.mean(numeric_only=True))
            stratify = y if spec.kind == KIND_CLASSIFIER and y.nunique() > 1 else None
            X_tr, X_te, y_tr, y_te = train_test_split(
                X, y, test_size=0.25, random_state=42, stratify=stratify
            )
            model = _wrap(spec, params)
            model.fit(X_tr, y_tr)
            pred = model.predict(X_te)
            if spec.kind == KIND_CLASSIFIER:
                acc = accuracy_score(y_te, pred)
                f1 = f1_score(y_te, pred, average="weighted")
                metrics = f"accuracy={acc:.3f}, f1_weighted={f1:.3f}"
            else:
                metrics = f"R2={r2_score(y_te, pred):.3f}, MAE={mean_absolute_error(y_te, pred):.3f}"
            report = [
                f"Trained {algo} ({spec.kind}) on {len(df)} rows, {X.shape[1]} features.",
                f"Test metrics: {metrics}",
            ]
            saved = _maybe_save(model, save_as, models_dir, algo, spec.kind, list(X.columns), target)
            if saved:
                report.append(saved)
            return "\n".join(report)

        if spec.kind == KIND_CLUSTER:
            X = _numeric_features(df)
            if X.shape[1] == 0:
                return "No numeric columns to cluster."
            X = X.fillna(X.mean(numeric_only=True))
            model = _wrap(spec, params)
            labels = model.fit_predict(X)
            uniq, counts = np.unique(labels, return_counts=True)
            sizes = ", ".join(f"cluster {int(u)}: {int(c)}" for u, c in zip(uniq, counts))
            report = [f"Clustered {len(df)} rows with {algo} -> {len(uniq)} groups.", f"Sizes: {sizes}"]
            if len(uniq) > 1 and -1 not in uniq:
                try:
                    report.append(f"Silhouette score: {silhouette_score(X, labels):.3f}")
                except Exception:
                    pass
            saved = _maybe_save(model, save_as, models_dir, algo, spec.kind, list(X.columns), None)
            if saved:
                report.append(saved)
            return "\n".join(report)

        if spec.kind == KIND_ANOMALY:
            X = _numeric_features(df)
            if X.shape[1] == 0:
                return "No numeric columns for anomaly detection."
            X = X.fillna(X.mean(numeric_only=True))
            model = _wrap(spec, params)
            labels = model.fit_predict(X)  # -1 = anomaly, 1 = normal
            n_anom = int((labels == -1).sum())
            report = [
                f"Ran {algo} on {len(df)} rows, {X.shape[1]} features.",
                f"Flagged {n_anom} anomalies ({n_anom / len(df) * 100:.1f}%).",
            ]
            saved = _maybe_save(model, save_as, models_dir, algo, spec.kind, list(X.columns), None)
            if saved:
                report.append(saved)
            return "\n".join(report)

        if spec.kind == KIND_REDUCE:
            X = _numeric_features(df)
            if X.shape[1] == 0:
                return "No numeric columns to reduce."
            X = X.fillna(X.mean(numeric_only=True))
            model = spec.factory(params)
            transformed = model.fit_transform(X)
            report = [f"Reduced {X.shape[1]} features -> {transformed.shape[1]} components with {algo}."]
            if algo == "pca" and hasattr(model, "explained_variance_ratio_"):
                evr = model.explained_variance_ratio_
                report.append(
                    "Explained variance: "
                    + ", ".join(f"PC{i+1}={v:.1%}" for i, v in enumerate(evr[:5]))
                    + f" (total {evr.sum():.1%})"
                )
            return "\n".join(report)

        return f"Unhandled algorithm kind: {spec.kind}"
    except Exception as e:
        return f"Training failed for {algo}: {type(e).__name__}: {e}"


def _maybe_save(
    model: Any, save_as: Optional[str], models_dir: Optional[str],
    algo: str, kind: str, features: list[str], target: Optional[str],
) -> Optional[str]:
    if not save_as or not models_dir:
        return None
    try:
        os.makedirs(models_dir, exist_ok=True)
        safe = "".join(c for c in save_as if c.isalnum() or c in ("-", "_")).strip("_") or "model"
        path = os.path.join(models_dir, f"{safe}.joblib")
        joblib.dump(
            {"model": model, "algo": algo, "kind": kind, "features": features, "target": target},
            path,
        )
        return f"Saved model as '{safe}' ({path})."
    except Exception as e:
        return f"(Model trained but save failed: {e})"


def predict(df: pd.DataFrame, model_name: str, models_dir: str) -> str:
    """Load a saved model and predict on `df`. Returns a short summary."""
    safe = "".join(c for c in (model_name or "") if c.isalnum() or c in ("-", "_")).strip("_")
    path = os.path.join(models_dir, f"{safe}.joblib")
    if not os.path.exists(path):
        return f"No saved model named '{model_name}'. Train one first with ml_train (save_as=...)."
    try:
        bundle = joblib.load(path)
        model, features, kind = bundle["model"], bundle["features"], bundle["kind"]
        missing = [c for c in features if c not in df.columns]
        if missing:
            return f"Input is missing required feature columns: {missing}"
        X = df[features].fillna(df[features].mean(numeric_only=True))
        preds = model.predict(X)
        if kind == KIND_ANOMALY:
            n_anom = int((preds == -1).sum())
            return f"Predicted with '{model_name}': {n_anom}/{len(df)} rows flagged as anomalies."
        head = ", ".join(str(p) for p in preds[:10])
        more = "" if len(preds) <= 10 else f" ... (+{len(preds) - 10} more)"
        return f"Predicted {len(preds)} rows with '{model_name}' ({bundle['algo']}). First: {head}{more}"
    except Exception as e:
        return f"Prediction failed: {type(e).__name__}: {e}"
