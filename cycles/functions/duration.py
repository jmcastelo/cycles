import numpy as np


def count_digits(lcoord: np.ndarray, base: int=4) -> np.ndarray:
    return np.array([np.count_nonzero(lcoord == n) for n in range(base)])


def duration_quotient(cdiff: np.ndarray) -> np.ndarray:
    return 2.0 ** (cdiff[0] + cdiff[2]) * 3.0 ** cdiff[1]


def equality_test(cdiff: np.ndarray) -> int:
    if 2 * cdiff[0] + cdiff[2] == 0 and cdiff[1] == 0:
        return 1
    return 0


def same_duration(lcoord1: np.ndarray, lcoord2: np.ndarray, base: int=4) -> bool:
    cdiff = count_digits(lcoord1, base) - count_digits(lcoord2, base)
    return 2 * cdiff[0] + cdiff[2] == 0 and cdiff[1] == 0


def same_digit_counts(lcoord1: np.ndarray, lcoord2: np.ndarray, base: int=4) -> bool:
    return np.all(count_digits(lcoord1, base) == count_digits(lcoord2, base), axis=0)


def compute_all_distances(starts: np.ndarray, indices: list[int]) -> tuple:
    idx_pairs = np.array([[indices[j], indices[i]] for i in range(1, len(indices)) for j in range(i+1, len(indices))], dtype=int)
    dists = np.array([starts[indices[j]] - starts[indices[i]] for i in range(1, len(indices)) for j in range(i+1, len(indices))], dtype=float)
    mdist = np.max(dists) if len(dists) > 0 else 1
    norm_dists = dists / mdist
    sort_indices = np.argsort(norm_dists)
    return idx_pairs[sort_indices], dists[sort_indices], norm_dists[sort_indices]


def compute_consecutive_distances(starts: np.ndarray, indices: list[int]) -> tuple:
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
