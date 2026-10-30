import numpy as np
import pytest

from sonifica.mapping import SCALES, SoundMapping


def test_endpoints_and_monotonicity():
    m = SoundMapping(f_min=220, f_max=880)
    assert m.frequency(0) == pytest.approx(220)
    assert m.frequency(1) == pytest.approx(880)
    assert m.frequency(0.5) == pytest.approx(440)  # scala logaritmica: metà = un'ottava
    f = m.frequency(np.linspace(0, 1, 50))
    assert np.all(np.diff(f) > 0)


def test_inverse():
    m = SoundMapping()
    v = np.linspace(0, 1, 21)
    assert np.allclose(m.value_from_frequency(m.frequency(v)), v)


def test_pentatonic_uses_only_scale_notes():
    m = SoundMapping(scale="pentatonic")
    f = m.frequency(np.linspace(0, 1, 200))
    midi = np.round(69 + 12 * np.log2(f / 440)).astype(int)
    assert set(midi % 12) <= set(SCALES["pentatonic"])


def test_loudness_and_panning():
    m = SoundMapping()
    assert m.amplitude(0) == pytest.approx(m.amp_min)
    assert m.amplitude(1) == pytest.approx(m.amp_max)
    assert m.pan(0, 5) == pytest.approx(-m.pan_width)
    assert m.pan(4, 5) == pytest.approx(m.pan_width)
    assert m.pan(0, 1) == 0


def test_invalid_parameters():
    with pytest.raises(ValueError):
        SoundMapping(f_min=500, f_max=400)
    with pytest.raises(ValueError):
        SoundMapping(scale="inesistente")
