"""
ai/threat/threat_model.py

PyTorch neural network for threat classification.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    nn = None  # type: ignore[misc]

try:
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Model Architecture
# ═══════════════════════════════════════════════════════════════════════════════

class ThreatClassifierNet(nn.Module if TORCH_AVAILABLE else object):  # type: ignore[misc]
    """PyTorch neural network for threat classification."""

    def __init__(
        self,
        input_dim: int = 21,
        hidden_dim: int = 64,
        n_classes: int = 7,
        dropout: float = 0.3,
    ) -> None:
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available — cannot instantiate ThreatClassifierNet")
        super().__init__()  # type: ignore[misc]
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),

            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),

            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),

            nn.Linear(hidden_dim // 2, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


# ═══════════════════════════════════════════════════════════════════════════════
# Trainer
# ═══════════════════════════════════════════════════════════════════════════════

class ThreatModelTrainer:
    """Trains the ThreatClassifierNet."""

    def __init__(self, model: ThreatClassifierNet, device: Optional[str] = None) -> None:
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available — cannot create trainer")
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = model.to(self.device)
        self.scaler: Any = None

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: Optional[np.ndarray] = None,
        y_test: Optional[np.ndarray] = None,
        epochs: int = 50,
        batch_size: int = 32,
        learning_rate: float = 0.001,
    ) -> dict[str, Any]:
        if not NUMPY_AVAILABLE or not SKLEARN_AVAILABLE:
            return {"error": "numpy or sklearn unavailable"}

        # Normalise features
        self.scaler = StandardScaler()
        X_norm = self.scaler.fit_transform(X_train)

        dataset = TensorDataset(
            torch.FloatTensor(X_norm),
            torch.LongTensor(y_train),
        )
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

        history: dict[str, list[float]] = {"loss": [], "acc": []}

        for epoch in range(epochs):
            self.model.train()
            epoch_loss = 0.0
            correct = 0
            total = 0

            for batch_x, batch_y in loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)

                optimizer.zero_grad()
                outputs = self.model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item() * batch_x.size(0)
                _, predicted = torch.max(outputs, 1)
                correct += (predicted == batch_y).sum().item()
                total += batch_y.size(0)

            avg_loss = epoch_loss / total
            acc = correct / total
            history["loss"].append(avg_loss)
            history["acc"].append(acc)
            scheduler.step(avg_loss)

            if (epoch + 1) % 10 == 0 or epoch == 0:
                logger.info(f"[ThreatModelTrainer] Epoch {epoch+1}/{epochs} — loss={avg_loss:.4f}, acc={acc:.4f}")

        # Evaluate on test set
        test_acc = None
        if X_test is not None and y_test is not None:
            test_acc = self._evaluate(X_test, y_test)

        return {
            "final_train_acc": history["acc"][-1],
            "final_train_loss": history["loss"][-1],
            "test_acc": test_acc,
            "epochs_trained": epochs,
            "history": history,
        }

    def _evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> float:
        if self.scaler is None:
            return 0.0
        X_norm = self.scaler.transform(X_test)
        self.model.eval()
        with torch.no_grad():
            inputs = torch.FloatTensor(X_norm).to(self.device)
            outputs = self.model(inputs)
            _, predicted = torch.max(outputs, 1)
            correct = (predicted.cpu().numpy() == y_test).sum()
            return float(correct / len(y_test))

    def save(self, path: str) -> None:
        state = {
            "model_state": self.model.state_dict(),
            "scaler": self.scaler,
            "input_dim": self.model.network[0].in_features,  # type: ignore[union-attr]
        }
        torch.save(state, path)

    def load(self, path: str) -> None:
        # weights_only=False: our checkpoint bundles a sklearn scaler object, and
        # torch>=2.6 defaults weights_only=True (which rejects it). These are
        # DEEP's own trusted checkpoints, so full unpickling is safe here.
        state = torch.load(path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(state["model_state"])
        self.scaler = state.get("scaler")


