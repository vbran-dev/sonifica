import re

from sonifica import __version__


def test_semantic_version():
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


def test_changelog_mentions_current_version():
    from pathlib import Path

    changelog = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
    assert f"[{__version__}]" in changelog.read_text(encoding="utf-8")
