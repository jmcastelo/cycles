import numpy as np
import itertools as itools

from conversion_functions import int_to_lcoords, lcoords_to_int
from color_functions import lcoords_to_rgb, lcoords_to_cmyk

# Cycle subdivision functions

proportions = np.array([0.4, 0.3, 0.2, 0.1], dtype=float)
offsets = np.insert(np.cumsum(proportions[:-1], dtype=float), 0, 0)

def weights(base: int, depth: int) -> np.ndarray:
    return np.array([base ** (-k) for k in range(1, depth + 1)])

def compute_duration(lcoords: list[int]) -> float:
    return np.prod(proportions[lcoords], dtype=float)

def compute_start(lcoords: list[int]) -> float:
    return np.dot(offsets[lcoords], np.insert(np.cumprod(proportions[lcoords][:-1]), 0, 1))

# def compute_level(depth: int, bases: list[int], subtraction_factor: float | None = None) -> tuple:
#     lcoords = np.array([int_to_lcoords(i, bases[0], depth) for i in range(bases[0]**depth)], dtype=int)
#
#     durations = np.array([compute_duration(lcoord) for lcoord in lcoords], dtype=float)
#     starts = np.array([compute_start(lcoord) for lcoord in lcoords], dtype=float)
#
#     weights = np.array([bases[1] ** (-k) for k in range(1, depth + 1)])
#     if subtraction_factor is None:
#         subtraction_factor = (bases[1] - 1) / (1 - bases[1]**(-depth))
#     colors = np.array([lcoords_to_color(lcoord, weights, subtraction_factor) for lcoord in lcoords], dtype=float)
#
#     return lcoords, durations, starts, colors

def compute_level(depth: int, bases: list[int], total_duration: float | None=None) -> tuple:
    lcoords = np.array([int_to_lcoords(i, bases[0], depth) for i in range(bases[0]**depth)], dtype=int)

    durations = np.array([compute_duration(lcoord) for lcoord in lcoords], dtype=float)
    starts = np.array([compute_start(lcoord) for lcoord in lcoords], dtype=float)
    rgb = np.array([lcoords_to_rgb(lcoord, weights(bases[1], depth)) for lcoord in lcoords], dtype=float)
    cmyk = np.array([lcoords_to_cmyk(lcoord, weights(bases[1], depth)) for lcoord in lcoords], dtype=float)

    if total_duration is not None:
        return lcoords, total_duration * durations, total_duration * starts, rgb, cmyk
    return lcoords, durations, starts, rgb, cmyk

def compute_deeper_subcycles(parent_coords: list[int], extra_depth: int, bases: list[int]) -> tuple:
    start_index = lcoords_to_int(parent_coords + [0] * extra_depth)
    end_index = start_index + bases[0]**extra_depth - 1
    print(start_index, end_index)

    depth = len(parent_coords) + extra_depth

    lcoords = np.array([int_to_lcoords(i, bases[0], depth) for i in range(start_index, end_index)], dtype=int)

    durations = np.array([compute_duration(lcoord) for lcoord in lcoords], dtype=float)
    starts = np.array([compute_start(lcoord) for lcoord in lcoords], dtype=float)
    colors = np.array([lcoords_to_rgb(lcoord, weights(bases[1], depth)) for lcoord in lcoords], dtype=float)

    return lcoords, durations, starts, colors

def select_subcycle(prefix_coords: list[int], level: tuple) -> tuple:
    depth = len(prefix_coords)
    if depth == 0:
        return level
    lcoords, durations, starts, colors = level
    sel_coords = [i for i, lcoord in enumerate(lcoords) if (lcoord[:depth] == prefix_coords).all()]
    return lcoords[sel_coords], durations[sel_coords], starts[sel_coords], colors[sel_coords]

def find_identical(a: np.ndarray, decimals: int) -> list:
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