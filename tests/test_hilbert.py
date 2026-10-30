import numpy as np
import pytest

from sonifica.analysis import run_round_trip
from sonifica.data import example_grid
from sonifica.hilbert import coherence, d2xy, order_for, path_for, sample, to_grid
from sonifica.mapping import SoundMapping
from sonifica.synth import SAMPLE_RATE, render_hilbert


def field(n_rows: int, n_cols: int) -> np.ndarray:
    """The same continuous field sampled at different resolutions."""
    yy, xx = np.meshgrid((np.arange(n_rows) + 0.5) / n_rows, (np.arange(n_cols) + 0.5) / n_cols, indexing="ij")
    f = np.sin(3 * xx) + np.cos(4 * yy) + 0.5 * np.exp(-((xx - 0.7) ** 2 + (yy - 0.3) ** 2) / 0.02)
    return (f - f.min()) / (f.max() - f.min())


@pytest.mark.parametrize("order", [1, 2, 3, 4, 5])
def test_curve_visits_each_cell_once_through_neighbours(order):
    x, y = d2xy(order, np.arange(4**order))
    side = 1 << order
    assert len(set(zip(x.tolist(), y.tolist(), strict=True))) == side * side
    assert np.all(np.abs(np.diff(x)) + np.abs(np.diff(y)) == 1)


@pytest.mark.parametrize("order", [2, 3, 4, 5])
def test_curve_is_nested(order):
    """Each order refines the previous one without changing its traversal order."""
    x, y = d2xy(order, np.arange(4**order))
    px, py = d2xy(order - 1, np.arange(4**order) // 4)
    assert np.all(x // 2 == px) and np.all(y // 2 == py)


def test_starts_top_left_and_ends_top_right():
    p = path_for((8, 8))
    assert (p.rows[0], p.cols[0]) == (0, 0)
    assert (p.rows[-1], p.cols[-1]) == (0, 7)


@pytest.mark.parametrize("shape", [(1, 1), (3, 7), (12, 10), (40, 40), (5, 33)])
def test_every_cell_visited_and_exact_reconstruction(shape):
    m = np.random.default_rng(0).random(shape)
    assert np.allclose(to_grid(sample(m), shape), m)
    assert 2 ** order_for(shape) >= max(shape)


@pytest.mark.parametrize("other", [(24, 20), (13, 10), (36, 30), (40, 40)])
def test_similar_matrices_sound_similar(other):
    base = field(12, 10)
    assert coherence(base, field(*other), "hilbert") > 0.97


def test_hilbert_more_coherent_than_rows_when_rows_change():
    base = field(12, 10)
    for other in [(24, 20), (13, 10), (36, 30)]:
        assert coherence(base, field(*other), "hilbert") > coherence(base, field(*other), "rows") + 0.05


def test_fixed_duration_independent_of_size():
    m = SoundMapping()
    a = render_hilbert(field(12, 10), m, duration=2.0)
    b = render_hilbert(field(37, 29), m, duration=2.0)
    assert a.shape == b.shape == (2 * SAMPLE_RATE, 2)
    assert np.abs(a).max() <= 1.0


def test_hilbert_round_trip():
    norm = example_grid().normalized()
    norm[2, 3] = np.nan
    res = run_round_trip(norm, SoundMapping(), snr_db=10)[0]
    assert res.mode == "hilbert"
    assert res.metrics["correlation"] > 0.99
    assert np.isnan(res.reconstructed[2, 3])
