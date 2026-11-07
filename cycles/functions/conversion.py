"""
Conversions between the representations of a subcycle address.

* ``lcoords``: array of digits, one per depth level, each the age (0 to 3)
  chosen at that level, from the outermost cycle inwards.
* ``tcoord``: the integer whose base-4 digits are the ``lcoords``; it is the
  position of the subcycle in time order among all subcycles of its depth.
* fractional: the number ``0.d1 d2 d3...`` in a given base.
"""

import numpy as np


def kronecker_vector(i: int, lcoords: np.ndarray) -> np.ndarray:
    """Indicator array of the positions of ``lcoords`` whose digit equals ``i``."""
    return np.array([int(i == c) for c in lcoords], dtype=int)


def lcoords_to_tcoord(lcoords: np.ndarray, reverse: bool=False) -> int:
    """
    Integer whose base-4 digits are ``lcoords`` (the time-order index).

    With ``reverse`` the digits are read from the last one to the first.
    """
    if reverse:
        return int(''.join(str(d) for d in lcoords[::-1]), base=4)
    else:
        return int(''.join(str(d) for d in lcoords), base=4)


def tcoord_to_lcoords(x: int, base: int, depth: int) -> np.ndarray:
    """Digits of ``x`` in base ``base``, left-padded with zeros to ``depth`` digits."""
    padding = max(0, depth - len(np.base_repr(x, base=base)))
    if x == 0:
        padding += 1
    return np.array([int(d) for d in np.base_repr(x, base=base, padding=padding)])


def fractional_to_lcoords(x: float, base: int, max_depth: int = 10) -> list[int]:
    """
    Base-``base`` digits of the fraction ``x`` (in [0, 1)).

    Digits are generated until a remainder repeats (the expansion has become
    periodic) or ``max_depth`` is exceeded; the last generated digit is dropped.
    """
    g = [x]
    digits = []
    i = 0
    while len(np.unique(np.array(g))) == len(g) and i <= max_depth:
        digits.append(int(np.floor(base * g[-1])))
        g.append(base * g[-1] - digits[-1])
        i += 1
    return digits[:-1]


def lcoords_to_fractional(lcoords: np.ndarray, base: int) -> float:
    """Value of the base-``base`` fraction ``0.d1 d2 d3...`` given by ``lcoords``."""
    x = 0
    for k, lcoord in enumerate(lcoords, 1):
        x += lcoord * base**(-k)
    return x