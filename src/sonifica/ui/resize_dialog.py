"""Resize a heatmap and compare how it looks against the original."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from sonifica.audio import Player
from sonifica.data import Grid, resample
from sonifica.hilbert import coherence, describe_coherence, listening_track
from sonifica.i18n import fixed, tr
from sonifica.ui import icons, theme

ORIGINAL_COLOR = "#3987e5"
RESIZED_COLOR = "#d95926"
FACTORS = (2, 4, 8, 10)


class ResizeDialog(QDialog):
    resizedChosen = Signal(object)  # Grid

    def __init__(self, grid: Grid, cmap, player: Player, make_audio: Callable[[np.ndarray], np.ndarray],
                 parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("rs.window"))
        self.resize(1180, 860)
        self.grid = grid
        self.cmap = cmap
        self.player = player
        self.make_audio = make_audio
        self.resized: Grid = grid
        self._linking = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self.refresh)

        title = QLabel(tr("rs.title"))
        title.setObjectName("heading")
        subtitle = QLabel(tr("rs.subtitle"))
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)

        # --- controls -------------------------------------------------------
        n_rows, n_cols = grid.shape
        self.rows_box = QSpinBox()
        self.rows_box.setRange(1, n_rows)
        self.cols_box = QSpinBox()
        self.cols_box.setRange(1, n_cols)
        self.rows_box.setAccessibleName(tr("rs.rows"))
        self.cols_box.setAccessibleName(tr("rs.cols"))
        self.keep_box = QCheckBox(tr("rs.keep"))
        self.keep_box.setChecked(True)
        self.method_box = QComboBox()
        self.method_box.addItem(tr("method.area"), "area")
        self.method_box.addItem(tr("method.nearest"), "nearest")
        self.method_box.setAccessibleName(tr("rs.method"))

        controls = QHBoxLayout()
        controls.setSpacing(10)
        for label, widget in ((tr("rs.rows"), self.rows_box), (tr("rs.cols"), self.cols_box)):
            lab = QLabel(label)
            lab.setObjectName("muted")
            lab.setBuddy(widget)
            controls.addWidget(lab)
            controls.addWidget(widget)
        controls.addWidget(self.keep_box)
        controls.addSpacing(12)
        for n in FACTORS:
            b = QPushButton(f"1/{n}")
            b.setToolTip(tr("rs.factor", n=n))
            b.setAccessibleName(tr("rs.factor", n=n))
            b.setEnabled(min(n_rows, n_cols) // n >= 1)
            b.clicked.connect(lambda _=False, f=n: self.apply_factor(f))
            controls.addWidget(b)
        controls.addSpacing(12)
        method_label = QLabel(tr("rs.method"))
        method_label.setObjectName("muted")
        method_label.setBuddy(self.method_box)
        controls.addWidget(method_label)
        controls.addWidget(self.method_box)
        controls.addStretch()

        # --- plots ---------------------------------------------------------
        self.fig = Figure(figsize=(11, 6), layout="constrained")
        self.fig.get_layout_engine().set(h_pad=0.12, hspace=0.08)
        gs = self.fig.add_gridspec(2, 2, height_ratios=[1.35, 1])
        self.ax_orig = self.fig.add_subplot(gs[0, 0])
        self.ax_res = self.fig.add_subplot(gs[0, 1])
        self.ax_th = self.fig.add_subplot(gs[1, 0])
        self.ax_tr = self.fig.add_subplot(gs[1, 1], sharey=self.ax_th)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setAccessibleName(tr("rtw.plots"))
        self.canvas.setAccessibleDescription(tr("rtw.plots.desc"))
        plot_card = QFrame()
        plot_card.setObjectName("canvas")
        pl = QVBoxLayout(plot_card)
        pl.setContentsMargins(10, 10, 10, 10)
        pl.addWidget(self.canvas)

        # --- results ---------------------------------------------------------
        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.coh_value: dict[str, QLabel] = {}
        self.coh_text: dict[str, QLabel] = {}
        for route, label in (("hilbert", tr("rs.coh.hilbert")), ("rows", tr("rs.coh.rows"))):
            frame = QFrame()
            frame.setObjectName("canvas")
            lay = QVBoxLayout(frame)
            lay.setContentsMargins(16, 12, 16, 14)
            lay.setSpacing(2)
            head = QLabel(label)
            head.setObjectName("sectionTitle")
            value = QLabel("–")
            value.setObjectName("bigValue")
            text = QLabel()
            text.setObjectName("muted")
            lay.addWidget(head)
            lay.addWidget(value)
            lay.addWidget(text)
            self.coh_value[route] = value
            self.coh_text[route] = text
            cards.addWidget(frame)

        self.summary = QLabel()
        self.summary.setObjectName("faint")
        self.summary.setWordWrap(True)
        self.summary.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.summary.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )

        # --- buttons ----------------------------------------------------------
        def btn(text: str, slot, name: str | None = None, icon=None) -> QPushButton:
            b = QPushButton(text)
            if name:
                b.setObjectName(name)
            if icon is not None:
                b.setIcon(icon)
                b.setIconSize(QSize(13, 13))
            b.clicked.connect(slot)
            return b

        buttons = QHBoxLayout()
        buttons.addWidget(btn(tr("btn.play_original"), lambda: self.play(self.grid), icon=icons.play()))
        buttons.addWidget(btn(tr("btn.play_resized"), lambda: self.play(self.resized), icon=icons.play()))
        buttons.addWidget(btn(tr("btn.stop"), self.player.stop, "stop", icons.stop()))
        buttons.addStretch()
        buttons.addWidget(btn(tr("btn.use_resized"), self.use_resized))
        buttons.addWidget(btn(tr("btn.close"), self.reject, "primary"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(controls)
        layout.addWidget(plot_card, 1)
        layout.addLayout(cards)
        layout.addWidget(self.summary)
        layout.addLayout(buttons)

        self.rows_box.valueChanged.connect(self._rows_changed)
        self.cols_box.valueChanged.connect(self._cols_changed)
        self.method_box.currentIndexChanged.connect(self._timer.start)
        self.keep_box.toggled.connect(lambda on: on and self._rows_changed(self.rows_box.value()))
        self.apply_factor(2 if min(n_rows, n_cols) >= 2 else 1)
        self.rows_box.setFocus()

    # --- logic ----------------------------------------------------------------
    def apply_factor(self, factor: int) -> None:
        n_rows, n_cols = self.grid.shape
        self._linking = True
        self.rows_box.setValue(max(1, round(n_rows / factor)))
        self.cols_box.setValue(max(1, round(n_cols / factor)))
        self._linking = False
        self.refresh()

    def _rows_changed(self, value: int) -> None:
        if self.keep_box.isChecked() and not self._linking:
            n_rows, n_cols = self.grid.shape
            self._linking = True
            self.cols_box.setValue(max(1, min(n_cols, round(value * n_cols / n_rows))))
            self._linking = False
        self._timer.start()

    def _cols_changed(self, value: int) -> None:
        if self.keep_box.isChecked() and not self._linking:
            n_rows, n_cols = self.grid.shape
            self._linking = True
            self.rows_box.setValue(max(1, min(n_rows, round(value * n_rows / n_cols))))
            self._linking = False
        self._timer.start()

    def refresh(self) -> None:
        self.resized = resample(self.grid, self.rows_box.value(), self.cols_box.value(),
                                self.method_box.currentData())
        a, b = self.grid.normalized(), self.resized.normalized()
        coh = {route: coherence(a, b, route) for route in ("hilbert", "rows")}
        for route, value in coh.items():
            self.coh_value[route].setText("–" if np.isnan(value) else fixed(value, 2))
            self.coh_text[route].setText(describe_coherence(value))
        (r0, c0), (r1, c1) = self.grid.shape, self.resized.shape
        text = tr("rs.summary", r0=r0, c0=c0, r1=r1, c1=c1,
                  h=fixed(coh["hilbert"], 2), hv=describe_coherence(coh["hilbert"]),
                  w=fixed(coh["rows"], 2), wv=describe_coherence(coh["rows"]))
        self.summary.setText(text)
        self.summary.setAccessibleName(text)
        self._draw(a, b)

    def _draw(self, a: np.ndarray, b: np.ndarray) -> None:
        for ax in (self.ax_orig, self.ax_res, self.ax_th, self.ax_tr):
            ax.clear()
        self.ax_orig.imshow(a, cmap=self.cmap, vmin=0, vmax=1, interpolation="nearest")
        self.ax_orig.set_title(tr("rs.original", rows=a.shape[0], cols=a.shape[1]))
        self.ax_res.imshow(b, cmap=self.cmap, vmin=0, vmax=1, interpolation="nearest")
        self.ax_res.set_title(tr("rs.resized", rows=b.shape[0], cols=b.shape[1]))
        for ax in (self.ax_orig, self.ax_res):
            ax.set_xticks([])
            ax.set_yticks([])
        t = (np.arange(4096) + 0.5) / 4096
        for ax, route, title in ((self.ax_th, "hilbert", tr("rs.track.hilbert")),
                                 (self.ax_tr, "rows", tr("rs.track.rows"))):
            ax.plot(t, listening_track(a, route), color=ORIGINAL_COLOR, lw=1.4, label=tr("rs.legend.original"))
            ax.plot(t, listening_track(b, route), color=RESIZED_COLOR, lw=1.4, label=tr("rs.legend.resized"))
            ax.set_title(title, loc="left")
            ax.set_xlabel(tr("rs.time"))
            ax.set_xlim(0, 1)
            ax.grid(axis="y", color=theme.BORDER, lw=0.8)
            leg = ax.legend(frameon=False, fontsize=8, loc="upper right", ncols=2)
            for txt in leg.get_texts():
                txt.set_color(theme.MUTED)
        self.ax_th.set_ylabel(tr("rs.value"))
        theme.matplotlib_dark(self.fig)
        for ax in (self.ax_th, self.ax_tr):
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
        self.canvas.draw_idle()

    def play(self, grid: Grid) -> None:
        self.player.stop()
        self.player.play(self.make_audio(grid.normalized()))

    def use_resized(self) -> None:
        self.resizedChosen.emit(self.resized)
        self.accept()

    def done(self, result: int) -> None:
        self.player.stop()
        super().done(result)
