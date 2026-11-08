"""Planetary events (conjunctions, trigon changes, the planets around a point) and the significance tests."""

import numpy as np
import pytest

from cycles.functions.significance import holm, nearest_distance, proximity_test, rotations, scan_models, value_test


# -- significance

def test_nearest_distance():
    events = np.array([10.0, 20.0, 50.0])
    assert np.allclose(nearest_distance([0, 12, 16, 49, 60], events), [10, 2, 4, 1, 10])
    assert np.allclose(nearest_distance([3.0], [5.0]), [2.0])


def test_rotations_keep_the_spacing_inside_the_cycle():
    times = np.array([0.0, 4.0, 7.0, 9.0, 10.0]) * 10
    shifted = rotations(times[:-1], 0.0, 100.0, 500, seed=3)
    assert shifted.shape == (500, 4) and shifted.min() >= 0 and shifted.max() < 100
    gaps = np.diff(np.sort(shifted, axis=1), axis=1)
    # the four boundaries keep their circular spacing (40, 30, 20 and the closing 10)
    circular = np.sort(np.concatenate([gaps, 100 - gaps.sum(axis=1, keepdims=True)], axis=1), axis=1)
    assert np.allclose(circular, [10, 20, 30, 40])


def test_events_on_the_boundaries_are_significant_and_unrelated_ones_are_not():
    rng = np.random.default_rng(0)
    boundaries = np.sort(rng.uniform(0, 10_000, 40))
    on = proximity_test(boundaries, boundaries + rng.normal(0, 1, 40), 0, 10_000, 2000)
    assert on['p'] < 0.01 and on['ratio'] < 0.1
    unrelated = [proximity_test(boundaries, np.sort(rng.uniform(-100, 10_100, 60)), 0, 10_000, 1000, seed=k)['p']
                 for k in range(30)]
    assert 0.25 < np.mean(unrelated) < 0.75                      # p roughly uniform under the null
    value = value_test(boundaries, lambda t: np.abs(np.sin(t)), 0, 10_000, 500)
    assert 0 < value['p'] <= 1 and value['null'].shape == (500,)


def test_holm():
    assert np.allclose(holm([0.01, 0.04, 0.03, 0.5]), [0.04, 0.09, 0.09, 0.5])
    assert np.allclose(holm([0.2]), [0.2])


# -- the events

@pytest.fixture(scope='module')
def tables(ephemeris):
    import cycles.functions.nbody_ephemeris as nbe
    from cycles.gui.sky import ephemeris_parts
    return [nbe.load_ephemeris(part) for part in ephemeris_parts(ephemeris)]


def _date(year):
    from cycles.functions.astro_dates import tdb_year_to_date
    y, m, d = tdb_year_to_date(year)
    return y, m, int(d)


@pytest.mark.ephemeris
def test_known_great_conjunctions(tables):
    from cycles.functions.events import SIGN_NAMES, conjunctions, first_of_series, sign_of
    c = conjunctions(tables, 'jupiter', 'saturn', 1975.0, 2025.0)
    dates = [_date(t) for t in c['times']]
    # the triple conjunction of 1980–81 in Libra, 28 May 2000 in Taurus, 21 December 2020 at 0°30′ Aquarius
    assert dates == [(1980, 12, 31), (1981, 3, 4), (1981, 7, 24), (2000, 5, 28), (2020, 12, 21)]
    assert list(c['series']) == [0, 0, 0, 1, 2] and list(first_of_series(c)) == [0, 3, 4]
    assert [SIGN_NAMES[s] for s in sign_of(c['tropical'])] == ['Libra'] * 3 + ['Taurus', 'Aquarius']
    assert abs(c['tropical'][-1] - 300.5) < 0.05
    # sidereal = tropical − ayanamsa (about 24.2° today)
    assert abs((c['tropical'][-1] - c['sidereal'][-1]) - 24.2) < 0.1


@pytest.mark.ephemeris
def test_outer_conjunctions(tables):
    from cycles.functions.events import conjunctions
    un = conjunctions(tables, 'uranus', 'neptune', 1990.0, 1996.0)
    assert [_date(t)[:2] for t in un['times']] == [(1993, 2), (1993, 8), (1993, 10)] and set(un['series']) == {0}
    npl = conjunctions(tables, 'neptune', 'pluto', 1885.0, 1896.0)
    assert len(npl['times']) == 3 and abs(npl['tropical'][0] - 68.6) < 0.2      # about 8° Gemini


@pytest.mark.ephemeris
def test_trigon_changes_settle(tables):
    from cycles.functions.events import conjunctions, trigon_changes
    c = conjunctions(tables, 'jupiter', 'saturn', 1000.0, 2100.0)
    changes = [_date(t)[0] for t in trigon_changes(c, 'tropical')]
    assert 1603 in changes and 2020 in changes                   # fire (Kepler's) and air
    assert 1980 not in changes and 1981 not in changes           # the passing air conjunction of 1980–81


@pytest.mark.ephemeris
def test_the_planets_around_a_point(tables):
    from cycles.functions.events import CLASSICAL, around_point
    kali = -3100.83                                              # the traditional start of the Kali (TDB ≈ UT)
    sidereal = around_point(tables, [kali], CLASSICAL, 0.0, 'sidereal')
    assert sidereal['spread'][0] < 45 and sidereal['mean_distance'][0] < 20   # gathered near 0° sidereal Aries
    tropical = around_point(tables, [kali], CLASSICAL, 0.0, 'tropical')
    assert np.isclose(tropical['spread'][0], sidereal['spread'][0])            # the arc does not depend on the zodiac
    assert tropical['mean_distance'][0] > 45


# -- the map over the models

def test_the_boundary_grid_is_the_models_division():
    from cycles.functions.cycle_analysis import boundary_grid
    from cycles.functions.cycle_model import BUILTIN_PRESETS, DEFAULT_PRESET
    model = BUILTIN_PRESETS[DEFAULT_PRESET]
    solution = model.solve()
    grid = boundary_grid(model, [solution['anchor'], solution['anchor'] + 5000], [solution['turns'], 3.0], 1)
    assert grid.shape == (2, 2, 5)
    assert np.allclose(grid[0, 0], model.boundaries(), atol=1e-6)
    far = boundary_grid(model, [2000.0 - 300000], [2.5], 1)          # outside the long-term precession model
    assert np.isnan(far).all()


def test_scan_models_finds_a_planted_model_and_corrects_for_the_search():
    rng = np.random.default_rng(4)
    span = (0.0, 100_000.0)
    models = np.sort(rng.uniform(5_000, 95_000, (40, 30, 9)), axis=-1)          # 1200 models of 9 boundaries
    planted = models[17, 5]
    events = np.sort(np.concatenate([planted + rng.normal(0, 0.5, planted.shape),
                                     rng.uniform(0, 100_000, 2000)]))
    found = scan_models(models, events, span, 200)
    assert found['best'] == (17, 5) and found['p_global'] < 0.05 and found['ratio'][17, 5] < 0.2
    unrelated = scan_models(models, np.sort(rng.uniform(0, 100_000, 2000)), span, 200)
    assert unrelated['p_global'] > 0.05
    # a model that leaves the span, or cannot be placed, is left out
    models[0, 0, 0] = -10.0
    models[1, 1, 3] = np.nan
    left_out = scan_models(models, events, span, 10)
    assert not left_out['valid'][0, 0] and not left_out['valid'][1, 1] and left_out['valid'].sum() == 1198
