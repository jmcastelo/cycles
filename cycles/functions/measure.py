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

# -- more measures of the address (vectorised over a level: ``lcoords`` of shape (N, depth))
#
# The virtue of a digit is v = (4 - age) / 4 (Satya 1, Treta 3/4, Dvapara 1/2, Kali 1/4), as in dharma. Each measure
# is scaled to a fixed range ([0, 1] or [-1, 1]) so that values of different depths compare.

VIRTUE_SPAN = 3 / 4          # the largest difference of two virtues (Satya against Kali)


def virtues(lcoords) -> np.ndarray:
    """Virtue of each digit: 1, 3/4, 1/2, 1/4 for the ages 0 to 3."""
    return (4 - np.asarray(lcoords, dtype=float)) / 4


def _normalised(weights) -> np.ndarray:
    weights = np.asarray(weights, dtype=float)
    return weights / weights.sum()


def age_shares(lcoords, weights) -> np.ndarray:
    """Weighted share of each age in each address: shape (N, 4), each row adding up to 1."""
    lcoords = np.atleast_2d(np.asarray(lcoords, dtype=int))
    w = _normalised(weights)
    return np.stack([((lcoords == a) * w).sum(axis=1) for a in range(4)], axis=1)


def mixture_measure(lcoords, weights) -> np.ndarray:
    """
    Entropy of the age shares, over log 4: 0 when all the digits are one age, 1 when the four ages weigh the same.
    Unlike purity (the largest share minus the smallest), it sees every share.
    """
    p = age_shares(lcoords, weights)
    with np.errstate(divide='ignore', invalid='ignore'):
        terms = np.where(p > 0, -p * np.log(p), 0.0)
    return terms.sum(axis=1) / np.log(4)


def tension_measure(lcoords, weights) -> np.ndarray:
    """
    Weighted standard deviation of the virtues, over its largest value (3/8, half Satya and half Kali): 0 for one
    age, 1 for the farthest ages mixed half and half. A Satya–Kali mix is tenser than a Satya–Treta one.
    """
    v = np.atleast_2d(virtues(lcoords))
    w = _normalised(weights)
    mean = v @ w
    return np.sqrt(((v - mean[:, None]) ** 2) @ w) / (VIRTUE_SPAN / 2)


def _steps(lcoords, weights):
    """Changes of virtue from each level to the next (inner minus outer) and their normalised weights."""
    v = np.atleast_2d(virtues(lcoords))
    if v.shape[1] < 2:
        return np.zeros((len(v), 0)), np.zeros(0)
    # a step between levels k and k + 1 weighs as the outer of the two
    return np.diff(v, axis=1), _normalised(np.asarray(weights, dtype=float)[:-1])


def trend_measure(lcoords, weights) -> np.ndarray:
    """
    Weighted mean change of virtue from each level to the next inner one, over 3/4: positive when the inner levels
    are better than the outer ones (a rise inside a decline, like an utsarpiṇī inside an avasarpiṇī), negative
    when they are worse; from -1 to 1, 0 at depth 1.
    """
    steps, w = _steps(lcoords, weights)
    return steps @ w / VIRTUE_SPAN if len(w) else np.zeros(len(steps))


def roughness_measure(lcoords, weights) -> np.ndarray:
    """Weighted mean size of the changes of virtue between consecutive levels, over 3/4: from 0 (smooth) to 1."""
    steps, w = _steps(lcoords, weights)
    return np.abs(steps) @ w / VIRTUE_SPAN if len(w) else np.zeros(len(steps))


def contrast_measure(dharmas) -> np.ndarray:
    """
    Jump of dharma at the start of each subcycle of a whole level (in time order): its dharma minus that of the
    previous one, over 3/4 (from -1 to 1). The cycle repeats, so the first follows the last.
    """
    dharmas = np.asarray(dharmas, dtype=float)
    return (dharmas - np.roll(dharmas, 1)) / VIRTUE_SPAN


def balance_measure(dharmas, durations) -> np.ndarray:
    """
    Accumulated balance at the end of each subcycle of a whole level (in time order): the running sum of
    (dharma − its mean over the cycle) × duration, the mean weighted by duration, so that it is 0 at the end of the
    cycle. Rising while the subcycles are better than the mean, falling while worse; its extremes are turning points.
    """
    dharmas, durations = np.asarray(dharmas, dtype=float), np.asarray(durations, dtype=float)
    mean = np.dot(dharmas, durations) / durations.sum()
    return np.cumsum((dharmas - mean) * durations)


# The measures: label, nominal range (None: no fixed range), the parameter they depend on ('color_base' and
# 'purity_base' as in division.COLOR_PARAMETER_EFFECTS, 'model' for the cycle model) and a description.
MEASURES = {
    'dharma': dict(label='Dharma', range=(0.25, 1.0), parameter='color_base',
                   description='Weighted mean virtue of the ages of the address'),
    'purity': dict(label='Purity', range=(0.0, 1.0), parameter='purity_base',
                   description='Largest weighted share of an age minus the smallest'),
    'mixture': dict(label='Mixture', range=(0.0, 1.0), parameter='purity_base',
                    description='Entropy of the weighted age shares (0: one age, 1: all four alike)'),
    'tension': dict(label='Tension', range=(0.0, 1.0), parameter='color_base',
                    description='Weighted spread of the virtues (how far apart the mixed ages are)'),
    'trend': dict(label='Trend', range=(-1.0, 1.0), parameter='color_base',
                  description='Inner levels better (+) or worse (−) than the outer ones'),
    'roughness': dict(label='Roughness', range=(0.0, 1.0), parameter='color_base',
                      description='Mean size of the jumps of virtue between consecutive levels'),
    'contrast': dict(label='Contrast', range=(-1.0, 1.0), parameter='color_base',
                     description='Jump of dharma from the previous subcycle (sandhi)'),
    'balance': dict(label='Balance', range=None, parameter='color_base',
                    description='Running sum of (dharma − mean) × duration from the start of the cycle'),
    'density': dict(label='Angular density', range=None, parameter='model',
                    description='Share of the precession arc over share of the time (the local mean rate '
                                'over the cycle\'s)'),
}
ADDRESS_MEASURES = tuple(key for key, m in MEASURES.items() if m['parameter'] != 'model')


def address_measures(lcoords, durations, dharmas, purities, bases) -> dict[str, np.ndarray]:
    """
    Every measure of ``ADDRESS_MEASURES`` for a whole level in time order (``lcoords`` (N, depth), its durations,
    dharmas and purities), with the weights of ``bases`` (``bases[1]`` for the virtues, ``bases[2]`` for the shares).
    """
    from cycles.functions.division import weights
    lcoords = np.asarray(lcoords, dtype=int)
    depth = lcoords.shape[1]
    w1, w2 = weights(bases[1], depth), weights(bases[2], depth)
    return {
        'dharma': np.asarray(dharmas, dtype=float),
        'purity': np.asarray(purities, dtype=float),
        'mixture': mixture_measure(lcoords, w2),
        'tension': tension_measure(lcoords, w1),
        'trend': trend_measure(lcoords, w1),
        'roughness': roughness_measure(lcoords, w1),
        'contrast': contrast_measure(dharmas),
        'balance': balance_measure(dharmas, durations),
    }
