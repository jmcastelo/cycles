import numpy as np

# Measure functions

def dharma_measure(cmyk: np.ndarray) -> float:
    return np.dot([1, 3/4, 1/2, 1/4], cmyk)

def purity_measure(cmyk: np.ndarray) -> float:
    return np.max(cmyk, axis=0) - np.min(cmyk, axis=0)