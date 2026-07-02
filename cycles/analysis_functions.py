import numpy as np


def autocorrelation(x: np.ndarray, normalize: bool=True) -> tuple[np.ndarray, np.ndarray]:
    acorr = np.correlate(x, x, mode='full')
    if normalize:
        acorr /= acorr[len(x) - 1]
    return np.arange(0, len(acorr) - len(x) + 1), acorr[len(x) - 1:]