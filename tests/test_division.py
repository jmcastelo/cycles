"""The division of the cycle: durations, starts and the conversions between address forms."""

import numpy as np
import pytest

from cycles.functions.conversion import (
    fractional_to_lcoords, lcoords_to_fractional, lcoords_to_tcoord, tcoord_to_lcoords,
)
from cycles.functions.division import compute_level, find_lcoords


@pytest.fixture(scope='module')
def levels():
    return {depth: compute_level(depth) for depth in range(1, 6)}


@pytest.mark.parametrize('depth', range(1, 6))
def test_durations_add_up_and_subcycles_are_contiguous(levels, depth):
    level = levels[depth]
    assert len(level.durations) == 4 ** depth
    assert np.isclose(level.durations.sum(), 1)
    assert np.allclose(level.starts[1:], level.starts[:-1] + level.durations[:-1])
    assert level.starts[0] == 0
    assert np.isclose(level.starts[-1] + level.durations[-1], 1)


def test_ages_last_4_3_2_1(levels):
    assert np.allclose(levels[1].durations, [0.4, 0.3, 0.2, 0.1])


@pytest.mark.parametrize('depth', range(1, 5))
def test_every_subcycle_divides_like_the_whole(levels, depth):
    parent, children = levels[depth], levels[depth + 1]
    shares = children.durations.reshape(-1, 4) / parent.durations[:, None]
    assert np.allclose(shares, [0.4, 0.3, 0.2, 0.1])


@pytest.mark.parametrize('depth', range(1, 5))
def test_address_conversions(levels, depth):
    level = levels[depth]
    for i, lcoords in enumerate(level.lcoords):
        assert lcoords_to_tcoord(lcoords) == i
        assert (tcoord_to_lcoords(i, 4, depth) == lcoords).all()
        fraction = lcoords_to_fractional(lcoords, 4)
        assert list(fractional_to_lcoords(fraction, 4)) == list(np.trim_zeros(lcoords, 'b'))


@pytest.mark.parametrize('depth', range(1, 5))
def test_time_finds_its_subcycle(levels, depth):
    level = levels[depth]
    for lcoords, start, duration in zip(level.lcoords, level.starts, level.durations):
        assert (find_lcoords(start + duration / 2, depth) == lcoords).all()


# -- the whole level at once (compute_level is vectorised) against the functions for one subcycle

@pytest.mark.parametrize('bases, scales', [([4, 2, 2], [0.5, 2 / 3, 0.5]), ([4, 3.5, 1], [0.3, 0.5, 0.75])])
def test_compute_level_matches_the_functions_of_one_subcycle(bases, scales):
    from cycles.functions.color import (
        cmyk_to_rgb, lcoords_to_cmyk, lcoords_to_lrgb, lcoords_to_rgb_tetrahedron,
    )
    from cycles.functions.conversion import tcoord_to_lcoords
    from cycles.functions.division import (
        TETRAHEDRON_COLORS, compute_duration, compute_level, compute_start, level_colors, weights,
    )
    from cycles.functions.measure import dharma_measure, purity_measure
    for depth in range(1, 6):
        level = compute_level(depth, bases, scales)
        colors = level_colors(level)
        w1, w2 = weights(bases[1], depth), weights(bases[2], depth)
        for i in np.random.default_rng(depth).choice(4 ** depth, min(4 ** depth, 40), replace=False):
            lcoords = tcoord_to_lcoords(int(i), 4, depth)
            assert np.array_equal(level.lcoords[i], lcoords)
            assert np.isclose(level.durations[i], compute_duration(lcoords))
            assert np.isclose(level.starts[i], compute_start(lcoords))
            cmyk = lcoords_to_cmyk(lcoords, w1, scales)
            assert np.allclose(level.cmyks[i], cmyk)
            assert np.allclose(level.rgbs[i, :6], [cmyk_to_rgb(c) for c in cmyk])
            assert np.allclose(level.rgbs[i, 6], lcoords_to_rgb_tetrahedron(lcoords, TETRAHEDRON_COLORS, scales[2]))
            assert np.isclose(level.dharmas[i], dharma_measure(lcoords, w1))
            assert np.isclose(level.purities[i], purity_measure(lcoords, w2))
            assert np.allclose(colors['lrgb'][i], lcoords_to_lrgb(lcoords)[-1])


def test_deep_levels_are_fast():
    import time
    from cycles.functions.division import compute_level
    start = time.perf_counter()
    level = compute_level(9)
    assert time.perf_counter() - start < 5 and len(level.durations) == 4 ** 9
    assert np.isclose(level.durations.sum(), 1) and np.all(np.diff(level.starts) > 0)
