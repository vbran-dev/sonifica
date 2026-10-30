"""Audio synthesis: individual tones, cell sequences, Hilbert traversal, and heatmaps as spectra."""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np

from sonifica.mapping import SoundMapping

SAMPLE_RATE = 44100


def _moving_average(x: np.ndarray, width: int) -> np.ndarray:
    if width <= 1:
        return x
    pad = width // 2
    xp = np.pad(x, (pad, width - pad - 1), mode="edge")
    c = np.cumsum(np.insert(xp, 0, 0.0))
    return (c[width:] - c[:-width]) / width


def _envelope(n: int, sr: int, attack: float = 0.005, release: float = 0.03) -> np.ndarray:
    env = np.ones(n)
    a = min(n // 2, int(attack * sr))
    r = min(n // 2, int(release * sr))
    if a:
        env[:a] = np.linspace(0.0, 1.0, a)
    if r:
        env[-r:] = np.linspace(1.0, 0.0, r)
    return env


def tone(
    freq: float,
    amp: float,
    pan: float = 0.0,
    duration: float = 0.15,
    sr: int = SAMPLE_RATE,
    harmonics: float = 0.0,
) -> np.ndarray:
    n = max(1, int(duration * sr))
    t = np.arange(n) / sr
    wave = np.sin(2 * np.pi * freq * t)
    if harmonics > 0:
        wave = wave + harmonics * (0.5 * np.sin(4 * np.pi * freq * t) + 0.25 * np.sin(6 * np.pi * freq * t))
        wave /= 1.0 + 0.75 * harmonics
    return pan_stereo(amp * wave * _envelope(n, sr), pan)


def pan_stereo(mono: np.ndarray, pan: float) -> np.ndarray:
    theta = (np.clip(pan, -1.0, 1.0) + 1.0) * np.pi / 4.0
    return np.column_stack([mono * np.cos(theta), mono * np.sin(theta)]).astype(np.float32)


def missing_sound(pan: float = 0.0, duration: float = 0.15, sr: int = SAMPLE_RATE) -> np.ndarray:
    """A short, soft noise: indicates a missing value."""
    n = max(1, int(duration * sr))
    noise = np.random.default_rng(0).standard_normal(n) * 0.08
    noise = np.convolve(noise, np.ones(8) / 8, mode="same")
    return pan_stereo(noise * _envelope(n, sr, release=duration / 2), pan)


def edge_sound(sr: int = SAMPLE_RATE) -> np.ndarray:
    """A low, sharp thud: indicates that the edge of the table has been reached."""
    n = int(0.08 * sr)
    t = np.arange(n) / sr
    return pan_stereo(0.5 * np.sin(2 * np.pi * 110 * t) * np.exp(-t / 0.02), 0.0)


def cell_sound(
    v: float,
    col: int,
    n_cols: int,
    mapping: SoundMapping,
    duration: float = 0.15,
    sr: int = SAMPLE_RATE,
    harmonics: float = 0.0,
) -> np.ndarray:
    pan = mapping.pan(col, n_cols)
    if np.isnan(v):
        return missing_sound(pan, duration, sr)
    return tone(mapping.frequency(v), mapping.amplitude(v), pan, duration, sr, harmonics)  # type: ignore[arg-type]


def iter_cells(shape: tuple[int, int], order: str = "rows") -> Iterator[tuple[int, int]]:
    n_rows, n_cols = shape
    if order == "rows":
        for r in range(n_rows):
            for c in range(n_cols):
                yield r, c
    elif order == "columns":
        for c in range(n_cols):
            for r in range(n_rows):
                yield r, c
    else:
        raise ValueError(f"Unknown order: {order}")


def step_samples(note_dur: float, gap: float, sr: int) -> int:
    return int(round((note_dur + gap) * sr))


def render_cells(
    cells: list[tuple[float, int]],
    n_cols: int,
    mapping: SoundMapping,
    note_dur: float = 0.12,
    gap: float = 0.03,
    sr: int = SAMPLE_RATE,
    harmonics: float = 0.0,
) -> np.ndarray:
    """Plays a list of cells (normalized value, column index) one after another."""
    step = step_samples(note_dur, gap, sr)
    out = np.zeros((step * len(cells), 2), dtype=np.float32)
    for i, (v, c) in enumerate(cells):
        s = cell_sound(v, c, n_cols, mapping, note_dur, sr, harmonics)
        out[i * step : i * step + len(s)] += s
    return out


def render_sequence(
    norm: np.ndarray,
    mapping: SoundMapping,
    order: str = "rows",
    note_dur: float = 0.12,
    gap: float = 0.03,
    sr: int = SAMPLE_RATE,
    harmonics: float = 0.0,
) -> np.ndarray:
    """The entire table as a sequence of notes (pitch encoding)."""
    cells = [(norm[r, c], c) for r, c in iter_cells(norm.shape, order)]
    return render_cells(cells, norm.shape[1], mapping, note_dur, gap, sr, harmonics)


def spectral_frequencies(n_rows: int, f_min: float = 200.0, f_max: float = 4000.0) -> np.ndarray:
    """One frequency per row: row 0 (top) is the highest, as in an image."""
    if n_rows == 1:
        return np.array([np.sqrt(f_min * f_max)])
    return np.geomspace(f_max, f_min, n_rows)


def render_spectral(
    norm: np.ndarray,
    f_min: float = 200.0,
    f_max: float = 4000.0,
    col_dur: float = 0.25,
    sr: int = SAMPLE_RATE,
) -> np.ndarray:
    """The heatmap used directly as a spectrogram (additive synthesis).

    Each row is a sine wave at a fixed frequency, each column represents
    a point in time, and the cell value determines the amplitude.
    All frequencies in a column are heard simultaneously.
    """
    n_rows, n_cols = norm.shape
    freqs = spectral_frequencies(n_rows, f_min, f_max)
    col_n = int(round(col_dur * sr))
    total = col_n * n_cols
    t = np.arange(total) / sr
    amps = np.nan_to_num(norm, nan=0.0)
    smooth = int(0.01 * sr)
    out = np.zeros(total)
    for r in range(n_rows):
        env = _moving_average(np.repeat(amps[r], col_n), smooth)
        out += env * np.sin(2 * np.pi * freqs[r] * t)
    peak = np.max(np.abs(out))
    if peak > 0:
        out *= 0.9 / peak
    out *= _envelope(total, sr, attack=0.01, release=0.01)
    return pan_stereo(out, 0.0)


def _forward_fill(values: np.ndarray) -> np.ndarray:
    """Replaces NaN values with the last valid value (or the first valid value at the beginning)."""
    ok = ~np.isnan(values)
    if not ok.any():
        return np.zeros_like(values)
    idx = np.where(ok, np.arange(len(values)), 0)
    np.maximum.accumulate(idx, out=idx)
    out = values[idx]
    first = np.argmax(ok)
    out[:first] = values[first]
    return out


def quadrant_tick(sr: int = SAMPLE_RATE) -> np.ndarray:
    """Sound that marks the transition from one quadrant to another."""
    n = int(0.04 * sr)
    t = np.arange(n) / sr
    return 0.3 * np.sin(2 * np.pi * 1600 * t) * np.exp(-t / 0.006)


def render_hilbert(
    norm: np.ndarray,
    mapping: SoundMapping,
    duration: float = 8.0,
    sr: int = SAMPLE_RATE,
    harmonics: float = 0.0,
    markers: bool = True,
) -> np.ndarray:
    """The entire heatmap as a single melodic line following the Hilbert curve.

    The total duration is fixed, regardless of the matrix dimensions: each
    instant corresponds to a point in the unit square. The value determines
    the pitch (and volume), while the horizontal position determines the
    panning. If `markers` is true, a tap marks the transition between the
    four quadrants.
    """
    from sonifica.hilbert import path_for, sample

    path = path_for(norm.shape)
    vals = sample(norm, path)
    m = len(vals)
    n = max(m, int(round(duration * sr)))
    idx = np.minimum(np.arange(n) * m // n, m - 1)

    missing = np.isnan(vals)
    filled = _forward_fill(vals)
    log_f = np.log(np.asarray(mapping.frequency(filled), dtype=float))
    amp = np.asarray(mapping.amplitude(filled), dtype=float) * ~missing
    pan = mapping.pan_width * (2 * path.x - 1)

    # Short transitions between vertices: no abrupt jumps, while keeping each value recognizable.
    per_point = n / m
    w = max(1, min(int(0.02 * sr), int(per_point / 2)))
    log_f_s = _moving_average(log_f[idx], w)
    amp_s = _moving_average(amp[idx], w)
    miss_s = _moving_average(missing[idx].astype(float), w)
    pan_s = _moving_average(pan[idx], max(w, int(0.03 * sr)))

    phase = 2 * np.pi * np.cumsum(np.exp(log_f_s)) / sr
    wave = np.sin(phase)
    if harmonics > 0:
        wave = (wave + harmonics * (0.5 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase))) / (1.0 + 0.75 * harmonics)
    mono = amp_s * wave
    if missing.any():
        noise = np.random.default_rng(0).standard_normal(n) * 0.08
        mono = mono + miss_s * _moving_average(noise, 8)
    mono *= _envelope(n, sr, attack=0.01, release=0.02)
    mono *= 0.85

    theta = (np.clip(pan_s, -1, 1) + 1.0) * np.pi / 4.0
    out = np.column_stack([mono * np.cos(theta), mono * np.sin(theta)])
    if markers:
        tick = quadrant_tick(sr)
        for q in (1, 2, 3):
            start = int(q * n / 4)
            seg = tick[: n - start]
            out[start : start + len(seg)] += (seg * np.sqrt(0.5))[:, None]
    return out.astype(np.float32)
