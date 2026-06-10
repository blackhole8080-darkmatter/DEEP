"""
voice/training/record_samples.py

Interactive CLI tool to collect voice samples for custom wake-word training.
Run once to record 50 positive "DEEP" samples and 30 negative samples.

Usage:
    python voice/training/record_samples.py
"""

from __future__ import annotations

import os
import sys
import wave
from pathlib import Path

import numpy as np

# Ensure project root on path for core imports if needed
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
RECORD_SECONDS = 1.5
SAMPLES_PER_RECORDING = int(SAMPLE_RATE * RECORD_SECONDS)
RMS_QUIET_THRESHOLD = 200

POSITIVE_DIR = Path("voice/training/samples/positive")
NEGATIVE_DIR = Path("voice/training/samples/negative")


def ensure_dirs() -> None:
    POSITIVE_DIR.mkdir(parents=True, exist_ok=True)
    NEGATIVE_DIR.mkdir(parents=True, exist_ok=True)


def compute_rms(audio_bytes: bytes) -> float:
    arr = np.frombuffer(audio_bytes, dtype=np.int16)
    if arr.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(arr.astype(np.float64) ** 2)))


def record_audio(duration: float = RECORD_SECONDS) -> bytes:
    try:
        import pyaudio
    except ImportError as exc:
        print(f"ERROR: pyaudio not installed. Install it first: {exc}")
        sys.exit(1)

    pa = pyaudio.PyAudio()
    try:
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
    except Exception as exc:
        print(f"ERROR: Failed to open microphone: {exc}")
        pa.terminate()
        sys.exit(1)

    frames: list[bytes] = []
    num_chunks = int((SAMPLE_RATE * duration) / CHUNK_SIZE) + 1

    print("    Recording...", end="", flush=True)
    for _ in range(num_chunks):
        try:
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            frames.append(data)
        except Exception:
            break

    print(" done.")
    stream.stop_stream()
    stream.close()
    pa.terminate()

    return b"".join(frames)


def save_wav(path: Path, audio_bytes: bytes) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_bytes)


def record_positive_samples(count: int = 50) -> None:
    print(f"\nYou will record {count} samples of saying 'DEEP'.")
    print("Say it naturally, as you would when talking to your system.")
    print("Vary your distance, tone, and volume slightly.")
    print("Press ENTER before each recording.\n")

    existing = sorted(POSITIVE_DIR.glob("deep_*.wav"))
    start_idx = len(existing) + 1

    for i in range(start_idx, start_idx + count):
        input(f"Sample {i}/{count} — press ENTER then say DEEP")
        audio = record_audio()
        rms = compute_rms(audio)
        if rms < RMS_QUIET_THRESHOLD:
            print(f"    WARNING: Audio seems quiet (RMS={rms:.1f}). Consider re-recording.")
        else:
            print(f"    RMS level: {rms:.1f} (OK)")

        path = POSITIVE_DIR / f"deep_{i:03d}.wav"
        save_wav(path, audio)
        print(f"    Saved: {path}\n")


def record_negative_samples(count: int = 30) -> None:
    print(f"\nNow record {count} samples of background noise and other words (NOT 'DEEP').")
    print("Say random words, let the mic capture room noise, talk normally.")
    print("Press ENTER before each recording.\n")

    existing = sorted(NEGATIVE_DIR.glob("noise_*.wav"))
    start_idx = len(existing) + 1

    for i in range(start_idx, start_idx + count):
        input(f"Sample {i}/{count} — press ENTER then speak background noise/other words")
        audio = record_audio()
        rms = compute_rms(audio)
        print(f"    RMS level: {rms:.1f}")

        path = NEGATIVE_DIR / f"noise_{i:03d}.wav"
        save_wav(path, audio)
        print(f"    Saved: {path}\n")


def main() -> None:
    ensure_dirs()
    print("=" * 50)
    print("DEEP Custom Wake-Word — Voice Sample Recorder")
    print("=" * 50)

    record_positive_samples(50)
    record_negative_samples(30)

    pos_count = len(list(POSITIVE_DIR.glob("*.wav")))
    neg_count = len(list(NEGATIVE_DIR.glob("*.wav")))

    print("=" * 50)
    print("Recording complete!")
    print(f"  Positive samples: {pos_count} in {POSITIVE_DIR}")
    print(f"  Negative samples: {neg_count} in {NEGATIVE_DIR}")
    print("\nNext step:")
    print("  python voice/training/train_wake_word.py")
    print("=" * 50)


if __name__ == "__main__":
    main()
