import numpy as np
import itertools as itools

from cycles.conversion_functions import int_to_lcoords, lcoords_to_int
from cycles.color_functions import lcoords_to_cmyk, cmyk_to_rgb
from cycles.measure_functions import dharma_measure, purity_measure


proportions = np.array([0.4, 0.3, 0.2, 0.1], dtype=float)
offsets = np.insert(np.cumsum(proportions[:-1], dtype=float), 0, 0)


def weights(base: int, depth: int) -> np.ndarray:
    return np.array([base ** (-k) for k in range(1, depth + 1)])


def compute_duration(lcoords: np.ndarray) -> float:
    return np.prod(proportions[lcoords], dtype=float)


def compute_start(lcoords: np.ndarray) -> float:
    return np.dot(offsets[lcoords], np.insert(np.cumprod(proportions[lcoords][:-1]), 0, 1))


def compute_level(depth: int, bases: list[int]) -> tuple:
    lcoords = np.array([int_to_lcoords(i, bases[0], depth) for i in range(bases[0]**depth)], dtype=int)

    durations = np.apply_along_axis(compute_duration, 1, lcoords)
    starts = np.apply_along_axis(compute_start, 1, lcoords)

    w1 = weights(bases[1], depth)
    cmyks = np.array([lcoords_to_cmyk(lcoord, w1) for lcoord in lcoords], dtype=float)
    rgbs = np.apply_along_axis(cmyk_to_rgb, 2, cmyks)
    dharmas = np.array([dharma_measure(lcoord, w1) for lcoord in lcoords])

    w2 = weights(bases[2], depth)
    purities = np.array([purity_measure(lcoord, w2) for lcoord in lcoords])

    return lcoords, durations, starts, cmyks, rgbs, dharmas, purities


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


def count_digits(lcoord: np.ndarray, base: int=4) -> np.ndarray:
    return np.array([np.count_nonzero(lcoord == n) for n in range(base)])


def duration_quotient(cdiff: np.ndarray) -> np.ndarray:
    return 2.0 ** (cdiff[0] + cdiff[2]) * 3.0 ** cdiff[1]


def equality_test(cdiff: np.ndarray) -> int:
    if 2 * cdiff[0] + cdiff[2] == 0 and cdiff[1] == 0:
        return 1
    return 0


def same_duration(lcoord1: np.ndarray, lcoord2: np.ndarray, base: int=4) -> bool:
    cdiff = count_digits(lcoord1, base) - count_digits(lcoord2, base)
    return 2 * cdiff[0] + cdiff[2] == 0 and cdiff[1] == 0


def same_digit_counts(lcoord1: np.ndarray, lcoord2: np.ndarray, base: int=4) -> bool:
    return np.all(count_digits(lcoord1, base) == count_digits(lcoord2, base), axis=0)


def compute_all_distances(starts: np.ndarray, indices: list[int]) -> tuple:
    idx_pairs = np.array([[indices[j], indices[i]] for i in range(1, len(indices)) for j in range(i+1, len(indices))], dtype=int)
    dists = np.array([starts[indices[j]] - starts[indices[i]] for i in range(1, len(indices)) for j in range(i+1, len(indices))], dtype=float)
    mdist = np.max(dists) if len(dists) > 0 else 1
    norm_dists = dists / mdist
    sort_indices = np.argsort(norm_dists)
    return idx_pairs[sort_indices], dists[sort_indices], norm_dists[sort_indices]


def compute_consecutive_distances(starts: np.ndarray, indices: list[int]) -> tuple:
    idx_pairs = np.array([[indices[i], indices[(i + 1) % len(indices)]] for i in range(len(indices))], dtype=int)
    if len(indices) > 1:
        dists = starts[indices[1:]] - starts[indices[:-1]]
        mdist = starts[indices[-1]] - starts[indices[0]]
        norm_dists = dists / mdist
        ratios = dists[:-1] / dists[1:]
        return idx_pairs, dists, norm_dists, ratios
    else:
        return idx_pairs, np.array([0], dtype=float), np.array([0], dtype=float), np.array([0], dtype=float)


def compute_sorted_consecutive_distances(starts: np.ndarray, indices: list[int]) -> tuple:
    idx_pairs = np.array([[indices[i], indices[(i + 1) % len(indices)]] for i in range(len(indices))], dtype=int)
    if len(indices) > 1:
        dists = starts[indices[1:]] - starts[indices[:-1]]
        sort_indices = np.argsort(dists, axis=0)[::-1]
        sorted_dists = dists[sort_indices]
        mdist = starts[indices[-1]] - starts[indices[0]]
        norm_dists = dists / mdist
        ratios = sorted_dists[:-1] / sorted_dists[1:]
        return idx_pairs[sort_indices], sorted_dists, norm_dists[sort_indices], ratios
    else:
        return idx_pairs, np.array([0], dtype=float), np.array([0], dtype=float), np.array([0], dtype=float)