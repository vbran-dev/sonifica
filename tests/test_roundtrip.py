import numpy as np

from sonifica.analysis import compare, run_round_trip
from sonifica.data import example_grid
from sonifica.mapping import SoundMapping
from sonifica.synth import SAMPLE_RATE, render_sequence


def test_continuous_sequence_almost_perfect():
    norm = example_grid().normalized()
    seq = run_round_trip(norm, SoundMapping())[1]
    assert seq.metrics["correlation"] > 0.999
    assert seq.metrics["max_error"] < 0.01


def test_spectral_preserves_the_pattern():
    norm = example_grid().normalized()
    spec = run_round_trip(norm, SoundMapping())[2]
    assert spec.metrics["correlation"] > 0.95


def test_pentatonic_scale_loses_information():
    norm = example_grid().normalized()
    cont = run_round_trip(norm, SoundMapping(scale="continuous"))[1]
    penta = run_round_trip(norm, SoundMapping(scale="pentatonic"))[1]
    assert penta.metrics["mean_error"] > cont.metrics["mean_error"] * 5


def test_with_noise_pitch_beats_loudness():
    norm = example_grid().normalized()
    _, seq, spec = run_round_trip(norm, SoundMapping(), snr_db=0)
    assert seq.metrics["mean_error"] < spec.metrics["mean_error"]


def test_missing_values_recognized():
    norm = example_grid().normalized()
    norm[2, 3] = np.nan
    seq = run_round_trip(norm, SoundMapping())[1]
    assert np.isnan(seq.reconstructed[2, 3])
    assert seq.metrics["missing_recognized"] == 1.0


def test_sequence_duration():
    norm = np.random.default_rng(0).random((3, 4))
    audio = render_sequence(norm, SoundMapping(), note_dur=0.1, gap=0.05)
    assert audio.shape == (12 * round(0.15 * SAMPLE_RATE), 2)
    assert np.abs(audio).max() <= 1.0


def test_compare_identico():
    a = np.random.default_rng(1).random((5, 5))
    m = compare(a, a)
    assert m["correlation"] == 1.0 and m["max_error"] == 0.0
