"""
Digit counts (compositions) of subcycle addresses and the duration
relations that follow from them.

The duration of a subcycle depends only on how many times each age appears in
its address (0.4^n0 * 0.3^n1 * 0.2^n2 * 0.1^n3), not on their order. At equal
depth, two addresses have the same duration when their count differences
``c = counts1 - counts2`` satisfy ``2*c0 + c2 == 0`` and ``c1 == 0``
(since 0.4 * 0.1 = 0.2 * 0.2).
"""

import numpy as np


def count_digits(lcoord: np.ndarray, base: int=4) -> np.ndarray:
    """Composition of an address: how many digits equal 0, 1, ..., base - 1."""
    return np.array([np.count_nonzero(lcoord == n) for n in range(base)])


def duration_quotient(cdiff: np.ndarray) -> np.ndarray:
    """
    Ratio of the durations of two subcycles of equal depth, from the difference
    of their digit counts ``cdiff = counts1 - counts2``.

    At equal depth the ratio is 4^c0 * 3^c1 * 2^c2 = 2^(2*c0 + c2) * 3^c1
    (the factors of 10 cancel and the Iron proportion contributes 1).
    """
    return 2.0 ** (2 * cdiff[0] + cdiff[2]) * 3.0 ** cdiff[1]


def equality_test(cdiff: np.ndarray) -> int:
    """1 if the count difference ``cdiff`` corresponds to equal durations, else 0."""
    if 2 * cdiff[0] + cdiff[2] == 0 and cdiff[1] == 0:
        return 1
    return 0


def same_duration(lcoord1: np.ndarray, lcoord2: np.ndarray, base: int=4) -> bool:
    """Whether two addresses of the same depth have the same duration."""
    cdiff = count_digits(lcoord1, base) - count_digits(lcoord2, base)
    return 2 * cdiff[0] + cdiff[2] == 0 and cdiff[1] == 0


def same_digit_counts(lcoord1: np.ndarray, lcoord2: np.ndarray, base: int=4) -> bool:
    """
    Whether two addresses have the same composition (are digit permutations of
    each other).
    """
    return np.all(count_digits(lcoord1, base) == count_digits(lcoord2, base), axis=0)


def compute_all_distances(starts: np.ndarray, indices: list[int]) -> tuple:
    """
    Time distances between the starts of a group of subcycles, for every pair.

    Returns ``(index_pairs, distances, normalised_distances)`` sorted by distance;
    each pair is ``[later, earlier]`` (positive distances when ``indices`` is in
    time order) and the normalisation divides by the largest distance.
    """
    idx_pairs = np.array([[indices[j], indices[i]] for i in range(len(indices)) for j in range(i+1, len(indices))], dtype=int)
    dists = np.array([starts[indices[j]] - starts[indices[i]] for i in range(len(indices)) for j in range(i+1, len(indices))], dtype=float)
    mdist = np.max(dists) if len(dists) > 0 else 1
    norm_dists = dists / mdist
    sort_indices = np.argsort(norm_dists)
    return idx_pairs[sort_indices], dists[sort_indices], norm_dists[sort_indices]


def compute_consecutive_distances(starts: np.ndarray, indices: list[int]) -> tuple:
    """
    Time distances between the starts of consecutive subcycles of a group.

    ``indices`` must be in time order. Returns ``(index_pairs, distances,
    normalised_distances, ratios)``: ``index_pairs`` includes the closing pair
    (last, first); distances are normalised by the span from the first to the
    last start; ``ratios`` are quotients of each distance by the next one. A
    group of one subcycle gives zeros.
    """
    idx_pairs = np.array([[indices[i], indices[(i + 1) % len(indices)]] for i in range(len(indices))], dtype=int)
    if len(indices) > 1:
        dists = starts[indices[1:]] - starts[indices[:-1]]
        mdist = starts[indices[-1]] - starts[indices[0]]
        norm_dists = dists / mdist
        ratios = dists[:-1] / dists[1:]
        return idx_pairs, dists, norm_dists, ratios
    else:
        return idx_pairs, np.array([0], dtype=float), np.array([0], dtype=float), np.array([0], dtype=float)


def compute_sorted_consecutive_distances(starts: np.ndarray, indices: list[int]) -> tuple:
    """
    Like ``compute_consecutive_distances``, with the distances sorted from the
    largest to the smallest (ratios are taken between sorted neighbours).
    """
    idx_pairs = np.array([[indices[i], indices[(i + 1) % len(indices)]] for i in range(len(indices))], dtype=int)
    if len(indices) > 1:
        dists = starts[indices[1:]] - starts[indices[:-1]]
        sort_indices = np.argsort(dists, axis=0)[::-1]
        sorted_dists = dists[sort_indices]
        mdist = starts[indices[-1]] - starts[indices[0]]
        norm_dists = dists / mdist
        ratios = sorted_dists[:-1] / sorted_dists[1:]
        return idx_pairs[sort_indices], sorted_dists, norm_dists[sort_indices], ratios
    else:
        return idx_pairs, np.array([0], dtype=float), np.array([0], dtype=float), np.array([0], dtype=float)
