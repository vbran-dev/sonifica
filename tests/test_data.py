import numpy as np
import pytest

from sonifica.data import Grid, example_grid, load


def test_italian_csv_with_year_header(tmp_path):
    p = tmp_path / "temp.csv"
    p.write_text("mese;2019;2020;2021\nGen;3,1;4,2;2,9\nFeb;5;;6,5\n", encoding="utf-8")
    g = load(p)
    assert g.shape == (2, 3)
    assert g.col_labels == ["2019", "2020", "2021"]
    assert g.row_labels == ["Gen", "Feb"]
    assert g.values[0, 0] == pytest.approx(3.1)
    assert np.isnan(g.values[1, 1])
    assert g.n_missing == 1


def test_csv_without_header(tmp_path):
    p = tmp_path / "m.csv"
    p.write_text("1,2,3\n4,5,6\n", encoding="utf-8")
    g = load(p)
    assert g.shape == (2, 3)
    assert g.values[1, 2] == 6


def test_image_downscaled_and_normalized(tmp_path):
    from PIL import Image

    arr = np.tile(np.linspace(0, 255, 300, dtype=np.uint8), (200, 1))
    p = tmp_path / "grad.png"
    Image.fromarray(arr).save(p)
    g = load(p)
    assert max(g.shape) <= 128
    assert not g.labeled
    assert 0 <= g.vmin < g.vmax <= 1


def test_normalization():
    g = Grid(np.array([[0.0, 5.0], [10.0, np.nan]]), ["a", "b"], ["x", "y"])
    n = g.normalized()
    assert n[0, 0] == 0 and n[1, 0] == 1 and n[0, 1] == 0.5
    assert np.isnan(n[1, 1])


def test_default_example():
    g = example_grid()
    assert g.shape == (12, 10)
    assert g.argmax()[0] in (5, 6, 7) 
