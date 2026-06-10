"""
ml_catalog.py - Layer 1 of the Deep ML capability stack.

A structured, queryable knowledge base of the prevalent machine-learning
algorithms. This module holds NO model code; it is the *brain* that lets Deep
be aware of every algorithm, explain it, and recommend the right one for a
problem. Execution (Layer 2) calls the real libraries (scikit-learn, XGBoost,
PyTorch) - see ml_runner.py when that lands.

Design goals:
- Compact: the whole catalog is plain data so it never blows the LLM context.
- Honest: every entry names the real library you would actually use.
- Evaluative: `recommend()` maps a problem description to candidate algorithms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True, slots=True)
class Algorithm:
    name: str
    family: str            # supervised | unsupervised | deep_learning | reinforcement | optimization
    summary: str           # one-line "what it does"
    when: str              # when to reach for it
    library: str           # the real library/class you'd actually call
    note: str = ""         # caveats / honest notes
    tags: tuple[str, ...] = field(default_factory=tuple)  # problem keywords for recommend()


# ---------------------------------------------------------------------------
# The catalog. ~27 unique algorithms across 5 families.
# ---------------------------------------------------------------------------

_CATALOG: dict[str, Algorithm] = {
    # ---- Supervised ----
    "linear_regression": Algorithm(
        "Linear Regression", "supervised",
        "Fits a straight line to predict a continuous number.",
        "Predicting a numeric value with roughly linear relationships (price, demand).",
        "sklearn.linear_model.LinearRegression",
        tags=("regression", "numeric", "predict", "continuous", "baseline"),
    ),
    "logistic_regression": Algorithm(
        "Logistic Regression", "supervised",
        "Outputs a probability (0-1) for binary/multiclass classification.",
        "Yes/no or class decisions when you want a fast, interpretable baseline.",
        "sklearn.linear_model.LogisticRegression",
        tags=("classification", "probability", "binary", "baseline"),
    ),
    "decision_tree": Algorithm(
        "Decision Tree", "supervised",
        "A flowchart of if/else splits on features.",
        "When you need a human-readable model you can inspect.",
        "sklearn.tree.DecisionTreeClassifier / DecisionTreeRegressor",
        note="Overfits easily on its own; usually better inside a forest/boosting.",
        tags=("classification", "regression", "interpretable", "rules"),
    ),
    "random_forest": Algorithm(
        "Random Forest", "supervised",
        "Many decision trees voting together (bagging).",
        "Strong, robust default for tabular data with little tuning.",
        "sklearn.ensemble.RandomForestClassifier / RandomForestRegressor",
        tags=("classification", "regression", "tabular", "robust", "ensemble"),
    ),
    "svm": Algorithm(
        "Support Vector Machine (SVM)", "supervised",
        "Finds the maximum-margin boundary between classes (kernelizable).",
        "Smaller datasets with clear separation; high-dimensional spaces (text).",
        "sklearn.svm.SVC / SVR",
        note="Scales poorly past ~10k+ rows; needs feature scaling.",
        tags=("classification", "regression", "margin", "kernel", "text"),
    ),
    "knn": Algorithm(
        "K-Nearest Neighbors (KNN)", "supervised",
        "Classifies a point by the majority vote of its k closest neighbors.",
        "Simple similarity-based prediction; no training step.",
        "sklearn.neighbors.KNeighborsClassifier / KNeighborsRegressor",
        note="Slow at predict time on big data; needs feature scaling.",
        tags=("classification", "regression", "similarity", "instance", "baseline"),
    ),
    "naive_bayes": Algorithm(
        "Naive Bayes", "supervised",
        "Probabilistic classifier via Bayes' theorem, assumes feature independence.",
        "Text/spam classification; very fast, strong baseline on bag-of-words.",
        "sklearn.naive_bayes.MultinomialNB / GaussianNB",
        tags=("classification", "text", "probability", "fast", "nlp"),
    ),
    "gradient_boosting": Algorithm(
        "Gradient Boosting", "supervised",
        "Builds trees sequentially, each correcting the previous errors.",
        "High-accuracy tabular models when you can afford tuning.",
        "sklearn.ensemble.GradientBoostingClassifier / HistGradientBoosting",
        tags=("classification", "regression", "tabular", "ensemble", "boosting"),
    ),
    "adaboost": Algorithm(
        "AdaBoost", "supervised",
        "Early boosting; reweights hard examples each round.",
        "Simple boosting baseline; mostly superseded by gradient boosting.",
        "sklearn.ensemble.AdaBoostClassifier / AdaBoostRegressor",
        tags=("classification", "regression", "boosting", "ensemble"),
    ),
    "xgboost": Algorithm(
        "XGBoost", "supervised",
        "Optimized, regularized gradient boosting - industrial grade.",
        "Default winner for most structured/tabular problems.",
        "xgboost.XGBClassifier / XGBRegressor",
        note="Separate pip package (xgboost). Often the strongest tabular model.",
        tags=("classification", "regression", "tabular", "boosting", "competition"),
    ),

    # ---- Unsupervised ----
    "kmeans": Algorithm(
        "K-Means Clustering", "unsupervised",
        "Partitions data into k clusters by distance to centroids.",
        "Fast clustering when you know roughly how many groups exist.",
        "sklearn.cluster.KMeans (init='k-means++' by default)",
        note="k-means++ is the smart centroid init, built into KMeans already.",
        tags=("clustering", "segmentation", "groups", "unsupervised"),
    ),
    "hierarchical_clustering": Algorithm(
        "Hierarchical Clustering", "unsupervised",
        "Builds a tree (dendrogram) of nested clusters.",
        "When you want cluster structure at multiple granularities.",
        "sklearn.cluster.AgglomerativeClustering",
        tags=("clustering", "dendrogram", "hierarchy", "unsupervised"),
    ),
    "dbscan": Algorithm(
        "DBSCAN", "unsupervised",
        "Density-based clustering; finds arbitrary shapes and flags noise.",
        "Clustering with outliers and unknown cluster count.",
        "sklearn.cluster.DBSCAN",
        tags=("clustering", "density", "outliers", "anomaly", "unsupervised"),
    ),
    "pca": Algorithm(
        "Principal Component Analysis (PCA)", "unsupervised",
        "Linear dimensionality reduction keeping maximum variance.",
        "Compressing features, denoising, speeding up downstream models.",
        "sklearn.decomposition.PCA",
        tags=("dimensionality", "reduction", "compression", "features"),
    ),
    "tsne": Algorithm(
        "t-SNE", "unsupervised",
        "Nonlinear reduction to 2D/3D for visualization.",
        "Visualizing high-dimensional clusters - viz only, not features.",
        "sklearn.manifold.TSNE",
        note="Not for feature engineering; use UMAP for speed on big data.",
        tags=("dimensionality", "visualization", "embedding", "reduction"),
    ),
    "autoencoder": Algorithm(
        "Autoencoder", "unsupervised",
        "Neural net that compresses then reconstructs its input.",
        "Learned compression, denoising, and anomaly detection.",
        "PyTorch (custom nn.Module) or keras",
        tags=("dimensionality", "anomaly", "compression", "neural", "reconstruction"),
    ),
    "isolation_forest": Algorithm(
        "Isolation Forest", "unsupervised",
        "Detects anomalies by how easily a point is isolated by random splits.",
        "Outlier/anomaly detection on tabular data - fast and scalable.",
        "sklearn.ensemble.IsolationForest",
        note="Deep already uses anomaly detection in ai/anomaly - reuse it.",
        tags=("anomaly", "outliers", "detection", "unsupervised", "security"),
    ),

    # ---- Deep learning ----
    "ann": Algorithm(
        "Artificial Neural Network (ANN/MLP)", "deep_learning",
        "Fully-connected layers; the foundation of deep learning.",
        "Nonlinear tabular problems when trees underperform.",
        "torch.nn (nn.Linear stacks) or sklearn.neural_network.MLPClassifier",
        tags=("neural", "classification", "regression", "deep"),
    ),
    "cnn": Algorithm(
        "Convolutional Neural Network (CNN)", "deep_learning",
        "Convolution layers specialized for spatial/image data.",
        "Image classification, detection, any grid-structured input.",
        "torch.nn.Conv2d stacks / torchvision models",
        tags=("image", "vision", "spatial", "neural", "deep"),
    ),
    "rnn": Algorithm(
        "Recurrent Neural Network (RNN)", "deep_learning",
        "Processes sequences step by step, carrying hidden state.",
        "Short sequence/time-series tasks (mostly superseded by LSTM/Transformer).",
        "torch.nn.RNN",
        note="Suffers vanishing gradients on long sequences - prefer LSTM.",
        tags=("sequence", "time-series", "text", "neural", "deep"),
    ),
    "lstm": Algorithm(
        "Long Short-Term Memory (LSTM)", "deep_learning",
        "Gated RNN that remembers long-range dependencies.",
        "Time series and sequence modeling without Transformer overhead.",
        "torch.nn.LSTM",
        tags=("sequence", "time-series", "text", "memory", "neural", "deep"),
    ),
    "transformer": Algorithm(
        "Transformer", "deep_learning",
        "Attention-based architecture; the backbone of modern LLMs.",
        "State-of-the-art for text/sequence; the core of Deep's own LLM.",
        "torch.nn.Transformer / HuggingFace transformers",
        note="Heavy to train from scratch; usually fine-tune a pretrained one.",
        tags=("sequence", "text", "attention", "nlp", "llm", "neural", "deep"),
    ),

    # ---- Reinforcement learning ----
    "mdp": Algorithm(
        "Markov Decision Process (MDP)", "reinforcement",
        "The math framework (states, actions, rewards) RL is built on.",
        "Framing any sequential decision problem before picking an RL algorithm.",
        "Conceptual framework (no single library); model in numpy/gymnasium.",
        note="Not an algorithm you 'run' - it's the model the rest assume.",
        tags=("framework", "decision", "rl", "states", "rewards"),
    ),
    "q_learning": Algorithm(
        "Q-Learning", "reinforcement",
        "Learns a table of action values; off-policy.",
        "Small discrete state/action problems.",
        "Custom (numpy Q-table) + gymnasium environments",
        tags=("rl", "value", "tabular", "control", "off-policy"),
    ),
    "sarsa": Algorithm(
        "SARSA", "reinforcement",
        "Like Q-learning but on-policy (learns the path actually taken).",
        "When you want the agent to account for its own exploration.",
        "Custom (numpy Q-table) + gymnasium environments",
        tags=("rl", "value", "tabular", "control", "on-policy"),
    ),
    "dqn": Algorithm(
        "Deep Q-Network (DQN)", "reinforcement",
        "Q-learning with a neural net replacing the value table.",
        "Large/continuous state spaces (e.g. learning from pixels).",
        "PyTorch + gymnasium, or stable-baselines3 DQN",
        tags=("rl", "value", "neural", "control", "deep"),
    ),
    "policy_gradient": Algorithm(
        "Policy Gradient (REINFORCE)", "reinforcement",
        "Directly learns which action to take, not action values.",
        "Continuous action spaces; stochastic policies.",
        "PyTorch, or stable-baselines3 (PPO/A2C build on this)",
        tags=("rl", "policy", "neural", "continuous", "control"),
    ),
    "actor_critic": Algorithm(
        "Actor-Critic", "reinforcement",
        "Combines a policy (actor) with a value estimator (critic).",
        "Stable, sample-efficient RL - basis of PPO/A2C/SAC.",
        "stable-baselines3 (PPO, A2C, SAC) on gymnasium",
        tags=("rl", "policy", "value", "neural", "control", "deep"),
    ),

    # ---- Optimization / search ----
    "genetic_algorithm": Algorithm(
        "Genetic Algorithm", "optimization",
        "Evolutionary search: mutate, recombine, and select candidates.",
        "Black-box optimization where gradients are unavailable.",
        "DEAP, or PyGAD (custom fitness function)",
        note="Optimization/search, not learning from labeled data.",
        tags=("optimization", "search", "evolution", "tuning", "blackbox"),
    ),
}


# ---------------------------------------------------------------------------
# Query API - used by the Deep ToolBox tools.
# ---------------------------------------------------------------------------

_FAMILY_LABELS = {
    "supervised": "Supervised Learning",
    "unsupervised": "Unsupervised Learning",
    "deep_learning": "Deep Learning",
    "reinforcement": "Reinforcement Learning",
    "optimization": "Optimization / Search",
}


def _resolve_key(query: str) -> Optional[str]:
    """Map a loose user string to a catalog key."""
    q = (query or "").strip().lower().replace("-", "_").replace(" ", "_")
    if q in _CATALOG:
        return q
    # alias / fuzzy contains match against keys and names
    for key, algo in _CATALOG.items():
        if q and (q in key or q in algo.name.lower().replace("-", "_").replace(" ", "_")):
            return key
    return None


def _format_algo(algo: Algorithm) -> str:
    lines = [
        f"{algo.name}  [{_FAMILY_LABELS.get(algo.family, algo.family)}]",
        f"  What it does : {algo.summary}",
        f"  When to use  : {algo.when}",
        f"  Real library : {algo.library}",
    ]
    if algo.note:
        lines.append(f"  Note         : {algo.note}")
    return "\n".join(lines)


def explain(query: str) -> str:
    """Explain one algorithm, or list the whole catalog if query is empty/'all'."""
    q = (query or "").strip().lower()
    if not q or q in ("all", "list", "everything", "*"):
        return list_all()

    key = _resolve_key(q)
    if key is None:
        return (
            f"No algorithm matched '{query}'. Use the ml_list tool to see all "
            f"{len(_CATALOG)} algorithms, or try a shorter name (e.g. 'xgboost', 'lstm')."
        )
    return _format_algo(_CATALOG[key])


def list_all() -> str:
    """Compact grouped listing of every algorithm Deep knows."""
    by_family: dict[str, list[Algorithm]] = {}
    for algo in _CATALOG.values():
        by_family.setdefault(algo.family, []).append(algo)

    parts = [f"Deep ML Algorithm Catalog - {len(_CATALOG)} algorithms:"]
    for family in ("supervised", "unsupervised", "deep_learning", "reinforcement", "optimization"):
        algos = by_family.get(family, [])
        if not algos:
            continue
        parts.append(f"\n## {_FAMILY_LABELS[family]}")
        for algo in algos:
            parts.append(f"  - {algo.name}: {algo.summary}")
    return "\n".join(parts)


def recommend(problem: str) -> str:
    """Score algorithms against a free-text problem description and rank them."""
    text = (problem or "").strip().lower()
    if not text:
        return "Describe the problem (e.g. 'classify spam emails', 'detect anomalies in network traffic')."

    def _tag_hit(tag: str) -> bool:
        # Match the tag or its singular stem so plurals ("anomalies") still hit.
        if tag in text:
            return True
        if len(tag) >= 5 and tag[:-1] in text:  # crude stem: "anomaly"->"anomal"
            return True
        return False

    scored: list[tuple[int, Algorithm]] = []
    for algo in _CATALOG.values():
        score = 0
        for tag in algo.tags:
            if _tag_hit(tag):
                score += 2
        # light boosts from family-level intent words
        if any(w in text for w in ("classify", "classification", "label")) and "classification" in algo.tags:
            score += 1
        if any(w in text for w in ("predict number", "forecast", "continuous", "price")) and "regression" in algo.tags:
            score += 1
        if any(w in text for w in ("cluster", "group", "segment")) and "clustering" in algo.tags:
            score += 1
        if any(w in text for w in ("anomaly", "outlier", "fraud", "intrusion")) and "anomaly" in algo.tags:
            score += 2
        if any(w in text for w in ("image", "photo", "vision")) and "image" in algo.tags:
            score += 2
        if any(w in text for w in ("text", "nlp", "language", "sentence")) and "text" in algo.tags:
            score += 1
        if any(w in text for w in ("sequence", "time series", "time-series", "temporal")) and "sequence" in algo.tags:
            score += 2
        if any(w in text for w in ("agent", "reward", "reinforcement", "game", "control")) and "rl" in algo.tags:
            score += 2
        if score:
            scored.append((score, algo))

    if not scored:
        return (
            f"Couldn't confidently match '{problem}'. Try keywords like classify, "
            f"cluster, forecast, anomaly, image, text, sequence, or reinforcement. "
            f"Or use ml_list to browse all {len(_CATALOG)} algorithms."
        )

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:4]
    parts = [f"Recommended algorithms for: \"{problem}\""]
    for rank, (_, algo) in enumerate(top, 1):
        parts.append(
            f"\n{rank}. {algo.name} - {algo.summary}"
            f"\n   When: {algo.when}"
            f"\n   Library: {algo.library}"
        )
    return "\n".join(parts)


def catalog_size() -> int:
    return len(_CATALOG)
