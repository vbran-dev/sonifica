"""Audio playback and saving."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import wavfile

from sonifica.synth import SAMPLE_RATE


class Player:
    """A lightweight wrapper around sounddevice. If no audio device is available, it skips playback without crashing."""

    def __init__(self, sr: int = SAMPLE_RATE) -> None:
        self.sr = sr
        self.error: str | None = None
        try:
            import sounddevice as sd

            self._sd = sd
            sd.query_devices(kind="output")
        except Exception as exc:  # PortAudio unavailable, no audio device, etc.
            self._sd = None
            self.error = str(exc)

    @property
    def available(self) -> bool:
        return self._sd is not None

    def play(self, audio: np.ndarray) -> None:
        if self._sd is None or audio.size == 0:
            return
        try:
            self._sd.stop()
            self._sd.play(np.clip(audio, -1.0, 1.0), self.sr)
        except Exception as exc:
            self.error = str(exc)

    def stop(self) -> None:
        if self._sd is not None:
            try:
                self._sd.stop()
            except Exception:
                pass


def save_wav(path: str | Path, audio: np.ndarray, sr: int = SAMPLE_RATE) -> None:
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    wavfile.write(str(path), sr, pcm)
