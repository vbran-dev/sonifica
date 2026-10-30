"""Vector icons drawn with QPainter: no external files, no Unicode symbols."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from sonifica import palettes
from sonifica.ui import theme

SIZE = 64


def _canvas() -> tuple[QPixmap, QPainter]:
    pm = QPixmap(SIZE, SIZE)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    return pm, p


def _finish(pm: QPixmap, p: QPainter) -> QIcon:
    p.end()
    return QIcon(pm)


def play(color: str = theme.TEXT) -> QIcon:
    pm, p = _canvas()
    path = QPainterPath()
    path.moveTo(20, 12)
    path.lineTo(52, 32)
    path.lineTo(20, 52)
    path.closeSubpath()
    p.setPen(QPen(QColor(color), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(QColor(color))
    p.drawPath(path)
    return _finish(pm, p)


def stop(color: str = theme.DANGER) -> QIcon:
    pm, p = _canvas()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawRoundedRect(QRectF(16, 16, 32, 32), 6, 6)
    return _finish(pm, p)


def spectrum(color: str = theme.TEXT) -> QIcon:
    pm, p = _canvas()
    p.setPen(QPen(QColor(color), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for x, h in zip((14, 25, 36, 47), (14, 34, 22, 40), strict=True):
        p.drawLine(QPointF(x, 32 - h / 2), QPointF(x, 32 + h / 2))
    return _finish(pm, p)


def compare(color: str = theme.TEXT) -> QIcon:
    pm, p = _canvas()
    p.setPen(QPen(QColor(color), 5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(10, 10, 30, 30), 6, 6)
    p.drawRoundedRect(QRectF(24, 24, 30, 30), 6, 6)
    return _finish(pm, p)


def folder(color: str = theme.ACCENT_TEXT) -> QIcon:
    pm, p = _canvas()
    path = QPainterPath()
    path.moveTo(8, 18)
    path.lineTo(26, 18)
    path.lineTo(31, 24)
    path.lineTo(56, 24)
    path.lineTo(56, 50)
    path.lineTo(8, 50)
    path.closeSubpath()
    p.setPen(QPen(QColor(color), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)
    return _finish(pm, p)


def logo_pixmap(size: int = 28) -> QPixmap:
    """The logo: a 3×3 mini heatmap using the palette colors."""
    scale = 4
    pm = QPixmap(size * scale, size * scale)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    cmap = palettes.get_cmap(palettes.DEFAULT)
    values = np.array([[0.35, 0.6, 0.95], [0.2, 0.75, 0.55], [0.1, 0.4, 0.8]])
    cell = size * scale / 3
    gap = cell * 0.12
    for r in range(3):
        for c in range(3):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor.fromRgbF(*cmap(values[r, c])[:3]))
            rect = QRectF(c * cell + gap / 2, r * cell + gap / 2, cell - gap, cell - gap)
            p.drawRoundedRect(rect, cell * 0.22, cell * 0.22)
    p.end()
    pm.setDevicePixelRatio(scale)
    return pm


def app_icon() -> QIcon:
    return QIcon(logo_pixmap(64))
