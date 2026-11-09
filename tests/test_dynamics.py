"""The time evolution as a dynamical system (functions.dynamics): estimators against the exact results."""

import math

import numpy as np
import pytest

from cycles.functions import dynamics as dy
from cycles.functions.division import compute_level
from cycles.functions.multifractal import MEASURES, key_values


@pytest.fixture(scope='module')
def level():
    return compute_level(8)


def test_consecutive_durations_follow_the_carries(level):
    ratios = level.durations[1:] / level.durations[:-1]
    assert np.allclose(ratios, dy.exact_duration_ratios(level.lcoords))
    carries = dy.carry_lengths(level.lcoords)
    for k in range(4):                                     # an odometer: k carries in 3 of every 4^(k+1) steps
        assert np.isclose(np.mean(carries == k), 3 / 4 ** (k + 1), atol=1e-4)


def test_the_steps_of_dharma_take_one_value_per_carry():
    for base in (2, 3):
        level = compute_level(7, [4, base, 2])
        steps = np.diff(level.dharmas)
        exact = dy.exact_dharma_steps(7, base)
        carries = dy.carry_lengths(level.lcoords)
        assert np.allclose(steps, exact[carries])
        assert exact[0] < 0 and np.all(exact[2:] > 0)      # the plain step lowers dharma, two carries raise it
        assert np.sign(exact[1]) == np.sign(3 - base)       # one carry: up below base 3, flat at 3, down above


def test_the_spectrum_of_the_durations_is_a_riesz_product(level):
    f, p = dy.power_spectrum(level.durations)
    assert np.allclose(p, dy.exact_duration_spectrum(f, 8), rtol=1e-8, atol=1e-12 * p.max())


def test_mfdfa_recovers_the_exact_hurst_exponents(level):
    x = level.durations
    scales = dy.scales_between(len(x))
    qs = [-2.0, 0.0, 2.0, 4.0]
    h = [dy.fit_exponent(scales, row) for row in dy.mfdfa(x, scales, qs)]
    assert np.allclose(h, dy.exact_duration_hurst(qs), atol=0.04)
    assert np.isclose(dy.exact_duration_hurst([2])[0], 0.934, atol=1e-3)
    # h(0) is the typical exponent of the time on the index line
    assert np.isclose(dy.exact_duration_hurst([0])[0], key_values(*MEASURES['time'])['alpha_0'])
    # the order holds the memory: shuffled, the durations are white noise
    assert abs(dy.fit_exponent(scales, dy.dfa(dy.shuffled(x), scales)) - 0.5) < 0.05
    # and the linear correlations are all of it at q = 2: phase-randomized keeps H, not its multifractality
    surrogate = dy.mfdfa(dy.phase_randomized(x), scales, [-2.0, 4.0])
    hs = [dy.fit_exponent(scales, row) for row in surrogate]
    assert abs(hs[0] - hs[1]) < 0.1 < h[0] - h[3]


@pytest.mark.parametrize('base', [2, 3])
def test_the_roughness_of_dharma(base):
    x = compute_level(8, [4, base, 2]).dharmas
    exact = dy.exact_dharma_roughness(base)
    assert np.isclose(exact['roughness'], math.log(base, 4))
    assert abs(dy.higuchi_dimension(x) - exact['graph_dimension']) < 0.05
    lags = dy.scales_between(len(x), 4)
    h1 = dy.fit_exponent(lags, dy.structure_functions(x, lags, [1])[0])
    assert abs(h1 - exact['roughness']) < 0.08


def test_the_zoom_map():
    zoom = dy.zoom_dynamics()
    entropy = -(dy.PROPORTIONS * np.log(dy.PROPORTIONS)).sum()
    assert np.isclose(zoom['entropy'], entropy) and np.isclose(zoom['lyapunov'], 1.2799, atol=1e-4)
    assert zoom['entropy'] < zoom['topological_entropy'] == pytest.approx(math.log(4))
    assert np.isclose(zoom['count_dimension'], key_values(*MEASURES['count'])['D1'])
    assert np.isclose(zoom['entropy'] / math.log(4), key_values(*MEASURES['time'])['D1'])


def test_ordinal_patterns():
    rng = np.random.default_rng(1)
    assert dy.permutation_entropy(np.arange(1000.0)) == pytest.approx(0.0)
    h, c = dy.statistical_complexity(rng.normal(size=20000), 4)
    assert h > 0.99 and c < 0.02
    h, c = dy.statistical_complexity(np.sin(np.arange(5000) * 0.3), 4)
    assert h < 0.5 and c > 0.1
    assert math.isclose(dy.ordinal_distribution(rng.normal(size=500), 3).sum(), 1.0)
    # few distinct values: ties ordered at random, so shuffled they are still noise; by position they are not
    steps = rng.integers(0, 3, 20000).astype(float)
    assert dy.permutation_entropy(steps, 4) > 0.99
    assert dy.permutation_entropy(steps, 4, ties='position') < 0.95


def test_recurrences():
    periodic = np.tile([0.0, 1.0, 2.0, 3.0], 50)
    q = dy.rqa(dy.recurrence_matrix(periodic, 0.1))
    assert np.isclose(q['rate'], 49 / 199, atol=1e-9) and q['determinism'] == pytest.approx(1.0)
    assert q['laminarity'] == 0.0
    steady = np.repeat([0.0, 1.0], 50)
    assert dy.rqa(dy.recurrence_matrix(steady, 0.1))['laminarity'] == pytest.approx(1.0, abs=0.01)
    assert dy.rqa(np.zeros((5, 5), dtype=bool))['rate'] == 0.0


def test_return_times_and_kac(level):
    for digit in range(4):
        members = level.lcoords[:, -1] == digit
        t = dy.return_times(members)
        assert np.all(t == 4) and t.mean() == 1 / members.mean()        # Kac's lemma for the odometer
        waits = dy.return_times(members, level.durations)
        first, last = np.flatnonzero(members)[[0, -1]]
        assert np.isclose(waits.sum(), level.starts[last] - level.starts[first])
        assert np.all(waits > 0)


def test_time_reversal(level):
    from cycles.functions.measure import address_measures
    values = address_measures(level.lcoords, level.durations, level.dharmas, level.purities, [4, 2, 2])
    assert dy.reversal_symmetry(values['purity']) == ('even', 0.0)
    assert dy.reversal_symmetry(values['tension'])[0] == 'even'
    kind, centre = dy.reversal_symmetry(level.dharmas)
    assert kind == 'odd' and np.isclose(centre, 5 / 8)
    assert dy.reversal_symmetry(values['trend'])[0] == 'odd'
    assert dy.reversal_symmetry(level.durations) is None


def test_sampling_in_time():
    level = compute_level(3)
    x = dy.time_samples(level.starts, np.arange(64), 10000)
    counts = np.bincount(x, minlength=64) / 10000
    assert np.allclose(counts, level.durations, atol=2e-4)          # each subcycle as long as it lasts
    from cycles.functions.timescale import TimeMap
    uneven = TimeMap([0.0, 100.0, 300.0], [0.0, 0.5, 1.0])         # the second half lasts twice as long
    y = dy.time_samples([0.0, 0.5], np.array([0, 1]), 3000, uneven)
    assert np.isclose(np.mean(y == 1), 2 / 3, atol=1e-3)


def test_surrogates_keep_what_they_should():
    x = np.random.default_rng(3).normal(size=4096).cumsum()
    assert np.array_equal(np.sort(dy.shuffled(x)), np.sort(x))
    y = dy.phase_randomized(x)
    assert np.allclose(np.abs(np.fft.rfft(y - y.mean())), np.abs(np.fft.rfft(x - x.mean())))
