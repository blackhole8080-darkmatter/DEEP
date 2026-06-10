"""Optional embedding-based intent fallback for the DEEP engine.

Keyword matching (`engine.main.DEEP.keyword_match`) stays the fast, precise
first pass. When it misses, this router embeds the query and the per-intent
keyword descriptions with a local sentence-transformers model and returns the
nearest intent above a cosine-similarity threshold — so paraphrases like
"spin up a container" can still reach `tech.cloud` even though they share no
literal keyword.

If sentence-transformers (or its model download) is unavailable, the router
stays disabled and routing behaves exactly as before. Initialization is lazy:
the model is only loaded the first time a keyword miss occurs.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

_DEFAULT_MODEL = os.getenv("DEEP_INTENT_EMBED_MODEL", "all-MiniLM-L6-v2")
_DEFAULT_THRESHOLD = float(os.getenv("DEEP_INTENT_SEMANTIC_THRESHOLD", "0.45"))


class SemanticIntentRouter:
    """Nearest-neighbour intent matcher over INTENT_MAP keyword descriptions."""

    def __init__(self, intent_map: dict, model_name: str = _DEFAULT_MODEL,
                 threshold: float = _DEFAULT_THRESHOLD):
        self._intent_map = intent_map
        self._model_name = model_name
        self._threshold = threshold
        self._model = None
        self._targets: list[Tuple[str, str]] = []
        self._embeddings = None  # normalized ndarray [n_intents, dim]
        self._enabled: Optional[bool] = None  # tri-state until first init attempt

    @property
    def enabled(self) -> bool:
        if self._enabled is None:
            self._try_init()
        return bool(self._enabled)

    def _try_init(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            descriptions = []
            for keywords, target in self._intent_map.items():
                descriptions.append(", ".join(keywords))
                self._targets.append(target)
            self._embeddings = self._model.encode(descriptions, normalize_embeddings=True)
            self._enabled = True
        except Exception:
            self._enabled = False

    def match(self, text: str) -> Optional[Tuple[str, str]]:
        """Return (module, function) for the nearest intent, or None below threshold."""
        if not self.enabled:
            return None
        try:
            import numpy as np

            q = self._model.encode([text], normalize_embeddings=True)[0]
            sims = self._embeddings @ q  # cosine, since both sides are normalized
            idx = int(np.argmax(sims))
            if float(sims[idx]) >= self._threshold:
                return self._targets[idx]
        except Exception:
            return None
        return None
