"""
voice/training/train_wake_word.py

Main training script for the custom "DEEP" wake word.
Run after record_samples.py.

Steps:
  1. Augment dataset
  2. Extract features
  3. Train base classifier
  4. Train voice verifier
  5. Export to ONNX
  6. Quick validation

Usage:
    python voice/training/train_wake_word.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from typing import List, Tuple

import numpy as np

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from voice.training.augment_samples import augment_dataset

warnings.filterwarnings("ignore", category=UserWarning)

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    SKL2ONNX_AVAILABLE = True
except ImportError:
    SKL2ONNX_AVAILABLE = False

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

SAMPLE_RATE = 16000
CLIP_DURATION = 1.5
CLIP_SAMPLES = int(SAMPLE_RATE * CLIP_DURATION)
FEATURE_DIM = 96

POSITIVE_DIR = Path("voice/training/samples/positive")
NEGATIVE_DIR = Path("voice/training/samples/negative")
AUG_POSITIVE_DIR = Path("voice/training/samples/augmented_positive")
AUG_NEGATIVE_DIR = Path("voice/training/samples/augmented_negative")
MODEL_DIR = Path("voice/models")


def ensure_dirs() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    AUG_POSITIVE_DIR.mkdir(parents=True, exist_ok=True)
    AUG_NEGATIVE_DIR.mkdir(parents=True, exist_ok=True)


def load_audio(path: Path, sr: int = SAMPLE_RATE) -> np.ndarray:
    audio, _ = librosa.load(str(path), sr=sr, mono=True)
    return audio


def pad_or_trim(audio: np.ndarray, target_len: int = CLIP_SAMPLES) -> np.ndarray:
    if len(audio) >= target_len:
        return audio[:target_len]
    return np.pad(audio, (0, target_len - len(audio)), mode="constant")


def extract_features(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Extract a 96-dimensional feature vector from a 1.5s audio clip.
    Tries openwakeword.utils.AudioFeatures first, falls back to mel-spectrogram.
    """
    try:
        from openwakeword.utils import AudioFeatures as OwwAudioFeatures

        feat_extractor = OwwAudioFeatures()
        features = feat_extractor.get_embeddings(audio)
        if features.shape[-1] == FEATURE_DIM or features.shape[0] == FEATURE_DIM:
            return features.reshape(1, FEATURE_DIM)
    except Exception:
        pass

    # Fallback: 96-bin mel spectrogram mean
    mel = librosa.feature.melspectrogram(
        y=audio, sr=sr, n_mels=FEATURE_DIM, n_fft=512, hop_length=256
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)
    features = np.mean(log_mel, axis=1)
    return features.reshape(1, FEATURE_DIM)


def build_dataset(pos_dir: Path, neg_dir: Path) -> Tuple[np.ndarray, np.ndarray]:
    features_list: List[np.ndarray] = []
    labels_list: List[int] = []

    pos_files = sorted(pos_dir.glob("*.wav"))
    neg_files = sorted(neg_dir.glob("*.wav"))

    if not pos_files:
        print(f"ERROR: No positive samples found in {pos_dir}")
        sys.exit(1)
    if not neg_files:
        print(f"ERROR: No negative samples found in {neg_dir}")
        sys.exit(1)

    for path in pos_files:
        audio = load_audio(path)
        audio = pad_or_trim(audio)
        feat = extract_features(audio)
        features_list.append(feat)
        labels_list.append(1)

    for path in neg_files:
        audio = load_audio(path)
        audio = pad_or_trim(audio)
        feat = extract_features(audio)
        features_list.append(feat)
        labels_list.append(0)

    X = np.vstack(features_list)
    y = np.array(labels_list, dtype=np.int32)
    return X, y


def train_base_classifier(X: np.ndarray, y: np.ndarray) -> Pipeline:
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(C=0.1, max_iter=1000, class_weight="balanced")),
    ])

    print("\nTraining base wake-word classifier...")
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    print(f"Cross-validation accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    model.fit(X, y)
    return model


def train_verifier(pos_dir: Path, neg_dir: Path) -> Pipeline:
    """
    Train a second-stage verifier on Aryan's real positive samples only.
    Uses original positives vs. a subset of negatives as impostors.
    """
    features_list: List[np.ndarray] = []
    labels_list: List[int] = []

    # Only original 50 (or however many) real positive samples
    pos_files = sorted(pos_dir.glob("*.wav"))
    for path in pos_files:
        audio = load_audio(path)
        audio = pad_or_trim(audio)
        feat = extract_features(audio)
        features_list.append(feat)
        labels_list.append(1)

    # Use negative samples as impostors (limit to same count for balance)
    neg_files = sorted(neg_dir.glob("*.wav"))
    impostor_count = min(len(pos_files), len(neg_files))
    for path in neg_files[:impostor_count]:
        audio = load_audio(path)
        audio = pad_or_trim(audio)
        feat = extract_features(audio)
        features_list.append(feat)
        labels_list.append(0)

    X = np.vstack(features_list)
    y = np.array(labels_list, dtype=np.int32)

    verifier = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced")),
    ])
    print("\nTraining voice verifier (Aryan's voice vs. impostors)...")
    verifier.fit(X, y)
    return verifier


def export_to_onnx(model: Pipeline, output_path: Path) -> None:
    if not SKL2ONNX_AVAILABLE:
        print("WARNING: skl2onnx not installed. Skipping ONNX export.")
        return

    onx = convert_sklearn(
        model,
        initial_types=[("input", FloatTensorType([None, FEATURE_DIM]))],
        target_opset=12,
    )
    with open(output_path, "wb") as f:
        f.write(onx.SerializeToString())
    print(f"ONNX model exported: {output_path}")


def quick_validate(onnx_path: Path, verifier: Pipeline, pos_dir: Path, neg_dir: Path) -> None:
    if not ONNX_AVAILABLE:
        print("WARNING: onnxruntime not available. Skipping validation.")
        return

    pos_files = sorted(pos_dir.glob("*.wav"))[-5:]  # last 5 as held-out
    neg_files = sorted(neg_dir.glob("*.wav"))[-5:]

    # If fewer than 5, just use whatever is available
    if not pos_files or not neg_files:
        print("Not enough samples for held-out validation.")
        return

    sess = ort.InferenceSession(str(onnx_path))

    tp = 0
    fp = 0
    fn = 0
    tn = 0
    base_threshold = 0.5
    verifier_threshold = 0.6

    for path in pos_files:
        audio = pad_or_trim(load_audio(path))
        feat = extract_features(audio).astype(np.float32)
        base_prob = sess.run(None, {"input": feat})[1][0][1]
        if base_prob >= base_threshold:
            v_prob = verifier.predict_proba(feat)[0][1]
            if v_prob >= verifier_threshold:
                tp += 1
            else:
                fn += 1
        else:
            fn += 1

    for path in neg_files:
        audio = pad_or_trim(load_audio(path))
        feat = extract_features(audio).astype(np.float32)
        base_prob = sess.run(None, {"input": feat})[1][0][1]
        if base_prob >= base_threshold:
            v_prob = verifier.predict_proba(feat)[0][1]
            if v_prob >= verifier_threshold:
                fp += 1
            else:
                tn += 1
        else:
            tn += 1

    total_pos = tp + fn
    total_neg = fp + tn
    tpr = tp / total_pos if total_pos else 0.0
    fpr = fp / total_neg if total_neg else 0.0

    print("\n--- Quick Validation (held-out samples) ---")
    print(f"True positives : {tp}/{total_pos}")
    print(f"False positives: {fp}/{total_neg}")
    print(f"True positive rate : {tpr:.2f}")
    print(f"False positive rate: {fpr:.2f}")

    if tpr < 0.8:
        print("WARNING: TPR < 0.80 — consider recording more samples and retraining.")
    if fpr > 0.15:
        print("WARNING: FPR > 0.15 — consider recording more negative samples or tuning thresholds.")


def main() -> None:
    print("=" * 50)
    print("DEEP Custom Wake-Word Training")
    print("=" * 50)

    if not LIBROSA_AVAILABLE:
        print("ERROR: librosa is required. Install: pip install librosa")
        sys.exit(1)
    if not SKLEARN_AVAILABLE:
        print("ERROR: scikit-learn is required. Install: pip install scikit-learn")
        sys.exit(1)
    if not JOBLIB_AVAILABLE:
        print("ERROR: joblib is required. Install: pip install joblib")
        sys.exit(1)

    ensure_dirs()

    # Step 1 — Augment
    print("\n[Step 1] Augmenting dataset...")
    augment_dataset(str(POSITIVE_DIR), str(AUG_POSITIVE_DIR), "deep")
    augment_dataset(str(NEGATIVE_DIR), str(AUG_NEGATIVE_DIR), "noise")

    n_pos = len(list(AUG_POSITIVE_DIR.glob("*.wav")))
    n_neg = len(list(AUG_NEGATIVE_DIR.glob("*.wav")))
    print(f"Dataset: {n_pos} positive, {n_neg} negative")

    if n_pos == 0 or n_neg == 0:
        print("ERROR: No augmented samples found. Record samples first:")
        print("  python voice/training/record_samples.py")
        sys.exit(1)

    # Step 2 — Extract features from augmented data
    print("\n[Step 2] Extracting features...")
    X, y = build_dataset(AUG_POSITIVE_DIR, AUG_NEGATIVE_DIR)
    print(f"Feature matrix: {X.shape}, Labels: {y.shape}")

    # Step 3 — Train base classifier
    print("\n[Step 3] Training base classifier...")
    model = train_base_classifier(X, y)

    # Step 4 — Train voice verifier
    print("\n[Step 4] Training voice verifier...")
    verifier = train_verifier(POSITIVE_DIR, NEGATIVE_DIR)

    # Save models
    model_pkl = MODEL_DIR / "deep_wake_word.pkl"
    verifier_pkl = MODEL_DIR / "deep_verifier.pkl"
    joblib.dump(model, model_pkl)
    joblib.dump(verifier, verifier_pkl)
    print(f"Models saved: {model_pkl}, {verifier_pkl}")

    # Step 5 — Export to ONNX
    print("\n[Step 5] Exporting to ONNX...")
    onnx_path = MODEL_DIR / "deep_wake_word.onnx"
    export_to_onnx(model, onnx_path)

    # Step 6 — Quick validation
    print("\n[Step 6] Running quick validation...")
    quick_validate(onnx_path, verifier, POSITIVE_DIR, NEGATIVE_DIR)

    print("\n" + "=" * 50)
    print("Training complete!")
    print(f"  Base model : {model_pkl}")
    print(f"  Verifier   : {verifier_pkl}")
    print(f"  ONNX model : {onnx_path}")
    print("\nRun DEEP to test — say 'DEEP' to activate")
    print("=" * 50)


if __name__ == "__main__":
    main()
