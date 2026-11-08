"""
Fractal division of a cycle into four ages and their subcycles.

A cycle is divided into four ages with proportions 0.4, 0.3, 0.2 and 0.1 of
its length (Golden, Silver, Bronze and Iron; or Satya, Treta, Dvapara and
Kali). Each age is divided again in the same way, and so on. A subcycle at
depth ``d`` is identified by its address (``lcoords``): ``d`` digits, each the
age chosen at one level. Durations and starts are fractions of the whole cycle.
"""

import numpy as np
import itertools as itools
from typing import NamedTuple

from cycles.functions.conversion import tcoord_to_lcoords
from cycles.functions.color import (
    DEFAULT_COLOR_MAPS, cmyk_to_rgb, duration_class_colors, lcoords_to_cmyk, lcoords_to_lrgb,
    lcoords_to_rgb_tetrahedron, level_rgb_oklab_tetrahedron, level_rgb_tetrahedron, measure_colors,
)
from cycles.functions.duration import count_digits
from cycles.functions.measure import dharma_measure, purity_measure


# Share of its parent cycle taken by each age (Golden, Silver, Bronze, Iron), and
# where each age starts within its parent (0, 0.4, 0.7, 0.9).
proportions = np.array([0.4, 0.3, 0.2, 0.1], dtype=float)
offsets = np.insert(np.cumsum(proportions[:-1], dtype=float), 0, 0)


# Names of the color variants stored in a Level, in storage order.
# CMYK variants come from lcoords_to_cmyk; the RGB variants are those same
# variants converted to RGB, plus the Sierpinski tetrahedron coloring.
CMYK_KEYS = ('cmyk', 'cmyk_normalised', 'cmyk_scaled', 'cmyk_kscaled', 'cmyk_composition', 'wcmy')
RGB_KEYS = CMYK_KEYS + ('tetrahedron', 'tetrahedron_oklab')

# 'cmyk_normalised' is the coloring of the original code (one CMYK/RGB color per subcycle)
DEFAULT_COLOR_KEY = 'cmyk_normalised'

# Default parameters of compute_level:
# [division base, color weight base, purity weight base]
DEFAULT_BASES = [4, 2, 2]
# [cmyk scale, black scale, tetrahedron step]
DEFAULT_SCALES = [1 / 2, 2 / 3, 0.5]
# Vertex colors of the tetrahedron coloring: Golden, Silver, Bronze, Iron
TETRAHEDRON_COLORS = np.array([[1, 1, 0], [0, 1, 1], [1, 0, 1], [0, 0, 0]])

# The colorings. level_colors gives those of a Level alone (the RGB variants and two more, and dharma and purity);
# the other measures of MEASURE_COLOR_KEYS also need the weights (gui.state.LevelCache), those of
# MODEL_COLOR_KEYS the cycle model and those of SKY_COLOR_KEYS the model and the ephemeris
# (gui.state.CycleState.colors). The measures take the sequential or the diverging
# color map of color.DEFAULT_COLOR_MAPS, or of the parameters.
LEVEL_COLOR_KEYS = RGB_KEYS + ('lrgb', 'duration_class')
MEASURE_COLOR_KEYS = ('dharma', 'purity', 'mixture', 'tension', 'trend', 'roughness', 'contrast', 'balance',
                      'microcosm', 'complexity')
MODEL_COLOR_KEYS = ('density', 'vernal_sign', 'vernal_element')
SKY_COLOR_KEYS = ('gathering', 'trigon_sidereal', 'trigon_tropical')      # need the model and the ephemeris
STATE_COLOR_KEYS = MODEL_COLOR_KEYS + SKY_COLOR_KEYS                     # given by CycleState.colors
COLOR_KEYS = LEVEL_COLOR_KEYS + MEASURE_COLOR_KEYS + STATE_COLOR_KEYS
COLOR_DESCRIPTIONS = {
    'cmyk': 'the ages as inks (Satya cyan, Treta magenta, Dvapara yellow, Kali black), weighted by level',
    'cmyk_normalised': 'the weighted inks divided by the sum of the weights',
    'cmyk_scaled': 'normalised and lightened by the cmyk_scaled scale',
    'cmyk_kscaled': 'normalised, with only the black lightened',
    'cmyk_composition': 'the digit counts as inks: one color per composition',
    'wcmy': 'normalised and shifted one ink: Satya white, Treta cyan, Dvapara magenta, Kali yellow',
    'tetrahedron': 'chaos game towards the four vertex colors, in RGB: a Sierpinski tetrahedron',
    'tetrahedron_oklab': 'the same chaos game in OKLab, a perceptual space: equal steps look equal',
    'lrgb': 'the ink of the innermost age',
    'duration_class': 'one color per class of equal duration',
    'dharma': 'dharma (weighted mean virtue), on the sequential map',
    'purity': 'purity (largest share of an age minus the smallest), on the sequential map',
    'mixture': 'mixture (entropy of the age shares), on the sequential map',
    'tension': 'tension (spread of the virtues), on the sequential map',
    'trend': 'trend (inner levels better or worse), on the diverging map: 0 in the middle',
    'roughness': 'roughness (jumps between levels), on the sequential map',
    'contrast': 'contrast (the jump of dharma from the previous subcycle), on the diverging map',
    'balance': 'balance (running sum of dharma above its mean), on the diverging map',
    'microcosm': 'microcosm (how closely the age shares match the whole cycle\'s), on the sequential map',
    'complexity': 'complexity (Lempel–Ziv, of the order of the ages), on the sequential map',
    'density': 'angular density (needs a cycle model), on the diverging map: 1, the mean rate, in the middle',
    'vernal_sign': 'the sidereal sign of the vernal point at the start (needs a cycle model)',
    'vernal_element': 'the element of that sign: fire red, earth green, air yellow, water blue (needs a model)',
    'gathering': 'how gathered Sun to Saturn are at the start, on the sequential map (needs a model and the '
                 'ephemeris)',
    'trigon_sidereal': 'the element of the great conjunctions in force at the start, sidereal zodiac: fire red, '
                       'earth green, air yellow, water blue (needs a model and the ephemeris)',
    'trigon_tropical': 'the same in the tropical zodiac (needs a model and the ephemeris)',
}

# Colorings (and measures, of the same names) that each color parameter changes; cmyk_composition and lrgb depend
# on none. The color base also changes the dharma values and the measures of measure.MEASURES built on the
# virtues, and the purity base the purity and mixture values; the two color maps only the colorings of the
# measures (CycleState.measure_parameters_of leaves them out).
COLOR_PARAMETER_EFFECTS = {
    'color_base': ('cmyk', 'cmyk_normalised', 'cmyk_scaled', 'cmyk_kscaled', 'wcmy', 'dharma',    # bases[1]
                   'tension', 'trend', 'roughness', 'contrast', 'balance'),
    'purity_base': ('purity', 'mixture', 'microcosm'),                                          # bases[2]
    'cmyk_scale': ('cmyk_scaled',),                                                             # scales[0]
    'black_scale': ('cmyk_kscaled',),                                                           # scales[1]
    'tetrahedron_step': ('tetrahedron', 'tetrahedron_oklab'),                                   # scales[2]
    'tetrahedron_colors': ('tetrahedron', 'tetrahedron_oklab'),                                 # colors
    'sequential_map': ('dharma', 'purity', 'mixture', 'tension', 'roughness', 'microcosm',     # maps[0]
                       'complexity', 'gathering'),
    'diverging_map': ('trend', 'contrast', 'balance', 'density'),                               # maps[1]
}


class Level(NamedTuple):
    """
    All the subcycles at one depth, as returned by compute_level.

    Being a NamedTuple, it can still be unpacked as a 7-tuple.
    """
    lcoords: np.ndarray     # (N, depth)
    durations: np.ndarray   # (N,)
    starts: np.ndarray      # (N,)
    cmyks: np.ndarray       # (N, len(CMYK_KEYS), 4)
    rgbs: np.ndarray        # (N, len(RGB_KEYS), 3)
    dharmas: np.ndarray     # (N,)
    purities: np.ndarray    # (N,)

    def cmyk(self, key: str = DEFAULT_COLOR_KEY) -> np.ndarray:
        """CMYK colors (N, 4) of the given variant."""
        return self.cmyks[:, CMYK_KEYS.index(key)]

    def rgb(self, key: str = DEFAULT_COLOR_KEY) -> np.ndarray:
        """RGB colors (N, 3) of the given variant."""
        return self.rgbs[:, RGB_KEYS.index(key)]

    def subset(self, index) -> 'Level':
        """Level restricted to the subcycles selected by index (array of indices or mask)."""
        return Level(*(field[index] for field in self))


def level_colors(level: Level, maps=DEFAULT_COLOR_MAPS) -> dict[str, np.ndarray]:
    """
    RGB color of every subcycle of ``level`` for each name in ``LEVEL_COLOR_KEYS``:
    the Level's RGB variants, ``lrgb`` (pure ink of the innermost age) and
    ``duration_class`` (one color per class of equal duration); and ``dharma``
    and ``purity`` on the sequential map of ``maps`` (``color.measure_colors``).
    """
    colors = {key: level.rgb(key) for key in RGB_KEYS}
    inks = np.array([[0, 1, 1], [1, 0, 1], [1, 1, 0], [0, 0, 0]], dtype=float)    # pure cyan, magenta, yellow, black
    colors['lrgb'] = inks[level.lcoords[:, -1]]
    colors['dharma'] = measure_colors(level.dharmas, 'dharma', maps)[0]
    colors['purity'] = measure_colors(level.purities, 'purity', maps)[0]
    colors['duration_class'] = duration_class_colors(level.durations)
    return colors


def weights(base: int, depth: int) -> np.ndarray:
    """
    Weight of each digit position: ``base^-1, base^-2, ..., base^-depth``.

    Used by colors and measures, so that outer levels count more.
    """
    return np.array([base ** (-k) for k in range(1, depth + 1)])


def compute_duration(lcoords: np.ndarray) -> float:
    """
    Duration of a subcycle as a fraction of the whole cycle: the product of the
    proportions of the ages in its address.
    """
    lcoords = np.asarray(lcoords, dtype=int)
    return np.prod(proportions[lcoords], dtype=float)


def compute_start(lcoords: np.ndarray) -> float:
    """Start of a subcycle as a fraction of the whole cycle."""
    lcoords = np.asarray(lcoords, dtype=int)
    return np.dot(offsets[lcoords], np.insert(np.cumprod(proportions[lcoords][:-1]), 0, 1))


def level_lcoords(depth: int, base: int = 4) -> np.ndarray:
    """The addresses of all ``base^depth`` subcycles of ``depth``, in time order: (N, depth) digits."""
    return (np.arange(base ** depth)[:, None] // base ** np.arange(depth - 1, -1, -1)) % base


def compute_level(depth: int, bases: list[int] = DEFAULT_BASES, scales: list[float] = DEFAULT_SCALES,
                  colors: np.ndarray = TETRAHEDRON_COLORS) -> Level:
    """
    All ``bases[0]^depth`` subcycles of depth ``depth``, in time order.

    Parameters
    ----------
    bases : [division base (4), color weight base, purity weight base]
    scales : [scales[0], scales[1]] for ``color.lcoords_to_cmyk``, and
        ``scales[2]`` for ``color.lcoords_to_rgb_tetrahedron``
    colors : the four vertex colors of the tetrahedron coloring

    The defaults are ``DEFAULT_BASES``, ``DEFAULT_SCALES`` and
    ``TETRAHEDRON_COLORS``.

    Returns a ``Level``: addresses, durations, starts, all CMYK and RGB color
    variants, dharma and purity of each subcycle.
    """
    lcoords = level_lcoords(depth, bases[0])
    n = len(lcoords)
    shares = proportions[lcoords]                                   # (N, depth)
    durations = np.prod(shares, axis=1) if depth else np.ones(n)
    # the start: each digit's offset scaled by the product of the shares of the levels above it
    above = np.hstack([np.ones((n, 1)), np.cumprod(shares, axis=1)[:, :-1]]) if depth else np.ones((n, 0))
    starts = np.sum(offsets[lcoords] * above, axis=1)

    w1 = weights(bases[1], depth)
    ink = lcoords[:, :, None] == np.arange(4)                       # (N, depth, 4): the ink of each digit
    sums = np.einsum('nki,k->ni', ink, w1)                          # weighted ink sums (lcoords_to_cmyk)
    normalised = sums / w1.sum()
    composition = ink.sum(axis=1) / max(depth, 1)
    cmyks = np.stack([sums, normalised, normalised * scales[0], normalised * [1, 1, 1, scales[1]], composition,
                      np.hstack([normalised[:, 1:], np.zeros((n, 1))])], axis=1)
    rgbs = (1 - cmyks[:, :, :3]) * (1 - cmyks[:, :, 3:])           # cmyk_to_rgb for every variant
    colors = np.asarray(colors, dtype=float)
    rgbs_tetrahedron = level_rgb_tetrahedron(lcoords, colors, scales[2])[:, None]
    rgbs_oklab = level_rgb_oklab_tetrahedron(lcoords, colors, scales[2])[:, None]
    all_rgbs = np.concatenate((rgbs, rgbs_tetrahedron, rgbs_oklab), axis=1)
    dharmas = (4 - lcoords) @ w1 / (4 * w1.sum())                   # dharma_measure

    w2 = weights(bases[2], depth)
    purity_shares = np.einsum('nki,k->ni', ink, w2)                 # purity_measure
    purities = (purity_shares.max(axis=1) - purity_shares.min(axis=1)) / w2.sum()

    return Level(lcoords, durations, starts, cmyks, all_rgbs, dharmas, purities)


def compute_levels_by_duration(depths: list[int], bases: list[int], scales: list[float]) -> dict:
    """
    Subcycles of several depths, grouped by duration.

    Returns a dict whose keys are durations (rounded to 10 decimals) and whose
    values are lists with one dict per subcycle, holding its depth, composition,
    tcoord, lcoords, duration, start, dharma, purity and a ``colors`` dict with
    the RGB color of each variant (see ``bases`` and ``scales`` in
    ``compute_level``).
    """
    subcycles = {}

    for depth in depths:
        for tcoord in range(bases[0] ** depth):
            lcoords = tcoord_to_lcoords(tcoord, bases[0], depth)
            duration = compute_duration(lcoords)
            start = compute_start(lcoords)

            w1 = weights(bases[1], depth)
            cmyks = lcoords_to_cmyk(lcoords, w1, scales)
            rgbs = [cmyk_to_rgb(cmyk) for cmyk in cmyks]
            lrgb = lcoords_to_lrgb(lcoords)

            dharma = dharma_measure(lcoords, w1)
            dharma_color = np.full(3, dharma)

            w2 = weights(bases[2], depth)
            purity = purity_measure(lcoords, w2)
            purity_color = np.full(3, purity)

            value = {
                'depth': depth,
                'composition': count_digits(lcoords, bases[0]),
                'tcoord': tcoord,
                'lcoords': lcoords,
                'duration': duration,
                'start': start,
                'dharma': dharma,
                'purity': purity,
                'colors': {
                    'cmyk': rgbs[0],
                    'cmyk_normalised': rgbs[1],
                    'cmyk_scaled': rgbs[2],
                    'cmyk_kscaled': rgbs[3],
                    'cmyk_composition': rgbs[4],
                    'wcmy': rgbs[5],
                    'lrgb': lrgb,
                    'dharma': dharma_color,
                    'purity': purity_color
                }
            }
            key = np.round(duration, 10)
            if key in subcycles.keys():
                subcycles[key].append(value)
            else:
                subcycles[key] = [value]

    return subcycles


'''
def compute_deeper_subcycles(parent_coords: list[int], extra_depth: int, bases: list[int]) -> tuple:
    start_index = lcoords_to_int(parent_coords + [0] * extra_depth)
    end_index = start_index + bases[0]**extra_depth - 1
    print(start_index, end_index)

    depth = len(parent_coords) + extra_depth

    lcoords = np.array([int_to_lcoords(i, bases[0], depth) for i in range(start_index, end_index)], dtype=int)

    durations = np.array([compute_duration(lcoord) for lcoord in lcoords], dtype=float)
    starts = np.array([compute_start(lcoord) for lcoord in lcoords], dtype=float)
    rgbs = np.array([lcoords_to_rgb(lcoord, weights(bases[1], depth)) for lcoord in lcoords], dtype=float)

    return lcoords, durations, starts, rgbs
'''


def select_subcycle(prefix_coords: list[int], level: Level) -> Level:
    """
    The subcycles of ``level`` inside the subcycle whose address is
    ``prefix_coords`` (all of ``level`` if the prefix is empty).
    """
    depth = len(prefix_coords)
    if depth == 0:
        return level
    sel_coords = [i for i, lcoord in enumerate(level.lcoords) if (lcoord[:depth] == prefix_coords).all()]
    return level.subset(sel_coords)


def find_identical(a: np.ndarray, decimals: int=10) -> list:
    """
    Groups of equal values (or rows) of ``a``, after rounding to ``decimals``.

    Returns a list of ``(value, indices)``, sorted by value, where ``indices``
    are the positions in ``a`` holding that value.
    """
    arounded = np.round(a, decimals)
    u, uidx, uinv = np.unique(arounded, axis=0, return_index=True, return_inverse=True)
    uu = uidx[uinv]
    return [(arounded[x], [i for i in range(len(uu)) if uu[i] == x]) for x in uidx]


def find_identical_colors(colors: list[list[float]], decimals: int) -> list:
    """Same as ``find_identical``, for an array of colors."""
    colors_rounded = np.round(colors, decimals)
    u, uidx, uinv = np.unique(colors_rounded, axis=0, return_index=True, return_inverse=True)
    uu = uidx[uinv]
    return [(colors_rounded[x], [i for i in range(len(uu)) if uu[i] == x]) for x in uidx]


def subdivision_map(i: int, u: float) -> float:
    """
    Map a position ``u`` (fraction of a cycle) to the same relative position
    inside age ``i`` of that cycle.
    """
    return proportions[i] * u + offsets[i]


def find_lcoords(x: float, depth: int) -> np.ndarray:
    """
    Address of the subcycle of depth ``depth`` that contains the time ``x``
    (a fraction of the whole cycle).
    """
    lcoords = []
    for d in range(depth):
        for coord, (x1, x2) in enumerate(zip(offsets, offsets + proportions)):
            if x1 <= x < x2:
                lcoords.append(coord)
                break
        x = (x - offsets[lcoords[-1]]) / proportions[lcoords[-1]]
    return np.array(lcoords)


def find_total_lcoords(x: float, dt: float, t: float) -> np.ndarray:
    """
    Address of the largest subcycle that contains time ``x`` and lasts less than
    ``dt``, in a cycle of total length ``t`` (``x`` and ``dt`` in the same units
    as ``t``).
    """
    lcoords = []
    while dt <= t:
        for coord, (x1, x2) in enumerate(zip(offsets, offsets + proportions)):
            if x1 <= x / t < x2:
                lcoords.append(coord)
                break
        x = (x - t * offsets[lcoords[-1]]) / proportions[lcoords[-1]]
        dt /= proportions[lcoords[-1]]
    return np.array(lcoords)


def fill_partition(t1: float, t2: float, t: float, dt: float, dt_min: float) -> tuple:
    """
    Cover the interval ``[t1, t2)`` of a cycle of length ``t`` with subcycles.

    The interval is split into windows of length ``dt``. Inside each window,
    subcycles are taken one after another with ``find_total_lcoords`` (each the
    largest one that fits in what remains of the window) until less than
    ``dt_min`` remains; that remainder is recorded as a gap.

    Returns ``(lcoords, locs, durs, gaps, n)``: the addresses (``None`` for each
    gap), the start time of each subcycle, the durations (subcycles and gaps),
    ``(end, remainder)`` for each window, and the number of windows.
    """
    x, dx = t1, dt
    lcoords = []
    locs = []
    durs = []
    ddurs = []
    loc = x
    n = 0
    while loc < t2:
        x = loc
        while dx > dt_min:
            coords = find_total_lcoords(x, dx, t)
            lcoords.append(coords)
            locs.append(x)
            d = t * compute_duration(coords)
            durs.append(d)
            x += d
            dx -= d
        ddurs.append((x, dx))
        lcoords.append(None)
        durs.append(dx)
        loc += dt
        dx = dt
        n += 1
    return lcoords, locs, durs, ddurs, n


def indentical_duration_lcoords(lcoords: list[int]):
    """
    All distinct reorderings of the digits of ``lcoords``; they all have the same
    duration.
    """
    return set(itools.permutations(lcoords))


def partition_level(level: Level, subdepth: int, base: int) -> list[Level]:
    """
    Split ``level`` into ``base^subdepth`` consecutive groups: the subcycles inside
    each subcycle of depth ``subdepth``. Returns ``[level]`` if ``level`` is not
    deeper than ``subdepth``.
    """
    depth = len(level.lcoords[0])
    if depth > subdepth:
        indices = np.arange(base**depth).reshape(base**subdepth, base**(depth - subdepth))
    else:
        return [level]
    return [level.subset(index) for index in indices]