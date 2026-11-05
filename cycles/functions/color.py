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


# Parameters of the colorings (see division.compute_level) and the values for
# which the colors of the subcycles of a level are all different (as RGB):
#
# * bases[1], the base of the position weights b^-k of the CMYK colorings (and
#   of dharma): b >= 2. Then each weight is at least the sum of all the later
#   ones, so the weighted ink sums give back the address. Below 2 colors repeat
#   at isolated bases (the golden ratio from depth 3; b = 1 from depth 2).
# * scales[0], cmyk_scaled: 0 < s <= 1 (the CMYK to RGB conversion of colors
#   whose inks add up to s is then one-to-one).
# * scales[1], black of cmyk_kscaled: t in [0, 1/4] or [1/2, 1]. In between the
#   conversion to RGB can have two preimages (no repeated colors were found
#   there for the subcycles, but uniqueness is not guaranteed).
# * scales[2], step of the tetrahedron coloring: 1/2 <= s < 1. Then the last
#   digit outweighs all the earlier ones; below 1/2 colors repeat at isolated
#   steps (0.382 from depth 3), and s = 1 keeps only the last digit.
# * colors, the four vertices of the tetrahedron coloring: RGB values in [0, 1]
#   that are affinely independent (a tetrahedron of nonzero volume), so that a
#   color gives back its barycentric coordinates. Flat sets may still give
#   unique colors (a square, a triangle and its centre), but not always: four
#   colors on a line repeat from depth 2, two equal ones from depth 1. The
#   largest tetrahedron in the
#   RGB cube (volume 1/3, the default yellow, cyan, magenta, black) keeps the
#   colors furthest apart.
#
# bases[2], the base of the purity weights, needs no such bound (1 weighs every
# level equally). Larger bases and steps keep the colors unique but bring the
# deep levels closer together, below what a display can show apart.
COLOR_BASE_MIN = 2.0
CMYK_SCALE_RANGE = (0.0, 1.0)             # open at 0
BLACK_SCALE_RANGES = ((0.0, 0.25), (0.5, 1.0))
TETRAHEDRON_STEP_RANGE = (0.5, 1.0)       # open at 1
MAX_TETRAHEDRON_VOLUME = 1 / 3            # largest tetrahedron inside the RGB cube


def tetrahedron_volume(colors) -> float:
    """Volume of the tetrahedron with the four RGB ``colors`` as vertices."""
    v = np.asarray(colors, dtype=float)
    return abs(np.linalg.det(v[1:] - v[0])) / 6


def color_parameter_problems(bases, scales, colors=None) -> list[str]:
    """
    Reasons why ``bases``, ``scales`` and the tetrahedron ``colors`` (as in
    ``division.compute_level``) may give repeated colors within a level; empty
    if they cannot.
    """
    problems = []
    if bases[1] < COLOR_BASE_MIN:
        problems.append(f"the color weight base must be at least {COLOR_BASE_MIN:g}")
    if not CMYK_SCALE_RANGE[0] < scales[0] <= CMYK_SCALE_RANGE[1]:
        problems.append("the cmyk_scaled scale must be in (0, 1]")
    if not any(low <= scales[1] <= high for low, high in BLACK_SCALE_RANGES):
        problems.append("the cmyk_kscaled black scale must be in [0, 0.25] or [0.5, 1]")
    if not TETRAHEDRON_STEP_RANGE[0] <= scales[2] < TETRAHEDRON_STEP_RANGE[1]:
        problems.append("the tetrahedron step must be in [0.5, 1)")
    if bases[2] <= 0:
        problems.append("the purity weight base must be positive")
    if colors is not None:
        colors = np.asarray(colors, dtype=float)
        if colors.shape != (4, 3) or np.any((colors < 0) | (colors > 1)):
            problems.append("the tetrahedron needs four RGB colors with values in [0, 1]")
        elif tetrahedron_volume(colors) < 1e-9:
            problems.append("the four tetrahedron colors must not lie in one plane")
    return problems
