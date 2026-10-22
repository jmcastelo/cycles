import numpy as np
import itertools as itools

from cycles.functions.conversion import tcoord_to_lcoords
from cycles.functions.color import lcoords_to_cmyk, cmyk_to_rgb, lcoords_to_lrgb
from cycles.functions.duration import count_digits
from cycles.functions.measure import dharma_measure, purity_measure


proportions = np.array([0.4, 0.3, 0.2, 0.1], dtype=float)
offsets = np.insert(np.cumsum(proportions[:-1], dtype=float), 0, 0)


def weights(base: int, depth: int) -> np.ndarray:
    return np.array([base ** (-k) for k in range(1, depth + 1)])


def compute_duration(lcoords: np.ndarray) -> float:
    return np.prod(proportions[lcoords], dtype=float)


def compute_start(lcoords: np.ndarray) -> float:
    return np.dot(offsets[lcoords], np.insert(np.cumprod(proportions[lcoords][:-1]), 0, 1))


def compute_level(depth: int, bases: list[int], scale: float) -> tuple:
    lcoords = np.array([tcoord_to_lcoords(i, bases[0], depth) for i in range(bases[0] ** depth)], dtype=int)

    durations = np.apply_along_axis(compute_duration, 1, lcoords)
    starts = np.apply_along_axis(compute_start, 1, lcoords)

    w1 = weights(bases[1], depth)
    cmyks = np.array([lcoords_to_cmyk(lcoord, w1, scale) for lcoord in lcoords], dtype=float)
    rgbs = np.apply_along_axis(cmyk_to_rgb, 2, cmyks)
    dharmas = np.array([dharma_measure(lcoord, w1) for lcoord in lcoords])

    w2 = weights(bases[2], depth)
    purities = np.array([purity_measure(lcoord, w2) for lcoord in lcoords])

    return lcoords, durations, starts, cmyks, rgbs, dharmas, purities


def compute_levels_by_duration(depths: list[int], bases: list[int], scale: float) -> dict:
    subcycles = {}

    for depth in depths:
        for tcoord in range(bases[0] ** depth):
            lcoords = tcoord_to_lcoords(tcoord, bases[0], depth)
            duration = compute_duration(lcoords)
            start = compute_start(lcoords)

            w1 = weights(bases[1], depth)
            cmyks = lcoords_to_cmyk(lcoords, w1, scale)
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


def select_subcycle(prefix_coords: list[int], level: tuple) -> tuple:
    depth = len(prefix_coords)
    if depth == 0:
        return level
    lcoords, durations, starts, colors = level
    sel_coords = [i for i, lcoord in enumerate(lcoords) if (lcoord[:depth] == prefix_coords).all()]
    return lcoords[sel_coords], durations[sel_coords], starts[sel_coords], colors[sel_coords]


def find_identical(a: np.ndarray, decimals: int=10) -> list:
    arounded = np.round(a, decimals)
    u, uidx, uinv = np.unique(arounded, axis=0, return_index=True, return_inverse=True)
    uu = uidx[uinv]
    return [(arounded[x], [i for i in range(len(uu)) if uu[i] == x]) for x in uidx]


def find_identical_colors(colors: list[list[float]], decimals: int) -> list:
    colors_rounded = np.round(colors, decimals)
    u, uidx, uinv = np.unique(colors_rounded, axis=0, return_index=True, return_inverse=True)
    uu = uidx[uinv]
    return [(colors_rounded[x], [i for i in range(len(uu)) if uu[i] == x]) for x in uidx]


def subdivision_map(i: int, u: float) -> float:
    return proportions[i] * u + offsets[i]


def find_lcoords(x: float, depth: int) -> np.ndarray:
    lcoords = []
    for d in range(depth):
        for coord, (x1, x2) in enumerate(zip(offsets, offsets + proportions)):
            if x1 <= x < x2:
                lcoords.append(coord)
                break
        x = (x - offsets[lcoords[-1]]) / proportions[lcoords[-1]]
    return np.array(lcoords)


def find_total_lcoords(x: float, dt: float, t: float) -> np.ndarray:
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
    return set(itools.permutations(lcoords))


def partition_level(level: tuple, subdepth: int, base: int) -> list[tuple]:
    lcoords, durations, starts, rgb, cmyk = level

    depth = len(lcoords[0])
    if depth > subdepth:
        indices = np.arange(base**depth).reshape(base**subdepth, base**(depth - subdepth))
    else:
        return [level]
    return [(lcoords[index], durations[index], starts[index], rgb[index], cmyk[index]) for index in indices]