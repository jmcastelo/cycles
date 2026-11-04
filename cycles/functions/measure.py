"""
Scalar "quality" measures of a subcycle, computed from its address.

Each digit position k has a weight (``division.weights``), so outer levels
count more than inner ones.
"""

import numpy as np

from cycles.functions.conversion import kronecker_vector


def dharma_measure(lcoords: np.ndarray, weights: np.ndarray) -> float:
    """
    Weighted mean of the age "virtue" of the digits of ``lcoords``.

    Ages 0, 1, 2, 3 are worth 1, 3/4, 1/2, 1/4, so an all-Golden address gives 1
    and an all-Iron address gives 1/4.
    """
    return np.dot(4 - lcoords, weights) / (4 * np.sum(weights))


def dharma_from_cmyk(cmyk: np.ndarray) -> float:
    """
    Dharma from a 'cmyk_normalised' color. For such a color it equals
    dharma_measure(lcoords, weights) with the weights used to build the color.
    """
    return np.dot([1, 3 / 4, 1 / 2, 1 / 4], cmyk)


def purity_measure(lcoords: np.ndarray, weights: np.ndarray) -> float:
    """
    Spread between the most and the least represented age in ``lcoords``.

    The weighted share of each age is computed; the result is the largest share
    minus the smallest. It is 1 when all digits are the same age and 0 when the
    four ages are equally represented.
    """
    vw = np.array([np.dot(kronecker_vector(i, lcoords), weights) for i in range(4)], dtype=float)
    sum_weights = np.sum(weights, dtype=float)
    return (np.max(vw, axis=0) - np.min(vw, axis=0)) / sum_weights