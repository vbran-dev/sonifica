"""Example heatmaps, all synthetic and reproducible (fixed random seed).

They cover different sizes and structures: small tables with labels,
a matrix with missing values, a 100×100 elevation map, and a 120×160
interference pattern, useful for testing resizing and playback consistency.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy.ndimage import gaussian_filter

from sonifica.data import Grid
from sonifica.i18n import tr


def _name(key: str) -> str:
    return f"{tr('ex.' + key)} ({tr('ex.synthetic')})"


def temperature() -> Grid:
    """Average monthly temperatures, 12 months × 10 years."""
    years = list(range(2015, 2025))
    rng = np.random.default_rng(42)
    m = np.arange(12)[:, None]
    y = np.arange(len(years))[None, :]
    seasonal = 13.0 - 11.0 * np.cos(2 * np.pi * (m + 0.5) / 12)
    values = np.round(seasonal + 0.08 * y + rng.normal(0, 0.9, (12, len(years))), 1)
    return Grid(values, tr("months").split(), [str(v) for v in years], name=_name("temperature"))


def traffic() -> Grid:
    """Hourly vehicle counts, 7 days × 24 hours, with peak traffic during weekday rush hours."""    
    rng = np.random.default_rng(7)
    h = np.arange(24)[None, :]
    peak = lambda center, width: np.exp(-((h - center) ** 2) / (2 * width**2))  # noqa: E731
    workday = 120 + 900 * peak(8, 1.3) + 750 * peak(18, 1.8) + 350 * peak(13, 3)
    weekend = 90 + 520 * peak(12, 3.5) + 260 * peak(20, 2)
    base = np.vstack([np.repeat(workday, 5, axis=0), np.repeat(weekend, 2, axis=0)])
    base[4] *= 1.08  
    values = np.round(base * rng.normal(1.0, 0.05, base.shape))
    return Grid(values, tr("weekdays").split(), [f"{v:02d}" for v in range(24)], name=_name("traffic"))


def correlation() -> Grid:
    """Correlations between 10 variables, with three groups of related variables."""
    rng = np.random.default_rng(3)
    x = rng.normal(size=(300, 10))
    x[:, 1] += 0.9 * x[:, 0]
    x[:, 2] += 0.6 * x[:, 0]
    x[:, 4] -= 0.8 * x[:, 3]
    x[:, 7] += x[:, 6]
    x[:, 8] += 0.7 * x[:, 6] - 0.4 * x[:, 3]
    labels = [f"V{i + 1}" for i in range(10)]
    return Grid(np.round(np.corrcoef(x.T), 2), labels, labels, name=_name("correlation"))


def sensors() -> Grid:
    """A 40×60 sensor grid with a faulty block and scattered missing readings."""
    rng = np.random.default_rng(11)
    field = gaussian_filter(rng.normal(size=(40, 60)), 5) * 40 + 20
    field[10:18, 35:47] = np.nan
    field[rng.random(field.shape) < 0.03] = np.nan
    return Grid(np.round(field, 2), [], [], name=_name("sensors"))


def terrain() -> Grid:
    """100×100 elevation map (meters): two peaks, a ridge, a valley, and surface roughness."""
    rng = np.random.default_rng(5)
    yy, xx = np.mgrid[0:1:100j, 0:1:100j]
    bump = lambda cx, cy, s, h: h * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s**2))  # noqa: E731
    z = bump(0.3, 0.35, 0.12, 2200) + bump(0.72, 0.62, 0.09, 1800) + bump(0.55, 0.2, 0.06, 900)
    z += 700 * np.exp(-((yy - 0.75 + 0.3 * xx) ** 2) / 0.004)  # cresta diagonale
    z -= 400 * np.exp(-((xx - 0.15) ** 2) / 0.002)  # valle
    z += gaussian_filter(rng.normal(size=z.shape), 2) * 120
    return Grid(np.round(z + 600), [], [], name=_name("terrain"))


def waves() -> Grid:
    """Interference pattern between two wave sources, 120×160."""
    yy, xx = np.mgrid[0:1:120j, 0:4 / 3:160j]
    d1 = np.hypot(xx - 0.45, yy - 0.5)
    d2 = np.hypot(xx - 0.9, yy - 0.5)
    k = 2 * np.pi / 0.11
    z = np.cos(k * d1) / (1 + 4 * d1) + np.cos(k * d2) / (1 + 4 * d2)
    return Grid(np.round(z, 4), [], [], name=_name("waves"))


EXAMPLES: dict[str, Callable[[], Grid]] = {
    "temperature": temperature,
    "traffic": traffic,
    "correlation": correlation,
    "sensors": sensors,
    "terrain": terrain,
    "waves": waves,
}
SHAPES = {"temperature": (12, 10), "traffic": (7, 24), "correlation": (10, 10), "sensors": (40, 60),
          "terrain": (100, 100), "waves": (120, 160)}


def build(key: str) -> Grid:
    grid = EXAMPLES[key]()
    grid.example = key
    return grid


def label(key: str) -> str:
    r, c = SHAPES[key]
    return f"{tr('ex.' + key)} · {r}×{c}"
