import numpy as np
import pytest
from matplotlib.colors import to_rgb

from sonifica.palettes import CVD_MATRICES, PALETTES, get_cmap, lightness, simulate_cvd

CONTINUOUS = [p for p in PALETTES if not p.discrete]
STEPPED = [p for p in PALETTES if p.discrete]
VISIONS = [None, *CVD_MATRICES]


@pytest.mark.parametrize("pal", CONTINUOUS, ids=lambda p: p.key)
@pytest.mark.parametrize("cvd", VISIONS)
def test_increasing_lightness(pal, cvd):
    """Higher values = lighter colors, even for users with color vision deficiencies."""
    rgb = get_cmap(pal.key)(np.linspace(0, 1, 256))[:, :3]
    if cvd:
        rgb = simulate_cvd(rgb, cvd)
    lum = lightness(rgb)
    assert np.all(np.diff(lum) > 0)
    assert lum[-1] - lum[0] > 60


@pytest.mark.parametrize("pal", STEPPED, ids=lambda p: p.key)
@pytest.mark.parametrize("cvd", VISIONS)
def test_steps_well_separated(pal, cvd):
    rgb = np.array([to_rgb(c) for c in pal.colors])
    if cvd:
        rgb = simulate_cvd(rgb, cvd)
    assert np.diff(lightness(rgb)).min() > 10


@pytest.mark.parametrize("pal", PALETTES, ids=lambda p: p.key)
def test_minimum_visible_on_dark_background(pal):
    """The cell with the minimum value must remain distinguishable from the interface background (L* ≈ 3)."""
    assert lightness(get_cmap(pal.key)(0.0)[:3]) > 7


def test_photophobia_is_not_glaring():
    pal = next(p for p in PALETTES if p.key == "photophobia")
    assert lightness(get_cmap(pal.key)(1.0)[:3]) < 80


def test_reverse():
    a = get_cmap("standard")(0.0)
    b = get_cmap("standard", reverse=True)(1.0)
    assert np.allclose(a, b)
