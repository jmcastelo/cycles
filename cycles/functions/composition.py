import numpy as np


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