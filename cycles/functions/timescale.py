"""
Physical time for subcycles.

The division works on the unit interval: starts and durations are fractions of
the whole cycle. A ``TimeMap`` links that interval to physical time (decimal
years, as used by ``astro_dates`` and the precession plots, or any other unit)
through matching anchor points:

* two anchors, ``0 -> start`` and ``1 -> end``: a linear map;
* five anchors at the age boundaries ``0, 0.4, 0.7, 0.9, 1``: each age is
  stretched to fit its own physical boundaries (for example, dates found from
  the precession of the equinoxes, which are not exactly 4:3:2:1), and the
  subdivision inside each age stays exact.

In general the map is piecewise linear between any increasing anchors. The
physical unit and time scale (UT, TDB...) are those of the anchors.

A map can also be built from any increasing function and its inverse with
``TimeMap.from_functions``; ``equinoctial_precession.precession_time_map``
uses it to divide a span of precession angle instead of a span of time, so
that the boundaries of every subcycle are precession boundaries.
"""

import itertools

import numpy as np

from cycles.functions.division import offsets, compute_start, compute_duration, find_lcoords

AGE_NAMES = ('Golden', 'Silver', 'Bronze', 'Iron')
YUGA_NAMES = ('Satya', 'Treta', 'Dvapara', 'Kali')

# Normalized times of the age boundaries: 0, 0.4, 0.7, 0.9, 1
AGE_BOUNDARIES = np.append(offsets, 1.0)


class TimeMap:
    """
    Increasing map between normalized time (0 to 1) and physical time.

    The constructor builds a piecewise-linear map: ``physical`` are the
    physical times of the anchors and ``normalized`` their normalized times;
    both must be strictly increasing, and ``normalized`` must go from 0 to 1.
    If ``normalized`` is omitted, two anchors are taken as the start and end of
    the cycle, and five as the age boundaries. See also ``from_functions``.
    """

    def __init__(self, physical, normalized=None):
        physical = np.asarray(physical, dtype=float)
        if normalized is None:
            if len(physical) == 2:
                normalized = [0.0, 1.0]
            elif len(physical) == len(AGE_BOUNDARIES):
                normalized = AGE_BOUNDARIES
            else:
                raise ValueError("give 2 anchors (start, end), 5 (age boundaries), or the normalized times")
        normalized = np.asarray(normalized, dtype=float)
        if normalized.shape != physical.shape or len(physical) < 2:
            raise ValueError("physical and normalized anchors must have the same length (at least 2)")
        if normalized[0] != 0.0 or normalized[-1] != 1.0:
            raise ValueError("normalized anchors must start at 0 and end at 1")
        if np.any(np.diff(normalized) <= 0) or np.any(np.diff(physical) <= 0):
            raise ValueError("anchors must be strictly increasing")
        self.physical = physical
        self.normalized = normalized
        self._forward = lambda u: np.interp(u, normalized, physical)
        self._inverse = lambda t: np.interp(t, physical, normalized)
        self.start = float(physical[0])
        self.end = float(physical[-1])

    @classmethod
    def from_functions(cls, to_physical, to_normalized) -> 'TimeMap':
        """
        Map given by an increasing function ``to_physical`` (normalized ->
        physical) and its inverse ``to_normalized``; both must accept arrays.
        """
        self = cls.__new__(cls)
        self.physical = self.normalized = None
        self._forward, self._inverse = to_physical, to_normalized
        probe = np.linspace(0.0, 1.0, 101)
        t = np.asarray(to_physical(probe), dtype=float)
        if np.any(np.diff(t) <= 0):
            raise ValueError("to_physical must be strictly increasing on [0, 1]")
        if not np.allclose(to_normalized(t), probe, rtol=0.0, atol=1e-9):
            raise ValueError("to_normalized is not the inverse of to_physical")
        self.start, self.end = float(t[0]), float(t[-1])
        return self

    @classmethod
    def linear(cls, start: float, end: float) -> 'TimeMap':
        """Linear map: 0 -> ``start``, 1 -> ``end``."""
        return cls([start, end])

    @classmethod
    def from_age_boundaries(cls, boundaries) -> 'TimeMap':
        """Map fitted to the five age boundaries (start of each age, and end)."""
        return cls(boundaries, AGE_BOUNDARIES)

    def to_physical(self, u):
        """Physical time of the normalized time ``u`` (scalar or array, within [0, 1])."""
        u = np.asarray(u, dtype=float)
        if np.any((u < 0) | (u > 1)):
            raise ValueError("normalized times must be within [0, 1]")
        t = np.asarray(self._forward(u), dtype=float)
        return float(t) if t.ndim == 0 else t

    def to_normalized(self, t):
        """Normalized time of the physical time ``t`` (scalar or array, within the cycle)."""
        t = np.asarray(t, dtype=float)
        tolerance = 1e-9 * (self.end - self.start)  # rounding of the end points
        if np.any((t < self.start - tolerance) | (t > self.end + tolerance)):
            raise ValueError(f"physical times must be within [{self.start}, {self.end}]")
        u = np.clip(np.asarray(self._inverse(t), dtype=float), 0.0, 1.0)
        return float(u) if u.ndim == 0 else u

    def interval(self, lcoords) -> tuple[float, float]:
        """Physical start and end of the subcycle with address ``lcoords``."""
        start = compute_start(lcoords)
        return self.to_physical(start), self.to_physical(min(1.0, start + compute_duration(lcoords)))

    def level_intervals(self, level) -> tuple[np.ndarray, np.ndarray]:
        """Physical starts and ends of all the subcycles of ``level``."""
        ends = np.minimum(1.0, level.starts + level.durations)
        return self.to_physical(level.starts), self.to_physical(ends)

    def subcycle_at(self, t: float, depth: int) -> np.ndarray:
        """Address of the subcycle of depth ``depth`` that contains the physical time ``t``."""
        return find_lcoords(self.to_normalized(t), depth)


def addresses_with_prefix(prefix, depth: int) -> list[list[int]]:
    """All addresses of depth ``depth`` that begin with ``prefix``, in time order."""
    prefix = list(prefix)
    return [prefix + list(rest) for rest in itertools.product(range(4), repeat=depth - len(prefix))]


def address_label(lcoords, names=YUGA_NAMES, separator: str = ' › ') -> str:
    """Readable name of an address, e.g. ``[3, 1]`` -> ``'Kali › Treta'``."""
    return separator.join(names[digit] for digit in lcoords)
