"""Round trip: data → audio → spectrogram → reconstructed data.

This is used to measure how much information survives sonification by comparing three encoding methods:

"hilbert": a single melodic line following the Hilbert curve, with a fixed duration;
"sequence": each cell is represented by a note, row by row, with the value encoded in the pitch;
"spectral": the heatmap is represented as a spectrogram, with the value encoded in the amplitude.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.signal import butter, sosfiltfilt, stft
from scipy.signal import hilbert as analytic_signal
from scipy.signal.windows import hann

from sonifica import hilbert
from sonifica.i18n import fixed, tr
from sonifica.mapping import SoundMapping
from sonifica.synth import (
    SAMPLE_RATE,
    iter_cells,
    render_hilbert,
    render_sequence,
    render_spectral,
    spectral_frequencies,
    step_samples,
)

def to_mono(audio: np.ndarray) -> np.ndarray:
    return audio.mean(axis=1) if audio.ndim == 2 else audio
    
def spectrogram(audio: np.ndarray, sr: int = SAMPLE_RATE, n_fft: int = 2048, max_frames: int = 4000):
    """Returns frequencies, times and dB values normalized to 0 and clipped at -80 dB."""
    mono = to_mono(audio).astype(float)
    hop = max(256, len(mono) // max_frames)
    hop = min(hop, n_fft)
    f, t, z = stft(mono, fs=sr, nperseg=n_fft, noverlap=n_fft - hop)
    s_db = 20 * np.log10(np.abs(z) + 1e-9)
    s_db -= s_db.max()
    return f, t, np.maximum(s_db, -80.0)


def _peak_frequency(segment: np.ndarray, sr: int) -> tuple[float, float]:
    """Frequency of the main peak and how much it stands out from the rest (tone vs. noise)."""
    n_pad = 1 << int(np.ceil(np.log2(len(segment) * 8)))
    spec = np.abs(np.fft.rfft(segment * hann(len(segment), sym=False), n=n_pad))
    k = int(np.argmax(spec[1:-1])) + 1
    a, b, c = np.log(spec[k - 1 : k + 2] + 1e-12)
    denom = a - 2 * b + c
    delta = 0.5 * (a - c) / denom if denom != 0 else 0.0
    prominence = spec[k] / (np.median(spec) + 1e-12)
    return (k + delta) * sr / n_pad, float(prominence)

def reconstruct_sequence(
    audio: np.ndarray,
    shape: tuple[int, int],
    mapping: SoundMapping,
    note_dur: float = 0.12,
    gap: float = 0.03,
    order: str = "rows",
    sr: int = SAMPLE_RATE,
) -> np.ndarray:
    mono = to_mono(audio)
    step = step_samples(note_dur, gap, sr)
    n_note = int(note_dur * sr)
    margin = min(int(0.02 * sr), n_note // 4)
    out = np.full(shape, np.nan)
    for i, (r, c) in enumerate(iter_cells(shape, order)):
        seg = mono[i * step + margin : i * step + n_note - margin]
        if len(seg) < 16:
            continue
        freq, prominence = _peak_frequency(seg, sr)
        if prominence > 50:  # net tone
            out[r, c] = mapping.value_from_frequency(freq)
    return out


def reconstruct_spectral(
    audio: np.ndarray,
    shape: tuple[int, int],
    f_min: float = 200.0,
    f_max: float = 4000.0,
    col_dur: float = 0.25,
    sr: int = SAMPLE_RATE,
) -> np.ndarray:
    mono = to_mono(audio)
    n_rows, n_cols = shape
    freqs = spectral_frequencies(n_rows, f_min, f_max)
    col_n = int(round(col_dur * sr))
    window = hann(col_n, sym=False)
    t = np.arange(col_n) / sr
    out = np.zeros(shape)
    for c in range(n_cols):
        seg = mono[c * col_n : (c + 1) * col_n]
        t0 = c * col_n / sr  # absolute phase
        basis = np.exp(-2j * np.pi * np.outer(freqs, t + t0))
        out[:, c] = 2 * np.abs(basis @ (seg * window)) / window.sum()
    peak = out.max()
    return out / peak if peak > 0 else out


def compare(original: np.ndarray, reconstructed: np.ndarray) -> dict[str, float]:
    """Fidelity metrics between the original grid and the reconstructed grid (both in the range [0, 1])."""
    o_nan, r_nan = np.isnan(original), np.isnan(reconstructed)
    mask = ~o_nan & ~r_nan
    o, r = original[mask], reconstructed[mask]
    err = np.abs(o - r)
    corr = float(np.corrcoef(o, r)[0, 1]) if o.size > 1 and o.std() > 0 and r.std() > 0 else float("nan")
    return {
        "correlation": corr,
        "mean_error": float(err.mean()) if err.size else float("nan"),
        "rmse": float(np.sqrt((err**2).mean())) if err.size else float("nan"),
        "max_error": float(err.max()) if err.size else float("nan"),
        "missing_recognized": float((o_nan == r_nan).mean()),
    }




@dataclass
class RoundTrip:
    mode: str
    title: str
    audio: np.ndarray
    reconstructed: np.ndarray
    metrics: dict[str, float]
    spectrogram: tuple[np.ndarray, np.ndarray, np.ndarray] = field(repr=False)
    band: tuple[float, float] = (0.0, 0.0)


def add_noise(audio: np.ndarray, snr_db: float | None, seed: int = 0) -> np.ndarray:
    """It adds white noise with indicated signal-to-noise ratio ( None = no noise).

    Simulates real-world conditions: low-quality speakers, noisy environments,
    audio compression.
    """
    if snr_db is None:
        return audio
    rms = np.sqrt(np.mean(audio**2))
    noise_rms = rms / (10 ** (snr_db / 20))
    noise = np.random.default_rng(seed).standard_normal(audio.shape) * noise_rms
    return (audio + noise).astype(np.float32)


def reconstruct_hilbert(
    audio: np.ndarray,
    shape: tuple[int, int],
    mapping: SoundMapping,
    duration: float = 8.0,
    sr: int = SAMPLE_RATE,
) -> np.ndarray:
    """Reconstructs the matrix from the Hilbert melodic line.

    The instantaneous frequency is obtained from the phase of the analytic
    signal; for each vertex of the curve, the median is taken over the central
    portion of its time interval, away from transitions.
    """
    path = hilbert.path_for(shape)
    mono = to_mono(audio).astype(float)
    lo_hz, hi_hz = mapping.f_min / 1.25, min(mapping.f_max * 1.25, sr / 2 * 0.95)
    mono = sosfiltfilt(butter(4, [lo_hz, hi_hz], btype="bandpass", fs=sr, output="sos"), mono)
    z = analytic_signal(mono)
    env = np.abs(z)
    inst = np.diff(np.unwrap(np.angle(z))) * sr / (2 * np.pi)
    inst = np.append(inst, inst[-1])
    m = path.n_points
    n = len(mono)
    bounds = np.linspace(0, n, m + 1)
    freqs = np.empty(m)
    levels = np.empty(m)
    for k in range(m):
        a, b = bounds[k], bounds[k + 1]
        q = (b - a) * 0.3
        lo, hi = int(a + q), max(int(a + q) + 1, int(b - q))
        freqs[k] = np.median(inst[lo:hi])
        levels[k] = np.median(env[lo:hi])
    values = np.asarray(mapping.value_from_frequency(np.clip(freqs, 1.0, None)), dtype=float)
    values[levels < 0.08] = np.nan  
    return hilbert.to_grid(values, shape, path)


# Beyond this threshold, the note-by-note sequence takes too long (1200 cells ≈ 3 minutes).
MAX_SEQUENCE_CELLS = 1200


def run_round_trip(
    norm: np.ndarray,
    mapping: SoundMapping,
    note_dur: float = 0.12,
    gap: float = 0.03,
    spectral_range: tuple[float, float] = (200.0, 4000.0),
    col_dur: float = 0.25,
    sr: int = SAMPLE_RATE,
    snr_db: float | None = None,
    hilbert_duration: float = 8.0,
) -> list[RoundTrip]:
    results = []

    audio = add_noise(render_hilbert(norm, mapping, hilbert_duration, sr, markers=False), snr_db)
    rec = reconstruct_hilbert(audio, norm.shape, mapping, hilbert_duration, sr)
    results.append(
        RoundTrip("hilbert", tr("rt.hilbert"), audio, rec, compare(norm, rec),
                  spectrogram(audio, sr), (mapping.f_min * 0.8, mapping.f_max * 1.25))
    )

    if norm.size <= MAX_SEQUENCE_CELLS:
        audio = add_noise(render_sequence(norm, mapping, "rows", note_dur, gap, sr), snr_db)
        rec = reconstruct_sequence(audio, norm.shape, mapping, note_dur, gap, "rows", sr)
        results.append(
            RoundTrip("sequence", tr("rt.sequence"), audio, rec, compare(norm, rec),
                      spectrogram(audio, sr), (mapping.f_min * 0.8, mapping.f_max * 1.25))
        )

    f_lo, f_hi = spectral_range
    audio = add_noise(render_spectral(norm, f_lo, f_hi, col_dur, sr), snr_db)
    rec = reconstruct_spectral(audio, norm.shape, f_lo, f_hi, col_dur, sr)
    results.append(
        RoundTrip("spectral", tr("rt.spectral"), audio, rec, compare(norm, rec),
                  spectrogram(audio, sr), (f_lo * 0.8, f_hi * 1.25))
    )
    return results


def describe_metrics(m: dict[str, float]) -> str:
    """Verbal interpretation, also useful for screen reader users."""
    r = m["correlation"]
    if np.isnan(r):
        verdict = tr("rt.verdict.na")
    elif r > 0.99:
        verdict = tr("rt.verdict.1")
    elif r > 0.95:
        verdict = tr("rt.verdict.2")
    elif r > 0.8:
        verdict = tr("rt.verdict.3")
    else:
        verdict = tr("rt.verdict.4")
    return tr("rt.describe", r=fixed(r), mean=fixed(m["mean_error"]), max=fixed(m["max_error"]),
              verdict=verdict)
