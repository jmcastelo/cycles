"""Which subcycles share a duration: compositions and the (1, 0, -2, 1) rule."""

from math import comb, factorial

import numpy as np
import pytest

from cycles.functions.composition import compositions, duration_equivalent_compositions, lexmin_enumeration
from cycles.functions.division import compute_level
from cycles.functions.duration import count_digits, same_duration


def duration_classes(level):
    """Indices of the subcycles grouped by duration."""
    rounded = np.round(level.durations, 12)
    return [np.flatnonzero(rounded == value) for value in np.unique(rounded)]


@pytest.mark.parametrize('depth', range(1, 6))
def test_number_of_compositions(depth):
    assert len(compositions(depth)) == comb(depth + 3, 3)


@pytest.mark.parametrize('depth', range(1, 6))
def test_duration_depends_only_on_the_composition(depth):
    level = compute_level(depth)
    counts = np.array([count_digits(lc) for lc in level.lcoords])
    for composition in np.unique(counts, axis=0):
        members = np.all(counts == composition, axis=1)
        assert np.ptp(level.durations[members]) < 1e-12
        n = composition
        assert members.sum() == factorial(depth) // np.prod([factorial(int(k)) for k in n])


@pytest.mark.parametrize('depth', range(1, 6))
def test_equal_durations_are_the_1_0_minus2_1_classes(depth):
    """Two compositions give the same duration exactly when they differ by a multiple of (1, 0, -2, 1)."""
    level = compute_level(depth)
    counts = np.array([count_digits(lc) for lc in level.lcoords])
    for indices in duration_classes(level):
        found = {tuple(c) for c in counts[indices]}
        expected = {tuple(c) for c in duration_equivalent_compositions(counts[indices[0]])}
        assert found == expected


def test_same_duration_agrees_with_the_durations():
    level = compute_level(3)
    rounded = np.round(level.durations, 12)
    for i in range(0, 64, 5):
        for j in range(64):
            assert same_duration(level.lcoords[i], level.lcoords[j]) == (rounded[i] == rounded[j])


@pytest.mark.parametrize('composition', [(1, 1, 1, 0), (2, 0, 1, 1), (0, 0, 0, 3), (1, 1, 1, 1)])
def test_lexmin_enumeration_lists_the_orderings_in_time_order(composition):
    composition = np.array(composition)
    arrangements = [tuple(a) for a in lexmin_enumeration(composition)]
    depth = int(composition.sum())
    expected = factorial(depth) // np.prod([factorial(int(k)) for k in composition])
    assert len(arrangements) == len(set(arrangements)) == expected
    assert arrangements == sorted(arrangements)
