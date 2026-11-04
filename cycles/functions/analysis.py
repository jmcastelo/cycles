"""Signal analysis helpers."""

import numpy as np


def autocorrelation(x: np.ndarray, normalize: bool=True) -> tuple[np.ndarray, np.ndarray]:
    """
    Autocorrelation of ``x`` for non-negative lags.

    Returns ``(lags, acorr)`` with lags ``0 .. len(x) - 1``. With ``normalize``
    the values are divided by the lag-0 value, so ``acorr[0] == 1``.
    """
    x = np.asarray(x, dtype=float)
    acorr = np.correlate(x, x, mode='full')
    if normalize:
        acorr /= acorr[len(x) - 1]
    return np.arange(0, len(acorr) - len(x) + 1), acorr[len(x) - 1:]