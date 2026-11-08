"""
Planetary events over long spans, computed from the N-body ephemeris: the exact moments of conjunctions (or any
aspect) between two bodies, grouped into series (a conjunction repeated by retrograde motion), the sign and
element of each in the sidereal (Lahiri) or the tropical zodiac, the changes of trigon (element) of the
Jupiter–Saturn great conjunctions, and how a set of bodies stands around a point of the zodiac.

Times are decimal years in TDB (the ephemeris time scale). Conjunctions happen at the same moment in both zodiacs
(the ayanamsa cancels in a difference of longitudes); only their sign, and so their element, depends on the zodiac.

The moments are found by sampling the angular separation every ``step_days`` and refining every sign change by
bisection, all at once (``planet_positions_many``), to a few seconds of time.
"""

import hashlib
import warnings
from pathlib import Path

import numpy as np

from cycles.plotting.equinoctial_precession import planet_positions_many

ASPECTS = {'conjunction': 0.0, 'sextile': 60.0, 'square': 90.0, 'trine': 120.0, 'opposition': 180.0}
ZODIACS = ('sidereal', 'tropical')
SIGN_NAMES = ('Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius',
              'Capricorn', 'Aquarius', 'Pisces')
ELEMENTS = ('fire', 'earth', 'air', 'water')          # of the signs in order: Aries fire, Taurus earth…
CLASSICAL = ('sun', 'mercury', 'venus', 'mars', 'jupiter', 'saturn')   # the visible planets but the Moon

# Mean planets, as the Sūrya Siddhānta means them: the mean Sun, the heliocentric mean longitudes of Mercury and
# Venus (their śīghra) and of Mars, Jupiter and Saturn. Mean longitudes at J2000.0 (mean equinox of date) and
# their rates in degrees per Julian century: Simon et al. (1994), as in Meeus, Astronomical Algorithms, table 31.A.
MEAN_ELEMENTS = {
    'sun': (280.466457, 36000.7698278),           # the Earth's + 180°
    'mercury': (252.250906, 149474.0722491),
    'venus': (181.979801, 58519.2130302),
    'mars': (355.433000, 19141.6964471),
    'jupiter': (34.351519, 3036.3027748),
    'saturn': (50.077444, 1223.5110686),
}
GENERAL_PRECESSION = 1.396971                     # degrees per Julian century at J2000 (5028.796″)

# The Sūrya Siddhānta's mean motions (1.29–34, Burgess's translation): revolutions in a Mahāyuga of 4 320 000
# years and its civil days. All are even, so a conjunction repeats every half Mahāyuga.
SURYA_SIDDHANTA_REVOLUTIONS = {
    'sun': 4_320_000, 'mercury': 17_937_060, 'venus': 7_022_376, 'mars': 2_296_832, 'jupiter': 364_220,
    'saturn': 146_568,
}
SURYA_SIDDHANTA_DAYS = 1_577_917_828
DAYS_PER_YEAR = 365.25
CHUNK = 200_000                                       # moments per call to the ephemeris
# Where the catalogues of conjunctions are kept (shared by the explorer and study_of_events.py)
DEFAULT_CACHE = Path(__file__).resolve().parents[2] / 'sandbox' / 'data' / 'events'
CACHE_VERSION = 'v1'


def wrap180(angle):
    """Angles in degrees to (−180, 180]."""
    return 180.0 - (180.0 - np.asarray(angle, dtype=float)) % 360.0


def sign_of(longitude):
    """Sign index (0 = Aries … 11 = Pisces) of longitudes in degrees."""
    return (np.floor(np.asarray(longitude, dtype=float) % 360.0 / 30.0)).astype(int)


def element_of(longitude):
    """Element index (0 fire, 1 earth, 2 air, 3 water) of longitudes in degrees."""
    return sign_of(longitude) % 4


def longitudes(tables, years, bodies, zodiac: str = 'sidereal') -> dict:
    """Geocentric ecliptic longitudes (degrees) of ``bodies`` at ``years`` (TDB), in chunks; NaN off the tables."""
    if zodiac not in ZODIACS:
        raise ValueError(f"zodiac must be one of {ZODIACS}")
    years = np.atleast_1d(np.asarray(years, dtype=float))
    out = {b: np.empty(len(years)) for b in bodies}
    for k in range(0, len(years), CHUNK):
        part = planet_positions_many(years[k:k + CHUNK], tables, bodies)
        for b in bodies:
            out[b][k:k + CHUNK] = part[b][zodiac]
    return out


def aspect_times(tables, a: str, b: str, start: float, end: float, angle: float = 0.0,
                 step_days: float = 10.0, iterations: int = 30) -> np.ndarray:
    """
    Moments (TDB years) in [start, end] when the longitude of ``a`` minus that of ``b`` equals ``angle``
    (0 for a conjunction; an aspect of 120° is found as +120 and −120 separately). Exact to
    ``step_days / 2^iterations`` days.
    """
    step = step_days / DAYS_PER_YEAR
    grid = np.arange(start, end + step, step)
    lon = longitudes(tables, grid, (a, b), 'tropical')
    f = wrap180(lon[a] - lon[b] - angle)
    f0, f1 = f[:-1], f[1:]
    # a crossing of zero, not the jump at ±180
    crossing = (np.sign(f0) != np.sign(f1)) & (np.abs(f0) < 90) & (np.abs(f1) < 90) & np.isfinite(f0) & \
        np.isfinite(f1)
    lo, hi = grid[:-1][crossing], grid[1:][crossing]
    f_lo = f0[crossing]
    for _ in range(iterations):
        mid = (lo + hi) / 2
        part = longitudes(tables, mid, (a, b), 'tropical')
        f_mid = wrap180(part[a] - part[b] - angle)
        same = np.sign(f_mid) == np.sign(f_lo)
        lo = np.where(same, mid, lo)
        f_lo = np.where(same, f_mid, f_lo)
        hi = np.where(same, hi, mid)
    return (lo + hi) / 2


def series(times: np.ndarray, gap_years: float) -> np.ndarray:
    """Series number of each moment: consecutive moments closer than ``gap_years`` belong to one series."""
    times = np.asarray(times, dtype=float)
    if not len(times):
        return np.zeros(0, dtype=int)
    return np.concatenate([[0], np.cumsum(np.diff(times) > gap_years)])


def conjunctions(tables, a: str, b: str, start: float, end: float, gap_years: float = 2.0,
                 step_days: float = 10.0) -> dict:
    """
    Conjunctions of ``a`` and ``b`` in [start, end]: their moments, the longitude of the conjunction in both
    zodiacs, and the series they belong to (a conjunction repeated within ``gap_years`` by retrograde motion).
    """
    times = aspect_times(tables, a, b, start, end, 0.0, step_days)
    result = {'times': times, 'series': series(times, gap_years)}
    for zodiac in ZODIACS:
        result[zodiac] = longitudes(tables, times, (a,), zodiac)[a] if len(times) else np.zeros(0)
    return result


def first_of_series(catalog: dict) -> np.ndarray:
    """Indices of the first conjunction of every series."""
    s = catalog['series']
    return np.flatnonzero(np.concatenate([[True], s[1:] != s[:-1]])) if len(s) else np.zeros(0, dtype=int)


def trigon_changes(catalog: dict, zodiac: str, settle: int = 2) -> np.ndarray:
    """
    Moments when the great conjunctions change trigon (element), as the tradition counts them: when they settle
    in a new element. Each series is judged by its first conjunction; runs of fewer than ``settle`` series in an
    element are passing (near a change the conjunctions alternate for a while: 1981 air, 2000 earth, 2020 air),
    and a change is the first series of a lasting run whose element differs from the previous lasting run.
    With ``settle=2`` the tropical changes come every 200 years on average (fire in 1603, air in 2020).
    """
    first = first_of_series(catalog)
    elements = element_of(catalog[zodiac][first])
    times = catalog['times'][first]
    starts = np.flatnonzero(np.concatenate([[True], elements[1:] != elements[:-1]]))
    lengths = np.diff(np.append(starts, len(elements)))
    lasting = starts[lengths >= settle]
    if len(lasting) < 2:
        return np.zeros(0)
    changed = np.concatenate([[False], elements[lasting][1:] != elements[lasting][:-1]])
    return times[lasting][changed]


def mean_longitudes(years, bodies=CLASSICAL, zodiac: str = 'sidereal') -> dict:
    """
    Mean longitudes (degrees) of the mean planets (``MEAN_ELEMENTS``) at ``years`` (TDB): sidereal in the Lahiri
    frame of the rest of the project (23.853° at J2000, advancing at the sidereal rates), or tropical (the sidereal
    plus the long-term ayanamsa). Linear in time: the mean planets, not the true ones.
    """
    from cycles.plotting.equinoctial_precession import LAHIRI_AYANAMSA_J2000_DEG, long_term_ayanamsa
    if zodiac not in ZODIACS:
        raise ValueError(f"zodiac must be one of {ZODIACS}")
    years = np.atleast_1d(np.asarray(years, dtype=float))
    centuries = (years - 2000.0) / 100.0
    out = {}
    for b in bodies:
        start, rate = MEAN_ELEMENTS[b]
        out[b] = (start - LAHIRI_AYANAMSA_J2000_DEG + (rate - GENERAL_PRECESSION) * centuries) % 360.0
    if zodiac == 'tropical':
        ayanamsa = np.asarray(long_term_ayanamsa(years), dtype=float)
        out = {b: (v + ayanamsa) % 360.0 for b, v in out.items()}
    return out


def surya_siddhanta_longitudes(years, epoch: float, bodies=CLASSICAL) -> dict:
    """
    Mean longitudes (degrees) by the Sūrya Siddhānta's own mean motions, all 0 at ``epoch`` (the start of Kali, in
    its tradition): its revolutions per Mahāyuga over its civil days, counted in days from the epoch (decimal
    Julian years of 365.25 days; the text's own year is 365.258756 days, so its periodicities, such as the
    conjunction every half Mahāyuga, hold in its years, not in these).
    """
    days = (np.atleast_1d(np.asarray(years, dtype=float)) - epoch) * DAYS_PER_YEAR
    return {b: (360.0 * SURYA_SIDDHANTA_REVOLUTIONS[b] * days / SURYA_SIDDHANTA_DAYS) % 360.0 for b in bodies}


def around_point(tables, years, bodies=CLASSICAL, point: float = 0.0, zodiac: str = 'sidereal',
                 mean: bool = False) -> dict:
    """
    How ``bodies`` stand around the longitude ``point`` (0 = the start of Aries) at ``years``: ``mean_distance``,
    the mean angle of the bodies from it (0 if all are on it, 90° on average for random longitudes), and
    ``spread``, the smallest arc that contains them all. With ``mean``, the mean planets (``mean_longitudes``,
    no ephemeris needed) instead of the true ones.
    """
    lon = mean_longitudes(years, bodies, zodiac) if mean else longitudes(tables, years, bodies, zodiac)
    stack = np.vstack([lon[b] for b in bodies])                          # (bodies, moments)
    distance = np.abs(wrap180(stack - point)).mean(axis=0)
    ordered = np.sort(stack % 360.0, axis=0)
    gaps = np.diff(np.vstack([ordered, ordered[:1] + 360.0]), axis=0)
    spread = 360.0 - gaps.max(axis=0)
    return {'mean_distance': distance, 'spread': spread, 'longitudes': lon}


# -- time scales and the cache

def table_span(tables) -> tuple[float, float]:
    """TDB years covered by the ephemeris ``tables`` together (from the earliest to the latest moment)."""
    ends = []
    for table in ([tables] if isinstance(tables, dict) else tables):
        reach = min(float(t[-1]) for t in table['times'].values())
        ends += [2000.0, 2000.0 + table['sign'] * reach / DAYS_PER_YEAR + (table['jd0'] - 2451545.0) / DAYS_PER_YEAR]
    return min(ends), max(ends)


def tdb_years(years_ut) -> np.ndarray:
    """Decimal years in UT to TDB (with the DeltaT of ``astro_dates``; its warnings far from the present silenced)."""
    from cycles.plotting.equinoctial_precession import _tdb_year
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return np.array([_tdb_year(float(y), 'UT') for y in np.atleast_1d(years_ut)])


def ut_years(years_tdb) -> np.ndarray:
    """Decimal years in TDB to UT (the inverse of ``tdb_years``)."""
    from cycles.functions.astro_dates import julian_day_to_year, tdb_to_ut, year_to_julian_day
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return np.array([julian_day_to_year(tdb_to_ut(year_to_julian_day(float(y))))
                         for y in np.atleast_1d(years_tdb)])


def cached_conjunctions(tables, table_path, a: str, b: str, start: float, end: float,
                        cache_dir=DEFAULT_CACHE) -> dict:
    """
    ``conjunctions`` of ``a`` and ``b`` in [start, end] (TDB years), kept in ``cache_dir`` under a name that
    depends on the ephemeris folder ``table_path`` and the span: computed once (seconds), then read.
    """
    key = hashlib.sha1(f"{Path(table_path).resolve()}|{a}|{b}|{start:.3f}|{end:.3f}|{CACHE_VERSION}".encode())
    path = Path(cache_dir) / f"{a}_{b}_{key.hexdigest()[:16]}.npz"
    if path.exists():
        return dict(np.load(path))
    data = conjunctions(tables, a, b, start, end)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, **data)
    return data
