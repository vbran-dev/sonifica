"""Sonifica's main window."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PySide6.QtCore import QElapsedTimer, QLocale, QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from sonifica import __version__, i18n, palettes
from sonifica.analysis import MAX_SEQUENCE_CELLS, run_round_trip
from sonifica.audio import Player, save_wav
from sonifica.data import Grid, load
from sonifica.examples import EXAMPLES, build, label
from sonifica.hilbert import order_for, path_for, quadrant_name
from sonifica.i18n import tr
from sonifica.mapping import SCALES, SoundMapping
from sonifica.synth import (
    SAMPLE_RATE,
    cell_sound,
    edge_sound,
    render_cells,
    render_hilbert,
    render_sequence,
    render_spectral,
    step_samples,
)
from sonifica.ui import icons
from sonifica.ui.heatmap_widget import HeatmapWidget
from sonifica.ui.resize_dialog import ResizeDialog
from sonifica.ui.roundtrip_dialog import RoundTripDialog

MAX_ROWS_PLAYBACK_S = 180  # max 3 minutes
DISPLAY_PATH_MAX_ORDER = 6  
NOISE_LEVELS = (None, 30.0, 20.0, 10.0, 5.0, 0.0)
DEFAULTS = {
    "palette": palettes.DEFAULT, "reverse": False, "route": "hilbert", "total": 8.0, "note": 0.12,
    "scale": "continuous", "fmin": 220, "fmax": 880, "noise": 0, "markers": True, "path": False,
    "rich": False, "hover": True, "voice": "enter",
}


def settings_store() -> QSettings:
    return QSettings("Sonifica", "Sonifica")


def fmt_number(v: float) -> str:
    return tr("missing") if np.isnan(v) else i18n.number(v)


def section(title: str) -> tuple[QWidget, QVBoxLayout]:
    """Lateral panel section."""
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(20, 16, 20, 18)
    layout.setSpacing(10)
    lab = QLabel(title)
    lab.setObjectName("sectionTitle")
    layout.addWidget(lab)
    return w, layout


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    return line


def muted_label(text: str, buddy: QWidget | None = None) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("muted")
    if buddy is not None:
        lab.setBuddy(buddy)
    return lab

def button(text: str, slot, name: str | None = None, tip: str | None = None, icon=None) -> QPushButton:
    b = QPushButton(text)
    if name:
        b.setObjectName(name)
    if tip:
        b.setToolTip(tip)
    if icon is not None:
        b.setIcon(icon)
        b.setIconSize(QSize(14, 14))
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.clicked.connect(slot)
    return b




class MainWindow(QMainWindow):
    def __init__(self, path: str | None = None) -> None:
        super().__init__()
        self.setWindowIcon(icons.app_icon())
        self.resize(1260, 820)
        self.setMinimumSize(960, 640)
        self.player = Player(SAMPLE_RATE)
        self.grid: Grid | None = None
        self.norm: np.ndarray | None = None
        self.tts = self._init_tts()
        self._anim = QTimer(self)
        self._anim.setInterval(33)
        self._anim.timeout.connect(self._tick_playhead)
        self._clock = QElapsedTimer()
        self._anim_duration = 0.0
        self._anim_quadrant = 0

        self._build_ui()
        self._restore(self._load_settings())
        if not self.player.available:
            self.statusBar().showMessage(tr("audio.unavailable", err=self.player.error or tr("audio.no_device")))
        try:
            self.set_grid(load(path) if path else build("temperature"))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("err.title"), tr("err.open_file", err=exc))
            self.set_grid(build("temperature"))
        self.heatmap.setFocus()

# --- UI construction (repeated whenever the language changes) ------------------
    def _build_ui(self) -> None:
        self.heatmap = HeatmapWidget()
        central = QWidget()
        central.setObjectName("central")
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_header())
        body = QHBoxLayout()
        body.setContentsMargins(16, 16, 16, 8)
        body.setSpacing(16)
        body.addWidget(self._build_canvas(), 1)
        body.addWidget(self._build_side_panel(), 0)
        outer.addLayout(body, 1)
        self.setCentralWidget(central)
        self.menuBar().clear()
        self._build_menu()

        hm = self.heatmap
        hm.cellChanged.connect(self.on_cell_changed)
        hm.edgeHit.connect(lambda: self.player.play(edge_sound()))
        hm.playRowRequested.connect(self.play_row)
        hm.playColumnRequested.connect(self.play_column)
        hm.announceRequested.connect(lambda: self.speak(self.describe_cell(hm.row, hm.col), force=True))
        hm.summaryRequested.connect(lambda: self.speak(self.summary(), force=True))
        hm.stopRequested.connect(self.stop_all)
        self.palette_box.currentIndexChanged.connect(self.on_palette_changed)
        self.reverse_box.toggled.connect(self.on_palette_changed)
        self.route_box.currentIndexChanged.connect(self._sync_route_controls)
        self.path_box.toggled.connect(self.heatmap.set_show_path)
        self.hover_box.toggled.connect(lambda on: setattr(self.heatmap, "hover_play", on))
        for w in (self.fmin_box, self.fmax_box):
            w.valueChanged.connect(self._check_range)
        self.language_box.currentIndexChanged.connect(
            lambda: self.set_language(self.language_box.currentData())
        )
        self._apply_tts_locale()

    def _examples_menu(self, parent: QWidget) -> QMenu:
        menu = QMenu(tr("menu.examples"), parent)
        for key in EXAMPLES:
            act = menu.addAction(label(key))
            act.triggered.connect(lambda _=False, k=key: self.set_grid(build(k)))
        return menu

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(icons.logo_pixmap(24))
        wordmark = QLabel("Sonifica")
        wordmark.setObjectName("wordmark")
        version = QLabel(f"v{__version__}")
        version.setObjectName("versionTag")
        version.setAccessibleName(tr("version.tag", version=__version__))
        slash = QLabel("/")
        slash.setObjectName("faint")
        self.dataset_name = QLabel()
        self.dataset_name.setObjectName("datasetName")
        lay.addWidget(logo)
        lay.addWidget(wordmark)
        lay.addWidget(version, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addSpacing(6)
        lay.addWidget(slash)
        lay.addSpacing(2)
        lay.addWidget(self.dataset_name)
        lay.addStretch()
        self.examples_button = button(tr("btn.examples"), lambda: None, "quiet", "Ctrl+E")
        self.examples_button.setMenu(self._examples_menu(self.examples_button))
        lay.addWidget(self.examples_button)
        lay.addWidget(button(tr("btn.compare"), self.open_resize, "quiet", "Ctrl+D"))
        lay.addWidget(button(tr("btn.open"), self.open_file, "primary", "Ctrl+O", icons.folder()))
        return header

    def _build_canvas(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("canvas")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(20, 18, 20, 14)
        lay.setSpacing(6)
        self.canvas_title = QLabel()
        self.canvas_title.setObjectName("heading")
        self.canvas_subtitle = QLabel()
        self.canvas_subtitle.setObjectName("muted")
        lay.addWidget(self.canvas_title)
        lay.addWidget(self.canvas_subtitle)
        lay.addSpacing(6)
        lay.addWidget(self.heatmap, 1)
        return frame

    def _build_side_panel(self) -> QFrame:
        panel = QWidget()
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # current cell
        cell, cl = section(tr("sec.cell"))
        self.cell_value = QLabel("–")
        self.cell_value.setObjectName("bigValue")
        self.cell_place = QLabel()
        self.cell_place.setObjectName("muted")
        self.cell_place.setWordWrap(True)
        cl.setSpacing(2)
        cl.addSpacing(4)
        cl.addWidget(self.cell_value)
        cl.addWidget(self.cell_place)
        stats = QGridLayout()
        stats.setContentsMargins(0, 14, 0, 0)
        stats.setHorizontalSpacing(18)
        stats.setVerticalSpacing(0)
        self.stats: dict[str, QLabel] = {}
        for i, key in enumerate(("min", "max", "missing")):
            val = QLabel("–")
            val.setObjectName("statValue")
            lab = QLabel(tr(f"stat.{key}"))
            lab.setObjectName("faint")
            stats.addWidget(val, 0, i)
            stats.addWidget(lab, 1, i)
            self.stats[key] = val
        cl.addLayout(stats)
        v.addWidget(cell)
        v.addWidget(divider())

        # palette
        pal, pl = section(tr("sec.palette"))
        self.palette_box = QComboBox()
        for p in palettes.PALETTES:
            self.palette_box.addItem(p.name, p.key)
        self.palette_box.setAccessibleName(tr("pal.accessible"))
        self.palette_desc = QLabel()
        self.palette_desc.setObjectName("faint")
        self.palette_desc.setWordWrap(True)
        self.reverse_box = QCheckBox(tr("pal.reverse"))
        pl.addWidget(self.palette_box)
        pl.addWidget(self.palette_desc)
        pl.addWidget(self.reverse_box)
        v.addWidget(pal)
        v.addWidget(divider())

        # listening
        listen, ll = section(tr("sec.listen"))
        seg = QFrame()
        seg.setObjectName("segmented")
        sl = QHBoxLayout(seg)
        sl.setContentsMargins(3, 3, 3, 3)
        sl.setSpacing(2)
        play = icons.play()
        sl.addWidget(button(tr("btn.row"), self.play_row, tip="Spazio / Space", icon=play))
        sl.addWidget(button(tr("btn.col"), self.play_column, tip="C", icon=play))
        sl.addWidget(button(tr("btn.all"), self.play_all, tip="Ctrl+P", icon=play))
        ll.addWidget(seg)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(button(tr("btn.spectrum"), self.play_spectral, tip="Ctrl+Shift+P", icon=icons.spectrum()), 1)
        row.addWidget(button(tr("btn.stop"), self.stop_all, "stop", "Esc", icons.stop()), 0)
        ll.addLayout(row)
        ll.addWidget(button(tr("btn.compare"), self.open_resize, tip="Ctrl+D", icon=icons.compare()))
        ll.addWidget(button(tr("btn.roundtrip"), self.open_round_trip, tip="Ctrl+R", icon=icons.compare()))
        v.addWidget(listen)
        v.addWidget(divider())

        # sound
        sound, snd = section(tr("sec.sound"))
        self.route_box = QComboBox()
        self.route_box.addItem(tr("route.hilbert"), "hilbert")
        self.route_box.addItem(tr("route.rows"), "rows")
        self.route_box.setToolTip(tr("route.tip"))
        self.total_box = QDoubleSpinBox()
        self.total_box.setRange(2.0, 60.0)
        self.total_box.setSingleStep(1.0)
        self.total_box.setSuffix(" s")
        self.total_box.setToolTip(tr("total.tip"))
        self.dur_box = QDoubleSpinBox()
        self.dur_box.setRange(0.04, 1.0)
        self.dur_box.setSingleStep(0.02)
        self.dur_box.setSuffix(" s")
        self.scale_box = QComboBox()
        for key in SCALES:
            self.scale_box.addItem(tr(f"scale.{key}"), key)
        self.fmin_box = QSpinBox()
        self.fmin_box.setRange(50, 4000)
        self.fmin_box.setSuffix(" Hz")
        self.fmax_box = QSpinBox()
        self.fmax_box.setRange(100, 8000)
        self.fmax_box.setSuffix(" Hz")
        self.noise_box = QComboBox()
        for level in NOISE_LEVELS:
            self.noise_box.addItem(tr("noise.none") if level is None else f"{level:g} dB", level)
        self.noise_box.setToolTip(tr("noise.tip"))
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        for key, w in (("f.route", self.route_box), ("f.total", self.total_box), ("f.note", self.dur_box),
                       ("f.scale", self.scale_box), ("f.from", self.fmin_box), ("f.to", self.fmax_box),
                       ("f.noise", self.noise_box)):
            form.addRow(muted_label(tr(key), w), w)
            w.setAccessibleName(tr(key))
        self.markers_box = QCheckBox(tr("chk.markers"))
        self.path_box = QCheckBox(tr("chk.path"))
        self.rich_box = QCheckBox(tr("chk.rich"))
        snd.addLayout(form)
        snd.addWidget(self.markers_box)
        snd.addWidget(self.path_box)
        snd.addWidget(self.rich_box)
        v.addWidget(sound)
        v.addWidget(divider())

        # accessibility and language
        access, al = section(tr("sec.access"))
        self.hover_box = QCheckBox(tr("chk.hover"))
        self.voice_box = QComboBox()
        for key in ("enter", "move", "never"):
            self.voice_box.addItem(tr(f"voice.{key}"), key)
        self.voice_box.setAccessibleName(tr("f.voice"))
        if self.tts is None:
            self.voice_box.setEnabled(False)
            self.voice_box.setToolTip(tr("voice.unavailable"))
        self.language_box = QComboBox()
        for code, name in i18n.LANGUAGES.items():
            self.language_box.addItem(name, code)
        self.language_box.setCurrentIndex(self.language_box.findData(i18n.language()))
        self.language_box.setAccessibleName("Lingua / Language")
        form2 = QFormLayout()
        form2.setSpacing(8)
        form2.addRow(muted_label(tr("f.voice"), self.voice_box), self.voice_box)
        form2.addRow(muted_label(tr("f.language"), self.language_box), self.language_box)
        al.addWidget(self.hover_box)
        al.addLayout(form2)
        v.addWidget(access)
        v.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        frame = QFrame()
        frame.setObjectName("sidebar")
        frame.setFixedWidth(340)
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.addWidget(scroll)
        return frame

    def _build_menu(self) -> None:
        def action(menu, text, shortcut, slot):
            a = QAction(text, self)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            a.triggered.connect(slot)
            menu.addAction(a)
            return a

        bar = self.menuBar()
        file_menu = bar.addMenu(tr("menu.file"))
        action(file_menu, tr("menu.open"), "Ctrl+O", self.open_file)
        file_menu.addMenu(self._examples_menu(file_menu))
        action(file_menu, tr("menu.export"), "Ctrl+S", self.export_wav)
        file_menu.addSeparator()
        action(file_menu, tr("menu.quit"), "Ctrl+Q", self.close)

        listen_menu = bar.addMenu(tr("menu.listen"))
        action(listen_menu, tr("menu.play_all"), "Ctrl+P", self.play_all)
        action(listen_menu, tr("menu.spectrum"), "Ctrl+Shift+P", self.play_spectral)
        action(listen_menu, tr("menu.stop"), None, self.stop_all)
        action(listen_menu, tr("menu.path"), "Ctrl+H", self.path_box.toggle)
        listen_menu.addSeparator()
        action(listen_menu, tr("menu.resize"), "Ctrl+D", self.open_resize)
        action(listen_menu, tr("menu.roundtrip"), "Ctrl+R", self.open_round_trip)
        action(listen_menu, tr("menu.focus"), "F6", self.heatmap.setFocus)

        lang_menu = bar.addMenu("Lingua / Language")
        group = QActionGroup(self)
        for code, name in i18n.LANGUAGES.items():
            act = lang_menu.addAction(name)
            act.setCheckable(True)
            act.setChecked(code == i18n.language())
            act.triggered.connect(lambda _=False, c=code: self.set_language(c))
            group.addAction(act)
        action(lang_menu, "Italiano ⇄ English", "Ctrl+L", self.toggle_language)

        help_menu = bar.addMenu(tr("menu.help"))
        action(help_menu, tr("menu.shortcuts"), "F1", self.show_help)
        action(help_menu, tr("menu.about"), None, self.show_about)

        examples = QAction(self)
        examples.setShortcut(QKeySequence("Ctrl+E"))
        examples.triggered.connect(self.examples_button.showMenu)
        self.addAction(examples)

    def _init_tts(self):
        try:
            from PySide6.QtTextToSpeech import QTextToSpeech

            tts = QTextToSpeech(self)
            if tts.state() == QTextToSpeech.State.Error:
                return None
            return tts
        except Exception:  # noqa: BLE001
            return None

    def _apply_tts_locale(self) -> None:
        if self.tts is None:
            return
        want = QLocale.Language.Italian if i18n.language() == "it" else QLocale.Language.English
        for loc in self.tts.availableLocales():
            if loc.language() == want:
                self.tts.setLocale(loc)
                break

    # --- configurations -----------------------------------------------------
    def _snapshot(self) -> dict:
        return {
            "palette": self.palette_box.currentData(), "reverse": self.reverse_box.isChecked(),
            "route": self.route_box.currentData(), "total": self.total_box.value(),
            "note": self.dur_box.value(), "scale": self.scale_box.currentData(),
            "fmin": self.fmin_box.value(), "fmax": self.fmax_box.value(),
            "noise": self.noise_box.currentIndex(), "markers": self.markers_box.isChecked(),
            "path": self.path_box.isChecked(), "rich": self.rich_box.isChecked(),
            "hover": self.hover_box.isChecked(), "voice": self.voice_box.currentData(),
        }

    def _restore(self, snap: dict) -> None:
        s = {**DEFAULTS, **snap}

        def select(box: QComboBox, data) -> None:
            idx = box.findData(data)
            box.setCurrentIndex(max(idx, 0))

        select(self.palette_box, s["palette"])
        self.reverse_box.setChecked(bool(s["reverse"]))
        select(self.route_box, s["route"])
        self.total_box.setValue(float(s["total"]))
        self.dur_box.setValue(float(s["note"]))
        select(self.scale_box, s["scale"])
        self.fmin_box.setValue(int(s["fmin"]))
        self.fmax_box.setValue(int(s["fmax"]))
        self.noise_box.setCurrentIndex(int(s["noise"]) if 0 <= int(s["noise"]) < len(NOISE_LEVELS) else 0)
        self.markers_box.setChecked(bool(s["markers"]))
        self.path_box.setChecked(bool(s["path"]))
        self.rich_box.setChecked(bool(s["rich"]))
        self.hover_box.setChecked(bool(s["hover"]))
        select(self.voice_box, s["voice"])
        self.heatmap.hover_play = self.hover_box.isChecked()
        self.heatmap.set_show_path(self.path_box.isChecked())
        self._sync_route_controls()
        self.on_palette_changed(announce=False)

    def _load_settings(self) -> dict:
        try:
            return json.loads(str(settings_store().value("settings", "{}")))
        except (ValueError, TypeError):
            return {}

    def _save_settings(self) -> None:
        store = settings_store()
        store.setValue("settings", json.dumps(self._snapshot()))
        store.setValue("language", i18n.language())

    # --- language -----------------------------------------------------------
    def set_language(self, lang: str) -> None:
        if lang == i18n.language():
            return
        snap = self._snapshot()
        cell = (self.heatmap.row, self.heatmap.col)
        self.stop_all()
        i18n.set_language(lang)
        old = self.centralWidget()
        self._build_ui()
        old.deleteLater()
        self._restore(snap)
        grid = self.grid
        if grid is not None:
            self.set_grid(build(grid.example) if grid.example else grid, cell=cell, announce=False)
        self._save_settings()
        self.speak(tr("lang.changed"), force=True)
        self.heatmap.setFocus()

    def toggle_language(self) -> None:
        self.set_language("en" if i18n.language() == "it" else "it")

    # --- state ------------------------------------------------------------
    @property
    def mapping(self) -> SoundMapping:
        f_min, f_max = self.fmin_box.value(), self.fmax_box.value()
        if f_max <= f_min:
            f_max = f_min * 2
        return SoundMapping(f_min=f_min, f_max=f_max, scale=self.scale_box.currentData())

    @property
    def note_dur(self) -> float:
        return self.dur_box.value()

    @property
    def harmonics(self) -> float:
        return 1.0 if self.rich_box.isChecked() else 0.0

    @property
    def route(self) -> str:
        return self.route_box.currentData()

    @property
    def cmap(self):
        return palettes.get_cmap(self.palette_box.currentData(), self.reverse_box.isChecked())

    def _sync_route_controls(self) -> None:
        hilbert_on = self.route == "hilbert"
        self.total_box.setEnabled(hilbert_on)
        self.markers_box.setEnabled(hilbert_on)
        self.dur_box.setEnabled(not hilbert_on)

    def on_palette_changed(self, *_args, announce: bool = True) -> None:
        pal = palettes.BY_KEY[self.palette_box.currentData()]
        self.palette_desc.setText(pal.description)
        self.heatmap.set_colormap(self.cmap)
        if announce and self.grid is not None:
            self.speak(tr("pal.spoken", name=pal.name, desc=pal.description), force=True)

    def _check_range(self) -> None:
        if self.fmax_box.value() <= self.fmin_box.value():
            self.statusBar().showMessage(tr("err.range"))

    def set_grid(self, grid: Grid, cell: tuple[int, int] = (0, 0), announce: bool = True) -> None:
        self.stop_all()
        self.grid = grid
        self.norm = grid.normalized()
        shape = self.norm.shape
        display = path_for(shape, min(order_for(shape), DISPLAY_PATH_MAX_ORDER))
        value_range = (fmt_number(grid.vmin), fmt_number(grid.vmax))
        self.heatmap.set_data(self.norm, grid.row_labels, grid.col_labels, value_range, self.cmap,
                              (display.x, display.y))
        self.setWindowTitle(tr("win.title", version=__version__, name=grid.name))
        self.dataset_name.setText(grid.name)
        self.canvas_title.setText(grid.name)
        self.canvas_subtitle.setText(tr("canvas.subtitle", rows=shape[0], cols=shape[1]))
        self.stats["min"].setText(fmt_number(grid.vmin))
        self.stats["max"].setText(fmt_number(grid.vmax))
        self.stats["missing"].setText(str(grid.n_missing))
        r, c = min(cell[0], shape[0] - 1), min(cell[1], shape[1] - 1)
        self.heatmap.row, self.heatmap.col = r, c
        self.on_cell_changed(r, c, play=False)
        if announce:
            self.speak(self.summary(), force=True)

    def describe_cell(self, r: int, c: int) -> str:
        g = self.grid
        assert g is not None and self.norm is not None
        v = g.values[r, c]
        text = f"{g.place(r, c)}: {fmt_number(v)}"
        if not np.isnan(v):
            text += f" ({tr('pct', pct=round(self.norm[r, c] * 100))})"
        return text

    def summary(self) -> str:
        g = self.grid
        if g is None:
            return ""
        (r0, c0), (r1, c1) = g.argmin(), g.argmax()
        text = tr("summary", name=g.name, rows=g.shape[0], cols=g.shape[1], vmin=fmt_number(g.vmin),
                  pmin=g.place(r0, c0), vmax=fmt_number(g.vmax), pmax=g.place(r1, c1))
        if g.n_missing:
            text += tr("summary.missing", n=g.n_missing)
        return text

    def speak(self, text: str, force: bool = False) -> None:
        self.statusBar().showMessage(text)
        mode = self.voice_box.currentData()
        if self.tts is None or mode == "never" or (mode == "enter" and not force):
            return
        self.tts.stop()
        self.tts.say(text)

    # --- actions -----------------------------------------------------------
    def on_cell_changed(self, r: int, c: int, play: bool = True) -> None:
        if self.grid is None or self.norm is None:
            return
        g = self.grid
        v = g.values[r, c]
        self.cell_value.setText(fmt_number(v))
        pct = "" if np.isnan(v) else f" · {tr('pct', pct=round(self.norm[r, c] * 100))}"
        self.cell_place.setText(f"{g.place(r, c)}{pct}")
        text = self.describe_cell(r, c)
        self.heatmap.announce(text)
        if play:
            self.player.play(cell_sound(self.norm[r, c], c, g.shape[1], self.mapping,
                                        self.note_dur * 1.5, harmonics=self.harmonics))
            if self.voice_box.currentData() == "move":
                self.speak(text)

    def play_row(self) -> None:
        if self.norm is None:
            return
        self.stop_all()
        r = self.heatmap.row
        cells = [(self.norm[r, c], c) for c in range(self.norm.shape[1])]
        self.player.play(render_cells(cells, self.norm.shape[1], self.mapping, self.note_dur, harmonics=self.harmonics))

    def play_column(self) -> None:
        if self.norm is None:
            return
        self.stop_all()
        c = self.heatmap.col
        cells = [(self.norm[r, c], c) for r in range(self.norm.shape[0])]
        self.player.play(render_cells(cells, self.norm.shape[1], self.mapping, self.note_dur, harmonics=self.harmonics))

    def hilbert_audio(self, norm: np.ndarray) -> np.ndarray:
        return render_hilbert(norm, self.mapping, self.total_box.value(), harmonics=self.harmonics,
                              markers=self.markers_box.isChecked())

    def _rows_too_long(self) -> bool:
        seconds = self.norm.size * step_samples(self.note_dur, 0.03, SAMPLE_RATE) / SAMPLE_RATE
        if seconds <= MAX_ROWS_PLAYBACK_S:
            return False
        QMessageBox.information(self, tr("rows.too_long.title"), tr("rows.too_long", minutes=round(seconds / 60)))
        return True

    def play_all(self) -> None:
        if self.norm is None:
            return
        self.stop_all()
        if self.route == "hilbert":
            self.player.play(self.hilbert_audio(self.norm))
            self._anim_duration = self.total_box.value()
            self._anim_quadrant = 0
            self._clock.start()
            self._anim.start()
            self._tick_playhead()
        elif not self._rows_too_long():
            self.player.play(render_sequence(self.norm, self.mapping, "rows", self.note_dur,
                                             harmonics=self.harmonics))

    def _tick_playhead(self) -> None:
        t = self._clock.elapsed() / 1000.0 / max(self._anim_duration, 1e-6)
        if t >= 1.0:
            self._anim.stop()
            self.heatmap.set_playhead(None)
            self.statusBar().showMessage(tr("play.end"), 3000)
            return
        self.heatmap.set_playhead(t)
        q = min(3, int(t * 4)) + 1
        if q != self._anim_quadrant:
            self._anim_quadrant = q
            self.statusBar().showMessage(tr("play.quadrant", q=q, name=quadrant_name(q)))

    def stop_all(self) -> None:
        self.player.stop()
        self._anim.stop()
        if hasattr(self, "heatmap"):
            self.heatmap.set_playhead(None)

    def play_spectral(self) -> None:
        if self.norm is not None:
            self.stop_all()
            self.player.play(render_spectral(self.norm))

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("open.title"), str(Path.home()),
            f"{tr('open.filter')} (*.csv *.tsv *.txt *.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp);;"
            f"{tr('open.all')} (*)",
        )
        if not path:
            return
        try:
            self.set_grid(load(path))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("err.title"), tr("err.open_file", err=exc))
        self.heatmap.setFocus()

    def export_wav(self) -> None:
        if self.norm is None or self.grid is None:
            return
        options = [tr("route.hilbert"), tr("route.rows"), tr("export.spectrum")]
        mode, ok = QInputDialog.getItem(self, tr("export.title"), tr("export.label"), options, 0, False)
        if not ok:
            return
        if mode == options[1] and self._rows_too_long():
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("export.save"), f"{self.grid.name}.wav", tr("export.filter"))
        if not path:
            return
        if mode == options[0]:
            audio = self.hilbert_audio(self.norm)
        elif mode == options[1]:
            audio = render_sequence(self.norm, self.mapping, "rows", self.note_dur, harmonics=self.harmonics)
        else:
            audio = render_spectral(self.norm)
        save_wav(path, audio)
        self.statusBar().showMessage(tr("export.saved", path=path))

    def open_round_trip(self) -> None:
        if self.norm is None:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            results = run_round_trip(self.norm, self.mapping, self.note_dur, snr_db=self.noise_box.currentData(),
                                     hilbert_duration=self.total_box.value())
        finally:
            QApplication.restoreOverrideCursor()
        self.stop_all()
        note = tr("rt.skipped", cells=self.norm.size) if self.norm.size > MAX_SEQUENCE_CELLS else None
        RoundTripDialog(self.norm, results, self.player, self.cmap, self, note=note).exec()
        self.heatmap.setFocus()

    def open_resize(self) -> None:
        if self.grid is None:
            return
        self.stop_all()
        dlg = ResizeDialog(self.grid, self.cmap, self.player, self.hilbert_audio, self)
        dlg.resizedChosen.connect(self.set_grid)
        dlg.exec()
        self.heatmap.setFocus()

    def show_help(self) -> None:
        QMessageBox.information(self, tr("help.title"), tr("help.text"))

    def show_about(self) -> None:
        QMessageBox.about(self, tr("about.title"), tr("about.text", version=__version__))

    def closeEvent(self, event) -> None:
        self.stop_all()
        self._save_settings()
        super().closeEvent(event)
