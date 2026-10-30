"""Heatmap color palettes designed for different types of low vision.

Each palette has monotonically increasing brightness (or, in the case of
the stepped palette, levels with large jumps in brightness): values remain
readable even when color perception is reduced. Tests also verify this
property by simulating protanopia, deuteranopia, and tritanopia.

The palette-to-condition associations follow general accessibility
guidelines and have not been clinically validated: the best choice
remains the one that each person finds easiest to read.
"""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib as mpl
import numpy as np
from matplotlib.colors import Colormap, LinearSegmentedColormap, ListedColormap

from sonifica.i18n import tr


@dataclass(frozen=True)
class Palette:
    key: str
    colors: tuple[str, ...] | None = None  # None = matplotlib colormap specified in `base`.
    base: str | None = None
    discrete: bool = False

    @property
    def cmap_name(self) -> str:
        return self.base or f"sonifica_{self.key}"

    @property
    def name(self) -> str:
        return tr(f"pal.{self.key}")

    @property
    def description(self) -> str:
        return tr(f"pal.{self.key}.desc")


PALETTES: tuple[Palette, ...] = (
    Palette("standard", base="viridis"),
    Palette("red_green", base="cividis"),
    Palette("blue_yellow", colors=("#3a0d14", "#5a1220", "#8c1c24", "#c8463a", "#ec8a72", "#f8c4b4", "#fff0ea")),
    Palette("cataract", colors=("#3a1804", "#5e2002", "#902e00", "#d25a00", "#f59220", "#ffc95a", "#fff4cc")),
    Palette("macular", colors=("#1f1a6e", "#0e6c90", "#3fae5a", "#f2c12e", "#ffffff"), discrete=True),
    Palette("greyscale", colors=("#1a1a1a", "#ffffff")),
    Palette("photophobia", colors=("#0f1d2b", "#173a52", "#2c6273", "#518a84", "#86ad8f", "#b4c49a")),
)

BY_KEY = {p.key: p for p in PALETTES}
DEFAULT = "standard"


def _register(p: Palette) -> None:
    if p.colors is None or p.cmap_name in mpl.colormaps:
        return
    cmap: Colormap
    if p.discrete:
        cmap = ListedColormap(list(p.colors), name=p.cmap_name)
    else:
        cmap = LinearSegmentedColormap.from_list(p.cmap_name, list(p.colors), N=256)
    mpl.colormaps.register(cmap)


for _p in PALETTES:
    _register(_p)


def get_cmap(key: str, reverse: bool = False) -> Colormap:
    cmap = mpl.colormaps[BY_KEY[key].cmap_name]
    return cmap.reversed() if reverse else cmap


# Machado, Oliveira, and Fernandes (2009) matrices, severity 1.0, in linear RGB.
CVD_MATRICES = {
    "protanopia": np.array(
        [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]
    ),
    "deuteranopia": np.array(
        [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]]
    ),
    "tritanopia": np.array(
        [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]]
    ),
}


def _to_linear(rgb: np.ndarray) -> np.ndarray:
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def _to_srgb(lin: np.ndarray) -> np.ndarray:
    lin = np.clip(lin, 0.0, 1.0)
    return np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)


def lightness(rgb: np.ndarray) -> np.ndarray:
    """Perceived lightness L* (CIE) of sRGB colors in [0, 1]."""
    y = _to_linear(np.asarray(rgb, dtype=float)) @ np.array([0.2126, 0.7152, 0.0722])
    return np.where(y > 0.008856, 116 * np.cbrt(y) - 16, 903.3 * y)

def simulate_cvd(rgb: np.ndarray, kind: str) -> np.ndarray:
    """Simulates how colors appear (sRGB in [0, 1], last dimension = 3) under a color vision deficiency."""
    return _to_srgb(_to_linear(np.asarray(rgb, dtype=float)) @ CVD_MATRICES[kind].T)