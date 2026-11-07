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
