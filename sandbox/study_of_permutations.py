import numpy as np

from cycles.functions.conversion import lcoords_to_int
from cycles.functions.cycle_division import compute_duration


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

if __name__ == "__main__":
    eq_comps = [duration_equivalent_compositions(c) for c in compositions(5)]
    for eqc in eq_comps:
        print([c for c in eqc])
        for c in eqc:
            print([[lcoords_to_int(lcoord), lcoord, compute_duration(lcoord)] for lcoord in lexmin_enumeration(c)])


    '''
    depth = 3
    lcoords = [tuple(int_to_lcoords(i, 4, depth)) for i in range(4 ** depth)]

    S3 = SymmetricGroup(depth)
    perms = np.array([[lcoords_to_int(S3.operation(lcoord, e)) for lcoord in lcoords] for e in S3.elements])
    eq_classes = [np.sort(np.unique_values(x)) for x in np.unique(np.sort(perms.T, axis=1), axis=0)]

    grouped = {}
    for eq_class in eq_classes:
        grouped.setdefault(len(eq_class), []).append(eq_class)

    print(grouped)

    for k, eqs in grouped.items():
        for eq in eqs:
            if len(eq) > 1:
                diff = eq[1:] - eq[:-1]
                print(k, eq, diff, diff / np.min(diff))
    '''