import numpy as np

# Color functions

def indicator_vector(i: int, lcoords: np.ndarray) -> np.ndarray:
    return np.array([int(i == c) for c in lcoords], dtype=int)

def lcoords_to_cmyk(lcoords: np.ndarray, weights: np.ndarray) -> np.ndarray:
    return np.array([np.dot(indicator_vector(i, lcoords), weights) for i in range(4)], dtype=float) / np.sum(weights)

# def lcoords_to_rgb(lcoords: np.ndarray, weights: np.ndarray, subtraction_factor: float):
#     return np.ones(3) - subtraction_factor * lcoords_to_cmyw(lcoords, weights)

def lcoords_to_rgb(lcoords: np.ndarray, weights: np.ndarray) -> np.ndarray:
    cmyk = lcoords_to_cmyk(lcoords, weights)
    return (np.ones(3) - cmyk[:3]) * (1 - cmyk[3])