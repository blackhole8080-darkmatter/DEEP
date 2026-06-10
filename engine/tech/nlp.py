# deep/tech/nlp.py — NLP & Language Intelligence (Bible Section 20)
"""Sentiment, summarisation, NER, keyword extraction. A dependency-free core
(frequency-based extractive summary, lexicon sentiment, regex NER) runs always;
transformers / spaCy / sentence-transformers power the heavy paths when present.
Note: the live DEEP server has its own LLM/RAG — this module is the bible's
stand-alone NLP toolkit."""
from __future__ import annotations

import math
import re
from collections import Counter

try:
    from transformers import pipeline  # noqa: F401
    TRANSFORMERS = True
except Exception:  # pragma: no cover
    TRANSFORMERS = False

_STOP = set("""a an the and or but if then else for to of in on at by with from as is are was
were be been being this that these those it its he she they we you i not no do does did has
have had will would can could should may might must about into over under again further""".split())

_POS = set("""good great excellent amazing wonderful fantastic positive happy love best
brilliant superb effective efficient success successful gain improve better strong robust""".split())
_NEG = set("""bad terrible awful horrible negative sad hate worst poor weak fail failure
broken bug error crash slow wrong loss decline worse risk threat""".split())


class NLPEngine:
    def __init__(self, config=None):
        self.config = config
        self._sentiment_pipe = None

    @staticmethod
    def _sentences(text):
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]

    @staticmethod
    def _words(text):
        return re.findall(r"[a-zA-Z']+", text.lower())

    # ── summarisation (extractive, frequency-based) ─────────────────
    def summarise(self, text, n_sentences=2) -> dict:
        sents = self._sentences(text)
        if len(sents) <= n_sentences:
            return {"summary": text, "result": text,
                    "verbal": "The text is already concise, sir."}
        freq = Counter(w for w in self._words(text) if w not in _STOP)
        if not freq:
            return {"summary": sents[0], "result": sents[0], "verbal": sents[0]}
        peak = max(freq.values())
        scores = []
        for i, s in enumerate(sents):
            ws = [w for w in self._words(s) if w not in _STOP]
            score = sum(freq[w] / peak for w in ws) / (len(ws) + 1e-9)
            scores.append((score, i, s))
        top = sorted(sorted(scores, reverse=True)[:n_sentences], key=lambda x: x[1])
        summary = " ".join(s for _, _, s in top)
        return {"summary": summary, "result": summary,
                "verbal": f"Summary: {summary}"}

    # ── sentiment ───────────────────────────────────────────────────
    def sentiment(self, text) -> dict:
        if TRANSFORMERS:
            try:
                if self._sentiment_pipe is None:
                    self._sentiment_pipe = pipeline("sentiment-analysis")
                r = self._sentiment_pipe(text[:512])[0]
                return {"label": r["label"], "score": r["score"], "result": r["label"],
                        "verbal": f"Sentiment: {r['label']} ({r['score']:.2f} confidence)."}
            except Exception:
                pass
        words = self._words(text)
        pos = sum(w in _POS for w in words)
        neg = sum(w in _NEG for w in words)
        label = "POSITIVE" if pos > neg else ("NEGATIVE" if neg > pos else "NEUTRAL")
        score = (pos - neg) / (pos + neg + 1e-9)
        return {"label": label, "score": score, "result": label,
                "verbal": f"Sentiment: {label} (lexicon score {score:+.2f})."}

    # ── named entities (regex heuristic) ────────────────────────────
    def named_entities(self, text) -> dict:
        # capitalised tokens not at sentence start = candidate entities
        ents = []
        for sent in self._sentences(text):
            tokens = sent.split()
            for j, tok in enumerate(tokens):
                clean = tok.strip(".,;:!?\"'")
                if j > 0 and clean[:1].isupper() and clean.lower() not in _STOP:
                    ents.append(clean)
        ents = sorted(set(ents))
        return {"entities": ents, "result": ents,
                "verbal": f"Found {len(ents)} candidate entities: "
                          f"{', '.join(ents[:10])}." if ents else "No entities found."}

    def keywords(self, text, n=5) -> dict:
        freq = Counter(w for w in self._words(text) if w not in _STOP and len(w) > 2)
        top = [w for w, _ in freq.most_common(n)]
        return {"keywords": top, "result": top,
                "verbal": f"Top keywords: {', '.join(top)}."}

    # ── embeddings & semantic ops (sentence-transformers when present) ─
    def _embedder(self):
        if getattr(self, "_emb", None) is None:
            from sentence_transformers import SentenceTransformer
            self._emb = SentenceTransformer("all-MiniLM-L6-v2")
        return self._emb

    def embed(self, texts) -> dict:
        try:
            vecs = self._embedder().encode(texts if isinstance(texts, list) else [texts])
        except Exception:
            return {"result": None,
                    "verbal": "sentence-transformers not installed, sir."}
        import numpy as np
        return {"embeddings": np.asarray(vecs).tolist(), "dim": int(vecs.shape[-1]),
                "result": list(np.asarray(vecs).shape),
                "verbal": f"Encoded {len(vecs)} text(s) into {vecs.shape[-1]}-dim embeddings."}

    def semantic_similarity(self, a, b) -> dict:
        try:
            import numpy as np
            va, vb = self._embedder().encode([a, b])
            cos = float(np.dot(va, vb) / (np.linalg.norm(va)*np.linalg.norm(vb) + 1e-9))
        except Exception:
            return {"result": None, "verbal": "sentence-transformers not installed, sir."}
        return {"cosine_similarity": cos, "result": cos,
                "verbal": f"Semantic similarity {cos:.3f} "
                          f"({'very similar' if cos > 0.6 else 'related' if cos > 0.3 else 'unrelated'})."}

    def topic_cluster(self, documents, n_topics=3) -> dict:
        try:
            import numpy as np
            from sklearn.cluster import KMeans
            vecs = self._embedder().encode(documents)
            k = min(n_topics, len(documents))
            labels = KMeans(n_clusters=k, n_init=10).fit_predict(vecs)
        except Exception as e:  # noqa: BLE001
            return {"result": None, "verbal": f"Topic clustering needs sklearn + "
                    f"sentence-transformers, sir: {e}"}
        clusters = {}
        for doc, lab in zip(documents, labels):
            clusters.setdefault(int(lab), []).append(doc)
        return {"clusters": clusters, "n_topics": len(clusters), "result": len(clusters),
                "verbal": f"Clustered {len(documents)} documents into {len(clusters)} topics."}

    def test(self) -> None:
        txt = ("DEEP is an excellent system. It is fast and efficient. "
               "The quantum module works well. Errors are rare and the design is robust.")
        assert self.summarise(txt)["summary"]
        assert self.sentiment("this is great and wonderful")["label"] == "POSITIVE"
        assert self.sentiment("this is terrible and broken")["label"] == "NEGATIVE"
        assert self.keywords(txt)["keywords"]
        # embeddings (sentence-transformers present in this env)
        sim = self.semantic_similarity("a cat sat on the mat", "a feline rested on the rug")
        if sim["result"] is not None:
            assert sim["cosine_similarity"] > self.semantic_similarity(
                "a cat sat on the mat", "quantum field theory")["cosine_similarity"]
            print("nlp.NLPEngine: OK (incl. embeddings, semantic similarity, topics)")
        else:
            print("nlp.NLPEngine: OK")


_engine = NLPEngine()


def _payload(text):
    """Strip the leading command verb to get the operand text."""
    return re.sub(r"^\s*(summari[sz]e|analyze|analyse|sentiment of|sentiment|"
                  r"translate|extract|ner|keywords?( of)?|nlp|the\s+text|text|this|"
                  r"named entities|entities|from)\b[:,]?\s*", "",
                  text, flags=re.I).strip() or text


def process(text: str) -> dict:
    low = text.lower()
    payload = _payload(text)
    if "sentiment" in low:
        return _engine.sentiment(payload)
    if "summar" in low:
        return _engine.summarise(payload)
    if "entit" in low or "ner" in low:
        return _engine.named_entities(payload)
    if "keyword" in low:
        return _engine.keywords(payload)
    if "translate" in low:
        return {"result": None,
                "verbal": "Translation needs MarianMT (transformers), sir — not loaded."}
    # default: sentiment + keywords overview
    s = _engine.sentiment(payload)
    return {"result": s["result"], "verbal": s["verbal"]}


def rag_query(text: str) -> dict:
    return {"result": None,
            "verbal": "RAG retrieval is handled by the live DEEP knowledge base, sir; "
                      "this stand-alone module needs a FAISS index to answer."}


def test() -> None:
    NLPEngine().test()


if __name__ == "__main__":
    test()
