import numpy as np
from itertools import groupby
from symmetrymath.groups import SymmetricGroup

from cycles.conversion_functions import int_to_lcoords, lcoords_to_int

def compositions(depth: int) -> list[tuple]:
    comps = []
    for n3 in range(depth + 1):
        for n2 in range(depth - n3 + 1):
            for n1 in range(depth - n3 - n2 + 1):
                n0 = depth - n3 - n2 - n1
                comps.append((n0, n1, n2, n3))
    return comps

def duration_equivalent_compositions(composition: tuple) -> list[tuple]:
    tmin = np.max([-composition[0], -composition[3]])
    tmax = np.floor(composition[2] / 2)

    comps = []
    for t in range(int(tmin), int(tmax) + 1):
        comps.append((composition[0] + t, composition[1], composition[2] - 2 * t, composition[3] + t))
    return comps

if __name__ == "__main__":
    comps = compositions(3)
    for c in comps:
        print(c, duration_equivalent_compositions(c))


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