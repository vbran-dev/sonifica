import string

import pytest

from sonifica import i18n
from sonifica.examples import EXAMPLES, build
from sonifica.palettes import PALETTES


def _fields(text: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


@pytest.mark.parametrize("key", sorted(i18n.STRINGS))
def test_translation_complete_and_placeholders_match(key):
    it, en = i18n.STRINGS[key]
    assert it.strip() and en.strip()
    assert _fields(it) == _fields(en)


@pytest.fixture
def english():
    i18n.set_language("en")
    yield
    i18n.set_language("it")


def test_language_switch(english):
    assert i18n.tr("row") == "row"
    assert i18n.number(3.5) == "3.5"
    assert build("temperature").row_labels[0] == "Jan"
    assert all(p.name and p.description for p in PALETTES)


def test_italian_numbers_use_comma():
    assert i18n.number(3.5) == "3,5"
    assert build("temperature").row_labels[0] == "Gen"


def test_every_example_has_a_name():
    for key in EXAMPLES:
        assert i18n.tr(f"ex.{key}")


def test_unknown_language():
    with pytest.raises(ValueError):
        i18n.set_language("fr")
