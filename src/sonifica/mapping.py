"""Data-to-sound mapping.

This is the project's design core: how to transform a number into a sound
that the ear can interpret correctly.

- value → pitch (frequency on a logarithmic scale, as perceived by the ear)
- value → volume (with a minimum level, so even low values remain audible)
- column → stereo position (left … right)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Allowed pitch classes (0 = C) for quantized scales.
SCALES: dict[str, tuple[int, ...] | None] = {
    "continuous": None,
    "chromatic": tuple(range(12)),
    "major": (0, 2, 4, 5, 7, 9, 11),
    "pentatonic": (0, 2, 4, 7, 9),
}



def _out(x: np.ndarray) -> float | np.ndarray:
    return float(x) if np.ndim(x) == 0 else x


def _midi_to_freq(m: np.ndarray) -> np.ndarray:
    return 440.0 * 2.0 ** ((m - 69.0) / 12.0)


def _freq_to_midi(f: np.ndarray) -> np.ndarray:
    return 69.0 + 12.0 * np.log2(f / 440.0)


@dataclass
class SoundMapping:
    f_min: float = 220.0
    f_max: float = 880.0
    scale: str = "continuous"
    amp_min: float = 0.35
    amp_max: float = 0.9
    pan_width: float = 0.9

    def __post_init__(self) -> None:
        if not 0 < self.f_min < self.f_max:
            raise ValueError("Requires 0 < f_min < f_max.")
        if self.scale not in SCALES:
            raise ValueError(f"Unknown scale: {self.scale}")

    def frequency(self, v: float | np.ndarray) -> float | np.ndarray:
        v = np.clip(np.asarray(v, dtype=float), 0.0, 1.0)
        f = self.f_min * (self.f_max / self.f_min) ** v
        pitch_classes = SCALES[self.scale]
        if pitch_classes is not None:
            f = self._quantize(f, pitch_classes)
        return _out(f)

    def _quantize(self, f: np.ndarray, pitch_classes: tuple[int, ...]) -> np.ndarray:
        lo, hi = _freq_to_midi(np.array(self.f_min)), _freq_to_midi(np.array(self.f_max))
        candidates = range(int(np.floor(lo)), int(np.ceil(hi)) + 1)
        notes = np.array(
            [n for n in candidates if n % 12 in pitch_classes and lo - 1e-9 <= n <= hi + 1e-9],
            dtype=float,
        )
        if notes.size == 0:
            return f
        midi = _freq_to_midi(f)
        idx = np.abs(midi[..., None] - notes).argmin(axis=-1)
        return _midi_to_freq(notes[idx])

    def value_from_frequency(self, f: float | np.ndarray) -> float | np.ndarray:
        """Inverse of the continuous mapping (used for reconstruction)."""
        f = np.asarray(f, dtype=float)
        v = np.log(f / self.f_min) / np.log(self.f_max / self.f_min)
        return _out(np.clip(v, 0.0, 1.0))

    def amplitude(self, v: float | np.ndarray) -> float | np.ndarray:
        v = np.clip(np.asarray(v, dtype=float), 0.0, 1.0)
        return _out(self.amp_min + (self.amp_max - self.amp_min) * v)

    def pan(self, col: int, n_cols: int) -> float:
        if n_cols <= 1:
            return 0.0
        return float(self.pan_width * (2.0 * col / (n_cols - 1) - 1.0))
