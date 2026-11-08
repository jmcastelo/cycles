"""
Colorings of subcycles from their addresses.

The four ages are mapped to the four process inks: Golden (0) -> cyan,
Silver (1) -> magenta, Bronze (2) -> yellow, Iron (3) -> black.
"""

import functools

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
        elif tetrahedron_volume(colors) < 1e-9 or tetrahedron_volume(srgb_to_oklab(colors)) < 1e-9:
            problems.append("the four tetrahedron colors must not lie in one plane (in RGB or in OKLab)")
    return problems


# -- OKLab (Björn Ottosson, 2020): a perceptual color space where distances match what we see

_LMS = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                 [0.2119034982, 0.6806995451, 0.1073969566],
                 [0.0883024619, 0.2817188376, 0.6299787005]])
_LAB = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                 [1.9779984951, -2.4285922050, 0.4505937099],
                 [0.0259040371, 0.7827717662, -0.8086757660]])
_LMS_INV, _LAB_INV = np.linalg.inv(_LMS), np.linalg.inv(_LAB)


def srgb_to_oklab(rgb) -> np.ndarray:
    """OKLab coordinates (L, a, b) of sRGB colors in [0, 1] (any shape ending in 3)."""
    c = np.asarray(rgb, dtype=float)
    linear = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return np.cbrt(linear @ _LMS.T) @ _LAB.T


def oklab_to_srgb(lab) -> np.ndarray:
    """sRGB colors of OKLab coordinates (outside [0, 1] where the color is out of the sRGB gamut)."""
    linear = ((np.asarray(lab, dtype=float) @ _LAB_INV.T) ** 3) @ _LMS_INV.T
    return np.where(linear <= 0.0031308, 12.92 * linear,
                    1.055 * np.sign(linear) * np.abs(linear) ** (1 / 2.4) - 0.055 * np.sign(linear))


def _chaos_game(lcoords: np.ndarray, vertices: np.ndarray, scale: float) -> np.ndarray:
    """The chaos game of ``lcoords_to_rgb_tetrahedron`` for a whole level at once: (N, 3) points."""
    lcoords = np.atleast_2d(np.asarray(lcoords, dtype=int))
    points = np.repeat(vertices.mean(axis=0)[None], len(lcoords), axis=0)
    for k in range(lcoords.shape[1]):
        points = points + scale * (vertices[lcoords[:, k]] - points)
    return points


OKLAB_CHECK_DEPTH = 8      # the deepest level of the explorer: the shrunk tetrahedron fits the gamut down to it


def oklab_tetrahedron(colors, scale: float, check_depth: int = OKLAB_CHECK_DEPTH) -> np.ndarray:
    """
    The vertices, in OKLab, of the tetrahedron of the ``tetrahedron_oklab`` coloring: the four vertex ``colors``
    (RGB) taken to OKLab and shrunk towards their centroid by the largest factor (to 0.1 %) that keeps the colors of
    every subcycle down to ``check_depth`` inside the sRGB gamut. The gamut is not convex in OKLab, so straight
    lines between in-gamut colors can leave it (yellow to magenta does); shrinking keeps the geometry exact where
    clipping would not. With the default yellow, cyan, magenta and black the factor is about 0.965.
    """
    return np.array(_oklab_tetrahedron(tuple(map(tuple, np.asarray(colors, dtype=float))), float(scale),
                                       int(check_depth)))


@functools.lru_cache(maxsize=16)
def _oklab_tetrahedron(colors: tuple, scale: float, check_depth: int) -> tuple:
    vertices = srgb_to_oklab(np.asarray(colors, dtype=float))
    centre = vertices.mean(axis=0)
    lcoords = (np.arange(4 ** check_depth)[:, None] // 4 ** np.arange(check_depth - 1, -1, -1)) % 4

    def fits(factor: float) -> bool:
        rgb = oklab_to_srgb(_chaos_game(lcoords, centre + factor * (vertices - centre), scale))
        return bool(np.all((rgb > -1e-9) & (rgb < 1 + 1e-9)))

    if fits(1.0):
        return tuple(map(tuple, vertices))
    low, high = 0.0, 1.0
    while high - low > 1e-3:
        middle = (low + high) / 2
        low, high = (middle, high) if fits(middle) else (low, middle)
    return tuple(map(tuple, centre + low * (vertices - centre)))


def level_rgb_oklab_tetrahedron(lcoords, colors, scale: float, vertices=None) -> np.ndarray:
    """
    The ``tetrahedron_oklab`` coloring of a whole level (``lcoords`` (N, depth)): the chaos game of the tetrahedron
    coloring played in OKLab (``vertices``, from ``oklab_tetrahedron`` unless given), so that equal steps of the
    game are equal steps to the eye and the regions of the four ages look equally large. As RGB, (N, 3).
    """
    vertices = oklab_tetrahedron(colors, scale) if vertices is None else vertices
    return np.clip(oklab_to_srgb(_chaos_game(lcoords, vertices, scale)), 0.0, 1.0)


def oklch_to_srgb(lightness, chroma, hue_degrees) -> np.ndarray:
    """sRGB (clipped to [0, 1]) of colors given by OKLab lightness, chroma and hue angle."""
    h = np.radians(np.asarray(hue_degrees, dtype=float))
    lab = np.stack(np.broadcast_arrays(np.asarray(lightness, dtype=float), chroma * np.cos(h), chroma * np.sin(h)),
                   axis=-1)
    return np.clip(oklab_to_srgb(lab), 0.0, 1.0)


# -- colorings by class, by measure and by the vernal point

GOLDEN_ANGLE = 137.50776405003785


def duration_class_colors(durations) -> np.ndarray:
    """
    One color per class of equal duration (``duration_class`` coloring), as (N, 3) RGB: the classes, longest
    first, take hues a golden angle apart (each far from the previous ones) and three alternating lightnesses, in
    OKLab so that they all look equally strong.
    """
    durations = np.asarray(durations, dtype=float)
    keys = np.round(np.log(durations), 9)
    classes, inverse = np.unique(-keys, return_inverse=True)          # rank 0 = the longest
    rank = np.arange(len(classes))
    palette = oklch_to_srgb(np.array([0.74, 0.60, 0.86])[rank % 3], 0.12, 30 + rank * GOLDEN_ANGLE)
    return palette[inverse.ravel()]


def measure_colors(values, key: str):
    """
    RGB colors (N, 3) of ``values`` of the measure ``key`` (``measure.MEASURES``) and the matplotlib mappable,
    for a color bar: a diverging map (centred on 0, on 1 for the angular density) for the signed measures, a
    sequential one otherwise, over the measure's nominal range (the values' own range if it has none).
    """
    from matplotlib import colormaps
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    from cycles.functions.measure import MEASURES
    values = np.asarray(values, dtype=float)
    lo_hi = MEASURES[key]['range']
    finite = values[np.isfinite(values)]
    if lo_hi is None:
        lo_hi = (float(finite.min()), float(finite.max())) if len(finite) else (0.0, 1.0)
        if key == 'balance':                      # signed: centre 0
            edge = max(abs(lo_hi[0]), abs(lo_hi[1])) or 1.0
            lo_hi = (-edge, edge)
        elif lo_hi[0] == lo_hi[1]:
            lo_hi = (lo_hi[0] - 0.5, lo_hi[1] + 0.5)
    diverging = lo_hi[0] < 0 < lo_hi[1] or key == 'density'
    if key == 'density':                          # centre 1, the cycle's mean rate
        edge = max(abs(lo_hi[0] - 1), abs(lo_hi[1] - 1)) or 0.01
        lo_hi = (1 - edge, 1 + edge)
    mappable = ScalarMappable(Normalize(*lo_hi), colormaps['RdBu_r' if diverging else 'viridis'])
    return mappable.to_rgba(np.nan_to_num(values, nan=lo_hi[0]))[:, :3], mappable


# The zodiac: Aries (0) to Pisces (11); the element of a sign is its index mod 4
SIGN_HUES = (np.arange(12) * 30.0 + 25.0) % 360           # Aries red, round the hue circle
ELEMENT_NAMES = ('fire', 'earth', 'air', 'water')
ELEMENT_COLORS = np.array([[0.85, 0.25, 0.17],             # fire: red
                           [0.31, 0.60, 0.23],             # earth: green
                           [0.90, 0.77, 0.25],             # air: yellow
                           [0.23, 0.44, 0.77]])            # water: blue


def vernal_point_longitude(ayanamsa) -> np.ndarray:
    """Sidereal longitude (degrees, [0, 360)) of the vernal point, which is at 0° tropical: −ayanamsa."""
    return np.mod(-np.asarray(ayanamsa, dtype=float), 360.0)


def vernal_colors(ayanamsa, mode: str = 'sign') -> np.ndarray:
    """
    Colors (N, 3) of the sign (``'sign'``: twelve hues, Aries red) or of the element of the sign (``'element'``:
    fire red, earth green, air yellow, water blue) in which the vernal point stands at the given ayanamsas.
    """
    sign = (vernal_point_longitude(ayanamsa) // 30).astype(int) % 12
    if mode == 'element':
        return ELEMENT_COLORS[sign % 4]
    return oklch_to_srgb(0.70, 0.13, SIGN_HUES[sign])
