import numpy as np

from cycles.conversion_functions import kronecker_vector


def lcoords_to_cmyk(lcoords: np.ndarray, weights: np.ndarray) -> np.ndarray:
    vw = np.array([np.dot(kronecker_vector(i, lcoords), weights) for i in range(4)], dtype=float)
    sum_weights = np.sum(weights, dtype=float)
    return np.array([
        vw / sum_weights,
        (np.append(vw[1:], 0)) / sum_weights
    ])


def cmyk_to_rgb(cmyk: np.ndarray) -> np.ndarray:
    return (np.ones(3) - cmyk[:3]) * (1 - cmyk[3])


def lcoords_to_lrgb(lcoords: np.ndarray) -> np.ndarray:
    wcmy = np.array([[0, 0, 0, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]], dtype=float)
    return np.array([cmyk_to_rgb(wcmy[lcoords[d]]) for d in range(len(lcoords))])