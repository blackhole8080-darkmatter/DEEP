"""
DEEP — Spectrum Analyzer
FFT-based signal analysis, peak detection, and offline IQ file processing.
Supports: live SDR (pyrtlsdr) or offline IQ binary files.
"""
from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple

try:
    import numpy as np
    _NUMPY_OK = True
except ImportError:
    _NUMPY_OK = False

try:
    import rtlsdr
    _RTL_OK = True
except ImportError:
    _RTL_OK = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    _MPL_OK = True
except ImportError:
    _MPL_OK = False


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class Signal:
    center_freq_hz: float
    bandwidth_hz: float
    peak_power_db: float
    noise_floor_db: float
    snr_db: float
    modulation_guess: str       # "AM" | "FM" | "FSK" | "PSK" | "QAM" | "Unknown"
    duration_s: float = 0.0
    notes: str = ""


@dataclass
class SpectrumResult:
    center_freq_hz: float
    sample_rate_hz: float
    frequencies: List[float]    # Hz (relative to center)
    power_db: List[float]       # dBFS
    noise_floor_db: float
    peak_db: float
    signals: List[Signal] = field(default_factory=list)
    waterfall_path: Optional[str] = None   # path to generated waterfall plot
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None


# ── Modulation classifier (heuristic) ────────────────────────────────────────

def _guess_modulation(bw_hz: float, snr_db: float, spectral_shape: str) -> str:
    """
    Heuristic modulation guess based on bandwidth and SNR.
    For definitive classification, use cyclostationary analysis.
    """
    if bw_hz < 5_000:
        return "CW/FSK"
    elif bw_hz < 25_000:
        if snr_db > 20:
            return "FM-Narrowband"
        return "FSK"
    elif bw_hz < 200_000:
        return "FM-Wideband"
    elif bw_hz < 1_000_000:
        return "OFDM/LTE" if spectral_shape == "flat" else "PSK"
    else:
        return "OFDM/WiFi"


# ── Spectrum Analyzer ─────────────────────────────────────────────────────────

class SpectrumAnalyzer:
    """
    FFT-based spectrum analysis engine.
    Supports: live RTL-SDR capture or offline IQ binary file analysis.
    """

    def __init__(self, data_dir: str = "data/rf"):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._plot_counter = 0
        self._waterfall_history: List[List[float]] = []
        self._waterfall_maxrows = 200

    # ── Public API ─────────────────────────────────────────────────────────────

    async def scan_band(
        self,
        center_freq: float,
        bandwidth: float,
        duration: float = 2.0,
        resolution: int = 1024,
        generate_waterfall: bool = True,
    ) -> SpectrumResult:
        """
        Scan a frequency band using an RTL-SDR.
        center_freq: Hz (e.g. 433.92e6 for 433.92 MHz)
        bandwidth:   Hz (SDR sample rate)
        duration:    seconds to capture
        """
        if not _RTL_OK:
            return SpectrumResult(
                center_freq_hz=center_freq,
                sample_rate_hz=bandwidth,
                frequencies=[],
                power_db=[],
                noise_floor_db=0.0,
                peak_db=0.0,
                error="pyrtlsdr not installed. Run: pip install pyrtlsdr\nAlternatively, use analyze_iq_file() for offline analysis.",
            )

        if not _NUMPY_OK:
            return SpectrumResult(
                center_freq_hz=center_freq,
                sample_rate_hz=bandwidth,
                frequencies=[],
                power_db=[],
                noise_floor_db=0.0,
                peak_db=0.0,
                error="numpy not installed. Run: pip install numpy",
            )

        try:
            iq_samples = await asyncio.to_thread(
                self._capture_iq, center_freq, bandwidth, duration, resolution
            )
            return await asyncio.to_thread(
                self._compute_spectrum, iq_samples, center_freq, bandwidth, resolution, generate_waterfall
            )
        except Exception as exc:
            return SpectrumResult(
                center_freq_hz=center_freq,
                sample_rate_hz=bandwidth,
                frequencies=[],
                power_db=[],
                noise_floor_db=0.0,
                peak_db=0.0,
                error=f"SDR capture failed: {exc}",
            )

    def analyze_iq_file(
        self,
        path: str,
        sample_rate: float,
        center_freq: float = 0.0,
        resolution: int = 2048,
        generate_waterfall: bool = True,
    ) -> SpectrumResult:
        """
        Analyze a pre-recorded IQ binary file (interleaved float32 or int8).
        Supports: .iq, .bin, .raw, .cf32 formats.
        """
        if not _NUMPY_OK:
            return SpectrumResult(
                center_freq_hz=center_freq,
                sample_rate_hz=sample_rate,
                frequencies=[],
                power_db=[],
                noise_floor_db=0.0,
                peak_db=0.0,
                error="numpy required for IQ analysis. Run: pip install numpy",
            )

        p = Path(path)
        if not p.exists():
            return SpectrumResult(
                center_freq_hz=center_freq,
                sample_rate_hz=sample_rate,
                frequencies=[],
                power_db=[],
                noise_floor_db=0.0,
                peak_db=0.0,
                error=f"File not found: {path}",
            )

        try:
            # Try float32 first (SDR# / GNU Radio default)
            raw = np.fromfile(str(p), dtype=np.float32)
            if len(raw) < 2:
                raise ValueError("File too small")

            iq = raw[0::2] + 1j * raw[1::2]  # de-interleave I/Q

            return self._compute_spectrum(iq, center_freq, sample_rate, resolution, generate_waterfall)
        except Exception as exc:
            # Try int8 (RTL-SDR raw)
            try:
                raw = np.fromfile(str(p), dtype=np.int8).astype(np.float32) / 128.0
                iq = raw[0::2] + 1j * raw[1::2]
                return self._compute_spectrum(iq, center_freq, sample_rate, resolution, generate_waterfall)
            except Exception as exc2:
                return SpectrumResult(
                    center_freq_hz=center_freq,
                    sample_rate_hz=sample_rate,
                    frequencies=[],
                    power_db=[],
                    noise_floor_db=0.0,
                    peak_db=0.0,
                    error=f"IQ file parse failed: {exc2}",
                )

    def detect_signals(
        self,
        spectrum: SpectrumResult,
        threshold_db: float = -60,
        min_bw_hz: float = 1000,
    ) -> List[Signal]:
        """
        Peak detection above noise floor.
        Returns list of Signal objects with frequency/BW/power/modulation estimate.
        """
        if not spectrum.frequencies or not spectrum.power_db:
            return []

        signals = []
        freqs = np.array(spectrum.frequencies) if _NUMPY_OK else spectrum.frequencies
        powers = np.array(spectrum.power_db) if _NUMPY_OK else spectrum.power_db

        # Simple threshold-based peak detection
        in_signal = False
        sig_start = 0
        sig_peak = -999.0

        for i, (f, p) in enumerate(zip(freqs, powers)):
            if p > threshold_db:
                if not in_signal:
                    in_signal = True
                    sig_start = i
                    sig_peak = p
                else:
                    sig_peak = max(sig_peak, p)
            else:
                if in_signal:
                    in_signal = False
                    sig_end = i
                    bw = float(freqs[sig_end] - freqs[sig_start])
                    if bw >= min_bw_hz:
                        center = float(freqs[(sig_start + sig_end) // 2])
                        snr = sig_peak - spectrum.noise_floor_db
                        mod = _guess_modulation(bw, snr, "flat")
                        signals.append(Signal(
                            center_freq_hz=spectrum.center_freq_hz + center,
                            bandwidth_hz=bw,
                            peak_power_db=sig_peak,
                            noise_floor_db=spectrum.noise_floor_db,
                            snr_db=snr,
                            modulation_guess=mod,
                        ))

        spectrum.signals = signals
        return signals

    # ── Internal ──────────────────────────────────────────────────────────────

    def _capture_iq(self, center_freq: float, sample_rate: float, duration: float, fft_size: int):
        """Capture IQ samples from RTL-SDR."""
        n_samples = int(sample_rate * duration)
        sdr = rtlsdr.RtlSdr()
        sdr.center_freq = center_freq
        sdr.sample_rate = sample_rate
        sdr.gain = "auto"
        samples = sdr.read_samples(n_samples)
        sdr.close()
        return np.array(samples)

    def _compute_spectrum(
        self,
        iq: Any,
        center_freq: float,
        sample_rate: float,
        fft_size: int,
        generate_waterfall: bool,
    ) -> SpectrumResult:
        """Compute FFT spectrum from IQ samples."""
        # Windowed FFT average
        n_chunks = max(1, len(iq) // fft_size)
        psd_accum = np.zeros(fft_size)

        for i in range(n_chunks):
            chunk = iq[i * fft_size:(i + 1) * fft_size]
            if len(chunk) < fft_size:
                chunk = np.pad(chunk, (0, fft_size - len(chunk)))
            window = np.hanning(fft_size)
            fft_out = np.fft.fftshift(np.fft.fft(chunk * window, fft_size))
            psd_accum += (np.abs(fft_out) ** 2) / n_chunks

        # Convert to dBFS
        eps = 1e-10
        power_db = 10 * np.log10(psd_accum / (fft_size ** 2) + eps)

        # Frequency axis (relative to center)
        freqs = np.fft.fftshift(np.fft.fftfreq(fft_size, 1 / sample_rate))

        noise_floor = float(np.percentile(power_db, 10))
        peak_db = float(np.max(power_db))

        result = SpectrumResult(
            center_freq_hz=center_freq,
            sample_rate_hz=sample_rate,
            frequencies=freqs.tolist(),
            power_db=power_db.tolist(),
            noise_floor_db=noise_floor,
            peak_db=peak_db,
        )

        # Waterfall
        if generate_waterfall and _MPL_OK:
            result.waterfall_path = self._generate_waterfall(freqs, power_db, center_freq, sample_rate)

        return result

    def _generate_waterfall(
        self,
        freqs: Any,
        power_db: Any,
        center_freq: float,
        sample_rate: float,
    ) -> str:
        """Generate a waterfall plot and save to disk."""
        self._waterfall_history.append(power_db.tolist())
        if len(self._waterfall_history) > self._waterfall_maxrows:
            self._waterfall_history = self._waterfall_history[-self._waterfall_maxrows:]

        self._plot_counter += 1
        path = str(self._data_dir / f"waterfall_{self._plot_counter}.png")

        waterfall_data = np.array(self._waterfall_history)
        freq_mhz = (freqs + center_freq) / 1e6

        fig, ax = plt.subplots(figsize=(12, 5))
        ax.imshow(
            waterfall_data,
            aspect="auto",
            origin="lower",
            extent=[freq_mhz[0], freq_mhz[-1], 0, len(self._waterfall_history)],
            cmap="inferno",
            vmin=float(np.percentile(waterfall_data, 5)),
            vmax=float(np.percentile(waterfall_data, 99)),
        )
        ax.set_xlabel(f"Frequency (MHz), center: {center_freq/1e6:.3f} MHz", color="#aaa")
        ax.set_ylabel("Time →", color="#aaa")
        ax.set_title("DEEP RF Waterfall", color="#00d4ff", fontsize=12)
        ax.tick_params(colors="#aaa")
        fig.patch.set_facecolor("#0d0d0d")
        ax.set_facecolor("#0d0d0d")
        cb = plt.colorbar(ax.images[0], ax=ax)
        cb.set_label("Power (dBFS)", color="#aaa")
        plt.tight_layout()
        plt.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0d0d0d")
        plt.close(fig)
        return path
