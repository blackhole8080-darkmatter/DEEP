"""
voice/training/augment_samples.py

Expands a small set of real voice samples into a large synthetic dataset
via pitch shift, time stretch, noise, reverb, and amplitude scaling.

Called automatically by train_wake_word.py.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import List

import numpy as np

# Suppress benign librosa warnings
warnings.filterwarnings("ignore", category=UserWarning)

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from scipy.signal import fftconvolve
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

SAMPLE_RATE = 16000


def _simple_room_ir(length: int = 8000, decay: float = 0.5) -> np.ndarray:
    """Generate a simple synthetic room impulse response for reverb."""
    ir = np.zeros(length, dtype=np.float32)
    ir[0] = 1.0
    # Early reflections
    reflections = [800, 1200, 1800, 2400, 3200, 4000]
    for pos in reflections:
        if pos < length:
            ir[pos] = decay * (1.0 - pos / length)
    # Tail
    for i in range(1, length):
        if ir[i] == 0:
            ir[i] = ir[i - 1] * 0.995
    return ir / (np.max(np.abs(ir)) + 1e-8)


def augment_audio(audio: np.ndarray, sr: int = SAMPLE_RATE) -> List[np.ndarray]:
    """
    Return 10 augmented versions of a single audio sample.

    1. Original
    2. Pitch shift +1 semitone
    3. Pitch shift -1 semitone
    4. Pitch shift +2 semitones
    5. Time stretch 0.9x
    6. Time stretch 1.1x
    7. Add white noise
    8. Add room reverb
    9. Amplitude scale 0.7x
    10. Amplitude scale 1.3x (clipped at 1.0)
    """
    if not LIBROSA_AVAILABLE:
        raise RuntimeError("librosa is required for audio augmentation")

    augmented: List[np.ndarray] = [audio.copy()]

    # 2. Pitch +1
    try:
        augmented.append(librosa.effects.pitch_shift(audio, sr=sr, n_steps=1))
    except Exception:
        augmented.append(audio.copy())

    # 3. Pitch -1
    try:
        augmented.append(librosa.effects.pitch_shift(audio, sr=sr, n_steps=-1))
    except Exception:
        augmented.append(audio.copy())

    # 4. Pitch +2
    try:
        augmented.append(librosa.effects.pitch_shift(audio, sr=sr, n_steps=2))
    except Exception:
        augmented.append(audio.copy())

    # 5. Time stretch 0.9x
    try:
        ts = librosa.effects.time_stretch(audio, rate=0.9)
        augmented.append(_pad_or_trim(ts, len(audio)))
    except Exception:
        augmented.append(audio.copy())

    # 6. Time stretch 1.1x
    try:
        ts = librosa.effects.time_stretch(audio, rate=1.1)
        augmented.append(_pad_or_trim(ts, len(audio)))
    except Exception:
        augmented.append(audio.copy())

    # 7. White noise
    noise = np.random.normal(0, 0.005, size=audio.shape)
    augmented.append(np.clip(audio + noise, -1.0, 1.0))

    # 8. Room reverb
    if SCIPY_AVAILABLE:
        ir = _simple_room_ir()
        reverb = fftconvolve(audio, ir, mode="full")[: len(audio)]
        reverb = reverb / (np.max(np.abs(reverb)) + 1e-8)
        augmented.append(reverb.astype(np.float32))
    else:
        augmented.append(audio.copy())

    # 9. Amplitude 0.7x
    augmented.append(audio * 0.7)

    # 10. Amplitude 1.3x (clipped)
    augmented.append(np.clip(audio * 1.3, -1.0, 1.0))

    return augmented


def _pad_or_trim(audio: np.ndarray, target_length: int) -> np.ndarray:
    if len(audio) >= target_length:
        return audio[:target_length]
    pad = target_length - len(audio)
    return np.pad(audio, (0, pad), mode="constant")


def augment_dataset(input_dir: str, output_dir: str, label: str) -> None:
    """
    For each .wav in *input_dir*, generate 10 augmented versions and save
    them into *output_dir* as {label}_{original_name}_{aug_n}.wav.
    """
    if not LIBROSA_AVAILABLE:
        raise RuntimeError("librosa is required for dataset augmentation")

    in_path = Path(input_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    wav_files = sorted(in_path.glob("*.wav"))
    if not wav_files:
        print(f"No .wav files found in {in_path}")
        return

    total = 0
    for wav_file in wav_files:
        audio, sr = librosa.load(str(wav_file), sr=SAMPLE_RATE, mono=True)
        variants = augment_audio(audio, sr=sr)
        base_name = wav_file.stem

        for idx, variant in enumerate(variants):
            out_name = f"{label}_{base_name}_aug{idx:02d}.wav"
            out_file = out_path / out_name
            # Write via soundfile for clean WAV output
            try:
                import soundfile as sf
                sf.write(str(out_file), variant, sr, subtype="PCM_16")
            except ImportError:
                # Fallback: scale to int16 and use wave module
                import wave
                import struct
                scaled = np.clip(variant * 32767, -32768, 32767).astype(np.int16)
                with wave.open(str(out_file), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sr)
                    wf.writeframes(scaled.tobytes())
            total += 1

    print(f"Augmented {len(wav_files)} files → {total} total in {out_path}")


if __name__ == "__main__":
    augment_dataset("voice/training/samples/positive", "voice/training/samples/augmented_positive", "deep")
    augment_dataset("voice/training/samples/negative", "voice/training/samples/augmented_negative", "noise")
