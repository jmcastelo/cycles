import numpy as np
from symmetrymath import SymmetricGroup

from cycles.functions.conversion import lcoords_to_tcoords


def permutation_matrix(permutation: tuple, lcoords: np.ndarray) -> np.ndarray:
    depth = len(lcoords[0])
    SG = SymmetricGroup(depth)
    perm_tcoords = np.array([lcoords_to_tcoords(np.array(SG.operation(tuple(lcoord), permutation))) for lcoord in lcoords])

    ones = np.array([[perm_tcoords[i], i] for i in range(len(perm_tcoords))])

    perm_matrix = np.zeros((len(perm_tcoords), len(perm_tcoords)), dtype=int)
    perm_matrix[*ones.T] = 1
    return perm_matrix
