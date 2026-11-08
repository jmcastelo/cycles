"""
Significance tests: do the boundaries of the subcycles fall closer to some events (or on some configuration of
the sky) than chance would place them?

The null model is a **rigid rotation**: every boundary is shifted by the same random offset, wrapping around the
cycle, so their spacing is kept and only their placement changes. It is the right comparison for periodic events
(conjunctions recur every ~20 years, say): random moments would mistake the rhythm of the events for a
coincidence with the division. The p-value is one-sided (closer than chance), counted as
``(1 + #{null ≤ observed}) / (1 + n)``, and a family of tests is corrected with Holm's method.
"""

import numpy as np


def nearest_distance(times, events) -> np.ndarray:
    """Distance from each of ``times`` to the nearest of ``events`` (same units)."""
    events = np.sort(np.asarray(events, dtype=float))
    times = np.asarray(times, dtype=float)
    if not len(events):
        return np.full(times.shape, np.inf)
    k = np.clip(np.searchsorted(events, times), 1, len(events) - 1)
    left, right = events[k - 1], events[k]
    distance = np.minimum(np.abs(times - left), np.abs(right - times))
    if len(events) == 1:
        distance = np.abs(times - events[0])
    return distance


def rotations(times, start: float, end: float, n: int, seed: int = 0) -> np.ndarray:
    """``n`` rigid rotations of ``times`` within [start, end): shape (n, len(times))."""
    times = np.asarray(times, dtype=float)
    length = end - start
    shifts = np.random.default_rng(seed).uniform(0.0, length, n)
    return start + (times[None, :] - start + shifts[:, None]) % length


def _result(observed: float, null: np.ndarray) -> dict:
    null = np.asarray(null, dtype=float)
    finite = null[np.isfinite(null)]
    p = (1 + np.count_nonzero(finite <= observed)) / (1 + len(finite))
    return {'observed': float(observed), 'null': finite, 'expected': float(finite.mean()) if len(finite) else np.nan,
            'p': float(p), 'ratio': float(observed / finite.mean()) if len(finite) and finite.mean() else np.nan}


def proximity_test(boundaries, events, start: float, end: float, n: int = 2000, seed: int = 0) -> dict:
    """
    Mean distance from the ``boundaries`` to their nearest event, against the same for ``n`` rigid rotations of
    the boundaries: ``observed``, ``expected`` (the mean under rotation), ``ratio``, ``p`` and the ``null`` values.
    The events should cover [start, end) with some margin, so that the nearest one exists near the ends.
    """
    observed = nearest_distance(boundaries, events).mean()
    shifted = rotations(boundaries, start, end, n, seed)
    null = nearest_distance(shifted.ravel(), events).reshape(shifted.shape).mean(axis=1)
    return _result(observed, null)


def value_test(boundaries, value, start: float, end: float, n: int = 2000, seed: int = 0) -> dict:
    """
    Mean of ``value(times)`` (any measure of the sky at those moments, smaller meaning more remarkable) over the
    ``boundaries``, against the same for ``n`` rigid rotations. ``value`` receives a 1-D array of moments.
    """
    observed = float(np.mean(value(np.asarray(boundaries, dtype=float))))
    shifted = rotations(boundaries, start, end, n, seed)
    null = np.asarray(value(shifted.ravel()), dtype=float).reshape(shifted.shape).mean(axis=1)
    return _result(observed, null)


def holm(pvalues) -> np.ndarray:
    """Holm's step-down adjustment of a family of p-values (same order as given)."""
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p)
    m = len(p)
    adjusted = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adjusted[i] = running
    return adjusted
