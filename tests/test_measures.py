"""The measures of the subcycles beyond dharma and purity (``measure.MEASURES``), and the angular density."""

import numpy as np
import pytest

from cycles.functions.division import compute_level, weights
from cycles.functions.measure import (
    ADDRESS_MEASURES, MEASURES, address_measures, age_shares, balance_measure, contrast_measure, mixture_measure,
    purity_measure, roughness_measure, tension_measure, trend_measure,
)


@pytest.fixture(scope='module')
def level():
    return compute_level(4)


@pytest.fixture(scope='module')
def values(level):
    return address_measures(level.lcoords, level.durations, level.dharmas, level.purities, [4, 2, 2])


def test_every_measure_stays_in_its_range(values):
    assert set(values) == set(ADDRESS_MEASURES)
    for key, v in values.items():
        assert v.shape == (256,) and np.isfinite(v).all()
        if MEASURES[key]['range'] is not None:
            lo, hi = MEASURES[key]['range']
            assert lo - 1e-12 <= v.min() and v.max() <= hi + 1e-12, key


def test_one_age_is_pure_unmixed_smooth_and_calm():
    for age in range(4):
        address = [[age] * 4]
        w = weights(2, 4)
        assert np.isclose(mixture_measure(address, w), 0) and np.isclose(tension_measure(address, w), 0)
        assert np.isclose(trend_measure(address, w), 0) and np.isclose(roughness_measure(address, w), 0)


def test_the_extremes():
    equal = np.ones(4)
    assert np.isclose(mixture_measure([[0, 1, 2, 3]], equal), 1)          # the four ages alike
    assert np.isclose(tension_measure([[0, 3]], [1, 1]), 1)               # half Satya, half Kali
    assert tension_measure([[0, 1]], [1, 1]) < tension_measure([[0, 3]], [1, 1])
    assert np.isclose(trend_measure([[3, 0]], [1, 1]), 1)                 # Satya inside Kali: a rise
    assert np.isclose(trend_measure([[0, 3]], [1, 1]), -1)
    assert np.isclose(roughness_measure([[0, 3, 0]], [1, 1, 1]), 1)
    assert np.isclose(trend_measure([[0, 3, 0]], [1, 1, 1]), 0)          # down and up again: no trend, rough
    assert np.allclose(trend_measure([[2], [3]], [1]), 0)                 # depth 1


def test_mixture_sees_what_purity_misses():
    w = np.ones(4)
    # shares (1/2, 1/2, 0, 0) and (1/2, 1/4, 1/4, 0): the same purity, not the same mixture
    a, b = [0, 0, 1, 1], [0, 0, 1, 2]
    assert np.isclose(purity_measure(np.array(a), w), purity_measure(np.array(b), w))
    assert mixture_measure([b], w) > mixture_measure([a], w)
    assert np.allclose(age_shares([a, b], w), [[.5, .5, 0, 0], [.5, .25, .25, 0]])


def test_contrast_and_balance_follow_time(level, values):
    d = level.dharmas
    assert np.isclose(values['contrast'][5], (d[5] - d[4]) / 0.75)
    assert np.isclose(values['contrast'][0], (d[0] - d[-1]) / 0.75)      # the cycle repeats
    # the balance closes at zero, and its steps are (dharma − mean) × duration
    assert np.isclose(values['balance'][-1], 0, atol=1e-12)
    mean = np.dot(d, level.durations)
    assert np.allclose(np.diff(values['balance']), ((d - mean) * level.durations)[1:])
    assert np.allclose(balance_measure([1, 0], [0.5, 0.5]), [0.25, 0])
    assert np.allclose(contrast_measure([1, 0.25]), [1, -1])


def test_the_angular_density():
    from cycles.functions.cycle_analysis import angular_density
    from cycles.functions.cycle_model import BUILTIN_PRESETS, DEFAULT_PRESET
    model = BUILTIN_PRESETS[DEFAULT_PRESET]
    whole = angular_density(model, [0.0], [1.0])
    assert np.isclose(whole[0], 1.0)                                      # the cycle against itself
    level = compute_level(2)
    density = angular_density(model, level.starts, level.durations)
    assert np.all((density > 0.9) & (density < 1.1))
    # arc shares weighted by the time shares add up to the whole arc
    time_map = model.time_map()
    years = np.asarray(time_map.to_physical(np.append(level.starts, 1.0)))
    shares = np.diff(years) / (years[-1] - years[0])
    assert np.isclose(np.sum(density * shares), 1.0)
    # with a constant precession every subcycle sweeps arc at the mean rate
    constant = model.replace(precession='constant')
    assert np.allclose(angular_density(constant, level.starts, level.durations), 1.0)
