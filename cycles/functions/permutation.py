"""Permutations of the digit positions of subcycle addresses."""

import numpy as np
from symmetrymath import SymmetricGroup

from cycles.functions.conversion import lcoords_to_tcoord


def permutation_matrix(permutation: tuple, lcoords: np.ndarray) -> np.ndarray:
    """
    Matrix of the action of ``permutation`` (an element of the symmetric group on
    the ``depth`` digit positions) on the subcycles of a level.

    Each address in ``lcoords`` has its digits permuted; ``M[new, old] = 1`` where
    ``new`` is the time-order index (tcoord) of the permuted address and ``old``
    the row of the address in ``lcoords``. With ``lcoords`` holding all addresses
    of the level in time order, ``M`` is a permutation matrix.
    """
    depth = len(lcoords[0])
    SG = SymmetricGroup(depth)
    perm_tcoords = np.array([lcoords_to_tcoord(np.array(SG.operation(tuple(lcoord), permutation))) for lcoord in lcoords])

    ones = np.array([[perm_tcoords[i], i] for i in range(len(perm_tcoords))])

    perm_matrix = np.zeros((len(perm_tcoords), len(perm_tcoords)), dtype=int)
    perm_matrix[*ones.T] = 1
    return perm_matrix
