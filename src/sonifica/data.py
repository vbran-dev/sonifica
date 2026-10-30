"""Data loading (CSV files and images) and heatmap resizing."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from sonifica.i18n import tr

MAX_IMAGE_SIDE = 128
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
MISSING_MARKERS = {"", "na", "n/a", "nan", "null", "-", "--", "?"}


@dataclass
class Grid:
    """A 2D table of values with row and column labels."""
    values: np.ndarray
    row_labels: list[str]
    col_labels: list[str]
    name: str = "data"
    labeled: bool = True  # False: rows and columns are simply numbered (images, grids).
    example: str | None = None  # Example key, used to regenerate it in another language.

    def __post_init__(self) -> None:
        self.values = np.asarray(self.values, dtype=float)
        if self.values.ndim != 2 or self.values.size == 0:
            raise ValueError(tr("err.not_2d"))
        if np.all(np.isnan(self.values)):
            raise ValueError(tr("err.no_numbers"))
        n_rows, n_cols = self.values.shape
        if len(self.row_labels) != n_rows or len(self.col_labels) != n_cols:
            self.labeled = False
        if len(self.row_labels) != n_rows:
            self.row_labels = [str(i + 1) for i in range(n_rows)]
        if len(self.col_labels) != n_cols:
            self.col_labels = [str(j + 1) for j in range(n_cols)]

    def place(self, r: int, c: int) -> str:
        """Verbal description of cell's position."""
        if self.labeled:
            return f"{self.row_labels[r]}, {self.col_labels[c]}"
        return f"{tr('row')} {r + 1}, {tr('col')} {c + 1}"

    def normalized(self) -> np.ndarray:
        span = self.vmax - self.vmin
        if span == 0:
            out = np.full(self.values.shape, 0.5)
        else:
            out = (self.values - self.vmin) / span
        out[np.isnan(self.values)] = np.nan
        return out

    def argmin(self) -> tuple[int, int]:
        return np.unravel_index(np.nanargmin(self.values), self.shape)  # type: ignore[return-value]

    def argmax(self) -> tuple[int, int]:
        return np.unravel_index(np.nanargmax(self.values), self.shape)  # type: ignore[return-value]

    @property
    def shape(self) -> tuple[int, int]:
        return self.values.shape  # type: ignore[return-value]

    @property
    def vmin(self) -> float:
        return float(np.nanmin(self.values))

    @property
    def vmax(self) -> float:
        return float(np.nanmax(self.values))

    @property
    def n_missing(self) -> int:
        return int(np.isnan(self.values).sum())




def _parse_cell(text: str) -> float | None:
    """Converts a cell into a number.

    Returns NaN for missing values and None for text (labels).
    Accepts both periods and commas as decimal separators.
    """
    s = text.strip().replace(" ", "").replace(" ", "")
    if s.lower() in MISSING_MARKERS:
        return float("nan")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):  # 1.234,5
            s = s.replace(".", "").replace(",", ".")
        else:  # 1,234.5
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _looks_like_header(values: list[float | None]) -> bool:
    """A row containing only increasing integers (e.g. years 2015, 2016, ...) is considered a header."""
    nums = [v for v in values if v is not None and not np.isnan(v)]
    if len(nums) < 2 or len(nums) != len(values):
        return False
    return all(float(v).is_integer() for v in nums) and all(b > a for a, b in zip(nums[:-1], nums[1:], strict=True))


def load_csv(path: str | Path) -> Grid:
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    try:
        delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
    except csv.Error:
        delimiter = ","

    rows = [r for r in csv.reader(text.splitlines(), delimiter=delimiter) if any(c.strip() for c in r)]
    if not rows:
        raise ValueError(tr("err.csv_empty"))
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    parsed = [[_parse_cell(c) for c in r] for r in rows]

    first = parsed[0]
    first_cell_is_label = first[0] is None or rows[0][0].strip() == ""
    has_header = (
        any(v is None for v in first[1:])
        or (width == 1 and first[0] is None)
        or (width > 1 and first_cell_is_label and _looks_like_header(first[1:]))
    )
    body_raw = rows[1:] if has_header else rows
    body = parsed[1:] if has_header else parsed
    if not body:
        raise ValueError(tr("err.csv_no_rows"))

    has_row_labels = width > 1 and sum(r[0] is None for r in body) > len(body) / 2
    start = 1 if has_row_labels else 0
    values = np.array([[np.nan if v is None else v for v in r[start:]] for r in body], dtype=float)

    row_labels = [r[0].strip() for r in body_raw] if has_row_labels else []
    col_labels = [c.strip() for c in rows[0][start:]] if has_header else []
    return Grid(values, row_labels, col_labels, name=path.stem)


def load_image(path: str | Path, max_side: int = MAX_IMAGE_SIDE) -> Grid:
    """Loads an image as a brightness grid (0 = black, 1 = white).

    The image is reduced to `max_side` cells per side (it can then be further
    downsampled using `resample`). With colormaps featuring increasing
    brightness (viridis, magma, grayscale), brightness closely follows the
    original value.
    """
    from PIL import Image

    path = Path(path)
    with Image.open(path) as img:
        img = img.convert("L")
        w, h = img.size
        scale = min(1.0, max_side / max(w, h))
        if scale < 1.0:
            size = (max(1, round(w * scale)), max(1, round(h * scale)))
            img = img.resize(size, Image.Resampling.BOX)
        arr = np.asarray(img, dtype=float) / 255.0
    return Grid(arr, [], [], name=path.stem)


def load(path: str | Path) -> Grid:
    if Path(path).suffix.lower() in IMAGE_SUFFIXES:
        return load_image(path)
    return load_csv(path)


def example_grid() -> Grid:
    """Default example"""
    from sonifica.examples import build

    return build("temperature")


# --- resizing ------------------------------------------------------
RESAMPLE_METHODS = ("area", "nearest")


def _area_weights(old: int, new: int) -> np.ndarray:
    """Fraction of each old cell (columns) that falls within each new cell (rows)."""
    o = np.arange(old + 1) / old
    n = np.arange(new + 1) / new
    lo = np.maximum(n[:-1, None], o[None, :-1])
    hi = np.minimum(n[1:, None], o[None, 1:])
    return np.clip(hi - lo, 0.0, None)


def _nearest_weights(old: int, new: int) -> np.ndarray:
    w = np.zeros((new, old))
    src = np.minimum(((np.arange(new) + 0.5) * old / new).astype(int), old - 1)
    w[np.arange(new), src] = 1.0
    return w


def _merge_labels(labels: list[str], weights: np.ndarray) -> list[str]:
    out = []
    for row in weights:
        idx = np.flatnonzero(row > 1e-9)
        first, last = labels[idx[0]], labels[idx[-1]]
        out.append(first if first == last else f"{first}–{last}")
    return out


def resample(grid: Grid, n_rows: int, n_cols: int, method: str = "area") -> Grid:
    """Resizes a heatmap to n_rows × n_cols.

    - "area": each new cell is the area-weighted average of the cells it covers,
      similar to image downscaling. Missing values are ignored; a new cell is
      considered missing only if it covers exclusively missing data.
    - "nearest": each new cell takes the value of the cell containing its center.

    The result looks visually similar to the original but differs numerically.
    """
    old_r, old_c = grid.shape
    n_rows, n_cols = int(np.clip(n_rows, 1, old_r)), int(np.clip(n_cols, 1, old_c))
    if method not in RESAMPLE_METHODS:
        raise ValueError(f"Unknown method: {method}")
    weights = _area_weights if method == "area" else _nearest_weights
    wr, wc = weights(old_r, n_rows), weights(old_c, n_cols)
    ok = ~np.isnan(grid.values)
    total = wr @ np.where(ok, grid.values, 0.0) @ wc.T
    mass = wr @ ok.astype(float) @ wc.T
    values = np.full((n_rows, n_cols), np.nan)
    np.divide(total, mass, out=values, where=mass > 1e-12)
    if grid.labeled:
        rows, cols = _merge_labels(grid.row_labels, wr), _merge_labels(grid.col_labels, wc)
    else:
        rows, cols = [], []
    return Grid(values, rows, cols, name=tr("resized_name", name=grid.name, rows=n_rows, cols=n_cols),
                labeled=grid.labeled)
