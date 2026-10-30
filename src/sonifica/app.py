"""Entry point: `sonifica [--lang it|en] [file]` or `python -m sonifica ...`."""

from __future__ import annotations

import argparse
import sys

from sonifica import __version__, i18n


def main(argv: list[str] | None = None) -> int:
    from PySide6.QtWidgets import QApplication

    from sonifica.ui.main_window import MainWindow, settings_store
    from sonifica.ui.theme import apply_dark_theme

    argv = sys.argv if argv is None else argv
    parser = argparse.ArgumentParser(
        prog="sonifica", description="Explore heatmaps by ear / Esplora heatmap con l'udito"
    )
    parser.add_argument("file", nargs="?", help="CSV file or image / file CSV o immagine")
    parser.add_argument("--version", action="version", version=f"Sonifica {__version__}")
    parser.add_argument("--lang", choices=sorted(i18n.LANGUAGES), help="interface language / lingua dell'interfaccia")
    args, qt_args = parser.parse_known_args(argv[1:])

    app = QApplication([argv[0], *qt_args])
    app.setApplicationName("Sonifica")
    app.setApplicationVersion(__version__)
    saved = str(settings_store().value("language", "") or "")
    i18n.set_language(args.lang or (saved if saved in i18n.LANGUAGES else i18n.system_language()))
    apply_dark_theme(app)
    window = MainWindow(args.file)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
