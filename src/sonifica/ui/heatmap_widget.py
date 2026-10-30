"""Keyboard-and mouse-navigable heatmap widget, with labels and a legend."""

from __future__ import annotations

import numpy as np
from matplotlib.colors import Colormap
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from sonifica import palettes
from sonifica.i18n import tr
from sonifica.ui import theme

try:
    from PySide6.QtGui import QAccessible, QAccessibleEvent
except ImportError:  # PySide6 versions without accessibility bindings.
    QAccessible = QAccessibleEvent = None  # type: ignore[assignment,misc]

MISSING_COLOR = QColor("#2e2836")
LEGEND_H = 10
LEGEND_GAP = 30


class HeatmapWidget(QWidget):
    cellChanged = Signal(int, int)
    edgeHit = Signal()
    playRowRequested = Signal()
    playColumnRequested = Signal()
    announceRequested = Signal()
    summaryRequested = Signal()
    stopRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumSize(360, 280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName(tr("hm.name"))
        self.setAccessibleDescription(tr("hm.desc"))
        self.hover_play = True
        self.row = 0
        self.col = 0
        self.hover: tuple[int, int] | None = None
        self._norm: np.ndarray | None = None
        self._colors: list[list[QColor]] = []
        self._row_labels: list[str] = []
        self._col_labels: list[str] = []
        self._range_text = ("", "")
        self._cmap: Colormap = palettes.get_cmap(palettes.DEFAULT)
        self.show_path = False
        self._path_xy: tuple[np.ndarray, np.ndarray] | None = None
        self._playhead: float | None = None
        self._cache: QPixmap | None = None  # Cells already drawn: redrawing is expensive with 10,000+ cells.
        self._rgba: np.ndarray | None = None
        self._label_width = 0.0
        self._label_font = QFont(self.font())
        self._label_font.setPointSizeF(8.5)

    # --- data -------------------------------------------------------------
    def set_data(
        self,
        norm: np.ndarray,
        row_labels: list[str] | None = None,
        col_labels: list[str] | None = None,
        range_text: tuple[str, str] = ("min", "max"),
        cmap: Colormap | None = None,
        path_xy: tuple[np.ndarray, np.ndarray] | None = None,
    ) -> None:
        self._norm = norm
        if cmap is not None:
            self._cmap = cmap
        self._recolor()
        self._path_xy = path_xy
        self._playhead = None
        self._row_labels = row_labels or []
        self._col_labels = col_labels or []
        fm = QFontMetrics(self._label_font)
        self._label_width = max((fm.horizontalAdvance(s) for s in self._row_labels), default=0) + 12
        self._range_text = range_text
        self.row = self.col = 0
        self.hover = None
        self.update()

    def set_colormap(self, cmap: Colormap) -> None:
        self._cmap = cmap
        self._recolor()
        self.update()

    def _recolor(self) -> None:
        norm = self._norm
        self._cache = None
        if norm is None:
            return
        rgba = self._cmap(np.nan_to_num(norm, nan=0.0))
        self._rgba = rgba
        self._colors = [
            [MISSING_COLOR if np.isnan(norm[r, c]) else QColor.fromRgbF(*rgba[r, c, :3]) for c in range(norm.shape[1])]
            for r in range(norm.shape[0])
        ]

    def set_show_path(self, on: bool) -> None:
        self.show_path = on
        self.update()

    def set_playhead(self, t: float | None) -> None:
        """Sound position along the curve (0–1), or None to hide it."""
        self._playhead = t
        self.update()

    @property
    def shape(self) -> tuple[int, int]:
        return (0, 0) if self._norm is None else self._norm.shape  # type: ignore[return-value]

    def set_cell(self, r: int, c: int) -> None:
        n_rows, n_cols = self.shape
        if not (0 <= r < n_rows and 0 <= c < n_cols):
            self.edgeHit.emit()
            return
        if (r, c) != (self.row, self.col):
            self.row, self.col = r, c
            self.update()
        self.cellChanged.emit(r, c)

    def announce(self, text: str) -> None:
        """Updates the accessible name: screen readers announce the current cell."""
        self.setAccessibleName(text)
        if QAccessible is not None:
            try:
                QAccessible.updateAccessibility(QAccessibleEvent(self, QAccessible.Event.NameChanged))
            except Exception:  # noqa: BLE001 - accessibility must never prevent the application from running.
                pass

    # --- geometry --------------------------------------------------------
    def _show_labels(self) -> bool:
        return bool(self._row_labels and self._col_labels)

    def _margins(self) -> tuple[float, float]:
        if not self._show_labels():
            return 0.0, 0.0
        top = QFontMetrics(self._label_font).height() + 8
        return min(self._label_width, self.width() * 0.25), top

    def _grid_rect(self) -> QRectF:
        left, top = self._margins()
        r = QRectF(self.rect()).adjusted(8 + left, 8 + top, -8, -(8 + LEGEND_GAP + LEGEND_H))
        n_rows, n_cols = self.shape
        if n_rows and n_cols:
            size = min(r.width() / n_cols, r.height() / n_rows)
            if size * n_cols < r.width() * 0.98:
                w = size * n_cols * 1.0
                r.setLeft(r.left() + (r.width() - w) / 2)
                r.setWidth(w)
        return r

    def _cell_size(self) -> tuple[float, float]:
        g = self._grid_rect()
        n_rows, n_cols = self.shape
        return g.width() / max(1, n_cols), g.height() / max(1, n_rows)

    def _cell_rect(self, r: int, c: int) -> QRectF:
        g = self._grid_rect()
        w, h = self._cell_size()
        return QRectF(g.left() + c * w, g.top() + r * h, w, h)

    def _cell_at(self, pos: QPoint) -> tuple[int, int] | None:
        if self._norm is None:
            return None
        g = self._grid_rect()
        w, h = self._cell_size()
        x, y = pos.x() - g.left(), pos.y() - g.top()
        if x < 0 or y < 0:
            return None
        c, r = int(x // w), int(y // h)
        n_rows, n_cols = self.shape
        return (r, c) if r < n_rows and c < n_cols else None

    # --- drawing ----------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._norm is None:
            p.setPen(QColor(theme.MUTED))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr("hm.empty"))
            return
        w, h = self._cell_size()
        radius = min(3.0, min(w, h) * 0.12)
        if self._cache is None or self._cache.size() != self.size():
            self._cache = self._render_cells()
        p.drawPixmap(0, 0, self._cache)

        self._draw_labels(p, w, h)
        self._draw_legend(p)

        g = self._grid_rect()
        guide = QColor(255, 255, 255, 14)
        p.setBrush(guide)
        p.drawRect(QRectF(g.left(), g.top() + self.row * h, g.width(), h))
        p.drawRect(QRectF(g.left() + self.col * w, g.top(), w, g.height()))

        if self.hover and self.hover != (self.row, self.col):
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(255, 255, 255, 120), 1.5))
            p.drawRoundedRect(self._cell_rect(*self.hover).adjusted(1, 1, -1, -1), radius, radius)

        # Selected cell: double dark/light border, visible against any background color.
        sel = self._cell_rect(self.row, self.col).adjusted(-1, -1, 1, 1)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(theme.BG), 5))
        p.drawRoundedRect(sel, radius + 1, radius + 1)
        p.setPen(QPen(QColor("white"), 3 if self.hasFocus() else 2))
        p.drawRoundedRect(sel, radius + 1, radius + 1)

        if self._path_xy is not None and (self.show_path or self._playhead is not None):
            self._draw_path(p)

    def _path_points(self) -> tuple[np.ndarray, np.ndarray]:
        g = self._grid_rect()
        x, y = self._path_xy  # type: ignore[misc]
        return g.left() + x * g.width(), g.top() + y * g.height()

    def _draw_path(self, p: QPainter) -> None:
        px, py = self._path_points()
        n = len(px)
        if self.show_path:
            poly = QPolygonF([QPointF(a, b) for a, b in zip(px, py, strict=True)])
            p.setBrush(Qt.BrushStyle.NoBrush)
            # Double dark-and-light stroke: visible against both light and dark colors.
            p.setPen(QPen(QColor(0, 0, 0, 110), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                          Qt.PenJoinStyle.RoundJoin))
            p.drawPolyline(poly)
            p.setPen(QPen(QColor(255, 255, 255, 150), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                          Qt.PenJoinStyle.RoundJoin))
            p.drawPolyline(poly)
        if self._playhead is not None:
            k = min(n - 1, int(self._playhead * n))
            done = QPainterPath(QPointF(px[0], py[0]))
            for i in range(1, k + 1):
                done.lineTo(px[i], py[i])
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(0, 0, 0, 160), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                          Qt.PenJoinStyle.RoundJoin))
            p.drawPath(done)
            p.setPen(QPen(QColor("white"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                          Qt.PenJoinStyle.RoundJoin))
            p.drawPath(done)
            center = QPointF(px[k], py[k])
            p.setPen(QPen(QColor(theme.BG), 3))
            p.setBrush(QColor("white"))
            p.drawEllipse(center, 7, 7)

    def _render_cells(self) -> QPixmap:
        pm = QPixmap(self.size())
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        n_rows, n_cols = self.shape
        g = self._grid_rect()
        w, h = g.width() / n_cols, g.height() / n_rows
        missing = np.isnan(self._norm)
        hatch = QBrush(QColor(theme.MUTED), Qt.BrushStyle.BDiagPattern)
        p.setPen(Qt.PenStyle.NoPen)
        if min(w, h) <= 10:
            # One pixel per cell, enlarged without smoothing.
            rgb = (self._rgba[..., :3] * 255).round().astype(np.uint8)
            rgb[missing] = (MISSING_COLOR.red(), MISSING_COLOR.green(), MISSING_COLOR.blue())
            rgb = np.ascontiguousarray(rgb)
            img = QImage(rgb.data, n_cols, n_rows, 3 * n_cols, QImage.Format.Format_RGB888)
            p.drawImage(g, img)
            if missing.any():
                p.setBrush(hatch)
                for r, c in zip(*np.nonzero(missing), strict=True):
                    p.drawRect(QRectF(g.left() + c * w, g.top() + r * h, w, h))
        else:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            gap = 2.0
            radius = min(3.0, min(w, h) * 0.12)
            for r in range(n_rows):
                for c in range(n_cols):
                    rect = QRectF(g.left() + c * w + gap / 2, g.top() + r * h + gap / 2, w - gap, h - gap)
                    p.setBrush(self._colors[r][c])
                    p.drawRoundedRect(rect, radius, radius)
                    if missing[r, c]:
                        # hatching: a missing value is not confused with a low value
                        p.setBrush(hatch)
                        p.drawRoundedRect(rect, radius, radius)
        p.end()
        return pm

    def resizeEvent(self, event) -> None:
        self._cache = None
        super().resizeEvent(event)

    def _draw_labels(self, p: QPainter, w: float, h: float) -> None:
        if not self._show_labels():
            return
        g = self._grid_rect()
        p.setFont(self._label_font)
        fm = QFontMetrics(self._label_font)
        n_rows, n_cols = self.shape
        row_step = max(1, int(np.ceil(fm.height() / max(h, 1))))
        widest = max((fm.horizontalAdvance(s) for s in self._col_labels), default=0) + 8
        col_step = max(1, int(np.ceil(widest / max(w, 1))))
        left, _ = self._margins()
        for r in range(0, n_rows, row_step):
            active = r == self.row
            p.setPen(QColor(theme.TEXT if active else theme.FAINT))
            cy = g.top() + (r + 0.5) * h
            rect = QRectF(g.left() - left - 4, cy - fm.height() / 2, left - 4, fm.height())
            text = fm.elidedText(self._row_labels[r], Qt.TextElideMode.ElideRight, int(rect.width()))
            p.drawText(rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, text)
        for c in range(0, n_cols, col_step):
            active = c == self.col
            p.setPen(QColor(theme.TEXT if active else theme.FAINT))
            rect = QRectF(g.left() + c * w - 20, g.top() - fm.height() - 6, w + 40, fm.height())
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._col_labels[c])

    def _draw_legend(self, p: QPainter) -> None:
        g = self._grid_rect()
        bar = QRectF(g.left(), g.bottom() + LEGEND_GAP - 6, min(g.width(), 260), LEGEND_H - 4)
        clip = QPainterPath()
        clip.addRoundedRect(bar, 3, 3)
        p.save()
        p.setClipPath(clip)
        p.setPen(Qt.PenStyle.NoPen)
        steps = 96
        for i in range(steps):
            p.setBrush(QColor.fromRgbF(*self._cmap((i + 0.5) / steps)[:3]))
            p.drawRect(QRectF(bar.left() + bar.width() * i / steps, bar.top(), bar.width() / steps + 0.6, bar.height()))
        p.restore()
        # posizione della cella corrente sulla scala
        v = self._norm[self.row, self.col] if self._norm is not None else np.nan
        if not np.isnan(v):
            x = bar.left() + v * bar.width()
            p.setPen(QPen(QColor(theme.BG), 4))
            p.drawLine(int(x), int(bar.top() - 3), int(x), int(bar.bottom() + 3))
            p.setPen(QPen(QColor("white"), 2))
            p.drawLine(int(x), int(bar.top() - 3), int(x), int(bar.bottom() + 3))
        p.setFont(self._label_font)
        p.setPen(QColor(theme.MUTED))
        lo, hi = self._range_text
        p.drawText(QRectF(bar.right() + 10, bar.top() - 6, 200, LEGEND_H + 12),
                   Qt.AlignmentFlag.AlignVCenter, f"{lo} – {hi}")

    # --- input ------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._norm is None:
            return super().keyPressEvent(event)
        key, mods = event.key(), event.modifiers()
        n_rows, n_cols = self.shape
        K = Qt.Key
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        moves = {K.Key_Up: (-1, 0), K.Key_Down: (1, 0), K.Key_Left: (0, -1), K.Key_Right: (0, 1)}
        if key in moves:
            dr, dc = moves[key]
            self.set_cell(self.row + dr, self.col + dc)
        elif key == K.Key_Home:
            self.set_cell(0, 0) if ctrl else self.set_cell(self.row, 0)
        elif key == K.Key_End:
            self.set_cell(n_rows - 1, n_cols - 1) if ctrl else self.set_cell(self.row, n_cols - 1)
        elif key == K.Key_PageUp:
            self.set_cell(0, self.col)
        elif key == K.Key_PageDown:
            self.set_cell(n_rows - 1, self.col)
        elif key == K.Key_Space:
            self.playRowRequested.emit()
        elif key == K.Key_C:
            self.playColumnRequested.emit()
        elif key in (K.Key_Return, K.Key_Enter):
            self.announceRequested.emit()
        elif key == K.Key_I:
            self.summaryRequested.emit()
        elif key == K.Key_Escape:
            self.stopRequested.emit()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        cell = self._cell_at(event.position().toPoint())
        if cell:
            self.set_cell(*cell)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        cell = self._cell_at(event.position().toPoint())
        if cell != self.hover:
            self.hover = cell
            self.update()
        if cell and cell != (self.row, self.col) and (self.hover_play or event.buttons()):
            self.set_cell(*cell)

    def leaveEvent(self, event) -> None:
        self.hover = None
        self.update()
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self.update()
        super().focusOutEvent(event)
