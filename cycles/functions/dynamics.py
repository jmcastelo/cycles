"""
The time evolution of the durations and the measures, from the point of view of dynamical systems.

Two dynamics act on the division:

* **along time**: the next subcycle of a level is its address plus one, in base 4 with carries (an *odometer*).
  It is deterministic and has zero entropy: every measure, read in the order of the subcycles (the *index
  order*), is a sum of patterns repeating every 4, 16, 64… subcycles. Read in physical time (sampled uniformly
  in years), the same values last as long as their subcycles;
* **across scales** (zooming in): stretching an age to the whole cycle is the expanding map T(x) = (x − o_a)/p_a,
  four linear branches of slopes 1/p (2.5, 3.33, 5, 10). It preserves the time (Lebesgue measure) and is
  chaotic: entropy = Lyapunov exponent = H(p) = Σ p log(1/p) ≈ 1.28 nats per level (``zoom_dynamics``).

The estimators here (fluctuation analysis, rescaled range, structure functions, the fractal dimension of a graph,
spectra, ordinal patterns, recurrences, return times) are the usual ones of time-series analysis; for the
durations and dharma some of their results are known exactly (``exact_*``), which tells which estimators can be
trusted here before using them on series without exact answers.
"""

import math

import numpy as np

PROPORTIONS = np.array([0.4, 0.3, 0.2, 0.1])
OFFSETS = np.array([0.0, 0.4, 0.7, 0.9])


# -- the series: in the index order and in physical time

def time_samples(starts, values, samples: int, time_map=None) -> np.ndarray:
    """
    ``values`` (one per subcycle of a level, in time order, starting at ``starts`` as fractions of the cycle)
    sampled at ``samples`` moments evenly spread over the cycle: in normalized time, or in years if a
    ``time_map`` is given (the subcycles then last their years). Each sample takes the value of the subcycle
    that contains it.
    """
    starts, values = np.asarray(starts, dtype=float), np.asarray(values)
    u = (np.arange(samples) + 0.5) / samples
    if time_map is not None:
        # moments evenly spread in years, back to normalized time by inverting the (monotone) map on a grid
        from cycles.functions.cycle_analysis import dense_years
        grid = np.linspace(0.0, 1.0, 20001)
        years = dense_years(time_map, grid)
        u = np.interp(years[0] + u * (years[-1] - years[0]), years, grid)
    return values[np.clip(np.searchsorted(starts, u, side='right') - 1, 0, len(starts) - 1)]


def scales_between(length: int, low: int = 16, count: int = 16) -> np.ndarray:
    """Window sizes (or lags) spread logarithmically from ``low`` to a sixteenth of ``length``."""
    return np.unique(np.logspace(np.log10(low), np.log10(max(low * 2, length // 16)), count).astype(int))


def fit_exponent(scales, values) -> float:
    """Slope of log(values) against log(scales) (least squares)."""
    scales, values = np.asarray(scales, dtype=float), np.asarray(values, dtype=float)
    ok = (values > 0) & np.isfinite(values)
    return float(np.polyfit(np.log(scales[ok]), np.log(values[ok]), 1)[0])


# -- fluctuation analysis: the Hurst exponent and its generalizations

def dfa(x, scales, order: int = 1) -> np.ndarray:
    """
    Detrended fluctuation analysis: F(s), the root mean square of the profile (cumulative sum of x minus its
    mean) after removing a polynomial of ``order`` in each window of ``s`` points. F ∝ s^α: α = 0.5 without
    memory, 0.5–1 for persistent stationary series (the Hurst exponent), 1 + H for a walk with exponent H.
    """
    return mfdfa(x, scales, [2.0], order)[0]


def mfdfa(x, scales, qs, order: int = 1) -> np.ndarray:
    """
    Multifractal DFA (Kantelhardt et al. 2002): F_q(s) for each q (rows), the q-th order mean of the windows'
    fluctuations; F_q ∝ s^h(q), the generalized Hurst exponents. h(q) constant: a monofractal series.
    """
    x = np.asarray(x, dtype=float)
    profile = np.cumsum(x - x.mean())
    qs = np.atleast_1d(np.asarray(qs, dtype=float))
    out = np.empty((len(qs), len(scales)))
    for k, s in enumerate(scales):
        s = int(s)
        n = len(profile) // s
        segments = np.concatenate([profile[:n * s].reshape(n, s), profile[-n * s:].reshape(n, s)])
        t = np.arange(s)
        fits = np.polynomial.polynomial.polyval(t, np.polynomial.polynomial.polyfit(t, segments.T, order))
        variance = np.mean((segments - fits) ** 2, axis=1)
        variance = variance[variance > 0]
        for i, q in enumerate(qs):
            if abs(q) < 1e-12:
                out[i, k] = np.exp(0.5 * np.mean(np.log(variance)))
            else:
                out[i, k] = np.mean(variance ** (q / 2)) ** (1 / q)
    return out


def rescaled_range(x, scales) -> np.ndarray:
    """Hurst's rescaled range R/S for windows of ``s`` points (mean over windows); R/S ∝ s^H."""
    x = np.asarray(x, dtype=float)
    out = []
    for s in scales:
        s = int(s)
        n = len(x) // s
        w = x[:n * s].reshape(n, s)
        deviations = np.cumsum(w - w.mean(axis=1, keepdims=True), axis=1)
        r = deviations.max(axis=1) - deviations.min(axis=1)
        sd = w.std(axis=1)
        ok = sd > 0
        out.append(np.mean(r[ok] / sd[ok]) if ok.any() else np.nan)
    return np.array(out)


def structure_functions(x, lags, qs) -> np.ndarray:
    """
    S_q(ℓ) = ⟨|x(n + ℓ) − x(n)|^q⟩^(1/q) for each q (rows). S_q ∝ ℓ^H(q): the roughness (Hölder exponent) seen
    by moments of order q. In a series with jumps the large q are pulled down by the jumps (intermittency), so
    q = 1 is the most reliable.
    """
    x = np.asarray(x, dtype=float)
    qs = np.atleast_1d(np.asarray(qs, dtype=float))
    out = np.empty((len(qs), len(lags)))
    for k, lag in enumerate(lags):
        increments = np.abs(x[int(lag):] - x[:-int(lag)])
        for i, q in enumerate(qs):
            out[i, k] = np.mean(increments ** q) ** (1 / q)
    return out


def higuchi_dimension(x, kmax: int = 256) -> float:
    """
    Higuchi's fractal dimension of the graph of ``x`` (1 for a smooth curve, 2 for one that fills the plane;
    2 − H for a walk of roughness H): from the length of the curve sampled every k points, L(k) ∝ k^−D.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    ks = np.unique(np.logspace(0, np.log10(kmax), 24).astype(int))
    lengths = []
    for k in ks:
        per_offset = []
        for m in range(k):
            sub = x[m::k]
            if len(sub) > 1:
                per_offset.append(np.abs(np.diff(sub)).sum() * (n - 1) / ((len(sub) - 1) * k) / k)
        lengths.append(np.mean(per_offset))
    return -fit_exponent(ks, lengths)


# -- spectra

def power_spectrum(x) -> tuple[np.ndarray, np.ndarray]:
    """Periodogram of ``x`` (mean removed): frequencies (cycles per sample, 0 excluded) and power."""
    x = np.asarray(x, dtype=float)
    spectrum = np.abs(np.fft.rfft(x - x.mean())) ** 2 / len(x)
    frequencies = np.fft.rfftfreq(len(x))
    return frequencies[1:], spectrum[1:]


def binned_spectrum(frequencies, power, bins: int = 40) -> tuple[np.ndarray, np.ndarray]:
    """The spectrum averaged in logarithmic bins of frequency (for fitting a power law, P ∝ f^−β)."""
    edges = np.logspace(np.log10(frequencies[0]), np.log10(frequencies[-1]), bins + 1)
    which = np.clip(np.searchsorted(edges, frequencies, side='right') - 1, 0, bins - 1)
    count = np.bincount(which, minlength=bins)
    total = np.bincount(which, weights=power, minlength=bins)
    ok = count > 0
    centres = np.sqrt(edges[:-1] * edges[1:])
    return centres[ok], total[ok] / count[ok]


# -- ordinal patterns: permutation entropy and complexity

def ordinal_distribution(x, order: int = 4, delay: int = 1, ties: str = 'random', seed: int = 0) -> np.ndarray:
    """
    Frequencies of the order patterns of ``order`` values ``delay`` apart (Bandt and Pompe 2002), over the
    ``order!`` possible ones, from the most frequent. Equal values have no order: by default they are ordered at
    random (``ties='random'``, reproducible with ``seed``), so that a shuffled series with repeated values is still
    noise; ``ties='position'`` orders them by position (a constant stretch counts as rising).
    """
    x = np.asarray(x, dtype=float)
    n = len(x) - (order - 1) * delay
    windows = np.stack([x[k * delay:k * delay + n] for k in range(order)], axis=1)
    if ties == 'random':
        jitter = np.random.default_rng(seed).random(windows.shape)
        ranks = np.lexsort((jitter, windows), axis=1)          # by value, equal values in a random order
    else:
        ranks = np.argsort(windows, axis=1, kind='stable')
    codes = (ranks * (order ** np.arange(order - 1, -1, -1))).sum(axis=1)
    counts = np.unique(codes, return_counts=True)[1]
    out = np.zeros(math.factorial(order))
    out[:len(counts)] = np.sort(counts)[::-1]
    return out / out.sum()


def permutation_entropy(x, order: int = 4, delay: int = 1, ties: str = 'random') -> float:
    """Shannon entropy of the order patterns over log(order!): 0 for a monotone series, 1 for white noise."""
    p = ordinal_distribution(x, order, delay, ties)
    p = p[p > 0]
    return float(-(p * np.log(p)).sum() / math.log(math.factorial(order)))


def statistical_complexity(x, order: int = 4, delay: int = 1, ties: str = 'random') -> tuple[float, float]:
    """
    (permutation entropy H, statistical complexity C) of Rosso et al. (2007): C = Q_JS · H, Q_JS the normalized
    Jensen–Shannon distance from the uniform distribution. Noise has H ≈ 1 and C ≈ 0, a periodic series H ≈ 0;
    chaotic and other structured series lie high in the plane.
    """
    p = ordinal_distribution(x, order, delay, ties)
    n = len(p)
    uniform = np.full(n, 1 / n)

    def shannon(v):
        v = v[v > 0]
        return -(v * np.log(v)).sum()
    h = shannon(p) / math.log(n)
    js = shannon((p + uniform) / 2) - shannon(p) / 2 - shannon(uniform) / 2
    js_max = -0.5 * ((n + 1) / n * math.log(n + 1) + math.log(n) - 2 * math.log(2 * n))
    return float(h), float(js / js_max * h)


# -- recurrences

def recurrence_matrix(x, radius: float | None = None, dimension: int = 1, delay: int = 1) -> np.ndarray:
    """
    Recurrence matrix of ``x`` (in a delay embedding of ``dimension``): R[i, j] when the states i and j are
    closer than ``radius`` (by default a tenth of the series' standard deviation). For a few thousand points.
    """
    x = np.asarray(x, dtype=float)
    n = len(x) - (dimension - 1) * delay
    states = np.stack([x[k * delay:k * delay + n] for k in range(dimension)], axis=1)
    radius = 0.1 * x.std() if radius is None else radius
    distance = np.max(np.abs(states[:, None, :] - states[None, :, :]), axis=2)
    return distance <= radius


def _line_lengths(rows) -> np.ndarray:
    """Lengths of the runs of True along each row (or diagonal) of a boolean array."""
    padded = np.pad(rows.astype(np.int8), ((0, 0), (1, 1)))
    changes = np.diff(padded, axis=1)
    starts, ends = np.nonzero(changes == 1), np.nonzero(changes == -1)
    return ends[1] - starts[1]


def rqa(matrix, minimum: int = 2) -> dict:
    """
    Recurrence quantification: ``rate`` (share of recurrent pairs), ``determinism`` (share of recurrent points
    in diagonal lines of at least ``minimum``: the future follows the past), ``laminarity`` (in vertical lines:
    the state stays) and ``mean_diagonal`` (mean length of those diagonals), without the main diagonal.
    """
    m = np.asarray(matrix, dtype=bool)
    n = len(m)
    off = m & ~np.eye(n, dtype=bool)
    total = off.sum()
    if total == 0:
        return {'rate': 0.0, 'determinism': 0.0, 'laminarity': 0.0, 'mean_diagonal': 0.0}
    diagonals = [np.diagonal(m, k) for k in range(1, n)]
    lengths = np.concatenate([_line_lengths(d[None]) for d in diagonals]) if diagonals else np.zeros(0)
    long_d = lengths[lengths >= minimum]
    verticals = _line_lengths(off.T)
    return {'rate': float(total / (n * n - n)),
            'determinism': float(2 * long_d.sum() / total),       # the upper diagonals, counted twice
            'laminarity': float(verticals[verticals >= minimum].sum() / total),
            'mean_diagonal': float(long_d.mean()) if len(long_d) else 0.0}


# -- return times

def return_times(members, durations=None) -> np.ndarray:
    """
    The waiting times between consecutive members of a class (``members``: a boolean array over the subcycles of
    a level, in time order): in subcycles, or in time if their ``durations`` are given (from the start of one
    member to the start of the next). Kac's lemma: their mean is the inverse of the share of the class.
    """
    members = np.asarray(members, dtype=bool)
    where = np.flatnonzero(members)
    if durations is None:
        return np.diff(where).astype(float)
    starts = np.concatenate([[0.0], np.cumsum(np.asarray(durations, dtype=float))])
    return np.diff(starts[where])


# -- time reversal

def reversal_symmetry(x, tolerance: float = 1e-9) -> tuple[str, float] | None:
    """
    How ``x`` (one value per subcycle, in the index order) behaves when time runs backwards: reading the subcycles
    from the last turns every digit a into 3 − a (Satya ↔ Kali, Treta ↔ Dvapara). ('even', 0) if
    x(N − 1 − n) = x(n): the series is a palindrome; ('odd', c) if x(N − 1 − n) = 2c − x(n): it turns around the
    value c; None otherwise.
    """
    x = np.asarray(x, dtype=float)
    r = x[::-1]
    scale = max(float(np.abs(x).max()), 1.0)
    if np.allclose(x, r, atol=tolerance * scale, rtol=0):
        return ('even', 0.0)
    centre = float(np.mean(x + r) / 2)
    if np.allclose(x + r, 2 * centre, atol=tolerance * scale, rtol=0):
        return ('odd', centre)
    return None


# -- surrogates

def shuffled(x, seed: int = 0) -> np.ndarray:
    """The same values in a random order: no memory, same distribution."""
    return np.random.default_rng(seed).permutation(np.asarray(x))


def phase_randomized(x, seed: int = 0) -> np.ndarray:
    """The same power spectrum with random phases: the linear correlations kept, the rest (jumps, nonlinear
    structure, the distribution) not."""
    x = np.asarray(x, dtype=float)
    spectrum = np.fft.rfft(x - x.mean())
    phases = np.random.default_rng(seed).uniform(0, 2 * np.pi, len(spectrum))
    phases[0] = 0.0
    if len(x) % 2 == 0:
        phases[-1] = 0.0
    return np.fft.irfft(np.abs(spectrum) * np.exp(1j * phases), n=len(x)) + x.mean()


# -- what is known exactly

def carry_lengths(lcoords) -> np.ndarray:
    """
    For each subcycle but the last (in time order), how many of its last digits are Kali (3): going to the next
    subcycle carries over them. The ratio of the next duration to this one is (p_{j+1}/p_j)·4^k, with j the
    digit before those k Kali digits.
    """
    lcoords = np.asarray(lcoords, dtype=int)
    is_kali = lcoords[:-1, ::-1] == 3
    return np.where(is_kali.all(axis=1), lcoords.shape[1], np.argmin(is_kali, axis=1))


def exact_duration_ratios(lcoords) -> np.ndarray:
    """The ratio of each duration to the previous one, from the digits (``carry_lengths``)."""
    lcoords = np.asarray(lcoords, dtype=int)
    k = carry_lengths(lcoords)
    depth = lcoords.shape[1]
    j = lcoords[:-1][np.arange(len(k)), np.clip(depth - 1 - k, 0, depth - 1)]
    return PROPORTIONS[np.minimum(j + 1, 3)] / PROPORTIONS[j] * 4.0 ** k


def exact_duration_hurst(q, proportions=PROPORTIONS) -> np.ndarray:
    """
    The generalized Hurst exponents of the durations in the index order: h(q) = (1 + τ(q))/q with
    τ(q) = −log₄ Σ p^q the moment function of the time on the index line (section 1.9); H = h(2) ≈ 0.934.
    """
    q = np.atleast_1d(np.asarray(q, dtype=float))
    p = np.asarray(proportions, dtype=float)
    tau = -np.log(np.array([np.sum(p ** v) for v in q])) / np.log(4)
    at_zero = -np.log(p).mean() / np.log(4)               # the limit q → 0: τ'(0), the α₀ of the time measure
    small = np.abs(q) < 1e-12
    return np.where(small, at_zero, (1 + tau) / np.where(small, 1.0, q))


def exact_duration_spectrum(frequencies, depth: int, proportions=PROPORTIONS) -> np.ndarray:
    """
    The Fourier transform of the durations in the index order is a product over the levels (a Riesz product):
    Σ_n duration(n) e^(−2πi n f) = Π_k Σ_j p_j e^(−2πi j 4^k f); its squared modulus over 4^d, at ``frequencies``
    (cycles per subcycle), is the periodogram of ``power_spectrum``.
    """
    f = np.asarray(frequencies, dtype=float)
    product = np.ones(len(f), dtype=complex)
    for level in range(depth):
        product *= np.exp(-2j * np.pi * np.outer(4.0 ** level * f, np.arange(4))) @ np.asarray(proportions)
    return np.abs(product) ** 2 / 4 ** depth


def exact_dharma_roughness(base: float) -> dict:
    """
    Dharma in the index order: level k adds steps of b^−k every 4^(d−k) subcycles, so its increments over ℓ
    subcycles grow as ℓ^H with H = log₄ b (the Hölder exponent: 0.5 at base 2, as Brownian motion), and its
    graph has dimension 2 − H. Base 4 makes dharma a straight line (H = 1), base 1 a 1/f noise (H = 0).
    """
    h = math.log(base) / math.log(4)
    return {'roughness': h, 'graph_dimension': 2 - h}


def exact_dharma_steps(depth: int, base: float) -> np.ndarray:
    """
    The step of dharma from one subcycle to the next, for 0 to depth − 1 Kali digits carried (k): the digit
    before them goes up by one age (dharma down by its weight) and the k Kali digits go back to Satya (up by three
    ages each): (3 Σ_{i > d−k} w_i − w_{d−k}) / (4 Σ w), with w_i = b^−i. Only these ``depth`` values occur;
    one carry raises dharma below base 3, leaves it at base 3 and lowers it above.
    """
    w = float(base) ** -np.arange(1, depth + 1)
    k = np.arange(depth)
    tails = np.concatenate([[0.0], np.cumsum(w[::-1])])[k]           # Σ of the last k weights
    return (3 * tails - w[depth - 1 - k]) / (4 * w.sum())


def zoom_dynamics(proportions=PROPORTIONS) -> dict:
    """
    The map that zooms in (each age stretched to the whole cycle): ``entropy`` (Kolmogorov–Sinai, of the time) =
    ``lyapunov`` (mean log stretch) = H(p) nats per level; ``mean_zoom`` = e^H, the typical magnification per
    level; ``topological_entropy`` = log 4 (four branches), reached by the count measure, whose Lyapunov exponent
    is ``count_lyapunov`` and whose dimension, entropy / Lyapunov exponent, is ``count_dimension`` (the D₁ of
    the count measure, section 1.9).
    """
    p = np.asarray(proportions, dtype=float)
    h = float(-(p * np.log(p)).sum())
    count_lyapunov = float(-np.log(p).mean())
    return {'entropy': h, 'lyapunov': h, 'mean_zoom': math.exp(h), 'topological_entropy': math.log(4),
            'count_lyapunov': count_lyapunov, 'count_dimension': math.log(4) / count_lyapunov}
