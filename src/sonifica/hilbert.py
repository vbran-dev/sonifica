"""Heatmap traversal along a Hilbert curve.

The problem with row-by-row playback: the sound depends on the number of
rows and columns in the matrix. Adding one row or doubling the resolution
changes the duration, rhythm, and order of the notes, making two nearly
identical matrices sound completely different.

The solution: the matrix is mapped onto the unit square and traversed
along a Hilbert curve, with a fixed total duration. Each instant of sound
therefore corresponds to a point in the square, regardless of the
resolution. Two properties of the curve make the sound consistent:

- locality: points that are close in time are also close in the matrix
  (and almost always vice versa), so a small local change affects only a
  short segment of the sound;
- nesting: the order n+1 curve refines the order n curve without changing
  its traversal order, so increasing the resolution adds detail rather
  than completely changing the melody.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sonifica.i18n import tr

MIN_ORDER = 1
MAX_ORDER = 8


def d2xy(order: int, d: np.ndarray | int) -> tuple[np.ndarray, np.ndarray]:
    """Position (x, y) of the d-th vertex of the Hilbert curve of order `order`.
    The grid is 2^order × 2^order. With x = column and y = row (row 0 at the top),
    the curve starts at the top left, moves downward, traverses the bottom, and
    ends at the top right.
    """
    t = np.array(d, dtype=np.int64, copy=True)
    x = np.zeros_like(t)
    y = np.zeros_like(t)
    s = 1
    side = 1 << order
    while s < side:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        # quadrant rotation
        flip = (ry == 0) & (rx == 1)
        x = np.where(flip, s - 1 - x, x)
        y = np.where(flip, s - 1 - y, y)
        swap = ry == 0
        x, y = np.where(swap, y, x), np.where(swap, x, y)
        x = x + s * rx
        y = y + s * ry
        t = t // 4
        s *= 2
    return x, y


def order_for(shape: tuple[int, int]) -> int:
    """Minimum order required to ensure that every cell in the matrix is visited at least once."""
    side = max(shape)
    return int(np.clip(np.ceil(np.log2(max(side, 2))), MIN_ORDER, MAX_ORDER))


@dataclass(frozen=True)
class HilbertPath:
    order: int
    rows: np.ndarray  # row index in the matrix for each vertex
    cols: np.ndarray  # column index in the matrix for each vertex
    x: np.ndarray  # horizontal position posizione in [0, 1] (vertex centre)
    y: np.ndarray  # vertical position in [0, 1]

    @property
    def n_points(self) -> int:
        return len(self.rows)

    def quadrant(self, t: float) -> int:
        """Quadrant (1–4) traversed at normalized time t ∈ [0, 1)."""
        return min(3, int(t * 4)) + 1


def quadrant_name(q: int) -> str:
    return tr(f"quadrant.{q}")


def path_for(shape: tuple[int, int], order: int | None = None) -> HilbertPath:
    """Hilbert path across the matrix `shape`, mapped onto the unit square."""
    n_rows, n_cols = shape
    order = order_for(shape) if order is None else order
    side = 1 << order
    xs, ys = d2xy(order, np.arange(side * side))
    x = (xs + 0.5) / side
    y = (ys + 0.5) / side
    rows = np.minimum((y * n_rows).astype(int), n_rows - 1)
    cols = np.minimum((x * n_cols).astype(int), n_cols - 1)
    return HilbertPath(order, rows, cols, x, y)


def sample(norm: np.ndarray, path: HilbertPath | None = None) -> np.ndarray:
    """Matrix values in the order in which they are visited by the curve."""
    path = path_for(norm.shape) if path is None else path
    return norm[path.rows, path.cols]


def to_grid(values: np.ndarray, shape: tuple[int, int], path: HilbertPath | None = None) -> np.ndarray:
    """Inverse operation: maps values along the curve back to the matrix (averaging the vertices within each cell)."""
    path = path_for(shape) if path is None else path
    total = np.zeros(shape)
    count = np.zeros(shape)
    ok = ~np.isnan(values)
    np.add.at(total, (path.rows[ok], path.cols[ok]), values[ok])
    np.add.at(count, (path.rows[ok], path.cols[ok]), 1)
    out = np.full(shape, np.nan)
    np.divide(total, count, out=out, where=count > 0)
    return out


# --- coherence between different matrices -----------------------------------------
def listening_track(norm: np.ndarray, route: str = "hilbert", n_samples: int = 4096) -> np.ndarray:
    """Value heard as a function of normalized time (0 = start, 1 = end).
    For a fair comparison, the row-by-row traversal is also normalized
    to the same total duration.
    """
    if route == "hilbert":
        seq = sample(norm)
    elif route == "rows":
        seq = norm.reshape(-1)
    else:
        raise ValueError(f"Unknown route: {route}")
    idx = np.minimum((np.arange(n_samples) + 0.5) / n_samples * len(seq), len(seq) - 1).astype(int)
    return seq[idx]


def coherence(a: np.ndarray, b: np.ndarray, route: str = "hilbert") -> float:
    """Correlation between the audio representations of two matrices (1 = they sound identical)."""
    ta, tb = listening_track(a, route), listening_track(b, route)
    ok = ~np.isnan(ta) & ~np.isnan(tb)
    if ok.sum() < 2 or ta[ok].std() == 0 or tb[ok].std() == 0:
        return float("nan")
    return float(np.corrcoef(ta[ok], tb[ok])[0, 1])


def describe_coherence(r: float) -> str:
    if np.isnan(r):
        return tr("rt.verdict.na")
    if r > 0.97:
        return tr("coh.verdict.1")
    if r > 0.9:
        return tr("coh.verdict.2")
    if r > 0.7:
        return tr("coh.verdict.3")
    return tr("coh.verdict.4")
