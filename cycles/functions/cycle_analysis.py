"""
How well the two criteria for dividing the yuga cycle agree: 4:3:2:1 in
precession angle and 4:3:2:1 in years.

With the division by angle exact, each subcycle's share of its parent's time
is its share of the arc (0.4, 0.3, 0.2, 0.1) times the parent's mean
precession rate over its own; the *mismatch* measures how far those time
shares are from 0.4, 0.3, 0.2, 0.1. It is zero only where the precession rate
is constant (or averages out). ``fit_anchor`` searches for the anchor (and
optionally the arc) that minimises the mismatch of the four yugas.
"""

from dataclasses import dataclass

import numpy as np

from cycles.functions.astro_dates import year_to_date
from cycles.functions.cycle_model import ANCHOR_POINTS, CycleModel
from cycles.functions.division import offsets, proportions

# Validity of the long-term precession model: years from J2000, and the ayanamsa it reaches (degrees)
LONG_TERM_SPAN = 199000.0
LONG_TERM_AYANAMSA = (-2787.0, 2818.0)


def boundary_fractions(depth: int) -> np.ndarray:
    """Normalized starts of all subcycles of ``depth`` in time order, and 1 (``4^depth + 1`` values)."""
    starts, durations = np.zeros(1), np.ones(1)
    for _ in range(depth):
        starts = (starts[:, None] + durations[:, None] * offsets[None, :]).ravel()
        durations = (durations[:, None] * proportions[None, :]).ravel()
    return np.append(starts, 1.0)


def time_shares(years: np.ndarray) -> np.ndarray:
    """
    From the boundary years of the subcycles of one depth (``4^d + 1`` values,
    or an array of such rows), each subcycle's share of its parent's time,
    shaped ``(..., 4^(d-1), 4)``.
    """
    years = np.asarray(years, dtype=float)
    lengths = np.diff(years, axis=-1)
    groups = lengths.reshape(*lengths.shape[:-1], -1, 4)
    return groups / groups.sum(axis=-1, keepdims=True)


def subdivision_deviations(model: CycleModel, depth: int) -> np.ndarray:
    """
    Deviation of the time shares from 0.4, 0.3, 0.2, 0.1 of the four parts of
    every subcycle of ``depth - 1``, dividing by angle: shape ``(4^(depth-1), 4)``.
    """
    angle_map = model.replace(division='angle').time_map()
    return time_shares(angle_map.to_physical(boundary_fractions(depth))) - proportions


def mismatch_by_depth(model: CycleModel, max_depth: int = 5) -> list[dict]:
    """For depths 1 to ``max_depth``: the largest and the RMS deviation of the time shares."""
    rows = []
    for depth in range(1, max_depth + 1):
        deviations = subdivision_deviations(model, depth)
        rows.append({'depth': depth, 'max': float(np.abs(deviations).max()),
                     'rms': float(np.sqrt(np.mean(deviations ** 2)))})
    return rows


def precession_rate(model: CycleModel, years) -> np.ndarray:
    """Precession rate (arcsec per year) of the model at ``years`` (central differences of a year)."""
    years = np.asarray(years, dtype=float)
    return (np.asarray(model.ayanamsa(years + 0.5)) - np.asarray(model.ayanamsa(years - 0.5))) * 3600


MEASURES = {'max': 'Largest deviation', 'rms': 'RMS deviation'}


def mismatch_grid(model: CycleModel, anchors: np.ndarray, turns: np.ndarray, depth: int,
                  measure: str = 'max') -> np.ndarray:
    """
    Deviation of the time shares from 4:3:2:1 when dividing by angle (the
    largest, or the RMS with ``measure='rms'``, over the parts of all
    subcycles at ``depth``), for every anchor year of the
    model's anchor point (rows) and arc in turns (columns); ``inf`` where the
    cycle leaves the range of the precession model.
    """
    if measure not in MEASURES:
        raise ValueError(f"measure must be one of {list(MEASURES)}")
    from cycles.plotting.equinoctial_precession import year_from_ayanamsa
    u = boundary_fractions(depth) - ANCHOR_POINTS[model.anchor_point]
    options = model._precession_options()
    result = np.full((len(anchors), len(turns)), np.inf)
    inside = np.abs(anchors - 2000.0) < LONG_TERM_SPAN
    if not inside.any():
        return result
    anchor_ayanamsa = np.asarray(model.ayanamsa(anchors[inside]))
    for j, n in enumerate(turns):
        rows = np.flatnonzero(inside)
        if model.precession == 'long_term':
            # targets of the ayanamsa must stay within the long-term model's range
            low, high = anchor_ayanamsa + u.min() * n * 360, anchor_ayanamsa + u.max() * n * 360
            valid = (low > LONG_TERM_AYANAMSA[0]) & (high < LONG_TERM_AYANAMSA[1])
            rows = rows[valid]
            if not len(rows):
                continue
        years = year_from_ayanamsa(u[None, :] * n, unit='turns', reference_year=anchors[rows, None], **options)
        deviations = time_shares(years) - proportions
        result[rows, j] = (np.abs(deviations).max(axis=(-2, -1)) if measure == 'max'
                           else np.sqrt(np.mean(deviations ** 2, axis=(-2, -1))))
    return result


_mismatch_grid = mismatch_grid


@dataclass
class FitResult:
    """Outcome of ``fit_anchor``."""
    model: CycleModel                 # the best model (anchor as a UT date)
    anchor_year: float                # its anchor (decimal year, UT)
    turns: float
    mismatch: float                   # largest deviation of the time shares at the fitted depth
    original_mismatch: float          # the same for the model the fit started from
    anchors: np.ndarray               # the scanned anchor years
    turn_values: np.ndarray           # the scanned arcs
    grid: np.ndarray                  # mismatch for every (anchor, arc)


def anchor_fields(year: float) -> tuple[str, str]:
    """``(anchor_date, anchor_time)`` of a decimal year, in UT: e.g. ``('3102 BC-02-17', '18:57')``."""
    y, m, d = year_to_date(year)
    minutes = round((d % 1) * 1440)
    if minutes == 1440:
        return anchor_fields(year + 1 / 525960)
    date = f"{1 - y} BC-{m:02d}-{int(d):02d}" if y <= 0 else f"{y}-{m:02d}-{int(d):02d}"
    return date, f"{minutes // 60:02d}:{minutes % 60:02d}"


def fit_anchor(model: CycleModel, anchor_range: tuple[float, float] = (-100000.0, 100000.0),
               turn_range: tuple[float, float] | None = None, depth: int = 1, step: float = 250.0,
               turn_step: float = 0.05) -> FitResult:
    """
    Anchor year (of the model's anchor point) and, if ``turn_range`` is given,
    precession arc that make the cycle's time shares closest to 4:3:2:1 when
    divided by angle (smallest largest deviation, at ``depth``: 1 for the four
    yugas, 2 for their parts too...).

    The search is a grid over ``anchor_range`` (every ``step`` years) and
    ``turn_range`` (every ``turn_step`` turns; the model's arc if not given),
    refined twice around the best point. The cycle must stay within the
    long-term precession model (about +/- 200,000 years from J2000).
    """
    solution = model.solve()
    fixed_turns = turn_range is None
    turns = np.array([solution['turns']]) if fixed_turns else np.arange(turn_range[0], turn_range[1] + 1e-9,
                                                                        turn_step)
    anchors = np.arange(anchor_range[0], anchor_range[1] + 1e-9, step)
    grid = _mismatch_grid(model, anchors, turns, depth)
    i, j = np.unravel_index(np.argmin(grid), grid.shape)
    best_anchor, best_turns = anchors[i], turns[j]
    a_step, t_step = step, turn_step
    for _ in range(2):                    # refine around the best point
        a_step, t_step = a_step / 10, t_step / 10
        local_anchors = np.clip(best_anchor + a_step * np.arange(-10, 11), *anchor_range)
        local_turns = (np.array([best_turns]) if fixed_turns
                       else np.clip(best_turns + t_step * np.arange(-10, 11), *turn_range))
        local = _mismatch_grid(model, local_anchors, local_turns, depth)
        i, j = np.unravel_index(np.argmin(local), local.shape)
        best_anchor, best_turns = local_anchors[i], local_turns[j]
    date, time = anchor_fields(best_anchor)
    best = model.replace(
        name=f"{model.name}, best fit", anchor_date=date, anchor_time=time, anchor_longitude=0.0,
        anchor_ayanamsa=None, turns=float(best_turns), years=None,
        description=f"Anchor{'' if fixed_turns else ' and arc'} fitted so that the time shares at depth {depth} "
                    f"are closest to 4:3:2:1 (from “{model.name}”).")
    original = _mismatch_grid(model, np.array([solution['anchor']]), np.array([solution['turns']]), depth)
    return FitResult(model=best, anchor_year=float(best_anchor), turns=float(best_turns),
                     mismatch=float(_mismatch_grid(model, np.array([best_anchor]), np.array([best_turns]),
                                                   depth)[0, 0]),
                     original_mismatch=float(original[0, 0]), anchors=anchors, turn_values=turns, grid=grid)
