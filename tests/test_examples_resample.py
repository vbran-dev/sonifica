import numpy as np
import pytest

from sonifica.data import Grid, resample
from sonifica.examples import EXAMPLES, SHAPES, build
from sonifica.hilbert import coherence


@pytest.mark.parametrize("key", list(EXAMPLES))
def test_examples(key):
    g = build(key)
    assert g.shape == SHAPES[key]
    assert g.example == key
    assert np.isfinite(g.vmin) and g.vmax > g.vmin


def test_at_least_one_100x100_example():
    assert any(min(s) >= 100 for s in SHAPES.values())


def test_examples_are_reproducible():
    assert np.array_equal(build("terrain").values, build("terrain").values)


def test_area_average_preserves_mean():
    g = build("terrain")
    for shape in [(50, 50), (33, 17), (7, 9)]:
        r = resample(g, *shape, method="area")
        assert r.shape == shape
        assert np.isclose(r.values.mean(), g.values.mean())


def test_nearest_uses_original_values():
    g = build("terrain")
    r = resample(g, 20, 30, method="nearest")
    assert np.isin(r.values, g.values).all()


def test_same_size_changes_nothing():
    g = build("temperature")
    assert np.allclose(resample(g, *g.shape).values, g.values)


def test_does_not_upscale():
    g = build("temperature")
    assert resample(g, 50, 50).shape == g.shape


def test_missing_values():
    v = np.array([[1.0, np.nan], [np.nan, np.nan]])
    g = Grid(np.kron(v, np.ones((2, 2))), [], [])
    r = resample(g, 2, 2)
    assert r.values[0, 0] == 1.0
    assert np.isnan(r.values[1, 1])
    # a new cell that partially overlaps missing data uses only valid values
    g2 = Grid(np.array([[1.0, np.nan], [3.0, 5.0]]), [], [])
    assert resample(g2, 1, 1).values[0, 0] == pytest.approx(3.0)


def test_merged_labels():
    r = resample(build("temperature"), 6, 5)
    assert r.labeled
    assert len(r.row_labels[0].split("–")) == 2
    assert r.col_labels[0] == "2015–2016"


@pytest.mark.parametrize("factor", [2, 4, 5])
def test_resized_sounds_similar_with_hilbert(factor):
    """Sharp and smooth heatmaps: the reduced version remains consistent with Hilbert, rather than row by row."""
    g = build("terrain")
    n = g.normalized()
    r = resample(g, 100 // factor, 100 // factor).normalized()
    assert coherence(n, r, "hilbert") > 0.95
    assert coherence(n, r, "hilbert") > coherence(n, r, "rows") + 0.4
