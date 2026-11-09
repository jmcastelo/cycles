"""
The multifractal spectrum of the division.

The fractal division puts two measures on the cycle, each very uneven when seen through the other:

* **time** (``'time'``): each subcycle gets its duration, the product of 0.4, 0.3, 0.2, 0.1 along its address.
  Seen on the **index** line (every subcycle of a depth the same width, 4⁻ᵈ), the durations are the multinomial
  cascade with weights (0.4, 0.3, 0.2, 0.1);
* **count** (``'count'``): every subcycle of a depth gets the same weight, 4⁻ᵈ. Seen on the **time** line (each
  subcycle as long as its duration), it is the self-similar measure with weights 1/4 and ratios 0.4 … 0.1.

Both are self-similar measures with four pieces of weights ``w`` and sizes ``r``. A subcycle shrinks in size as
``r_a1 … r_ad`` and in weight as ``w_a1 … w_ad``; its **Hölder exponent** is α = log(weight) / log(size). The
**spectrum** f(α) is the dimension of the set of points where the exponent is α. With the moment function τ(q)
defined by Σ wᵢ^q rᵢ^(−τ(q)) = 1, α(q) = τ′(q) and f(α(q)) = q α(q) − τ(q) (a Legendre transform). Notable values:
f's maximum, 1 at q = 0 (the exponent of the typical subcycle by count of pieces); the **information dimension**
D₁ = α(1) = f(α(1)), the dimension of the set that carries the measure; and the ends α_min, α_max (the densest and
the sparsest points).

At a finite depth α depends only on the **composition** of an address (how many digits of each age): the
subcycles of a composition n all have α = Σ nᵢ log wᵢ / Σ nᵢ log rᵢ, and there are as many as the multinomial
coefficient, so f is estimated by log(count) / −log(size) (``composition_spectrum``), which tends to the exact
curve as the depth grows.
"""

import math

import numpy as np

PROPORTIONS = np.array([0.4, 0.3, 0.2, 0.1])
EQUAL = np.full(4, 0.25)
MEASURES = {
    # name: (weights w, sizes r) of the four pieces
    'time': (PROPORTIONS, EQUAL),       # durations on the index line
    'count': (EQUAL, PROPORTIONS),      # equal weights on the time line
}


def tau(q, weights, sizes) -> np.ndarray:
    """τ(q): the solution of Σ wᵢ^q rᵢ^(−τ) = 1 (decreasing in τ, solved by bisection), for each q."""
    w, r = np.log(np.asarray(weights, dtype=float)), np.log(np.asarray(sizes, dtype=float))
    q = np.atleast_1d(np.asarray(q, dtype=float))
    low, high = np.full(q.shape, -1e3), np.full(q.shape, 1e3)
    for _ in range(200):                # log Σ exp(q w − τ r) grows with τ (r < 0); its root is the τ sought
        middle = (low + high) / 2
        exponents = q[:, None] * w - middle[:, None] * r
        top = exponents.max(axis=1)
        value = top + np.log(np.exp(exponents - top[:, None]).sum(axis=1))
        low, high = np.where(value < 0, middle, low), np.where(value < 0, high, middle)
    return (low + high) / 2


def spectrum(q, weights, sizes) -> dict:
    """
    The multifractal spectrum at the moments ``q``: ``tau``, ``alpha`` = τ′(q) (from the implicit derivative) and
    ``f`` = q α − τ.
    """
    q = np.atleast_1d(np.asarray(q, dtype=float))
    t = tau(q, weights, sizes)
    w, r = np.log(np.asarray(weights, dtype=float)), np.log(np.asarray(sizes, dtype=float))
    exponents = q[:, None] * w - t[:, None] * r
    terms = np.exp(exponents - exponents.max(axis=1, keepdims=True))
    alpha = (terms * w).sum(axis=1) / (terms * r).sum(axis=1)
    return {'q': q, 'tau': t, 'alpha': alpha, 'f': q * alpha - t}


def key_values(weights, sizes) -> dict:
    """
    ``alpha_min`` and ``alpha_max`` (the ends of the spectrum), ``alpha_0`` (where f = 1, the most numerous
    pieces), ``D1`` (information dimension, α(1)) and ``D2`` (correlation dimension, τ(2)).
    """
    w, r = np.log(np.asarray(weights, dtype=float)), np.log(np.asarray(sizes, dtype=float))
    at = spectrum([0.0, 1.0, 2.0], weights, sizes)
    return {'alpha_min': float((w / r).min()), 'alpha_max': float((w / r).max()),
            'alpha_0': float(at['alpha'][0]), 'D1': float(at['alpha'][1]), 'D2': float(at['tau'][2])}


def compositions(depth: int) -> np.ndarray:
    """All compositions (n₀, n₁, n₂, n₃) of ``depth``: non-negative, adding up to it."""
    out = [(a, b, c, depth - a - b - c) for a in range(depth + 1) for b in range(depth + 1 - a)
           for c in range(depth + 1 - a - b)]
    return np.array(out, dtype=int)


def composition_spectrum(depth: int, weights, sizes) -> dict:
    """
    The spectrum at a finite depth, from the compositions. α depends only on the product of the proportions along
    the address, the duration, so the subcycles with a given α are exactly a **class of equal duration**
    (compositions that differ by multiples of (1, 0, −2, 1)). For each class: ``alpha``, ``f`` = log(number of
    subcycles in it) / −log(size of one), and the logarithms ``log_count`` and ``log_size`` (the numbers overflow
    at large depths). There are (d + 1)(d + 2)(d + 3)/6 compositions and about (d + 1)² classes.
    """
    n = compositions(depth)
    w, r = np.log(np.asarray(weights, dtype=float)), np.log(np.asarray(sizes, dtype=float))
    log_count = np.array([math.lgamma(depth + 1) - sum(math.lgamma(k + 1) for k in row) for row in n])
    # the class of a composition: its duration (log Σ nᵢ log pᵢ, rounded)
    classes, inverse = np.unique(np.round(n @ np.log(PROPORTIONS), 9), return_inverse=True)
    inverse = inverse.ravel()
    top = np.full(len(classes), -np.inf)
    np.maximum.at(top, inverse, log_count)
    total = np.zeros(len(classes))
    np.add.at(total, inverse, np.exp(log_count - top[inverse]))
    class_count = top + np.log(total)
    first = np.unique(inverse, return_index=True)[1]          # one composition of each class
    log_size = (n @ r)[first]
    return {'alpha': (n @ w)[first] / log_size, 'f': class_count / -log_size,
            'log_count': class_count, 'log_size': log_size, 'compositions': n[first]}


def histogram_spectrum(depth: int, weights, sizes, width: float = 0.02) -> dict:
    """
    The spectrum at a finite depth by the histogram method: the classes of ``composition_spectrum`` grouped in
    bins of α ``width`` wide, f ≈ log(subcycles in the bin) / −log(size of those of its largest class). It tends
    to the exact f(α) as the depth grows (more slowly near the ends): f counts all the points with exponents
    near α, and a single class can be small while its neighbours hold most of the subcycles (the class of the
    address all Treta has one member, yet f there is about 0.86 for the time measure).
    """
    classes = composition_spectrum(depth, weights, sizes)
    bins = np.floor(classes['alpha'] / width).astype(int)
    keys, inverse = np.unique(bins, return_inverse=True)
    inverse = inverse.ravel()
    top = np.full(len(keys), -np.inf)
    np.maximum.at(top, inverse, classes['log_count'])
    total = np.zeros(len(keys))
    np.add.at(total, inverse, np.exp(classes['log_count'] - top[inverse]))
    largest = np.array([np.flatnonzero((inverse == k) & (classes['log_count'] == top[k]))[0]
                        for k in range(len(keys))])
    return {'alpha': (keys + 0.5) * width, 'f': (top + np.log(total)) / -classes['log_size'][largest]}
