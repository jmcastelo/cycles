import numpy as np

from cycles.functions.division import compute_duration, compute_start, weights
from cycles.functions.color import lcoords_to_cmyk, cmyk_to_rgb


def compositions(depth: int) -> np.ndarray:
    comps = []
    for n3 in range(depth + 1):
        for n2 in range(depth - n3 + 1):
            for n1 in range(depth - n3 - n2 + 1):
                n0 = depth - n3 - n2 - n1
                comps.append([n0, n1, n2, n3])
    return np.array(comps)


def duration_equivalent_compositions(composition: np.ndarray) -> np.ndarray:
    tmin = int(np.max([-composition[0], -composition[3]]))
    tmax = int(np.floor(composition[2] / 2))

    comps = []
    for t in range(tmin, tmax + 1):
        comps.append(composition + [t, 0, -2 * t, t])
    return np.array(comps)


def compositions_grouped_by_duration(depth: int) -> list[np.ndarray]:
    grouped_comps = []
    for n3 in range(depth + 1):
        for n2 in range(depth - n3 + 1):
            for n1 in range(depth - n3 - n2 + 1):
                n0 = depth - n3 - n2 - n1
                comp = np.array([n0, n1, n2, n3])
                if np.all([not np.any(np.all(comp == gc, axis=1)) for gc in grouped_comps]):
                    grouped_comps.append(duration_equivalent_compositions(comp))
    return grouped_comps


def lexmin_enumeration(composition: np.ndarray) -> np.ndarray:
    depth = np.sum(composition)
    lexmin = np.concatenate([np.repeat(k, composition[k]) for k in range(4) if composition[k] > 0])
    enumeration = [lexmin]

    while True:
        prev = np.array(enumeration[-1])

        i = -1
        for k in range(depth - 2, -1, -1):
            if prev[k] < prev[k + 1]:
                i = k
                break
        if i == -1:
            break

        j = -1
        for k in range(depth - 1, i, -1):
            if prev[k] > prev[i]:
                j = k
                break

        prev[[i,j]] = prev[[j,i]]
        prev[i+1:] = prev[depth-1:i:-1]
        enumeration.append(prev)

    return np.array(enumeration)


def analyse_level(depth: int, scale: float, color_basis: int = 2) -> tuple:
    gcomps = compositions_grouped_by_duration(depth)
    glcoords = [[lexmin_enumeration(comp) for comp in gc] for gc in gcomps]
    gdurations = [[np.apply_along_axis(compute_duration, 1, lcoords)  for lcoords in gl] for gl in glcoords]
    gstarts = [[np.apply_along_axis(compute_start, 1, lcoords) for lcoords in gl] for gl in glcoords]

    w = weights(color_basis, depth)
    gcmyks = [[np.array([lcoords_to_cmyk(lcoord, w, scale) for lcoord in lcoords], dtype=float) for lcoords in gl] for gl in glcoords]
    grgbs = [[np.apply_along_axis(cmyk_to_rgb, 2, cmyk) for cmyk in cmyks] for cmyks in gcmyks]

    return glcoords, gdurations, gstarts, gcmyks, grgbs