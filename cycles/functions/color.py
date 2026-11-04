"""
Colorings of subcycles from their addresses.

The four ages are mapped to the four process inks: Golden (0) -> cyan,
Silver (1) -> magenta, Bronze (2) -> yellow, Iron (3) -> black.
"""

import numpy as np

from cycles.functions.conversion import kronecker_vector
from cycles.functions.duration import count_digits


def lcoords_to_cmyk(lcoords: np.ndarray, weights: np.ndarray, scales: list[float]) -> np.ndarray:
    """
    CMYK color variants of a subcycle, as a (6, 4) array.

    Each digit adds its position weight (``weights[k]``) to the ink of its age.
    The rows, in the order of ``division.CMYK_KEYS``, are:

    0. ``cmyk``: the weighted ink sums.
    1. ``cmyk_normalised``: divided by the sum of the weights.
    2. ``cmyk_scaled``: normalised and multiplied by ``scales[0]``.
    3. ``cmyk_kscaled``: normalised, with only black multiplied by ``scales[1]``.
    4. ``cmyk_composition``: unweighted digit counts divided by the depth.
    5. ``wcmy``: normalised and shifted down one ink (Golden -> white, Silver ->
       cyan, Bronze -> magenta, Iron -> yellow, no black).
    """
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
    """Simple CMYK to RGB conversion: ``(1 - CMY) * (1 - K)``."""
    return (np.ones(3) - cmyk[:3]) * (1 - cmyk[3])
    # return (np.ones(3) - np.array([cmyk[0], cmyk[2], cmyk[1]])) * (1 - cmyk[3])


def lcoords_to_lrgb(lcoords: np.ndarray) -> np.ndarray:
    """
    RGB color of the pure ink of each digit of ``lcoords``, as a (depth, 3) array.

    Row ``k`` is the color of the age at level ``k``; ``[-1]`` is the color of
    the innermost level.
    """
    cmyk = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=float)
    return np.array([cmyk_to_rgb(cmyk[lcoords[d]]) for d in range(len(lcoords))])


def lcoords_to_rgb_tetrahedron(lcoords: np.ndarray, colors: np.ndarray, scale: float) -> np.ndarray:
    """
    Color from a "chaos game" in RGB space, giving a Sierpinski tetrahedron.

    ``colors`` are the four vertex colors (one per age). Starting at their
    centroid, each digit moves the point a fraction ``scale`` of the way towards
    the vertex of its age. With ``scale = 0.5`` the colors of all addresses fill
    a Sierpinski tetrahedron.
    """
    center = np.mean(colors, axis=0)
    for alpha in lcoords:
        delta = (colors[alpha] - center) * scale
        center += delta
    return center