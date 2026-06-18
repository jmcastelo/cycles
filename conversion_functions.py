import numpy as np

# Conversion functions

def lcoords_to_int(lcoords: list[int]) -> int:
    return int(''.join(str(d) for d in lcoords), base=4)

def int_to_lcoords(x: int, base: int, depth: int) -> list[int]:
    padding = max(0, depth - len(np.base_repr(x, base=base)))
    if x == 0:
        padding += 1
    return [int(d) for d in np.base_repr(x, base=base, padding=padding)]

def fractional_to_lcoords(x: float, base: int, max_depth: int = 10) -> list[int]:
    g = [x]
    digits = []
    i = 0
    while len(np.unique(np.array(g))) == len(g) and i <= max_depth:
        digits.append(int(np.floor(base * g[-1])))
        g.append(base * g[-1] - digits[-1])
        i += 1
    return digits[:-1]

def lcoords_to_fractional(lcoords: np.ndarray, base: int) -> float:
    x = 0
    for k, lcoord in enumerate(lcoords, 1):
        x += lcoord * base**(-k)
    return x