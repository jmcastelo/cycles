"""
equinoctial_precession.py

Position of the equinoctial and solstitial axes relative to the sidereal
zodiac (Lahiri ayanamsa), including spans of several precession turns (tens of
thousands of years).

Plots are seen from the north ecliptic pole, with 0 degrees at the top and
longitudes increasing counterclockwise. The sidereal zodiac (12 signs of 30
degrees) is fixed; the equinoctial/solstitial axes, together with the tropical
zodiac attached to them, rotate clockwise because of precession.

Models for the ayanamsa A(year)
-------------------------------
``long_term`` (default)
    Non-linear model based on the Vondrak, Capitaine & Wallace (2011, A&A 534,
    A22; corrigendum 2012, A&A 541, C1) long-term precession expressions,
    valid for +/- 200,000 years around J2000.0. The model gives the pole of
    the ecliptic and the pole of the mean equator of date. From them, the
    ecliptic longitude *of date* of a fixed reference direction (Spica, as in
    the Lahiri definition) is computed and its change since J2000.0 is
    accumulated continuously (without reduction modulo 360):

        A(year) = A_J2000 + [lambda_Spica(year) - lambda_Spica(2000)]

    with A_J2000 = 23.853 deg (23 deg 51' 11'', Lahiri value at J2000.0).
    Spica's proper motion is ignored (the sidereal reference is a fixed
    direction). The model agrees with the IAU 2006 precession at J2000.0; per
    the ERFA documentation it is accurate to a few arcseconds over the
    historical period and degrades to a few tenths of a degree at the ends of
    the +/- 200,000 year span.

``linear``
    Constant rate:  A(year) = A_J2000 + (year - 2000) * rate / 3600  with
    rate = 50.29 arcsec/year (one turn per ~25772 years). It has no physical
    validity beyond a few millennia; the figures say so (in Spanish) when the
    year is more than 6000 years from J2000.

A custom model can be supplied to the precession plot with
``ayanamsa_function`` (a callable ``year -> ayanamsa in degrees``). In every
case the ayanamsa is NOT reduced modulo 360: over long spans it accumulates
several turns, and the precession plot shows it as a spiral arc.

Attribution
-----------
The periodic and polynomial coefficients were transcribed from the ERFA
library (liberfa/erfa, files ltpecl.c and ltpequ.c; BSD-3-Clause license,
"derived, with permission, from the SOFA library" of the IAU) and checked
against it. If you redistribute this module, keep this attribution ("a
library derived from SOFA") and the reference to the paper.

Year convention
---------------
Astronomical year numbering (1 BC = year 0, 3102 BC = -3101), fractional years
allowed (Julian years from J2000.0, i.e. Julian epochs). For calendar dates
use the companion module ``astro_dates``:

    from astro_dates import date_to_year, parse_date
    plot_equinoctial_precession(date_to_year(*parse_date("3102 BC-02-18")))

Dependencies
------------
NumPy (imported at module level) and, lazily inside the plotting functions,
matplotlib.

Public API
----------
lahiri_ayanamsa(year, ...)             linear model (scalar or array)
long_term_ayanamsa(year, ...)          non-linear model (scalar or array)
year_from_ayanamsa(value, ...)         inverse: year at which A takes a value
plot_equinoctial_precession(year, ...) polar diagram for one year
plot_ayanamsa_comparison(...)          A(t) for both models + difference
"""

from __future__ import annotations

import functools
import math
from typing import Callable, Dict, Optional, Sequence, Tuple

import numpy as np

__all__ = ["lahiri_ayanamsa", "long_term_ayanamsa", "year_from_ayanamsa",
           "plot_equinoctial_precession", "plot_ayanamsa_comparison"]

# ----------------------------------------------------------------------------
# Model constants
# ----------------------------------------------------------------------------

LAHIRI_AYANAMSA_J2000_DEG = 23.853
PRECESSION_RATE_ARCSEC_PER_YEAR = 50.29
LONG_TERM_VALIDITY_YEARS = 200000.0
_EXTRAPOLATION_THRESHOLD_YEARS = 6000.0
_MAX_UNWRAP_STEP_YEARS = 5000.0

_DAS2R = math.pi / (180.0 * 3600.0)   # arcseconds to radians
_D2PI = 2.0 * math.pi
_EPS0 = 84381.406 * _DAS2R            # mean obliquity at J2000.0 (IAU 2006)

# Reference direction: Spica (alpha Virginis), J2000.0 ICRS, fixed in space.
_SPICA_RA = math.radians(201.298246)
_SPICA_DEC = math.radians(-11.161319)
_SPICA = np.array([math.cos(_SPICA_DEC) * math.cos(_SPICA_RA),
                   math.cos(_SPICA_DEC) * math.sin(_SPICA_RA),
                   math.sin(_SPICA_DEC)])

# Vondrak, Capitaine & Wallace (2011, 2012). Polynomial terms in arcseconds
# per century^i; periodic terms: (period in centuries, cos P, cos Q, sin P,
# sin Q) for the ecliptic pole (P_A, Q_A) and (period, cos X, cos Y, sin X,
# sin Y) for the equator pole (X, Y), in arcseconds.
_PQ_POLY = np.array([
    [5851.607687, -0.1189000, -0.00028913, 0.000000101],
    [-1600.886300, 1.1689818, -0.00000020, -0.000000437],
])
_PQ_PERIODIC = np.array([
    [708.15, -5486.751211, -684.661560, 667.666730, -5523.863691],
    [2309.00, -17.127623, 2446.283880, -2354.886252, -549.747450],
    [1620.00, -617.517403, 399.671049, -428.152441, -310.998056],
    [492.20, 413.442940, -356.652376, 376.202861, 421.535876],
    [1183.00, 78.614193, -186.387003, 184.778874, -36.776172],
    [622.00, -180.732815, -316.800070, 335.321713, -145.278396],
    [882.00, -87.676083, 198.296701, -185.138669, -34.744450],
    [547.00, 46.140315, 101.135679, -120.972830, 22.885731],
])
_XY_POLY = np.array([
    [5453.282155, 0.4252841, -0.00037173, -0.000000152],
    [-73750.930350, -0.7675452, -0.00018725, 0.000000231],
])
_XY_PERIODIC = np.array([
    [256.75, -819.940624, 75004.344875, 81491.287984, 1558.515853],
    [708.15, -8444.676815, 624.033993, 787.163481, 7774.939698],
    [274.20, 2600.009459, 1251.136893, 1251.296102, -2219.534038],
    [241.45, 2755.175630, -1102.212834, -1257.950837, -2523.969396],
    [2309.00, -167.659835, -2660.664980, -2966.799730, 247.850422],
    [492.20, 871.855056, 699.291817, 639.744522, -846.485643],
    [396.10, 44.769698, 153.167220, 131.600209, -1393.124055],
    [288.90, -512.313065, -950.865637, -445.040117, 368.526116],
    [231.10, -819.415595, 499.754645, 584.522874, 749.045012],
    [1610.00, -538.071099, -145.188210, -89.756563, 444.704518],
    [620.00, -189.793622, 558.116553, 524.429630, 235.934465],
    [157.87, -402.922932, -23.923029, -13.549067, 374.049623],
    [220.30, 179.516345, -165.405086, -210.157124, -171.330180],
    [1200.00, -9.814756, 9.344131, -44.919798, -22.899655],
])

# ----------------------------------------------------------------------------
# Visual constants (colors) and user-facing text (Spanish)
# ----------------------------------------------------------------------------

_RED = "#D85A30"
_GREEN = "#1D9E75"
_PURPLE = "#534AB7"
_AMBER = "#EF9F27"
_AMBER_EDGE = "#BA7517"
_RING_LIGHT = "#F1EFE8"
_RING_DARK = "#DCD9CF"
_RING_EDGE = "#888780"
_TEXT_DARK = "#2C2C2A"
_TEXT_MUTED = "#888780"
_TEXT_NOTE = "#A32D2D"
_TEXT_NOTE_MODEL = "#5F5E5A"

_SIGN_NAMES = ["Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo",
               "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario",
               "Piscis"]
_SIGN_ABBREVIATIONS = ["Ari", "Tau", "Gem", "Cán", "Leo", "Vir",
                       "Lib", "Esc", "Sag", "Cap", "Acu", "Pis"]

_LABEL_VERNAL = "Punto vernal"
_LABEL_JUNE = "Solsticio\nde junio"
_LABEL_AUTUMNAL = "Punto otoñal"
_LABEL_DECEMBER = "Solsticio\nde diciembre"
_LABEL_SPICA = "Spica (Chitrā)"
_TITLE_TEMPLATE = "Precesión de los equinoccios · año {year}"
_SUMMARY_AYANAMSA_LAHIRI = "Ayanāṃśa de Lahiri: A = {deg}° = {dms}{turns}"
_SUMMARY_AYANAMSA_CUSTOM = "Ayanāṃśa (modelo propio): A = {deg}° = {dms}{turns}"
_SUMMARY_TURNS = " ({turns} vueltas)"
_SUMMARY_VERNAL = ("Punto vernal: longitud sidérea {lon}° → "
                   "{dms} de {sign} (sidéreo)")
_ARC_LABEL_TURNS = "\n({turns} vueltas)"
_NOTE_LONG_TERM = "Precesión de largo plazo (Vondrák, Capitaine y Wallace, 2011)"
_NOTE_EXTRAPOLATION = ("Modelo lineal (tasa constante): extrapolación sin "
                       "validez física más allá de unos milenios")
_LEGEND_EQUINOCTIAL = "Eje equinoccial"
_LEGEND_SOLSTITIAL = "Eje solsticial"
_LEGEND_AYANAMSA = "Ayanāṃśa (↻ los ejes retroceden)"
_LEGEND_SIDEREAL_ZERO = "0° sidéreo"
_LEGEND_TROPICAL = "Zodiaco tropical (marcas)"
_ERA_AD = "d. C."
_ERA_BC = "a. C."

_CMP_TITLE = "Ayanāṃśa: modelo lineal frente a precesión de largo plazo"
_CMP_XLABEL = "Año (numeración astronómica: 0 = 1 a. C.)"
_CMP_YLABEL_A = "Ayanāṃśa A (°)"
_CMP_YLABEL_TURNS = "Vueltas"
_CMP_YLABEL_DIFF = "Largo plazo − lineal (°)"
_CMP_YLABEL_RATE = "Tasa (″/año)"
_CMP_LEGEND_LINEAR = "Lineal ({rate}″/año)"
_CMP_LEGEND_LONG_TERM = "Largo plazo (Vondrák et al., 2011)"
_CMP_LABEL_J2000 = "J2000"
_CMP_MAX_DIFFERENCE = "Diferencia máxima: {value}° (año {year})"
_CMP_MARKS_HEADER = "Año en que se alcanza cada valor"
_CMP_MARK_LINE = "{label}: lineal {linear} · largo plazo {long_term}{outside}"
_CMP_MARK_OUTSIDE = " (fuera del tramo)"
_CMP_MARK_A = "A = {value}°"
_CMP_MARK_A_TURNS = "A = {value} {unit}"
_CMP_MARK_DELTA = "ΔA = {value}° desde {ref}"
_CMP_MARK_DELTA_TURNS = "ΔA = {value} {unit} desde {ref}"
_CMP_TURN_SINGULAR = "vuelta"
_CMP_TURN_PLURAL = "vueltas"


# ----------------------------------------------------------------------------
# Models (scalar or array input)
# ----------------------------------------------------------------------------

def lahiri_ayanamsa(
    year,
    j2000_ayanamsa_deg: float = LAHIRI_AYANAMSA_J2000_DEG,
    rate_arcsec_per_year: float = PRECESSION_RATE_ARCSEC_PER_YEAR,
):
    """
    Return the Lahiri ayanamsa in degrees for ``year`` (linear model).

    ``year`` may be a float or an array; the result is not reduced modulo 360.
    """
    result = (j2000_ayanamsa_deg
              + (np.asarray(year, dtype=float) - 2000.0)
              * rate_arcsec_per_year / 3600.0)
    return float(result) if np.ndim(year) == 0 else result


def _poles_of_date(epochs: np.ndarray):
    """
    Ecliptic pole (N, 3) and equator pole (N, 3) unit vectors of date, in the
    J2000.0 mean equatorial frame, for an array of Julian epochs.
    """
    t = (epochs - 2000.0) / 100.0
    powers = t[:, None] ** np.arange(4)                      # (N, 4)
    phase = (_D2PI * t)[:, None]

    a = phase / _PQ_PERIODIC[:, 0]                           # (N, 8)
    s, c = np.sin(a), np.cos(a)
    p = (c * _PQ_PERIODIC[:, 1] + s * _PQ_PERIODIC[:, 3]).sum(axis=1)
    q = (c * _PQ_PERIODIC[:, 2] + s * _PQ_PERIODIC[:, 4]).sum(axis=1)
    p = (p + powers @ _PQ_POLY[0]) * _DAS2R
    q = (q + powers @ _PQ_POLY[1]) * _DAS2R
    w = np.sqrt(np.clip(1.0 - p * p - q * q, 0.0, None))
    sin_e, cos_e = math.sin(_EPS0), math.cos(_EPS0)
    ecliptic = np.stack([p, -q * cos_e - w * sin_e, -q * sin_e + w * cos_e],
                        axis=1)

    a = phase / _XY_PERIODIC[:, 0]                           # (N, 14)
    s, c = np.sin(a), np.cos(a)
    x = (c * _XY_PERIODIC[:, 1] + s * _XY_PERIODIC[:, 3]).sum(axis=1)
    y = (c * _XY_PERIODIC[:, 2] + s * _XY_PERIODIC[:, 4]).sum(axis=1)
    x = (x + powers @ _XY_POLY[0]) * _DAS2R
    y = (y + powers @ _XY_POLY[1]) * _DAS2R
    z = np.sqrt(np.clip(1.0 - x * x - y * y, 0.0, None))
    equator = np.stack([x, y, z], axis=1)
    return ecliptic, equator


def _spica_longitude_of_date(epochs: np.ndarray) -> np.ndarray:
    """Ecliptic longitude (radians, mod 2*pi) of Spica w.r.t. equinox and ecliptic of date."""
    ecliptic, equator = _poles_of_date(epochs)
    x = np.cross(equator, ecliptic)                          # equinox of date
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    y = np.cross(ecliptic, x)
    return np.arctan2(y @ _SPICA, x @ _SPICA)


def long_term_ayanamsa(
    year,
    j2000_ayanamsa_deg: float = LAHIRI_AYANAMSA_J2000_DEG,
    step_years: float = 100.0,
):
    """
    Return the ayanamsa in degrees for ``year`` using the Vondrak et al. (2011)
    long-term precession model (non-linear), accumulated without reduction
    modulo 360.

    Parameters
    ----------
    year : float or array_like
        Julian epochs (astronomical year numbering, fractional allowed). All
        values must be within +/- 200,000 years of J2000.0. The array shape is
        preserved; a scalar input returns a float.
    j2000_ayanamsa_deg : float
        Ayanamsa at J2000.0 used as the anchor (Lahiri: 23.853 deg).
    step_years : float
        Maximum spacing of the internal grid used to unwrap the longitude
        continuously (0 < step <= 5000). The default is far below the spacing
        at which a wrap could be ambiguous (180 degrees of precession); the
        result at the requested years is exact (no interpolation).
    """
    values = np.asarray(year, dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("year must be finite")
    if np.any(np.abs(values - 2000.0) > LONG_TERM_VALIDITY_YEARS):
        raise ValueError(
            f"the long-term model is valid only within +/- "
            f"{LONG_TERM_VALIDITY_YEARS:.0f} years of J2000.0")
    if not 0.0 < step_years <= _MAX_UNWRAP_STEP_YEARS:
        raise ValueError(f"step_years must be in (0, {_MAX_UNWRAP_STEP_YEARS:.0f}]")

    flat = values.ravel()
    low = min(float(flat.min(initial=2000.0)), 2000.0)
    high = max(float(flat.max(initial=2000.0)), 2000.0)
    n_nodes = max(2, int(math.ceil((high - low) / step_years)) + 1)
    # Grid = requested years + J2000 + filler nodes; the result is read off at
    # the requested years, so nothing is interpolated.
    grid = np.unique(np.concatenate([flat, [2000.0],
                                     np.linspace(low, high, n_nodes)]))
    longitude = np.unwrap(_spica_longitude_of_date(grid))
    at_j2000 = np.searchsorted(grid, 2000.0)
    degrees = j2000_ayanamsa_deg + np.degrees(longitude - longitude[at_j2000])
    result = degrees[np.searchsorted(grid, flat)].reshape(values.shape)
    return float(result) if values.ndim == 0 else result


@functools.lru_cache(maxsize=1)
def _long_term_lookup():
    """Cached table (years, change of A since J2000.0) over the validity range."""
    years = np.arange(2000.0 - LONG_TERM_VALIDITY_YEARS,
                      2000.0 + LONG_TERM_VALIDITY_YEARS + 1e-9, 10.0)
    return years, long_term_ayanamsa(years, 0.0)


def year_from_ayanamsa(
    value,
    unit: str = "degrees",
    reference_year: Optional[float] = None,
    model: str = "long_term",
    j2000_ayanamsa_deg: float = LAHIRI_AYANAMSA_J2000_DEG,
    rate_arcsec_per_year: float = PRECESSION_RATE_ARCSEC_PER_YEAR,
):
    """
    Inverse of the ayanamsa models: the year at which A reaches a target.

    Both models are strictly increasing, so the year is unique. The linear
    model is inverted in closed form; the long-term model is inverted with a
    lookup table (10-year step) refined by Newton iterations, so the result
    is accurate to far better than a day.

    Parameters
    ----------
    value : float or array_like
        Target, accumulated and NOT reduced modulo 360. Negative values are
        allowed (A decreases, so the year is earlier).
    unit : {"degrees", "turns"}
        Unit of ``value``. One turn is 360 degrees.
    reference_year : float, optional
        If None (default), ``value`` is the ayanamsa A itself (so turns=1
        means A = 360 deg). If given, ``value`` is the change of A *since that
        year*, evaluated with the same model: the target is
        A(reference_year) + value, so ``value=0`` returns ``reference_year``
        itself, turns=1 gives the year one full turn later and turns=-1 one
        full turn earlier. ``reference_year=2000`` is the change since
        J2000.0. Astronomical year numbering, fractional allowed; arrays
        broadcast against ``value``.
    model : {"long_term", "linear"}
        Model to invert. The long-term model only covers the A range reached
        within +/- 200,000 years of J2000.0 (about -2788 to +2819 degrees);
        a target outside it, or a ``reference_year`` outside the validity
        range, raises ``ValueError``.
    j2000_ayanamsa_deg, rate_arcsec_per_year : float
        As in the forward models.

    Returns
    -------
    float or ndarray
        Julian epoch (astronomical year numbering, fractional). Combine with
        ``astro_dates.year_to_date`` to get a calendar date.

    Example
    -------
    >>> year_from_ayanamsa(30.0)                          # A = 30 degrees
    >>> year_from_ayanamsa(2.5, unit="turns", reference_year=2000)
    >>> year_from_ayanamsa(-1, unit="turns", reference_year=-3101)
    """
    if unit not in ("degrees", "turns"):
        raise ValueError("unit must be 'degrees' or 'turns'")
    if model not in ("long_term", "linear"):
        raise ValueError("model must be 'long_term' or 'linear'")
    if isinstance(reference_year, (bool, np.bool_)):
        raise TypeError("reference_year must be a year (use reference_year=2000 "
                        "for 'since J2000'), not a bool")
    values = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("value must be finite")

    degrees = values * 360.0 if unit == "turns" else values
    if reference_year is None:
        target = degrees
    else:
        reference = np.asarray(reference_year, dtype=float)
        if not np.all(np.isfinite(reference)):
            raise ValueError("reference_year must be finite")
        if model == "linear":
            at_reference = lahiri_ayanamsa(reference, j2000_ayanamsa_deg,
                                           rate_arcsec_per_year)
        else:
            at_reference = long_term_ayanamsa(reference, j2000_ayanamsa_deg)
        target = np.asarray(at_reference) + degrees
    delta = target - j2000_ayanamsa_deg          # change of A since J2000.0

    if model == "linear":
        result = 2000.0 + delta * 3600.0 / rate_arcsec_per_year
    else:
        years_grid, delta_grid = _long_term_lookup()
        if np.any(delta < delta_grid[0]) or np.any(delta > delta_grid[-1]):
            low = j2000_ayanamsa_deg + delta_grid[0]
            high = j2000_ayanamsa_deg + delta_grid[-1]
            raise ValueError(
                f"the long-term model covers ayanamsa values from {low:.1f} "
                f"to {high:.1f} degrees (+/- {LONG_TERM_VALIDITY_YEARS:.0f} "
                f"years around J2000.0)")
        t_min = 2000.0 - LONG_TERM_VALIDITY_YEARS
        t_max = 2000.0 + LONG_TERM_VALIDITY_YEARS
        result = np.interp(delta, delta_grid, years_grid)
        for _ in range(8):                      # Newton refinement
            residual = long_term_ayanamsa(result, 0.0) - delta
            lo = np.clip(result - 1.0, t_min, t_max)
            hi = np.clip(result + 1.0, t_min, t_max)
            slope = (long_term_ayanamsa(hi, 0.0)
                     - long_term_ayanamsa(lo, 0.0)) / (hi - lo)
            step = residual / slope
            result = np.clip(result - step, t_min, t_max)
            if np.max(np.abs(step)) < 1e-10:
                break
    return float(result) if np.ndim(result) == 0 else result

# ----------------------------------------------------------------------------
# Private formatting helpers
# ----------------------------------------------------------------------------

def _format_number(value: float, decimals: int = 2) -> str:
    """Format with a decimal comma and a typographic minus sign."""
    return f"{value:.{decimals}f}".replace(".", ",").replace("-", "−")


def _format_deg_min(degrees: float) -> str:
    """Format decimal degrees as D°MM′ (rounded to the nearest arcminute)."""
    sign = "−" if degrees < 0 else ""
    absolute = abs(degrees)
    whole = int(absolute)
    minutes = int(round((absolute - whole) * 60))
    if minutes == 60:
        whole, minutes = whole + 1, 0
    return f"{sign}{whole}°{minutes:02d}′"


def _format_year(year: float) -> str:
    """Format an astronomical year as a Spanish 'd. C.' / 'a. C.' string."""
    decimals = 0 if float(year).is_integer() else 2
    if year > 0:
        return f"{_format_number(year, decimals)} {_ERA_AD}"
    return f"{_format_number(1 - year, decimals)} {_ERA_BC}"


def _format_compact(value: float) -> str:
    """Compact number with a decimal comma (30 -> '30', 2.5 -> '2,5')."""
    return f"{value:g}".replace(".", ",").replace("-", "−")


def _mark_label(value: float, unit: str,
                reference_year: Optional[float]) -> str:
    """Spanish label for a mark, e.g. 'A = 30°' or 'ΔA = 2,5 vueltas desde 2000'."""
    relative = reference_year is not None
    if unit == "turns":
        template = _CMP_MARK_DELTA_TURNS if relative else _CMP_MARK_A_TURNS
    else:
        template = _CMP_MARK_DELTA if relative else _CMP_MARK_A
    unit_text = _CMP_TURN_SINGULAR if abs(value) == 1 else _CMP_TURN_PLURAL
    ref_text = _format_compact(reference_year) if relative else ""
    return template.format(value=_format_compact(value), unit=unit_text,
                           ref=ref_text)

def _least_crowded_corner(ax, x_values, curves):
    """
    Pick the axes corner (lower right, upper right or lower left) where the
    curves pass least, as (x, y, horizontal alignment, vertical alignment) in
    axes coordinates. The upper left is kept free for the legend.
    """
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    xn = (np.asarray(x_values) - x0) / (x1 - x0)
    counts = {"lower right": 0, "upper right": 0, "lower left": 0}
    for curve in curves:
        yn = (np.asarray(curve) - y0) / (y1 - y0)
        counts["lower right"] += int(np.sum((xn > 0.50) & (yn < 0.32)))
        counts["upper right"] += int(np.sum((xn > 0.50) & (yn > 0.68)))
        counts["lower left"] += int(np.sum((xn < 0.50) & (yn < 0.32)))
    best = min(counts, key=lambda name: counts[name])   # ties: first listed
    return {"lower right": (0.98, 0.04, "right", "bottom"),
            "upper right": (0.98, 0.96, "right", "top"),
            "lower left": (0.02, 0.04, "left", "bottom")}[best]


def _sign_index_and_offset(longitude_deg: float) -> Tuple[int, float]:
    """Return (sign index 0-11, degrees inside the sign) for a longitude."""
    longitude_deg %= 360.0
    index = int(longitude_deg // 30)
    return index, longitude_deg - 30 * index


# ----------------------------------------------------------------------------
# Plot 1: polar diagram for a single year
# ----------------------------------------------------------------------------

def plot_equinoctial_precession(
    year: float,
    model: str = "long_term",
    j2000_ayanamsa_deg: float = LAHIRI_AYANAMSA_J2000_DEG,
    rate_arcsec_per_year: float = PRECESSION_RATE_ARCSEC_PER_YEAR,
    ayanamsa_function: Optional[Callable[[float], float]] = None,
    short_names: bool = True,
    ax=None,
    legend: bool = True,
    save_path: Optional[str] = None,
    show: bool = True,
    dpi: int = 150,
):
    """
    Draw the equinoctial and solstitial axes against the sidereal zodiac.

    Parameters
    ----------
    year : float
        Astronomical year (3102 BC = -3101). Fractional years are allowed.
    model : {"long_term", "linear"}
        Ayanamsa model (see the module docstring). Ignored if
        ``ayanamsa_function`` is given.
    j2000_ayanamsa_deg : float
        Ayanamsa at J2000.0 (degrees), anchor of both built-in models.
    rate_arcsec_per_year : float
        Precession rate of the linear model (arcsec/year).
    ayanamsa_function : callable, optional
        Custom model ``year -> ayanamsa in degrees``. It may return values
        outside 0-360 (several turns); the plot shows the accumulated angle
        as a spiral arc and reduces it modulo 360 for the axes.
    short_names : bool
        Three-letter sign abbreviations inside the ring (True) or full names.
    ax : matplotlib polar Axes, optional
        Existing polar axes to draw on. If omitted, a new figure is created
        and the summary text and legend are placed at the bottom of it. If
        given, the summary goes into the axes title and the legend (if
        enabled) is placed to the right of the axes.
    legend : bool
        Whether to draw the legend.
    save_path : str, optional
        If given, the figure is saved to this path.
    show : bool
        Call ``plt.show()`` at the end.
    dpi : int
        Resolution used when saving.

    Returns
    -------
    (figure, axes, ayanamsa_deg)
        ``ayanamsa_deg`` is the accumulated angle (not reduced modulo 360).
    """
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    year = float(year)
    if not math.isfinite(year):
        raise ValueError("year must be a finite number")
    if model not in ("long_term", "linear"):
        raise ValueError("model must be 'long_term' or 'linear'")

    custom_model = ayanamsa_function is not None
    note_text, note_color = None, None
    if custom_model:
        ayanamsa = float(ayanamsa_function(year))
        if not math.isfinite(ayanamsa):
            raise ValueError("ayanamsa_function returned a non-finite value")
    elif model == "long_term":
        ayanamsa = long_term_ayanamsa(year, j2000_ayanamsa_deg)
        note_text, note_color = _NOTE_LONG_TERM, _TEXT_NOTE_MODEL
    else:
        ayanamsa = float(lahiri_ayanamsa(year, j2000_ayanamsa_deg,
                                         rate_arcsec_per_year))
        if abs(year - 2000.0) > _EXTRAPOLATION_THRESHOLD_YEARS:
            note_text, note_color = _NOTE_EXTRAPOLATION, _TEXT_NOTE
    rad = math.radians

    own_figure = ax is None
    if own_figure:
        fig = plt.figure(figsize=(8.2, 8.8))
        ax = fig.add_subplot(111, projection="polar")
    else:
        if getattr(ax, "name", None) != "polar":
            raise ValueError("ax must be a polar Axes (projection='polar')")
        fig = ax.figure

    # 0 degrees at the top, longitudes increasing counterclockwise
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(1)
    ax.set_ylim(0, 1.3)
    ax.set_axis_off()

    inner_radius, outer_radius = 0.80, 1.00

    # --- Sidereal zodiac: 12 sectors of 30 degrees ---------------------------
    centers = [rad(30 * i + 15) for i in range(12)]
    colors = [_RING_LIGHT if i % 2 == 0 else _RING_DARK for i in range(12)]
    ax.bar(centers, outer_radius - inner_radius, width=rad(30),
           bottom=inner_radius, color=colors, edgecolor=_RING_EDGE,
           linewidth=0.6, zorder=1)
    names = _SIGN_ABBREVIATIONS if short_names else _SIGN_NAMES
    for i, center in enumerate(centers):
        ax.text(center, (inner_radius + outer_radius) / 2, names[i],
                ha="center", va="center",
                fontsize=9 if short_names else 7.5, color=_TEXT_DARK,
                zorder=3)
        ax.text(rad(30 * i), outer_radius + 0.07, f"{30 * i}°",
                ha="center", va="center", fontsize=7.5, color=_TEXT_MUTED)

    # --- Sidereal zero reference and Spica (180 degrees sidereal) ------------
    ax.plot([0, 0], [0, outer_radius], linestyle="--", color=_PURPLE,
            linewidth=1, zorder=2)
    ax.plot([rad(180)], [outer_radius], marker="*", color=_AMBER,
            markeredgecolor=_AMBER_EDGE, markersize=13, zorder=5)
    ax.text(rad(180), outer_radius + 0.19, _LABEL_SPICA, ha="center",
            va="center", fontsize=8, color="#5F5E5A")

    # --- Tropical zodiac ticks (attached to the axes) ------------------------
    for k in range(12):
        theta = rad(-ayanamsa + 30 * k)
        ax.plot([theta, theta], [inner_radius - 0.07, inner_radius],
                color=_RED, linewidth=1.3, alpha=0.85, zorder=2)

    # --- Equinoctial and solstitial axes -------------------------------------
    axis_length = 1.13
    for tropical_angle, color in ((0, _RED), (90, _GREEN)):
        theta = rad(tropical_angle - ayanamsa)
        for end_theta in (theta, theta + math.pi):
            ax.plot([end_theta, end_theta], [0, axis_length], color=color,
                    linewidth=2.4, zorder=4, solid_capstyle="round")

    axis_labels = [(0, _LABEL_VERNAL, _RED),
                   (90, _LABEL_JUNE, _GREEN),
                   (180, _LABEL_AUTUMNAL, _RED),
                   (270, _LABEL_DECEMBER, _GREEN)]
    for tropical_angle, text, color in axis_labels:
        theta = rad(tropical_angle - ayanamsa)
        ux, uy = -math.sin(theta), math.cos(theta)  # visual direction of the tip
        ha = "left" if ux > 0.35 else ("right" if ux < -0.35 else "center")
        va = "bottom" if uy > 0.35 else ("top" if uy < -0.35 else "center")
        ax.text(theta, 1.24, text, ha=ha, va=va, fontsize=8.5, color=color,
                fontweight="medium", zorder=6)

    # --- Ayanamsa arc: from the sidereal zero to the vernal point ------------
    # Accumulated angle drawn as a spiral so several turns stay distinguishable.
    total_turns = abs(ayanamsa) / 360.0
    turns_text = _format_number(total_turns, 2)
    arc_radius, turn_shrink = 0.62, 0.045
    if abs(ayanamsa) > 0.05:
        end_theta = rad(-ayanamsa)
        n_points = max(200, int(200 * total_turns) + 1)
        arc_thetas = np.linspace(0.0, end_theta, n_points)
        arc_radii = arc_radius - turn_shrink * np.abs(arc_thetas) / _D2PI
        ax.plot(arc_thetas, arc_radii, color=_PURPLE, linewidth=2.2, zorder=5)
        if abs(ayanamsa) > 1.5:
            back = min(8, n_points - 1)
            ax.annotate("", xy=(arc_thetas[-1], arc_radii[-1]),
                        xytext=(arc_thetas[-1 - back], arc_radii[-1 - back]),
                        arrowprops=dict(arrowstyle="-|>", color=_PURPLE,
                                        lw=2.2, mutation_scale=14),
                        zorder=6)
        label = f"A = {_format_number(ayanamsa, 2)}°"
        if total_turns >= 1:
            label += _ARC_LABEL_TURNS.format(turns=turns_text)
        mid = end_theta / 2
        mid_radius = arc_radius - turn_shrink * abs(mid) / _D2PI - 0.13
        ax.text(mid, mid_radius, label, ha="center", va="center",
                fontsize=9, color=_PURPLE, zorder=8,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.5))

    # --- Sun at the center (reference point) ---------------------------------
    ax.plot([0], [0], marker="o", color=_AMBER, markeredgecolor=_AMBER_EDGE,
            markersize=13, zorder=7)

    # --- Texts ---------------------------------------------------------------
    vernal_longitude = (-ayanamsa) % 360.0
    sign_index, sign_offset = _sign_index_and_offset(vernal_longitude)
    title = _TITLE_TEMPLATE.format(year=_format_year(year))
    turns_summary = (_SUMMARY_TURNS.format(turns=turns_text)
                     if total_turns >= 1 else "")
    summary_template = (_SUMMARY_AYANAMSA_CUSTOM if custom_model
                        else _SUMMARY_AYANAMSA_LAHIRI)
    summary = (
        summary_template.format(deg=_format_number(ayanamsa, 3),
                                dms=_format_deg_min(ayanamsa),
                                turns=turns_summary)
        + "\n"
        + _SUMMARY_VERNAL.format(lon=_format_number(vernal_longitude, 2),
                                 dms=_format_deg_min(sign_offset),
                                 sign=_SIGN_NAMES[sign_index]))

    handles = [
        Line2D([0], [0], color=_RED, lw=2.4, label=_LEGEND_EQUINOCTIAL),
        Line2D([0], [0], color=_GREEN, lw=2.4, label=_LEGEND_SOLSTITIAL),
        Line2D([0], [0], color=_PURPLE, lw=2.2, label=_LEGEND_AYANAMSA),
        Line2D([0], [0], color=_PURPLE, lw=1, linestyle="--",
               label=_LEGEND_SIDEREAL_ZERO),
        Line2D([0], [0], color=_RED, lw=1.3, alpha=0.85,
               label=_LEGEND_TROPICAL),
    ]

    if own_figure:
        ax.set_title(title, fontsize=13, pad=14)
        fig.text(0.5, 0.10, summary, ha="center", va="center", fontsize=10)
        if note_text:
            fig.text(0.5, 0.152, note_text, ha="center", va="center",
                     fontsize=8.5, color=note_color, style="italic")
        if legend:
            fig.legend(handles=handles, loc="lower center", ncol=3,
                       frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, 0.0))
        fig.subplots_adjust(top=0.9, bottom=0.2)
    else:
        extra = ("\n" + note_text.replace(": ", ":\n").replace(" (", "\n(")
                 if note_text else "")
        ax.set_title(title + "\n" + summary + extra, fontsize=9, pad=14)
        if legend:
            ax.legend(handles=handles, loc="upper left",
                      bbox_to_anchor=(1.02, 1.0), frameon=False, fontsize=8)

    if save_path:
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
    if show:
        plt.show()
    return fig, ax, ayanamsa


# ----------------------------------------------------------------------------
# Plot 2: A(t) for both models and their difference
# ----------------------------------------------------------------------------

def plot_ayanamsa_comparison(
    start_year: float = -30215.0,
    end_year: float = 34215.0,
    n_points: int = 1000,
    j2000_ayanamsa_deg: float = LAHIRI_AYANAMSA_J2000_DEG,
    rate_arcsec_per_year: float = PRECESSION_RATE_ARCSEC_PER_YEAR,
    show_rate: bool = False,
    marks: Optional[Sequence[float]] = None,
    marks_unit: str = "degrees",
    marks_reference_year: Optional[float] = None,
    axes: Optional[Sequence] = None,
    save_path: Optional[str] = None,
    show: bool = True,
    dpi: int = 150,
):
    """
    Plot the ayanamsa A(t) of the linear and the long-term models together,
    and their difference, over a span of years.

    The default span is 64430 years (2.5 linear precession periods) centered
    on J2000.

    Parameters
    ----------
    start_year, end_year : float
        Span in astronomical years; must satisfy start_year < end_year and lie
        within +/- 200,000 years of J2000.0 (validity of the long-term model).
    n_points : int
        Number of sample years (evenly spaced).
    j2000_ayanamsa_deg, rate_arcsec_per_year : float
        Anchor value at J2000.0 and rate of the linear model.
    show_rate : bool
        Add a third panel with the instantaneous precession rate (arcsec/year)
        of the long-term model against the constant rate of the linear one.
    marks : sequence of float, optional
        Ayanamsa values whose year is to be marked on each model (see
        ``year_from_ayanamsa``). For each value the plot draws a horizontal
        reference, a marker on each curve, vertical lines at the two years
        (red dotted: linear, purple dotted: long-term, in all panels) and a
        text box listing both years. Marks whose year falls outside the
        plotted span are listed but not drawn.
    marks_unit : {"degrees", "turns"}
        Unit of ``marks``.
    marks_reference_year : float, optional
        If given, ``marks`` are changes of A since that year (e.g. with
        ``marks_reference_year=-3101`` and ``marks=[1]``, the year one full turn
        after 3102 BC) instead of absolute values of A. Each model uses its own
        A at that year (see ``year_from_ayanamsa``).
    axes : sequence of matplotlib Axes, optional
        Existing axes (2 panels, or 3 if ``show_rate``), in the order
        A(t), difference[, rate]. They should share the x axis.
    save_path, show, dpi
        As in ``plot_equinoctial_precession``.

    Returns
    -------
    (figure, axes, data)
        ``data`` is a dict of arrays: "years", "linear", "long_term",
        "difference" (long_term - linear) and, if ``show_rate``, "rate_long_term"
        in arcsec/year. If ``marks`` is given: "marks_ayanamsa_linear" and
        "marks_ayanamsa_long_term" (absolute A in degrees at each mark, equal
        unless ``marks_reference_year`` is used), "marks_year_linear" and
        "marks_year_long_term".
    """
    import matplotlib.pyplot as plt

    if not (math.isfinite(start_year) and math.isfinite(end_year)
            and start_year < end_year):
        raise ValueError("start_year and end_year must be finite, start < end")
    n_points = int(n_points)
    if n_points < 2:
        raise ValueError("n_points must be >= 2")

    years = np.linspace(start_year, end_year, n_points)
    linear = np.asarray(lahiri_ayanamsa(years, j2000_ayanamsa_deg,
                                        rate_arcsec_per_year))
    long_term = long_term_ayanamsa(years, j2000_ayanamsa_deg)
    difference = long_term - linear
    data: Dict[str, np.ndarray] = {"years": years, "linear": linear,
                                   "long_term": long_term,
                                   "difference": difference}

    mark_values = None
    if marks is not None:
        if isinstance(marks_reference_year, (bool, np.bool_)):
            raise TypeError("marks_reference_year must be a year, not a bool")
        mark_values = np.atleast_1d(np.asarray(marks, dtype=float)).ravel()
        mark_years_linear = np.atleast_1d(year_from_ayanamsa(
            mark_values, marks_unit, marks_reference_year, "linear",
            j2000_ayanamsa_deg, rate_arcsec_per_year))
        mark_years_long_term = np.atleast_1d(year_from_ayanamsa(
            mark_values, marks_unit, marks_reference_year, "long_term",
            j2000_ayanamsa_deg))
        mark_degrees = mark_values * 360.0 if marks_unit == "turns" \
            else mark_values
        if marks_reference_year is None:
            mark_degrees_linear = mark_degrees_long_term = mark_degrees
        else:
            mark_degrees_linear = mark_degrees + float(lahiri_ayanamsa(
                marks_reference_year, j2000_ayanamsa_deg,
                rate_arcsec_per_year))
            mark_degrees_long_term = mark_degrees + float(long_term_ayanamsa(
                marks_reference_year, j2000_ayanamsa_deg))
        data["marks_ayanamsa_linear"] = mark_degrees_linear
        data["marks_ayanamsa_long_term"] = mark_degrees_long_term
        data["marks_year_linear"] = mark_years_linear
        data["marks_year_long_term"] = mark_years_long_term

    n_panels = 3 if show_rate else 2
    if axes is None:
        fig, axes = plt.subplots(
            n_panels, 1, sharex=True,
            figsize=(9.5, 10.0 if show_rate else 8.0),
            gridspec_kw={"height_ratios": [3.0] + [1.3] * (n_panels - 1)})
    else:
        axes = list(axes)
        if len(axes) != n_panels:
            raise ValueError(f"axes must contain {n_panels} Axes")
        fig = axes[0].figure
    ax_a, ax_d = axes[0], axes[1]

    # --- Panel 1: A(t) for both models ---------------------------------------
    ax_a.plot(years, linear, color=_RED, linestyle="--", linewidth=1.6,
              label=_CMP_LEGEND_LINEAR.format(
                  rate=_format_number(rate_arcsec_per_year, 2)))
    ax_a.plot(years, long_term, color=_PURPLE, linewidth=2.0,
              label=_CMP_LEGEND_LONG_TERM)
    low = min(linear.min(), long_term.min())
    high = max(linear.max(), long_term.max())
    for k in range(math.ceil(low / 360.0), math.floor(high / 360.0) + 1):
        ax_a.axhline(360.0 * k, color=_TEXT_MUTED, linewidth=0.6,
                     linestyle=":", zorder=0)
    ax_a.set_ylabel(_CMP_YLABEL_A)
    ax_a.grid(True, alpha=0.25)
    ax_a.legend(loc="upper left", frameon=False)
    turns_axis = ax_a.secondary_yaxis(
        "right", functions=(lambda a: a / 360.0, lambda t: t * 360.0))
    turns_axis.set_ylabel(_CMP_YLABEL_TURNS)

    # --- Panel 2: difference --------------------------------------------------
    ax_d.plot(years, difference, color=_GREEN, linewidth=1.8)
    ax_d.axhline(0.0, color=_TEXT_MUTED, linewidth=0.8)
    ax_d.set_ylabel(_CMP_YLABEL_DIFF)
    ax_d.grid(True, alpha=0.25)
    i_max = int(np.argmax(np.abs(difference)))
    ax_d.annotate(
        _CMP_MAX_DIFFERENCE.format(value=_format_number(difference[i_max], 2),
                                   year=_format_number(years[i_max], 0)),
        xy=(years[i_max], difference[i_max]), xytext=(0.02, 0.88),
        textcoords="axes fraction", fontsize=9, color=_GREEN, va="top",
        arrowprops=dict(arrowstyle="-", color=_GREEN, lw=0.8))

    # --- Optional panel 3: precession rate -----------------------------------
    if show_rate:
        ax_r = axes[2]
        rate_long_term = np.gradient(long_term, years) * 3600.0
        data["rate_long_term"] = rate_long_term
        ax_r.plot(years, rate_long_term, color=_PURPLE, linewidth=1.8)
        ax_r.axhline(rate_arcsec_per_year, color=_RED, linestyle="--",
                     linewidth=1.4)
        ax_r.set_ylabel(_CMP_YLABEL_RATE)
        ax_r.grid(True, alpha=0.25)

    # --- Marks: years at which chosen values of A are reached ----------------
    if mark_values is not None:
        def inside(y):
            return start_year <= y <= end_year

        lines = [_CMP_MARKS_HEADER]
        for i, value in enumerate(mark_values):
            y_lin, y_long = mark_years_linear[i], mark_years_long_term[i]
            deg_lin = mark_degrees_linear[i]
            deg_long = mark_degrees_long_term[i]
            if marks_reference_year is None:
                ax_a.axhline(deg_long, color=_TEXT_MUTED, linewidth=0.6,
                             linestyle="-.", alpha=0.7, zorder=0)
            else:
                for degrees_value, color in ((deg_lin, _RED),
                                             (deg_long, _PURPLE)):
                    ax_a.axhline(degrees_value, color=color, linewidth=0.6,
                                 linestyle="-.", alpha=0.5, zorder=0)
            for y, degrees_value, color, marker_style in (
                    (y_lin, deg_lin, _RED, "D"),
                    (y_long, deg_long, _PURPLE, "o")):
                if inside(y):
                    ax_a.plot([y], [degrees_value], marker=marker_style,
                              color=color, markersize=5.5,
                              markeredgecolor="white", linestyle="none",
                              zorder=6)
                    for panel in axes:
                        panel.axvline(y, color=color, linewidth=0.7,
                                      linestyle=":", alpha=0.8, zorder=0)
            lines.append(_CMP_MARK_LINE.format(
                label=_mark_label(value, marks_unit, marks_reference_year),
                linear=_format_number(y_lin, 1),
                long_term=_format_number(y_long, 1),
                outside=_CMP_MARK_OUTSIDE
                if not (inside(y_lin) and inside(y_long)) else ""))
        ax_a.set_xlim(start_year, end_year)
        box_x, box_y, box_ha, box_va = _least_crowded_corner(
            ax_a, years, (linear, long_term))
        ax_a.text(box_x, box_y, "\n".join(lines), transform=ax_a.transAxes,
                  ha=box_ha, va=box_va, fontsize=8, color=_TEXT_DARK,
                  bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                            edgecolor=_TEXT_MUTED, alpha=0.9), zorder=7)

    # --- J2000 marker and labels ---------------------------------------------
    if start_year <= 2000.0 <= end_year:
        for panel in axes:
            panel.axvline(2000.0, color=_TEXT_MUTED, linewidth=0.8,
                          linestyle="--")
        ax_a.text(2000.0, 1.0, " " + _CMP_LABEL_J2000, color=_TEXT_MUTED,
                  fontsize=8.5, va="bottom", ha="left",
                  transform=ax_a.get_xaxis_transform())
    axes[-1].set_xlabel(_CMP_XLABEL)
    axes[-1].set_xlim(start_year, end_year)
    fig.suptitle(_CMP_TITLE, fontsize=13)
    fig.align_ylabels(axes)
    fig.tight_layout(rect=(0, 0, 1, 0.965))

    if save_path:
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
    if show:
        plt.show()
    return fig, axes, data
