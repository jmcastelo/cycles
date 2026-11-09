"""The multifractal spectrum of the division (functions.multifractal)."""

import numpy as np
import pytest

from cycles.functions.multifractal import (
    MEASURES, PROPORTIONS, composition_spectrum, histogram_spectrum, key_values, spectrum, tau,
)


@pytest.mark.parametrize('name', ['time', 'count'])
def test_the_moments_and_the_spectrum(name):
    weights, sizes = MEASURES[name]
    assert np.allclose(tau([0.0, 1.0], weights, sizes), [-1.0, 0.0])       # the cycle has dimension 1; total 1
    exact = spectrum(np.linspace(-30, 30, 3001), weights, sizes)
    assert np.isclose(exact['f'].max(), 1.0, atol=1e-9)
    assert np.all(exact['f'] <= exact['alpha'] + 1e-9)                       # f(α) ≤ α, touching at D₁
    values = key_values(weights, sizes)
    ends = np.log(weights) / np.log(sizes)
    assert np.isclose(values['alpha_min'], ends.min()) and np.isclose(values['alpha_max'], ends.max())
    assert values['alpha_min'] <= exact['alpha'].min() + 1e-3 and exact['alpha'].max() <= values['alpha_max'] + 1e-6


def test_the_dimensions_in_closed_form():
    entropy = -(PROPORTIONS * np.log(PROPORTIONS)).sum()
    time, count = key_values(*MEASURES['time']), key_values(*MEASURES['count'])
    assert np.isclose(time['D1'], entropy / np.log(4))                    # 0.9232
    assert np.isclose(count['D1'], np.log(4) / -np.log(PROPORTIONS).mean())  # 0.9192
    assert np.isclose(time['D2'], -np.log((PROPORTIONS ** 2).sum()) / np.log(4))
    # the two measures are dual: each one's D₁ is the inverse of the other's typical exponent
    assert np.isclose(time['D1'], 1 / count['alpha_0']) and np.isclose(count['D1'], 1 / time['alpha_0'])


def test_the_classes_of_equal_alpha_are_the_classes_of_equal_duration():
    for depth in (3, 10):
        classes = composition_spectrum(depth, *MEASURES['time'])
        assert len(classes['alpha']) == (depth + 1) ** 2                    # the (d + 1)² durations
        assert np.isclose(np.logaddexp.reduce(classes['log_count']), depth * np.log(4))   # every subcycle once


@pytest.mark.parametrize('name', ['time', 'count'])
def test_the_histogram_tends_to_the_exact_spectrum(name):
    weights, sizes = MEASURES[name]
    exact = spectrum(np.linspace(-60, 60, 6001), weights, sizes)
    order = np.argsort(exact['alpha'])
    values = key_values(weights, sizes)
    errors = []
    for depth in (20, 120):
        estimate = histogram_spectrum(depth, weights, sizes, 0.02)
        inner = (estimate['alpha'] > values['alpha_min'] + 0.1) & (estimate['alpha'] < values['alpha_max'] - 0.1)
        curve = np.interp(estimate['alpha'], exact['alpha'][order], exact['f'][order])
        errors.append(np.abs(estimate['f'] - curve)[inner].max())
    assert errors[1] < errors[0] and errors[1] < 0.04
