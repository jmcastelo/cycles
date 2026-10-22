import numpy as np

from cycles.functions.conversion import kronecker_vector
from cycles.functions.duration import count_digits


def lcoords_to_cmyk(lcoords: np.ndarray, weights: np.ndarray, scales: list[float]) -> np.ndarray:
    vw = np.array([np.dot(kronecker_vector(i, lcoords), weights) for i in range(4)], dtype=float)
    sum_weights = np.sum(weights, dtype=float)
    composition = count_digits(lcoords)
    return np.array([
        vw,
        vw / sum_weights,
        vw * scales[0] / sum_weights,
        vw * [1, 1, 1, scales[1]] / sum_weights,
        composition / np.sum(composition),
        (np.append(vw[1:], 0)) / sum_weights,
    ])


def cmyk_to_rgb(cmyk: np.ndarray) -> np.ndarray:
    return (np.ones(3) - cmyk[:3]) * (1 - cmyk[3])
    # return (np.ones(3) - np.array([cmyk[0], cmyk[2], cmyk[1]])) * (1 - cmyk[3])


def lcoords_to_lrgb(lcoords: np.ndarray) -> np.ndarray:
    wcmy = np.array([[0, 0, 0, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]], dtype=float)
    return np.array([cmyk_to_rgb(wcmy[lcoords[d]]) for d in range(len(lcoords))])


def lcoords_to_rgb_tetrahedron(lcoords: np.ndarray, colors: np.ndarray, scale: float) -> np.ndarray:
    center = np.mean(colors, axis=0)
    for alpha in lcoords:
        delta = (colors[alpha] - center) * scale
        center += delta
    return center