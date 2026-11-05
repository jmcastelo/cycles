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

    from cycles.functions.astro_dates import date_to_year, parse_date
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
ecliptic_coordinates_of_date(vectors, year, ...)  ICRF vectors -> longitude and
                                       latitude of date (tropical or sidereal)
plot_equinoctial_precession(year, ...) polar diagram for one year
plot_zodiac_with_planets(year, ephemeris, ...)  the same diagram with the planets
plot_zodiac_planets_grid(years, ephemeris, ...) several years side by side
plot_ayanamsa_comparison(...)          A(t) for both models + difference
"""

from __future__ import annotations

import functools
import math
from pathlib import Path
from typing import Callable, Dict, Optional, Sequence, Tuple

import numpy as np

from cycles.functions.astro_dates import date_time_to_julian_day, julian_day_to_year
from cycles.functions.timescale import TimeMap

__all__ = ["lahiri_ayanamsa", "long_term_ayanamsa", "year_from_ayanamsa",
           "precession_time_map", "yuga_boundaries", "yuga_time_maps", "KALI_YUGA_START", "YUGA_TURNS",
           "ecliptic_coordinates_of_date", "plot_equinoctial_precession",
           "plot_zodiac_with_planets", "plot_zodiac_planets_grid",
           "plot_ayanamsa_comparison"]

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
# centre of the diagram: (symbol, disc colour); the Earth is the astronomical symbol
_CENTER_SYMBOLS = {"earth": ("⊕", "#5BA3E0"), "sun": ("☉", "#EF9F27")}
_SIGN_GLYPHS = ("♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓")
_SIGN_ABBREVIATIONS = ["Ari", "Tau", "Gem", "Cán", "Leo", "Vir",
                       "Lib", "Esc", "Sag", "Cap", "Acu", "Pis"]

_LABEL_VERNAL = "Punto vernal"
_LABEL_JUNE = "Solsticio\nde junio"
_LABEL_AUTUMNAL = "Punto otoñal"
_LABEL_DECEMBER = "Solsticio\nde diciembre"
_LABEL_SPICA = "Spica (Chitrā)"
_TITLE_HEAD = "Precesión de los equinoccios"
_TITLE_TEMPLATE = _TITLE_HEAD + " · año {year}"
_EPOCH_PARTS = ("year", "date", "julian_day")      # canonical order of the epoch display
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

_NAK_RING_LIGHT = "#EEF2F6"
_NAK_RING_DARK = "#D6DFE9"
_NAK_RING_EDGE = "#7F8A99"
_NAK_RING_WIDTH = 0.16        # radial width of the nakshatra ring, outside the signs
_EMBLEMS_HEADER = "Emblemas tradicionales de los nakṣatras ocupados (hay variantes entre textos):"
_PLANETS_HEAD = "Zodiaco sidéreo y planetas"
_PLANETS_TITLE = _PLANETS_HEAD + " · año {year}"
_PLANETS_TABLE_HEADER = ("Cuerpo      Long. sidérea   Long. trópica   Signo (sidéreo)        "
                         "Nakṣatra (pada)")
_PLANETS_NOTE_METHOD = ("Posiciones geométricas geocéntricas (desde el baricentro Tierra-Luna), "
                        "sin tiempo de luz ni aberración.")
_PLANETS_NOTE_EPOCH_TDB = "Época en TDB."
_PLANETS_NOTE_EPOCH_UT = "Época dada en UT y convertida a TDB (ΔT = {seconds} s)."
_PLANETS_NOTE_NO_MOON = ("La Luna no se muestra: su posición no es fiable a estas "
                         "distancias.")
_PLANETS_NOTE_EXTERNAL = "Los puntos añadidos con extra_points proceden de otra fuente."
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

def precession_time_map(
    start_year: float,
    turns: float,
    model: str = "long_term",
    j2000_ayanamsa_deg: float = LAHIRI_AYANAMSA_J2000_DEG,
    rate_arcsec_per_year: float = PRECESSION_RATE_ARCSEC_PER_YEAR,
) -> TimeMap:
    """
    Time map that divides precession angle instead of time.

    Normalized time ``u`` (0 to 1) is sent to the year at which the ayanamsa
    has advanced ``u * turns`` turns since ``start_year``. Equal fractions of
    the cycle are therefore equal arcs of precession, and the boundaries of
    every subcycle, at any depth, are precession boundaries. With a model in
    which the precession rate varies (``long_term``), equal arcs are not equal
    spans of years.

    Parameters
    ----------
    start_year : float
        Year of normalized time 0 (Julian epoch, astronomical numbering).
    turns : float
        Precession arc of the whole cycle, in turns (positive).
    model, j2000_ayanamsa_deg, rate_arcsec_per_year
        As in ``year_from_ayanamsa``.

    Returns
    -------
    TimeMap
        See ``cycles.functions.timescale``.
    """
    if turns <= 0:
        raise ValueError("turns must be positive")
    if model == "long_term":
        def ayanamsa(year):
            return long_term_ayanamsa(year, j2000_ayanamsa_deg)
    elif model == "linear":
        def ayanamsa(year):
            return lahiri_ayanamsa(year, j2000_ayanamsa_deg, rate_arcsec_per_year)
    else:
        raise ValueError(f"Unknown model {model!r}; use 'long_term' or 'linear'.")
    a0 = ayanamsa(start_year)

    def to_physical(u):
        return year_from_ayanamsa(np.asarray(u, dtype=float) * turns, unit="turns",
                                  reference_year=start_year, model=model,
                                  j2000_ayanamsa_deg=j2000_ayanamsa_deg,
                                  rate_arcsec_per_year=rate_arcsec_per_year)

    def to_normalized(year):
        return (np.asarray(ayanamsa(year), dtype=float) - a0) / (360.0 * turns)

    return TimeMap.from_functions(to_physical, to_normalized)


# Start of the Kali Yuga (decimal year, UT): 6:30 local solar time in Ujjain
KALI_YUGA_START = julian_day_to_year(date_time_to_julian_day(-3103, 2, 7, 6, 30, utc_offset_hours=75.77 / 15))
# Precession arc of each yuga, in turns of the ayanamsa (4:3:2:1 in angle)
YUGA_TURNS = (1.0, 3 / 4, 1 / 2, 1 / 4)


def yuga_boundaries(kali_start: float = KALI_YUGA_START, model: str = "long_term") -> list[float]:
    """
    Years of the yuga boundaries found from the precession of the equinoxes:
    starts of Satya, Treta, Dvapara and Kali, and the end of Kali.

    From the start of the Kali Yuga, each earlier boundary is found by going
    back the arc of the yuga before it (1/2 turn of the ayanamsa for Dvapara,
    3/4 for Treta, 1 for Satya), and the end is 1/4 turn after the start of
    Kali. ``model`` is as in ``year_from_ayanamsa``.
    """
    tk = kali_start
    td = year_from_ayanamsa(-YUGA_TURNS[2], unit='turns', reference_year=tk, model=model)
    tt = year_from_ayanamsa(-YUGA_TURNS[1], unit='turns', reference_year=td, model=model)
    ts = year_from_ayanamsa(-YUGA_TURNS[0], unit='turns', reference_year=tt, model=model)
    tm = year_from_ayanamsa(YUGA_TURNS[3], unit='turns', reference_year=tk, model=model)
    return [float(t) for t in (ts, tt, td, tk, tm)]


def yuga_time_maps(kali_start: float = KALI_YUGA_START, model: str = "long_term") -> Dict[str, TimeMap]:
    """
    The three time maps of the yuga cycle (see ``yuga_boundaries``):

    * ``'precession'``: divides precession angle (``precession_time_map``), so
      every subcycle boundary, at any depth, is a precession boundary;
    * ``'fitted'``: divides time, each yuga fitted to its boundaries;
    * ``'linear'``: divides time uniformly between the first and last boundary.
    """
    boundaries = yuga_boundaries(kali_start, model)
    return {
        'precession': precession_time_map(boundaries[0], sum(YUGA_TURNS), model=model),
        'fitted': TimeMap.from_age_boundaries(boundaries),
        'linear': TimeMap.linear(boundaries[0], boundaries[-1]),
    }


def ecliptic_coordinates_of_date(
    vectors,
    year,
    sidereal: bool = False,
    model: str = "long_term",
    j2000_ayanamsa_deg: float = LAHIRI_AYANAMSA_J2000_DEG,
    rate_arcsec_per_year: float = PRECESSION_RATE_ARCSEC_PER_YEAR,
):
    """
    Ecliptic longitude and latitude (degrees) of directions given in the ICRF /
    J2000.0 mean equatorial frame, referred to the mean ecliptic and equinox of
    date from the long-term precession model (the same frame as the ayanamsa).

    Parameters
    ----------
    vectors : array_like, shape (3,) or (N, 3)
        Directions or positions in the ICRF (need not be unit vectors), for
        example the output of ``nbody_ephemeris.geocentric_direction``.
    year : float or array_like of shape (N,)
        Julian epoch(s) of the vectors (astronomical year numbering). The
        frame depends on the epoch, so use the epoch at which each vector was
        computed. Must be within +/- 200,000 years of J2000.0.
    sidereal : bool
        If True, subtract the ayanamsa of ``model`` ("long_term" or "linear")
        to get sidereal longitudes (Lahiri anchor ``j2000_ayanamsa_deg``).
    model, j2000_ayanamsa_deg, rate_arcsec_per_year
        Ayanamsa model, only used when ``sidereal`` is True.

    Returns
    -------
    (longitude_deg, latitude_deg)
        Longitude in [0, 360) (tropical, or sidereal if requested) and
        latitude in [-90, 90]. Floats for a single vector, arrays otherwise.
        Geometric directions: no light-time, aberration or nutation.
    """
    if model not in ("long_term", "linear"):
        raise ValueError("model must be 'long_term' or 'linear'")
    v = np.asarray(vectors, dtype=float)
    single = v.ndim == 1
    v = np.atleast_2d(v)
    if v.shape[1] != 3:
        raise ValueError("vectors must have shape (3,) or (N, 3)")
    years = np.broadcast_to(np.asarray(year, dtype=float), (v.shape[0],)).copy()
    if not np.all(np.isfinite(years)):
        raise ValueError("year must be finite")
    if np.any(np.abs(years - 2000.0) > LONG_TERM_VALIDITY_YEARS):
        raise ValueError(f"year must be within +/- {LONG_TERM_VALIDITY_YEARS:.0f} "
                         "years of J2000.0")
    ecliptic, equator = _poles_of_date(years)
    x = np.cross(equator, ecliptic)                       # equinox of date
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    y = np.cross(ecliptic, x)
    longitude = np.degrees(np.arctan2(np.einsum("ij,ij->i", v, y),
                                      np.einsum("ij,ij->i", v, x)))
    norm = np.linalg.norm(v, axis=1)
    latitude = np.degrees(np.arcsin(np.clip(np.einsum("ij,ij->i", v, ecliptic) / norm,
                                            -1.0, 1.0)))
    if sidereal:
        if model == "long_term":
            ayanamsa = np.asarray(long_term_ayanamsa(years, j2000_ayanamsa_deg))
        else:
            ayanamsa = np.asarray(lahiri_ayanamsa(years, j2000_ayanamsa_deg,
                                                  rate_arcsec_per_year))
        longitude = longitude - ayanamsa
    longitude = longitude % 360.0
    if single:
        return float(longitude[0]), float(latitude[0])
    return longitude, latitude


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


def _format_year(year: float, short: bool = False) -> str:
    """
    Spanish text of an astronomical year. Integer years use the usual era names
    ("3103 a. C." is the astronomical year -3102). A decimal year before the year 1
    is written as the signed astronomical number ("-3102,86 (astronómico)"),
    because "N a. C." would be ambiguous for a point inside a year. ``short``
    drops the parenthesis.
    """
    year = float(year)
    if year.is_integer():
        if year > 0:
            return f"{_format_number(year, 0)} {_ERA_AD}"
        return f"{_format_number(1 - year, 0)} {_ERA_BC}"
    if year >= 1:
        return f"{_format_number(year, 2)} {_ERA_AD}"
    text = _format_number(year, 2)
    return text if short else f"{text} (astronómico)"


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
    center: str = "sun",
    show_arc: bool = True,
    annotations: bool = True,
    nakshatras: bool = False,
    sign_labels: str = "both",
    epoch_display: Sequence[str] = ("year",),
    calendar: str = "auto",
    epoch_position: str = "title",
    center_symbol: bool = False,
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
    center : {"sun", "earth", "none"}
        Marker drawn at the centre: the Sun (view from the Sun, default), the
        Earth (geocentric view of the sky) or nothing.
    show_arc : bool
        Draw the spiral arc of the ayanamsa (default True).
    annotations : bool
        Draw the degree marks, the names of the four axis ends and the label
        of Spica (default True). Switch off for small panels (the sign ring then
        shows only the glyphs and the nakshatra ring only the numbers).
    nakshatras : bool
        Draw the ring of the 27 nakshatras (13 deg 20 min each, counted from the
        sidereal zero) outside the ring of the signs, with number and
        abbreviation (default False).
    sign_labels : {"text", "symbol", "both"}
        How the twelve signs are labelled: with their name, with their glyph
        (♈ ♉ …) or with both (default). In small panels (``annotations=False``)
        "both" shows only the glyph. The nakshatras have no standard glyphs; see
        ``_NAKSHATRA_EMBLEMS`` for their traditional emblems.
    center_symbol : bool
        Draw the symbol of the centre (⊕ for the Earth, ☉ for the Sun) on a disc,
        like the planets, instead of a plain dot (default False). With the epoch
        in the centre box the symbol is the first element of the box.
    epoch_display : sequence of {"year", "date", "julian_day"}
        What to show of the epoch under the title (default only the year, in
        the title itself; an empty sequence shows nothing). "date" needs the
        companion module ``astro_dates``. The year is taken as a decimal Julian
        year without a stated time scale.
    calendar : {"auto", "julian", "gregorian"}
        Calendar of the displayed date (automatic: Julian up to 4 Oct 1582).
    epoch_position : {"title", "center"}
        Where the epoch items go: under the title (default) or in a box in the
        centre of the diagram (the title then has no epoch line).

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
    if center not in ("sun", "earth", "none"):
        raise ValueError("center must be 'sun', 'earth' or 'none'")
    epoch_parts = _epoch_parts(epoch_display)
    _check_calendar_name(calendar)
    _check_epoch_position(epoch_position)
    _check_sign_labels(sign_labels)
    center_in_box = (epoch_position == "center" and bool(epoch_parts) and center_symbol
                     and center in ("sun", "earth"))
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
    extra = _NAK_RING_WIDTH if nakshatras else 0.0      # room taken by the nakshatra ring
    ax.set_ylim(0, 1.3 + extra)
    ax.set_axis_off()

    inner_radius, outer_radius = 0.80, 1.00

    # --- Sidereal zodiac: 12 sectors of 30 degrees ---------------------------
    centers = [rad(30 * i + 15) for i in range(12)]
    colors = [_RING_LIGHT if i % 2 == 0 else _RING_DARK for i in range(12)]
    ax.bar(centers, outer_radius - inner_radius, width=rad(30),
           bottom=inner_radius, color=colors, edgecolor=_RING_EDGE,
           linewidth=0.6, zorder=1)
    import matplotlib.patheffects as path_effects
    names = _SIGN_ABBREVIATIONS if short_names else _SIGN_NAMES
    middle = (inner_radius + outer_radius) / 2
    for i, sector_angle in enumerate(centers):
        halo = [path_effects.withStroke(linewidth=2.2, foreground=colors[i])]
        text_style = dict(ha="center", va="center", color=_TEXT_DARK, zorder=6,
                          path_effects=halo)
        if sign_labels == "text":
            ax.text(sector_angle, middle, names[i], fontsize=9 if short_names else 7.5,
                    **text_style)
        else:
            both = sign_labels == "both" and annotations     # small panels: glyph only
            glyph_size = 13.0 if both else (17.0 if annotations else 10.5)   # points
            ax.scatter([sector_angle], [middle + (0.045 if both else 0.0)], s=glyph_size ** 2,
                       marker=_centered_glyph(_SIGN_GLYPHS[i], _PLANET_FONT),
                       c=_TEXT_DARK, edgecolors=_TEXT_DARK, linewidths=0.2, zorder=6,
                       path_effects=halo)
            if both:
                ax.text(sector_angle, middle - 0.055, names[i], fontsize=7.5, **text_style)
        if annotations:
            ax.text(rad(30 * i), outer_radius + extra + 0.07, f"{30 * i}°",
                    ha="center", va="center", fontsize=7.5, color=_TEXT_MUTED)

    # --- Nakshatra ring: 27 sectors of 13 deg 20 min, outside the signs ------
    if nakshatras:
        width = 360.0 / 27.0
        nak_centers = [rad(width * k + width / 2) for k in range(27)]
        nak_colors = [_NAK_RING_LIGHT if k % 2 == 0 else _NAK_RING_DARK for k in range(27)]
        ax.bar(nak_centers, extra, width=rad(width), bottom=outer_radius,
               color=nak_colors, edgecolor=_NAK_RING_EDGE, linewidth=0.5, zorder=1)
        for k, sector_angle in enumerate(nak_centers):
            label = f"{k + 1} {_NAKSHATRA_ABBREVIATIONS[k]}" if annotations else f"{k + 1}"
            ax.text(sector_angle, outer_radius + extra / 2, label, ha="center", va="center",
                    rotation=_radial_rotation(sector_angle), rotation_mode="anchor",
                    fontsize=6.4 if annotations else 5.0, color=_TEXT_DARK, zorder=6,
                    path_effects=[path_effects.withStroke(
                        linewidth=2.0, foreground=nak_colors[k])])

    # --- Sidereal zero reference and Spica (180 degrees sidereal) ------------
    ax.plot([0, 0], [0, outer_radius + extra], linestyle="--", color=_PURPLE,
            linewidth=1, zorder=2)
    ax.plot([rad(180)], [outer_radius], marker="*", color=_AMBER,    # on the edge of the signs
            markeredgecolor=_AMBER_EDGE, markersize=11 if extra else 13, zorder=5)
    if annotations:
        ax.text(rad(180), outer_radius + extra + 0.19, _LABEL_SPICA, ha="center",
                va="center", fontsize=8, color="#5F5E5A")

    # --- Tropical zodiac ticks (attached to the axes) ------------------------
    for k in range(12):
        theta = rad(-ayanamsa + 30 * k)
        ax.plot([theta, theta], [inner_radius - 0.07, inner_radius],
                color=_RED, linewidth=1.3, alpha=0.85, zorder=2)

    # --- Equinoctial and solstitial axes -------------------------------------
    axis_length = 1.13 + extra
    for tropical_angle, color in ((0, _RED), (90, _GREEN)):
        theta = rad(tropical_angle - ayanamsa)
        for end_theta in (theta, theta + math.pi):
            ax.plot([end_theta, end_theta], [0, axis_length], color=color,
                    linewidth=2.4, zorder=4, solid_capstyle="round")

    axis_labels = [(0, _LABEL_VERNAL, _RED),
                   (90, _LABEL_JUNE, _GREEN),
                   (180, _LABEL_AUTUMNAL, _RED),
                   (270, _LABEL_DECEMBER, _GREEN)]
    for tropical_angle, text, color in (axis_labels if annotations else ()):
        theta = rad(tropical_angle - ayanamsa)
        ux, uy = -math.sin(theta), math.cos(theta)  # visual direction of the tip
        ha = "left" if ux > 0.35 else ("right" if ux < -0.35 else "center")
        va = "bottom" if uy > 0.35 else ("top" if uy < -0.35 else "center")
        ax.text(theta, 1.24 + extra, text, ha=ha, va=va, fontsize=8.5, color=color,
                fontweight="medium", zorder=6)

    # --- Ayanamsa arc: from the sidereal zero to the vernal point ------------
    # Accumulated angle drawn as a spiral so several turns stay distinguishable.
    total_turns = abs(ayanamsa) / 360.0
    turns_text = _format_number(total_turns, 2)
    arc_radius, turn_shrink = 0.62, 0.045
    if show_arc and abs(ayanamsa) > 0.05:
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

    # --- Centre marker (reference point) -------------------------------------
    if center_in_box:
        pass                                    # the epoch box carries the symbol
    elif center in ("sun", "earth") and center_symbol:
        _draw_center_disc(ax, center, compact=not annotations)
    elif center == "sun":
        ax.plot([0], [0], marker="o", color=_AMBER, markeredgecolor=_AMBER_EDGE,
                markersize=13, zorder=7)
    elif center == "earth":
        ax.plot([0], [0], marker="o", color="#378ADD", markeredgecolor="#185FA5",
                markersize=11, zorder=7)

    # --- Texts ---------------------------------------------------------------
    vernal_longitude = (-ayanamsa) % 360.0
    sign_index, sign_offset = _sign_index_and_offset(vernal_longitude)
    epoch_texts = _epoch_texts(year, year, None, epoch_parts, calendar)
    if epoch_position == "center":
        title = _TITLE_HEAD
        _draw_epoch_center(ax, _epoch_center_lines(year, year, None, epoch_parts, calendar),
                           compact=not annotations,
                           symbol=_CENTER_SYMBOLS[center] if center_in_box else None)
    elif epoch_parts == ("year",):
        title = _TITLE_HEAD + " · " + epoch_texts[0]
    elif epoch_parts:
        title = _TITLE_HEAD + "\n" + _join_epoch(epoch_texts)
    else:
        title = _TITLE_HEAD
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
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
    if show:
        plt.show()
    return fig, ax, ayanamsa


# ----------------------------------------------------------------------------
# Plot 3: the zodiac with the planets of a given year
# ----------------------------------------------------------------------------

# key in the ephemeris -> (Spanish name, astronomical symbol, colour)
_PLANETS = {
    "sun": ("Sol", "☉", "#EF9F27"),
    "mercury": ("Mercurio", "☿", "#B4B2A9"),
    "venus": ("Venus", "♀", "#ED93B1"),
    "mars": ("Marte", "♂", "#E24B4A"),
    "jupiter": ("Júpiter", "♃", "#F0997B"),
    "saturn": ("Saturno", "♄", "#BA7517"),
    "uranus": ("Urano", "♅", "#5DCAA5"),
    "neptune": ("Neptuno", "♆", "#85B7EB"),
    "pluto": ("Plutón", "♇", "#AFA9EC"),
}
_NAKSHATRAS = ("Aśvinī", "Bharaṇī", "Kṛttikā", "Rohiṇī", "Mṛgaśiras", "Ārdrā",
               "Punarvasu", "Puṣya", "Āśleṣā", "Maghā", "Pūrva Phālgunī",
               "Uttara Phālgunī", "Hasta", "Citrā", "Svātī", "Viśākhā",
               "Anurādhā", "Jyeṣṭhā", "Mūla", "Pūrvāṣāḍhā", "Uttarāṣāḍhā",
               "Śravaṇa", "Śraviṣṭhā", "Śatabhiṣaj", "Pūrva Bhādrapadā",
               "Uttara Bhādrapadā", "Revatī")
_NAKSHATRA_ABBREVIATIONS = ("Aśv", "Bha", "Kṛt", "Roh", "Mṛg", "Ārd", "Pun", "Puṣ",
                            "Āśl", "Mag", "PPh", "UPh", "Has", "Cit", "Svā", "Viś",
                            "Anu", "Jye", "Mūl", "PĀṣ", "UĀṣ", "Śra", "Śrv", "Śat",
                            "PBh", "UBh", "Rev")
# Traditional iconographic emblems (there are no standard glyphs for them; the
# texts give variants, the most common is listed first).
_NAKSHATRA_EMBLEMS = (
    "cabeza de caballo", "yoni", "navaja o llama", "carro de bueyes",
    "cabeza de ciervo", "gota o lágrima", "carcaj o arco", "ubre de vaca",
    "serpiente enroscada", "trono real", "patas delanteras de la cama",
    "patas traseras de la cama", "mano", "perla o joya brillante",
    "brote mecido por el viento", "arco triunfal o rueda de alfarero",
    "flor de loto", "amuleto circular o paraguas", "raíces atadas",
    "abanico o colmillo de elefante", "colmillo de elefante", "oreja o tres huellas",
    "tambor", "círculo vacío o mil flores", "patas delanteras del lecho fúnebre",
    "patas traseras del lecho fúnebre", "pez o tambor")
_PLANET_FONT = "DejaVu Sans"        # ships with matplotlib, has the planetary symbols
_DISC_AREA = 300.0                  # planet discs, area in points^2 (diameter about 19.5 pt)
_DISC_AREA_COMPACT = 165.0          # the same in small panels
_GLYPH_FILL = 0.58                  # largest dimension of the symbol, as a fraction of the disc
_TABLE_FONT = "DejaVu Sans Mono"


def _epoch_parts(epoch_display) -> tuple:
    """Validate ``epoch_display`` (a name or a sequence of names) and return it in canonical order."""
    if epoch_display is None:
        return ()
    if isinstance(epoch_display, str):
        epoch_display = (epoch_display,)
    unknown = [p for p in epoch_display if p not in _EPOCH_PARTS]
    if unknown:
        raise ValueError(f"unknown epoch_display items {unknown}; use {list(_EPOCH_PARTS)}")
    return tuple(p for p in _EPOCH_PARTS if p in epoch_display)


def _check_calendar_name(calendar: str) -> None:
    if calendar not in ("auto", "julian", "gregorian"):
        raise ValueError("calendar must be 'auto', 'julian' or 'gregorian'")


def _civil_date_parts(jd: float, calendar: str) -> tuple:
    """(date text, calendar tag, 'HH:MM') of a Julian Day, to the minute, in Spanish."""
    try:
        from cycles.functions.astro_dates import format_date, julian_day_to_date, split_day
    except ImportError as error:
        raise ImportError("epoch_display='date' needs the companion module "
                          "astro_dates") from error
    # whole minutes (no 60 s or day carry); the quarter second keeps the minute
    # from falling to the previous one through floating-point noise
    rounded = round(jd * 1440.0) / 1440.0 + 0.25 / 86400.0
    year, month, fraction_day = julian_day_to_date(rounded, calendar)
    day, hour, minute, _ = split_day(fraction_day)
    text = format_date(year, month, day, calendar)
    core, _, tag = text.partition(" (calendario ")
    tag = "jul." if tag.startswith("juliano") else "greg."
    return core, tag, f"{hour:02d}:{minute:02d}"


def _civil_date_text(jd: float, scale_label: Optional[str], calendar: str,
                     compact: bool) -> str:
    """Spanish date and time (to the minute) of a Julian Day, with its time scale."""
    core, tag, clock = _civil_date_parts(jd, calendar)
    calendar_text = f" {tag}" if compact else (
        " (calendario juliano)" if tag == "jul." else " (calendario gregoriano)")
    return f"{core}{calendar_text}, {clock}" + (f" {scale_label}" if scale_label else "")


def _epoch_center_lines(year_given: float, year_tdb: float, scale_label: Optional[str],
                        parts: tuple, calendar: str) -> list:
    """Short lines (for the box in the centre of the diagram) of the requested epoch items."""
    lines = []
    jd_given = 2451545.0 + (year_given - 2000.0) * 365.25
    scale = f" {scale_label}" if scale_label else ""
    for part in parts:
        if part == "year":
            lines.append(f"año {_format_year(year_given, short=True)}")
        elif part == "date":
            core, tag, clock = _civil_date_parts(jd_given, calendar)
            lines += [core, f"{tag} {clock}{scale}"]
        else:
            lines.append(f"JD {_format_number(jd_given, 3)}{scale}")
            if scale_label == "UT":
                jd_tdb = 2451545.0 + (year_tdb - 2000.0) * 365.25
                lines.append(f"→ {_format_number(jd_tdb, 3)} TDB")
    return lines


def _disc_diameter(compact: bool) -> float:
    """Diameter in points of the planet discs."""
    return math.sqrt(4.0 * (_DISC_AREA_COMPACT if compact else _DISC_AREA) / math.pi)


def _draw_center_disc(ax, kind: str, compact: bool) -> None:
    """The Earth (or the Sun) at the centre: a disc with its symbol, like the planets."""
    glyph, face = _CENTER_SYMBOLS[kind]
    area = _DISC_AREA_COMPACT if compact else _DISC_AREA
    size = _GLYPH_FILL * math.sqrt(4.0 * area / math.pi)
    ax.scatter([0], [0], s=area, c=face, edgecolors="#2C2C2A", linewidths=0.8, zorder=7)
    ax.scatter([0], [0], s=size ** 2, marker=_centered_glyph(glyph, _PLANET_FONT),
               c="#2C2C2A", edgecolors="#2C2C2A", linewidths=0.25, zorder=8)


def _draw_epoch_center(ax, lines: list, compact: bool, symbol=None) -> None:
    """
    Epoch box in the centre of a polar diagram, above the axes. With a
    ``symbol`` (glyph, colour) the box starts with that symbol on a disc, so the
    Earth (or the Sun) stays visible at the centre of the diagram.
    """
    if not lines:
        return
    fontsize = 6.0 if compact else 8.0
    if symbol is None:
        ax.text(0, 0, "\n".join(lines), ha="center", va="center",
                multialignment="center", fontsize=fontsize,
                linespacing=1.3, color=_TEXT_DARK, zorder=12,
                bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                          edgecolor=_RING_EDGE, linewidth=0.6, alpha=0.93))
        return
    from matplotlib.offsetbox import AnnotationBbox, DrawingArea, TextArea, VPacker
    from matplotlib.patches import Circle, PathPatch
    from matplotlib.path import Path
    glyph, face = symbol
    diameter = _disc_diameter(compact)
    drawing = DrawingArea(diameter, diameter, 0, 0)
    drawing.add_artist(Circle((diameter / 2, diameter / 2), diameter / 2 - 0.4,
                              facecolor=face, edgecolor="#2C2C2A", linewidth=0.8))
    outline = _centered_glyph(glyph, _PLANET_FONT)
    scale = _GLYPH_FILL * diameter / (2.0 * np.max(np.abs(outline.vertices)))
    drawing.add_artist(PathPatch(Path(outline.vertices * scale + diameter / 2, outline.codes),
                                 facecolor="#2C2C2A", edgecolor="#2C2C2A", linewidth=0.25))
    text = TextArea("\n".join(lines), textprops=dict(
        fontsize=fontsize, color=_TEXT_DARK, multialignment="center", linespacing=1.3))
    packed = VPacker(children=[drawing, text], align="center", pad=0, sep=3)
    box = AnnotationBbox(packed, (0, 0), xycoords="data", box_alignment=(0.5, 0.5),
                         frameon=True, pad=0.3,
                         bboxprops=dict(boxstyle="round,pad=0.25", facecolor="white",
                                        edgecolor=_RING_EDGE, linewidth=0.6, alpha=0.93))
    box.set_zorder(12)
    ax.add_artist(box)


def _check_sign_labels(sign_labels: str) -> None:
    if sign_labels not in ("text", "symbol", "both"):
        raise ValueError("sign_labels must be 'text', 'symbol' or 'both'")


def _check_epoch_position(epoch_position: str) -> None:
    if epoch_position not in ("title", "center"):
        raise ValueError("epoch_position must be 'title' or 'center'")


def _epoch_texts(year_given: float, year_tdb: float, scale_label: Optional[str],
                 parts: tuple, calendar: str, compact: bool = False) -> list:
    """
    Texts of the requested epoch items, in canonical order. ``year_given`` is in
    the time scale ``scale_label`` ("UT", "TDB" or None when unspecified) and
    ``year_tdb`` is the same instant in TDB (only used to show both Julian Days).
    """
    texts = []
    jd_given = 2451545.0 + (year_given - 2000.0) * 365.25
    suffix = f" {scale_label}" if scale_label else ""
    for part in parts:
        if part == "year":
            text = _format_year(year_given) if compact else f"año {_format_year(year_given)}"
            if scale_label == "UT" and not compact:
                text = text[:-1] + ", UT)" if text.endswith(")") else text + " (UT)"
        elif part == "date":
            text = _civil_date_text(jd_given, scale_label, calendar, compact)
        else:
            text = f"JD {_format_number(jd_given, 3)}{suffix}"
            if scale_label == "UT" and not compact:
                jd_tdb = 2451545.0 + (year_tdb - 2000.0) * 365.25
                text += f" → {_format_number(jd_tdb, 3)} TDB"
        texts.append(text)
    return texts


def _join_epoch(texts: list) -> str:
    """Epoch items on one line, or one per line when they would be too long."""
    line = " · ".join(texts)
    return line if len(line) <= 80 else "\n".join(texts)


@functools.lru_cache(maxsize=None)
def _centered_glyph(symbol: str, family: str):
    """
    Outline of a glyph as a matplotlib Path whose bounding box is centred on the
    origin. Used as a scatter marker it is centred exactly on its point, which
    text alignment cannot do: matplotlib centres a line of text by the metrics
    of the line, not by the ink of the glyph, and the planetary symbols then
    sit about a point above the middle of their discs.
    """
    from matplotlib.font_manager import FontProperties
    from matplotlib.path import Path
    from matplotlib.textpath import TextPath
    outline = TextPath((0, 0), symbol, size=1.0, prop=FontProperties(family=family))
    box = outline.get_extents()
    centre = np.array([(box.x0 + box.x1) / 2.0, (box.y0 + box.y1) / 2.0])
    return Path(outline.vertices - centre, outline.codes)


def _radial_rotation(theta: float) -> float:
    """Text rotation (degrees) that reads along the radius at polar angle theta (radians)."""
    rotation = (90.0 + math.degrees(theta)) % 360.0
    return rotation + 180.0 if 90.0 < rotation < 270.0 else rotation


def _tdb_year(year: float, time_scale: str) -> float:
    """Decimal year in TDB from a decimal year in ``time_scale`` ("TDB" or "UT")."""
    if time_scale == "TDB":
        return year
    if time_scale != "UT":
        raise ValueError("time_scale must be 'TDB' or 'UT'")
    try:
        from cycles.functions.astro_dates import julian_day_to_year, ut_to_tdb, year_to_julian_day
    except ImportError as error:
        raise ImportError("time_scale='UT' needs the companion module astro_dates "
                          "(it provides DeltaT)") from error
    return julian_day_to_year(ut_to_tdb(year_to_julian_day(year)))


def _direction_function(ephemeris, jd: float):
    """Return f(body, jd) -> ICRF direction from the Earth, from a table, tables or a callable."""
    if callable(ephemeris):
        return ephemeris
    import cycles.functions.nbody_ephemeris as nbe
    candidates = [ephemeris] if isinstance(ephemeris, dict) else list(ephemeris)
    spans = []
    for table in candidates:
        tau = table["sign"] * (jd - table["jd0"])
        reach = min(float(t[-1]) for t in table["times"].values())
        spans.append((table["jd0"], table["jd0"] + table["sign"] * reach))
        if 0.0 <= tau <= reach:
            return lambda body, when, _t=table: nbe.geocentric_direction(_t, body, when)
    raise ValueError(f"JD {jd:.1f} is outside every ephemeris provided; "
                     "stored spans (JD from, JD to): " + ", ".join(
                         f"({a:.0f}, {b:.0f})" for a, b in spans))


def _stagger_levels(longitudes, radii, min_separation_deg: float):
    """Pick a radius for each marker so that neighbouring markers do not overlap."""
    order = sorted(range(len(longitudes)), key=lambda i: longitudes[i])
    placed = {r: [] for r in radii}
    chosen = {}
    for i in order:
        best, best_gap = radii[0], -1.0
        for r in radii:
            scale = radii[0] / r                      # inner levels need more angle
            gaps = [abs((longitudes[i] - longitudes[j] + 180.0) % 360.0 - 180.0)
                    for j in placed[r]]
            gap = min(gaps) if gaps else 360.0
            if gap >= min_separation_deg * scale:
                best = r
                break
            if gap > best_gap:
                best, best_gap = r, gap
        chosen[i] = best
        placed[best].append(i)
    return chosen


def plot_zodiac_with_planets(
    year: float,
    ephemeris,
    bodies: Sequence[str] = ("sun", "mercury", "venus", "mars", "jupiter", "saturn"),
    model: str = "long_term",
    j2000_ayanamsa_deg: float = LAHIRI_AYANAMSA_J2000_DEG,
    rate_arcsec_per_year: float = PRECESSION_RATE_ARCSEC_PER_YEAR,
    extra_points: Optional[Dict[str, float]] = None,
    table: bool = True,
    ax=None,
    save_path: Optional[str] = None,
    show: bool = True,
    dpi: int = 150,
    compact: bool = False,
    time_scale: str = "TDB",
    nakshatras: bool = True,
    sign_labels: str = "both",
    epoch_display: Sequence[str] = ("year",),
    calendar: str = "auto",
    epoch_position: str = "title",
    center_symbol: bool = True,
):
    """
    Draw the sidereal zodiac, the equinoctial and solstitial axes and the
    geocentric positions of the planets for a given year.

    Parameters
    ----------
    year : float
        Julian epoch in astronomical year numbering (3102 BC = -3101), in the
        time scale given by ``time_scale``. For ancient dates TT - UT is large
        (about a day around 3100 BC), which moves the Sun by about one degree,
        so civil dates must be given with ``time_scale="UT"``.
    time_scale : {"TDB", "UT"}
        Time scale of ``year``. "TDB" (default) is the scale of the ephemeris;
        with "UT" the year (for example from ``astro_dates.date_to_year``) is
        converted to TDB with ``astro_dates.ut_to_tdb`` (needs that module; a
        DeltaT warning is issued outside -1999..3000). The title shows the year
        as given, with "(UT)", and a note states the DeltaT applied.
    ephemeris : dict, sequence of dict, or callable
        A table from ``nbody_ephemeris.load_ephemeris``; several tables (for
        example one towards the past and one towards the future), from which
        the one covering the epoch is used; or a function
        ``f(body, jd_tdb) -> vector`` returning the ICRF direction from the
        Earth to the body.
    bodies : sequence of str
        Ephemeris names to draw: "sun", "mercury", "venus", "mars", "jupiter",
        "saturn", "uranus", "neptune", "pluto".
    model, j2000_ayanamsa_deg, rate_arcsec_per_year
        Ayanamsa model, as in ``plot_equinoctial_precession``.
    extra_points : dict, optional
        Additional sidereal longitudes in degrees to draw, e.g. the Moon from
        another source: ``{"Luna": 123.4}``.
    nakshatras : bool
        Draw the ring of the 27 nakshatras outside the signs (number and
        abbreviation) and, under the table, the traditional emblem of each
        nakshatra occupied by a body (default True).
    sign_labels : {"text", "symbol", "both"}
        How the twelve signs are labelled: with their name, with their glyph
        (♈ ♉ …) or with both (default; small panels show only the glyph). The
        nakshatras have no standard glyphs, so their emblems are given as text.
    center_symbol : bool
        Show the Earth at the centre as its astronomical symbol ⊕ on a disc, like
        the planets (default True; False gives a plain blue dot). With
        ``epoch_position="center"`` the symbol is the first element of the epoch
        box.
    epoch_display : sequence of {"year", "date", "julian_day"}
        What to show of the epoch under the title: the year, the civil date
        and time (to the minute) and/or the Julian Day, each with its time
        scale (UT or TDB, as in ``time_scale``). With ``time_scale="UT"`` the
        Julian Day line also gives the TDB one that was used. Default: only the
        year, as before; an empty sequence shows nothing. "date" needs the
        companion module ``astro_dates``.
    calendar : {"auto", "julian", "gregorian"}
        Calendar of the displayed date (automatic: Julian up to 4 Oct 1582;
        use "julian" or "gregorian" to force one for ancient dates).
    epoch_position : {"title", "center"}
        Where the epoch items go. "title" (default): under the title. "center":
        in a short box in the centre of the circle (year, date and time on two
        lines, Julian Day), which frees the title; the planets are then kept
        clear of the box and, in a figure created here, the diagram is made
        about a quarter larger (the figure is taller and its margins narrower).
    table : bool
        Add a table with the longitudes, signs and nakshatras (only when the
        figure is created here).
    ax : matplotlib polar Axes, optional
        Existing polar axes to draw on (no table is added in that case).
    save_path, show, dpi
        As in ``plot_equinoctial_precession``.
    compact : bool
        Small-panel version: no degree marks or axis names, smaller markers and
        a two-line title (year and ayanamsa). Used by ``plot_zodiac_planets_grid``.

    Returns
    -------
    (figure, axes, positions)
        ``positions`` maps each name to a dict with "sidereal", "tropical"
        (longitudes in degrees) and "latitude" (ecliptic, degrees); the entries
        of ``extra_points`` only have "sidereal".
    """
    import matplotlib.pyplot as plt

    year = float(year)
    if not math.isfinite(year):
        raise ValueError("year must be a finite number")
    epoch_parts = _epoch_parts(epoch_display)
    _check_calendar_name(calendar)
    _check_epoch_position(epoch_position)
    _check_sign_labels(sign_labels)
    centered = epoch_position == "center" and bool(epoch_parts)
    year_given = year
    year = _tdb_year(year, time_scale)                 # from here on, TDB
    delta_t_seconds_used = (year - year_given) * 365.25 * 86400.0
    bodies = list(bodies)
    unknown = [b for b in bodies if b not in _PLANETS]
    if unknown:
        raise ValueError(f"unknown bodies {unknown}; use {list(_PLANETS)}")
    jd = 2451545.0 + (year - 2000.0) * 365.25
    direction = _direction_function(ephemeris, jd) if bodies else None

    # --- positions -----------------------------------------------------------
    positions: Dict[str, Dict[str, float]] = {}
    if bodies:
        vectors = np.array([np.asarray(direction(b, jd), dtype=float) for b in bodies])
        years = np.full(len(bodies), year)
        kwargs = dict(model=model, j2000_ayanamsa_deg=j2000_ayanamsa_deg,
                      rate_arcsec_per_year=rate_arcsec_per_year)
        sidereal, latitude = ecliptic_coordinates_of_date(vectors, years,
                                                          sidereal=True, **kwargs)
        tropical, _ = ecliptic_coordinates_of_date(vectors, years, **kwargs)
        for i, b in enumerate(bodies):
            positions[b] = {"sidereal": float(sidereal[i]), "tropical": float(tropical[i]),
                            "latitude": float(latitude[i])}
    for name, longitude in (extra_points or {}).items():
        positions[name] = {"sidereal": float(longitude) % 360.0}

    # --- base diagram (geocentric view: the Earth is at the centre) ----------
    own_figure = ax is None
    if own_figure:
        if epoch_position == "center":       # larger circle: shorter title, taller figure
            text_block = 4.05 if (table and not compact) else 0.3     # inches under it
            title_block = 1.15
            fig_height = 8.0 + title_block + text_block
            fig = plt.figure(figsize=(9.0, fig_height))
        else:
            fig = plt.figure(figsize=(9.0, 12.2))
        ax = fig.add_subplot(111, projection="polar")
    else:
        fig = ax.figure
    plot_equinoctial_precession(
        year, model=model, j2000_ayanamsa_deg=j2000_ayanamsa_deg,
        rate_arcsec_per_year=rate_arcsec_per_year, ax=ax, legend=False,
        show=False, center="none" if (centered and center_symbol) else "earth",
        show_arc=False, annotations=not compact, nakshatras=nakshatras,
        sign_labels=sign_labels, epoch_display=(), center_symbol=center_symbol)
    summary_lines = ax.get_title().split("\n")[1:]    # ayanamsa and vernal point
    epoch_texts = _epoch_texts(year_given, year, time_scale, epoch_parts, calendar,
                               compact=compact)
    if epoch_position == "center":
        head_lines = [_PLANETS_HEAD]
        if centered:
            _draw_epoch_center(ax, _epoch_center_lines(year_given, year, time_scale,
                                                       epoch_parts, calendar), compact,
                               symbol=_CENTER_SYMBOLS["earth"] if center_symbol else None)
    elif epoch_parts == ("year",):
        head_lines = [_PLANETS_HEAD + " · " + epoch_texts[0]]
    elif epoch_parts:
        head_lines = [_PLANETS_HEAD, _join_epoch(epoch_texts)]
    else:
        head_lines = [_PLANETS_HEAD]
    if compact:
        ax.set_ylim(0, 1.08 + (_NAK_RING_WIDTH if nakshatras else 0.0))   # no outer labels
        ax.set_title("\n".join(head_lines + summary_lines[:1]), fontsize=8, pad=6)
    else:
        ax.set_title("\n".join(head_lines + summary_lines), fontsize=9, pad=14)

    # --- planets: markers at staggered radii, with a tick to the ring --------
    names = list(positions)
    longitudes = [positions[n]["sidereal"] for n in names]
    if centered and center_symbol:                  # taller box: planets a little further out
        radii = (0.72, 0.65, 0.58, 0.51, 0.45)
    elif centered:                                  # clear of the centre box
        radii = (0.70, 0.62, 0.54, 0.47, 0.40)
    else:
        radii = (0.66, 0.56, 0.46, 0.36, 0.26)
    levels = _stagger_levels(longitudes, radii, 13.0 if compact else 10.0)
    for i, name in enumerate(names):
        theta = math.radians(longitudes[i])
        _, symbol, color = _PLANETS.get(name, (name, "●", "#888780"))
        radius = levels[i]
        ax.plot([theta, theta], [radius, 0.80], color=color, linewidth=1.3,
                alpha=0.9, zorder=8)
        disc_area = _DISC_AREA_COMPACT if compact else _DISC_AREA
        glyph_size = _GLYPH_FILL * math.sqrt(4.0 * disc_area / math.pi)   # points
        ax.scatter([theta], [radius], s=disc_area, c=color, edgecolors="#2C2C2A",
                   linewidths=0.8, zorder=9)
        ax.scatter([theta], [radius], s=glyph_size ** 2,
                   marker=_centered_glyph(symbol, _PLANET_FONT), c="#2C2C2A",
                   edgecolors="#2C2C2A", linewidths=0.25, zorder=10)

    # --- table ---------------------------------------------------------------
    if own_figure:
        height = fig.get_figheight()
        if epoch_position == "center":
            fig.subplots_adjust(left=0.02, right=0.98, top=1 - title_block / height,
                                bottom=text_block / height)
        else:
            fig.subplots_adjust(top=0.86, bottom=0.33 if table else 0.08)
        if table and not compact:
            rows = [_PLANETS_TABLE_HEADER]
            for name in names:
                label, symbol, _ = _PLANETS.get(name, (name, "●", ""))
                data = positions[name]
                longitude = data["sidereal"]
                sign_index, offset = _sign_index_and_offset(longitude)
                width = 360.0 / 27.0
                nak = int(longitude // width)
                pada = int((longitude % width) // (width / 4)) + 1
                tropical = (_format_deg_min(data["tropical"]) if "tropical" in data
                            else "—")
                rows.append(f"{symbol} {label:<9} {_format_deg_min(longitude):>10}"
                            f"      {tropical:>10}      "
                            f"{_SIGN_NAMES[sign_index]:<12}{_format_deg_min(offset):>7}   "
                            f"{_NAKSHATRAS[nak]} ({pada})")
            fig.text(0.5, 3.72 / height, "\n".join(rows), ha="center", va="top",
                     multialignment="left", fontsize=8.6, family=_TABLE_FONT,
                     linespacing=1.45)
            if nakshatras:
                import textwrap
                width = 360.0 / 27.0
                occupied = []
                for name in names:
                    k = int(positions[name]["sidereal"] // width)
                    if k not in occupied:
                        occupied.append(k)
                items = "; ".join(f"{_NAKSHATRAS[k]}: {_NAKSHATRA_EMBLEMS[k]}"
                                  for k in occupied)
                fig.text(0.5, 1.81 / height, _EMBLEMS_HEADER + "\n" + textwrap.fill(items, 105),
                         ha="center", va="top", multialignment="left", fontsize=8.2,
                         color=_TEXT_DARK)
            epoch_note = (_PLANETS_NOTE_EPOCH_UT.format(
                seconds=_format_number(delta_t_seconds_used, 0))
                if time_scale == "UT" else _PLANETS_NOTE_EPOCH_TDB)
            note = (_PLANETS_NOTE_METHOD + "\n" + epoch_note + "\n"
                    + (_PLANETS_NOTE_EXTERNAL if extra_points else _PLANETS_NOTE_NO_MOON))
            fig.text(0.5, 0.915 / height, note, ha="center", va="top",
                     multialignment="center", fontsize=8.2, color=_TEXT_NOTE_MODEL,
                     style="italic")

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
    if show:
        plt.show()
    return fig, ax, positions


def plot_zodiac_planets_grid(
    years: Sequence[float],
    ephemeris,
    labels: Optional[Sequence[str]] = None,
    bodies: Sequence[str] = ("sun", "mercury", "venus", "mars", "jupiter", "saturn"),
    columns: Optional[int] = None,
    model: str = "long_term",
    j2000_ayanamsa_deg: float = LAHIRI_AYANAMSA_J2000_DEG,
    rate_arcsec_per_year: float = PRECESSION_RATE_ARCSEC_PER_YEAR,
    table: bool = True,
    save_path: Optional[str] = None,
    show: bool = True,
    dpi: int = 150,
    time_scale: str = "TDB",
    nakshatras: bool = True,
    sign_labels: str = "both",
    epoch_display: Optional[Sequence[str]] = None,
    calendar: str = "auto",
    epoch_position: str = "title",
    panel_size: float = 3.7,
    center_symbol: bool = True,
):
    """
    Draw several years side by side: one small zodiac diagram with the planets
    per year, and an optional summary table of the sidereal longitudes.

    Parameters
    ----------
    years : sequence of float
        Julian epochs (astronomical year numbering), one panel each, in the
        time scale ``time_scale``.
    time_scale : {"TDB", "UT"}
        As in ``plot_zodiac_with_planets``: with "UT" every year is converted
        to TDB before querying the ephemeris (the panel labels keep the years
        as given).
    ephemeris : dict, sequence of dict, or callable
        As in ``plot_zodiac_with_planets``; with several tables, each year uses
        the one that covers it.
    labels : sequence of str, optional
        Panel titles (default: the year, in Spanish with "a. C." / "d. C.").
    epoch_display : sequence of {"year", "date", "julian_day"}, optional
        Extra lines under each panel title: the year, the civil date and time
        (to the minute, with its time scale and a short calendar tag) and/or
        the Julian Day. Without it, panels show only ``labels`` (or the year).
    calendar : {"auto", "julian", "gregorian"}
        Calendar of the displayed dates.
    epoch_position : {"title", "center"}
        Put the ``epoch_display`` items under each panel title (default) or in
        a small box in the centre of each circle, which shortens the titles.
    panel_size : float
        Width in inches of each panel (default 3.7); the circles grow with it.
    bodies, model, j2000_ayanamsa_deg, rate_arcsec_per_year, nakshatras, sign_labels, center_symbol
        As in ``plot_zodiac_with_planets`` (in the small panels "both" shows only
        the glyph of each sign, and the nakshatras only their number).
    columns : int, optional
        Panels per row (default: all in one row).
    table : bool
        Add a table with each body's sign, degrees and (if ``nakshatras``) the
        abbreviation of its nakshatra for every year.
    save_path, show, dpi
        As in ``plot_equinoctial_precession``.

    Returns
    -------
    (figure, axes, positions)
        ``axes`` is the list of polar axes and ``positions`` the list of the
        dictionaries returned by ``plot_zodiac_with_planets``, in the order of
        ``years``.
    """
    import matplotlib.pyplot as plt

    years = [float(y) for y in years]
    count = len(years)
    if count == 0:
        raise ValueError("years must not be empty")
    epoch_parts = _epoch_parts(epoch_display)
    _check_calendar_name(calendar)
    _check_epoch_position(epoch_position)
    _check_sign_labels(sign_labels)
    in_center = epoch_position == "center"
    if float(panel_size) <= 0:
        raise ValueError("panel_size must be positive")
    if labels is None:
        title_labels = ([_format_year(y) for y in years] if epoch_display is None
                        else [None] * count)
        labels = [_format_year(y, short=True) for y in years]      # table header
    else:
        labels = list(labels)
        title_labels = labels
    if len(labels) != count:
        raise ValueError("labels must have one entry per year")
    columns = count if columns is None else int(columns)
    if columns < 1:
        raise ValueError("columns must be >= 1")
    rows = -(-count // columns)
    body_list = list(bodies)
    if time_scale not in ("TDB", "UT"):
        raise ValueError("time_scale must be 'TDB' or 'UT'")

    panel = float(panel_size)
    table_lines = len(body_list) + 2
    table_height = 0.20 * table_lines + 0.5 if table else 0.0
    title_line_count = (0 if all(t is None for t in title_labels) else 1) \
        + (0 if in_center else len(epoch_parts)) + 1     # label, epoch items, ayanamsa
    header = 0.30 + 0.17 * title_line_count         # room for the panel titles, inches
    height = 0.92 * panel * rows + header + 0.15 + table_height
    fig = plt.figure(figsize=(panel * columns, height))
    axes, all_positions, ayanamsas = [], [], []
    for k, (year, label) in enumerate(zip(years, labels)):
        ax = fig.add_subplot(rows, columns, k + 1, projection="polar")
        _, _, positions = plot_zodiac_with_planets(
            year, ephemeris, bodies=body_list, model=model,
            j2000_ayanamsa_deg=j2000_ayanamsa_deg,
            rate_arcsec_per_year=rate_arcsec_per_year,
            ax=ax, show=False, compact=True, time_scale=time_scale,
            nakshatras=nakshatras, sign_labels=sign_labels, calendar=calendar,
            center_symbol=center_symbol,
            epoch_display=epoch_parts if in_center else (),
            epoch_position=epoch_position)
        year_tdb = _tdb_year(year, time_scale)
        title_lines = ([title_labels[k]] if title_labels[k] is not None else []) \
            + ([] if in_center else _epoch_texts(year, year_tdb, time_scale, epoch_parts,
                                                 calendar, compact=True))
        if model == "long_term":
            ayanamsa = long_term_ayanamsa(year_tdb, j2000_ayanamsa_deg)
        else:
            ayanamsa = float(lahiri_ayanamsa(year_tdb, j2000_ayanamsa_deg,
                                             rate_arcsec_per_year))
        ax.set_title("\n".join(title_lines + [f"A = {_format_number(ayanamsa, 2)}°"]),
                     fontsize=9 if len(title_lines) < 3 else 8, pad=8)
        axes.append(ax)
        all_positions.append(positions)
        ayanamsas.append(ayanamsa)

    bottom = (table_height + 0.15) / height if table else 0.04
    fig.subplots_adjust(left=0.02, right=0.98, top=1 - header / height,
                        bottom=bottom, wspace=0.08, hspace=0.30)
    if table:
        short = [label if len(label) <= 15 else label[:14] + "…" for label in labels]
        width = max(16 if nakshatras else 12, max(len(label) for label in short) + 1)
        rows_text = ["Cuerpo      " + "".join(f"{label:<{width}}" for label in short)]
        for body in body_list:
            name, symbol, _ = _PLANETS[body]
            cells = []
            for positions in all_positions:
                longitude = positions[body]["sidereal"]
                sign_index, offset = _sign_index_and_offset(longitude)
                cell = f"{_SIGN_ABBREVIATIONS[sign_index]} {_format_deg_min(offset):>6}"
                if nakshatras:
                    cell += f" {_NAKSHATRA_ABBREVIATIONS[int(longitude // (360.0 / 27.0))]}"
                cells.append(cell)
            rows_text.append(f"{symbol} {name:<9} " + "".join(f"{c:<{width}}" for c in cells))
        fig.text(0.5, (table_height / 2 + 0.05) / height, "\n".join(rows_text),
                 ha="center", va="center", multialignment="left", fontsize=8.6,
                 family=_TABLE_FONT, linespacing=1.45)

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
    if show:
        plt.show()
    return fig, axes, all_positions


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
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
    if show:
        plt.show()
    return fig, axes, data
