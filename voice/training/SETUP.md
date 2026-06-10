# DEEP Custom Wake-Word Setup Guide

This guide walks you through recording your voice, training a custom "DEEP" wake-word model, and enabling it in DEEP.

---

## Step 1 — Record Your Voice (~10 minutes)

```bash
python voice/training/record_samples.py
```

You will record:
- **50 positive samples** of you saying "DEEP" in different conditions
- **30 negative samples** of background noise, random words, room ambience

### Tips for best results
- Record in your **actual room** (not a quiet booth)
- Vary your **distance**: 0.5 m, 1 m, 2 m from the microphone
- Vary your **tone**: normal, tired, energetic, quiet
- Say it as you **naturally would** — not robotically
- Record at **different times of day** if possible

---

## Step 2 — Train the Model (5–15 minutes on CPU)

```bash
python voice/training/train_wake_word.py
```

The script will:
1. Augment your 50 samples into 500+ synthetic variants
2. Augment 30 negatives into 300 variants
3. Extract 96-dimensional audio features
4. Train a base wake-word classifier
5. Train a **voice verifier** on your real samples only
6. Export both models to ONNX + joblib format
7. Run quick validation and print accuracy / TPR / FPR

### Watch for these metrics
- **Cross-validation accuracy > 0.90** is good
- **True positive rate (TPR) > 0.80** on validation set
- If accuracy < 0.85: record 20 more samples and retrain

---

## Step 3 — Test It Live

```bash
python voice/training/evaluate_model.py
```

This will:
- Show historical detection stats (if any exist)
- Run a **30-second live test**: say "DEEP" ~5 times
- Report real-time TPR and FPR for this session

---

## Step 4 — Enable in DEEP

Edit `core/config.py`:

```python
wake_word_model: str = _get_env("WAKE_WORD_MODEL", "deep_custom")
```

Or set the environment variable:

```bash
export WAKE_WORD_MODEL=deep_custom
```

Restart DEEP — it will now wake **only** on your voice saying "DEEP".

---

## Step 5 — Tune If Needed

| Problem | Fix |
|---|---|
| Too many false positives | Increase `VOICE_VERIFIER_THRESHOLD` to **0.7** |
| Misses your voice sometimes | Decrease `VOICE_VERIFIER_THRESHOLD` to **0.5** |
| Still poor after tuning | Record **30 more samples** and retrain |

Edit in `core/config.py`:

```python
voice_verifier_threshold: float = float(_get_env("VOICE_VERIFIER_THRESHOLD", "0.6"))
```

Or via environment variable:

```bash
export VOICE_VERIFIER_THRESHOLD=0.7
```

---

## File Layout

```
voice/training/
  record_samples.py          # Step 1: record your voice
  augment_samples.py         # Step 2: synthetic data expansion
  train_wake_word.py         # Step 2: train + export models
  evaluate_model.py          # Step 3: live evaluation
  SETUP.md                   # this file

voice/training/samples/
  positive/                  # 50+ "DEEP" recordings
  negative/                  # 30+ noise / other words
  augmented_positive/        # 500+ generated automatically
  augmented_negative/        # 300+ generated automatically

voice/models/
  deep_wake_word.onnx       # base classifier (fast inference)
  deep_verifier.pkl         # voice verifier (Aryan's voice filter)
```

---

## Troubleshooting

### `librosa not installed`
```bash
pip install librosa soundfile scipy
```

### `skl2onnx not installed` (ONNX export skipped)
```bash
pip install skl2onnx
```

### `onnxruntime not installed` (inference fails)
```bash
pip install onnxruntime
```

### Model files not found on startup
DEEP will **gracefully fall back** to the built-in `hey_jarvis` model. Re-run `train_wake_word.py` to generate the missing files.

---

## Advanced: Re-train Periodically

Voice changes over time (colds, microphone changes, room changes). Re-run Steps 1–2 every few months for best accuracy.

```bash
# Quick re-train with existing + new samples
python voice/training/record_samples.py   # add 20 more
python voice/training/train_wake_word.py  # retrain
```
