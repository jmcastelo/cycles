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


# -- permutations as tuples, with the convention of ``SymmetricGroup.operation``:
# (a ∘ b)[i] = a[b[i]], and an address ``a`` becomes ``a ∘ σ`` (its digit i is
# the digit σ[i] of the original).

def compose(a: tuple, b: tuple) -> tuple:
    """``a ∘ b``: ``(a ∘ b)[i] = a[b[i]]``."""
    return tuple(a[i] for i in b)


def identity(m: int) -> tuple:
    return tuple(range(m))


def power(permutation: tuple, r: int) -> tuple:
    """``σ^r`` (``r >= 0``)."""
    result = identity(len(permutation))
    for _ in range(r):
        result = compose(result, permutation)
    return result


def cycles(permutation: tuple) -> list[tuple]:
    """The cycles of ``permutation`` (fixed positions included), each from its smallest position."""
    seen, result = set(), []
    for start in range(len(permutation)):
        if start in seen:
            continue
        cycle, i = [], start
        while i not in seen:
            seen.add(i)
            cycle.append(i)
            i = permutation[i]
        result.append(tuple(cycle))
    return result


def order(permutation: tuple) -> int:
    """Least ``r > 0`` with ``σ^r`` the identity: the lcm of the cycle lengths."""
    from math import lcm
    return lcm(*(len(c) for c in cycles(permutation))) if permutation else 1


def sign(permutation: tuple) -> int:
    """+1 for even permutations, -1 for odd ones."""
    return -1 if sum(len(c) - 1 for c in cycles(permutation)) % 2 else 1


def cycle_type(permutation: tuple) -> tuple:
    """Lengths of the cycles, longest first."""
    return tuple(sorted((len(c) for c in cycles(permutation)), reverse=True))


def cycle_text(permutation: tuple) -> str:
    """Cycle notation without the fixed positions, e.g. ``(0 1 2)(3 4)``; ``()`` for the identity."""
    moving = [c for c in cycles(permutation) if len(c) > 1]
    return ''.join('(' + ' '.join(map(str, c)) + ')' for c in moving) or '()'


def parse_permutation(text: str, m: int) -> tuple:
    """
    A permutation of ``0 … m-1`` from one-line notation (``1 2 0``, ``1,2,0`` or
    ``120``) or from cycles (``(0 1 2)``, ``(01)(23)``, ``()`` for the identity).
    Raises ``ValueError`` if it is not one.
    """
    import re
    text = text.strip()
    if text.startswith('('):
        if not re.fullmatch(r'(\(\s*[\d\s,]*\))+', text):
            raise ValueError("cycles are written like (0 1 2)(3 4)")
        result = list(range(m))
        used = set()
        for group in re.findall(r'\(([^)]*)\)', text):
            items = re.findall(r'\d+', group) if re.search(r'[\s,]', group.strip()) else list(group.strip())
            cycle = [int(i) for i in items]
            if any(i >= m for i in cycle) or used & set(cycle) or len(set(cycle)) != len(cycle):
                raise ValueError(f"the cycles must use distinct positions 0 to {m - 1}")
            used |= set(cycle)
            for i, j in zip(cycle, cycle[1:] + cycle[:1]):
                result[i] = j
        return tuple(result)
    items = re.findall(r'\d+', text) if re.search(r'[\s,]', text) else list(text)
    try:
        result = tuple(int(i) for i in items)
    except ValueError:
        raise ValueError("write the images of 0, 1, … (like 1 2 0) or cycles (like (0 1 2))") from None
    if sorted(result) != list(range(m)):
        raise ValueError(f"a permutation of the {m} positions 0 to {m - 1} is needed")
    return result


def permute_digits(lcoords: np.ndarray, permutation: tuple, first: int = 0) -> np.ndarray:
    """
    Addresses (rows of ``lcoords``) with the digits from position ``first`` on
    permuted by ``permutation`` (``a ∘ σ`` on those digits); the earlier ones are kept.
    """
    result = np.array(lcoords, copy=True)
    tail = result[:, first:]
    result[:, first:] = tail[:, list(permutation)]
    return result


def tcoords_of(lcoords: np.ndarray) -> np.ndarray:
    """Time-order indices of the addresses (rows of ``lcoords``), the first digit the most significant."""
    lcoords = np.asarray(lcoords, dtype=np.int64)
    depth = lcoords.shape[1]
    return lcoords @ (4 ** np.arange(depth - 1, -1, -1, dtype=np.int64))
