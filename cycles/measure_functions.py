import numpy as np

from cycles.conversion_functions import kronecker_vector


def dharma_measure(lcoords: np.ndarray, weights: np.ndarray) -> float:
    return np.dot(4 - lcoords, weights) / (4 * np.sum(weights))


def purity_measure(lcoords: np.ndarray, weights: np.ndarray) -> float:
    vw = np.array([np.dot(kronecker_vector(i, lcoords), weights) for i in range(4)], dtype=float)
    sum_weights = np.sum(weights, dtype=float)
    return (np.max(vw, axis=0) - np.min(vw, axis=0)) / sum_weights