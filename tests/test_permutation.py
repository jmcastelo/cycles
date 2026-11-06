"""Permutations of the digit positions of addresses."""

import itertools
from math import comb

import numpy as np
import pytest
from symmetrymath import SymmetricGroup

from cycles.functions.conversion import lcoords_to_tcoord
from cycles.functions.division import compute_level
from cycles.functions.duration import count_digits
from cycles.functions.permutation import (
    compose, cycle_text, cycle_type, cycles, order, parse_permutation, permutation_matrix, permute_digits, power,
    sign, tcoords_of,
)


def test_helpers_agree_with_symmetrymath():
    group = SymmetricGroup(4)
    elements = list(group.elements)
    for a in elements:
        assert order(a) == group.order_of(a)
        assert power(a, order(a)) == tuple(range(4))
        for b in elements:
            assert compose(a, b) == group.operation(a, b)


@pytest.mark.parametrize('m', range(1, 6))
def test_notations_round_trip(m):
    for sigma in itertools.permutations(range(m)):
        assert parse_permutation(cycle_text(sigma), m) == sigma
        assert parse_permutation(' '.join(map(str, sigma)), m) == sigma
        assert parse_permutation(''.join(map(str, sigma)), m) == sigma
        assert sum(cycle_type(sigma)) == m
        assert sign(sigma) == (-1) ** sum(len(c) - 1 for c in cycles(sigma))


@pytest.mark.parametrize('text', ['1 1 0', '0 1', '(0 1)(1 2)', '(0 5)', 'abc', '(0 1'])
def test_invalid_permutations_are_rejected(text):
    with pytest.raises(ValueError):
        parse_permutation(text, 3)


def test_cycle_notation_means_i_goes_to_sigma_i():
    assert parse_permutation('(0 1 2)', 3) == (1, 2, 0)
    assert cycle_text((1, 2, 0, 4, 3)) == '(0 1 2)(3 4)'
    assert cycle_text((0, 1, 2)) == '()'


def test_vectorized_action_agrees_with_the_study():
    """``permute_digits`` and ``tcoords_of`` give what study_of_permutations computes address by address."""
    group = SymmetricGroup(3)
    level = compute_level(3)
    for sigma in group.elements:
        expected = [lcoords_to_tcoord(np.array(group.operation(tuple(lc), sigma))) for lc in level.lcoords]
        assert (tcoords_of(permute_digits(level.lcoords, sigma)) == expected).all()


def test_permuting_only_the_tail_keeps_the_prefix():
    level = compute_level(4)
    tail = permute_digits(level.lcoords, (2, 0, 1), first=1)
    assert (tail[:, 0] == level.lcoords[:, 0]).all()


@pytest.mark.parametrize('depth', [2, 3, 4])
def test_permutations_keep_durations(depth):
    level = compute_level(depth)
    for sigma in itertools.permutations(range(depth)):
        images = tcoords_of(permute_digits(level.lcoords, sigma))
        assert np.allclose(level.durations[images], level.durations)


@pytest.mark.parametrize('depth', [2, 3])
def test_permutation_matrix_is_a_permutation_matrix(depth):
    level = compute_level(depth)
    for sigma in itertools.permutations(range(depth)):
        matrix = permutation_matrix(sigma, level.lcoords)
        assert (matrix.sum(axis=0) == 1).all() and (matrix.sum(axis=1) == 1).all()


@pytest.mark.parametrize('m', range(1, 7))
def test_burnside_the_orbits_of_the_group_are_the_compositions(m):
    """The mean of the fixed subcycles (4 ** cycles) over S_m is the number of compositions."""
    fixed = [4 ** len(cycles(sigma)) for sigma in itertools.permutations(range(m))]
    assert sum(fixed) % len(fixed) == 0
    assert sum(fixed) // len(fixed) == comb(m + 3, 3)


def test_orbits_of_the_whole_group_are_the_composition_classes():
    level = compute_level(3)
    orbit_of = {}
    for i, lc in enumerate(level.lcoords):
        orbit_of[i] = frozenset(int(lcoords_to_tcoord(np.array(p))) for p in set(itertools.permutations(lc)))
    for i, lc in enumerate(level.lcoords):
        same = {j for j, other in enumerate(level.lcoords) if (count_digits(other) == count_digits(lc)).all()}
        assert orbit_of[i] == same


def test_fixed_subcycles_of_one_element():
    level = compute_level(4)
    sigma = (1, 0, 3, 2)
    images = tcoords_of(permute_digits(level.lcoords, sigma))
    assert (images == np.arange(256)).sum() == 4 ** len(cycles(sigma))
