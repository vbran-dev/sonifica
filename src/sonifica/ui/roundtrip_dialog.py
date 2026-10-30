"""Analysis window: comparison between the original heatmap and the one reconstructed from audio."""

from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from sonifica import palettes
from sonifica.analysis import RoundTrip, describe_metrics
from sonifica.audio import Player
from sonifica.i18n import fixed, tr
from sonifica.ui import icons, theme


def _fmt(x: float) -> str:
    return "–" if np.isnan(x) else fixed(x)


class RoundTripDialog(QDialog):
    def __init__(self, norm: np.ndarray, results: list[RoundTrip], player: Player, cmap=None, parent=None,
                 note: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("rtw.window"))
        self.resize(1280, 880)
        self.player = player

        title = QLabel(tr("rtw.title"))
        title.setObjectName("heading")
        subtitle = QLabel(tr("rtw.subtitle"))
        subtitle.setObjectName("muted")

        cmap = cmap if cmap is not None else palettes.get_cmap(palettes.DEFAULT)
        fig = Figure(figsize=(12, 2.4 * len(results)), layout="constrained")
        axes = fig.subplots(len(results), 4)
        for row, res in zip(axes, results, strict=True):
            ax_o, ax_s, ax_r, ax_e = row
            ax_o.imshow(norm, cmap=cmap, vmin=0, vmax=1, aspect="auto")
            ax_o.set_title(tr("rtw.original"))
            f, t, s_db = res.spectrogram
            lo, hi = res.band
            band = (f >= lo) & (f <= hi)
            ax_s.imshow(s_db[band], origin="lower", aspect="auto", cmap="magma",
                        extent=(t[0], t[-1], f[band][0], f[band][-1]))
            ax_s.set_title(tr("rtw.spectrogram", mode=tr(f"mode.{res.mode}")))
            ax_s.set_xlabel(tr("rtw.time"))
            ax_s.set_ylabel("Hz")
            ax_r.imshow(res.reconstructed, cmap=cmap, vmin=0, vmax=1, aspect="auto")
            ax_r.set_title(tr("rtw.reconstructed"))
            err = np.abs(norm - res.reconstructed)
            vmax = max(0.05, float(np.nanmax(err)))
            im = ax_e.imshow(err, cmap=theme.ERROR_CMAP_NAME, vmin=0, vmax=vmax, aspect="auto")
            ax_e.set_title(tr("rtw.error"))
            cb = fig.colorbar(im, ax=ax_e)
            cb.ax.tick_params(colors=theme.MUTED, labelsize=8)
            cb.outline.set_edgecolor(theme.BORDER)
            for ax in (ax_o, ax_r, ax_e):
                ax.set_xticks([])
                ax.set_yticks([])
        theme.matplotlib_dark(fig)

        canvas = FigureCanvasQTAgg(fig)
        canvas.setAccessibleName(tr("rtw.plots"))
        canvas.setAccessibleDescription(tr("rtw.plots.desc"))
        plot_card = QFrame()
        plot_card.setObjectName("canvas")
        pl = QVBoxLayout(plot_card)
        pl.setContentsMargins(10, 10, 10, 10)
        pl.addWidget(canvas)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.summary_labels: list[QLabel] = []
        for res in results:
            cards.addWidget(self._result_card(res))

        buttons = QHBoxLayout()
        stop = QPushButton(tr("btn.stop"))
        stop.setObjectName("stop")
        stop.setIcon(icons.stop())
        stop.setIconSize(QSize(13, 13))
        stop.clicked.connect(self.player.stop)
        close = QPushButton(tr("btn.close"))
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        buttons.addWidget(stop)
        buttons.addStretch()
        buttons.addWidget(close)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(plot_card, 1)
        layout.addLayout(cards)
        if note:
            note_label = QLabel(note)
            note_label.setObjectName("muted")
            note_label.setWordWrap(True)
            layout.addWidget(note_label)
        layout.addLayout(buttons)
        self.summary_labels[0].setFocus()

    def _result_card(self, res: RoundTrip) -> QFrame:
        frame = QFrame()
        frame.setObjectName("canvas")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 14, 16, 16)
        head = QHBoxLayout()
        name = QLabel(res.title)
        name.setObjectName("sectionTitle")
        play = QPushButton(tr("btn.listen"))
        play.setIcon(icons.play())
        play.setIconSize(QSize(13, 13))
        play.clicked.connect(lambda _=False, a=res.audio: self.player.play(a))
        head.addWidget(name)
        head.addStretch()
        head.addWidget(play)
        lay.addLayout(head)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        metrics = ((tr("m.corr"), "correlation"), (tr("m.mean"), "mean_error"), (tr("m.max"), "max_error"))
        for i, (label, key) in enumerate(metrics):
            v = QLabel(_fmt(res.metrics[key]))
            v.setObjectName("heading")
            lab = QLabel(label)
            lab.setObjectName("faint")
            grid.addWidget(v, 0, i)
            grid.addWidget(lab, 1, i)
        lay.addLayout(grid)

        desc = describe_metrics(res.metrics)
        text = QLabel(desc[:1].upper() + desc[1:])
        text.setWordWrap(True)
        text.setObjectName("muted")
        text.setAccessibleName(tr("rtw.results", mode=tr(f"mode.{res.mode}")))
        text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        text.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.summary_labels.append(text)
        lay.addWidget(text)
        return frame

    def done(self, result: int) -> None:
        self.player.stop()
        super().done(result)
