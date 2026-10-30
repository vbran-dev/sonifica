"""Sonifica's Theme"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

# The heatmap palettes are in sonifica.palettes. Only interface colors are defined here.
ERROR_CMAP_NAME = "inferno"

# --- interface colors ----------------------------------------------
BG = "#0c0a10"
SURFACE = "#14111a"
SURFACE_2 = "#1c1824"
SURFACE_3 = "#28222f"
BORDER = "#26202e"
TEXT = "#f1ecf7"
MUTED = "#a59cb2"
FAINT = "#6f6679"
ACCENT = "#f17fa8"
ACCENT_HOVER = "#f59cbd"
ACCENT_TEXT = "#1b0f2e"
LILAC = "#c9a7ff"  # focus from keyboard
DANGER = "#ff8095"

STYLESHEET = f"""
* {{ color: {TEXT}; font-size: 10pt; }}
QMainWindow, QDialog, QWidget#central {{ background: {BG}; }}

QFrame#header {{ background: {BG}; border-bottom: 1px solid {BORDER}; }}
QLabel#wordmark {{ font-size: 14pt; font-weight: 650; }}
QLabel#versionTag {{
    color: {MUTED};
    font-size: 8.5pt;
    font-weight: 600;
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 1px 7px;
}}
QLabel#datasetName {{ color: {MUTED}; }}

QFrame#canvas {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#sidebar {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#divider {{ background: {BORDER}; max-height: 1px; min-height: 1px; border: none; }}

QLabel#sectionTitle {{ color: {MUTED}; font-size: 9.5pt; font-weight: 600; }}
QLabel#heading {{ font-size: 18pt; font-weight: 650; }}
QLabel#bigValue {{ font-size: 30pt; font-weight: 600; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#faint {{ color: {FAINT}; font-size: 9pt; }}
QLabel#statValue {{ font-size: 11pt; font-weight: 600; }}

QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: {SURFACE_3}; border-radius: 3px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

QPushButton {{
    background: transparent;
    border: 1px solid {SURFACE_3};
    border-radius: 8px;
    padding: 7px 12px;
    min-height: 18px;
}}
QPushButton:hover {{ background: {SURFACE_2}; }}
QPushButton:pressed {{ background: {SURFACE_3}; }}
QPushButton:focus {{ border: 2px solid {LILAC}; padding: 6px 11px; }}
QPushButton#primary {{ background: {ACCENT}; color: {ACCENT_TEXT}; border: none; font-weight: 600; }}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:focus {{ border: 2px solid {LILAC}; }}
QPushButton#quiet {{ border: none; color: {MUTED}; }}
QPushButton#quiet:hover {{ color: {TEXT}; background: {SURFACE_2}; }}
QPushButton#stop {{ border: none; color: {DANGER}; }}
QPushButton#stop:hover {{ background: #2a1620; }}

QFrame#segmented {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 9px; }}
QFrame#segmented QPushButton {{ border: none; border-radius: 6px; padding: 7px 6px; }}
QFrame#segmented QPushButton:hover {{ background: {SURFACE_3}; }}
QFrame#segmented QPushButton:focus {{ border: 2px solid {LILAC}; padding: 5px 4px; }}

QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 5px 8px;
    min-height: 18px;
}}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: {SURFACE_3}; }}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 2px solid {LILAC}; padding: 4px 7px; }}
QComboBox:disabled {{ color: {FAINT}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    selection-background-color: {SURFACE_3};
    selection-color: {TEXT};
    outline: none;
    padding: 4px;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 16px; border: none; background: transparent; }}

QCheckBox {{ spacing: 9px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px; border: 1px solid {SURFACE_3}; background: {BG};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QCheckBox:focus {{ color: {LILAC}; }}

QMenuBar {{ background: {BG}; padding: 2px 8px; }}
QMenuBar::item {{ padding: 4px 9px; border-radius: 6px; background: transparent; color: {MUTED}; }}
QMenuBar::item:selected {{ background: {SURFACE_2}; color: {TEXT}; }}
QMenu {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 6px 28px 6px 12px; border-radius: 5px; }}
QMenu::item:selected {{ background: {SURFACE_3}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 6px; }}
QStatusBar {{ background: {BG}; color: {MUTED}; padding-left: 10px; }}
QStatusBar::item {{ border: none; }}
QToolTip {{ background: {SURFACE_3}; color: {TEXT}; border: none; padding: 5px 8px; }}
"""


def apply_dark_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: BG,
        QPalette.ColorRole.WindowText: TEXT,
        QPalette.ColorRole.Base: BG,
        QPalette.ColorRole.AlternateBase: SURFACE,
        QPalette.ColorRole.Text: TEXT,
        QPalette.ColorRole.Button: SURFACE_2,
        QPalette.ColorRole.ButtonText: TEXT,
        QPalette.ColorRole.Highlight: ACCENT,
        QPalette.ColorRole.HighlightedText: ACCENT_TEXT,
        QPalette.ColorRole.ToolTipBase: SURFACE_3,
        QPalette.ColorRole.ToolTipText: TEXT,
        QPalette.ColorRole.PlaceholderText: FAINT,
        QPalette.ColorRole.Link: ACCENT,
    }
    for role, color in roles.items():
        pal.setColor(role, QColor(color))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(FAINT))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(FAINT))
    app.setPalette(pal)
    font = QFont(app.font())
    font.setFamilies(["Inter", "Segoe UI Variable", "Segoe UI", "SF Pro Text", "Cantarell", "Noto Sans"])
    app.setFont(font)
    app.setStyleSheet(STYLESHEET)


def matplotlib_dark(fig) -> None:
    """Adatta una figura matplotlib al tema."""
    fig.patch.set_facecolor(SURFACE)
    for ax in fig.axes:
        ax.set_facecolor(SURFACE)
        ax.tick_params(colors=MUTED, labelsize=8)
        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)
        for title in (ax.title, ax._left_title, ax._right_title):
            title.set_color(TEXT)
            title.set_fontsize(10)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
