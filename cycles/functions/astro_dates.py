"""
astro_dates.py

Conversions between calendar dates, Julian Day numbers and decimal years,
valid for arbitrarily remote years (tens of thousands of years either side of
the present).

Conventions
-----------
* Years use astronomical numbering: 1 BC is year 0, 2 BC is -1, ..., so
  3102 BC is -3101. ``bc_to_astronomical`` converts BC years.
* Calendars: ``"julian"``, ``"gregorian"`` (both proleptic, i.e. extended
  backwards and forwards without limit) or ``"auto"``. With ``"auto"``, dates
  up to 1582-10-04 are Julian and dates from 1582-10-15 are Gregorian; the
  dates 1582-10-05 to 1582-10-14 do not exist and raise ``ValueError``.
  Far from 1582, calendar dates have no historical or seasonal meaning (the
  Julian calendar drifts ~0.0078 days/year relative to the seasons); the Julian
  Day itself is always exact.
* Julian Day (JD): continuous day count; JD 0.0 is noon of 4713-01-01 BC
  (Julian) = -4712-01-01 12:00. Noon of a civil day has an integer JD (its
  "Julian Day Number", JDN), so midnight at the start of that day is JDN - 0.5.
  The ``day`` argument may carry a fraction: ``day=1.5`` is noon on the 1st
  (``day_with_time`` builds that fraction from hours, minutes and seconds).
* Decimal year: Julian years of exactly 365.25 days anchored at J2000.0,
      year = 2000 + (JD - 2451545.0) / 365.25
  This is the unit of the precession rate (arcsec per Julian year). Note that
  an exact decimal year such as -16000.0 does not fall on January 1st of that
  calendar year (the anchor is Gregorian 2000-01-01 12:00, which is
  Julian 1999-12-19).

All conversions use integer arithmetic with floor division, so they are exact
for any integer day number (negative JD included).

Time scales
-----------
Civil dates are in Universal Time (UT, tied to the rotation of the Earth);
planetary ephemerides (``nbody_ephemeris``) work in dynamical time (TDB).
TDB ~ TT = UT + DeltaT, with DeltaT in seconds (TDB - TT is a periodic term of
at most 1.7 ms). ``delta_t_seconds`` uses the polynomial expressions of
Espenak & Meeus (NASA, valid -1999 to +3000), which are a parabola
-20 + 32 u^2 (u in centuries from 1820) before the year -500. DeltaT is only
known from observations back to about -700 and is extrapolated before that:
around 3100 BC it is about 21.5 hours with this parabola (25.5 hours with an
older expression by Stephenson & Houlden), so treat it as uncertain by
several hours there. Outside -1999..3000 a warning is issued.
``date_to_tdb_year`` and ``tdb_year_to_date`` do the whole civil date <-> TDB
decimal year conversion in one step.

Dependencies: standard library only (``math``, ``operator``, ``re``).

Public API
----------
bc_to_astronomical, parse_date, format_date,
date_to_julian_day_number, julian_day_number_to_date,
date_to_julian_day, julian_day_to_date, calendar_for_julian_day,
julian_day_to_year, year_to_julian_day, date_to_year, year_to_date,
day_with_time, split_day, date_time_to_julian_day,
delta_t_seconds, ut_to_tdb, tdb_to_ut, date_to_tdb_year, tdb_year_to_date.

Example
-------
>>> date_to_julian_day(2000, 1, 1.5)
2451545.0
>>> date_to_julian_day(*parse_date("3102 BC-02-18"), calendar="julian")
588465.5
>>> year_to_date(-16000)
(-16001, 12, 19.5)
>>> format_date(-3101, 2, 18)
'18 feb 3102 a. C. (calendario juliano)'
"""

from __future__ import annotations

import math
import operator
import re
import warnings
from typing import Tuple

__all__ = [
    "JD_J2000",
    "DAYS_PER_JULIAN_YEAR",
    "bc_to_astronomical",
    "parse_date",
    "format_date",
    "date_to_julian_day_number",
    "julian_day_number_to_date",
    "date_to_julian_day",
    "julian_day_to_date",
    "calendar_for_julian_day",
    "julian_day_to_year",
    "year_to_julian_day",
    "date_to_year",
    "year_to_date",
    "day_with_time",
    "split_day",
    "date_time_to_julian_day",
    "delta_t_seconds",
    "ut_to_tdb",
    "tdb_to_ut",
    "date_to_tdb_year",
    "tdb_year_to_date",
]

JD_J2000 = 2451545.0
DAYS_PER_JULIAN_YEAR = 365.25

_CALENDARS = ("auto", "julian", "gregorian")
_GREGORIAN_REFORM_JDN = 2299161  # 1582-10-15 Gregorian = 1582-10-04 Julian + 1 day
_DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# User-facing text (Spanish)
_MONTH_ABBREVIATIONS = ["ene", "feb", "mar", "abr", "may", "jun",
                        "jul", "ago", "sep", "oct", "nov", "dic"]
_CALENDAR_NAMES = {"julian": "juliano", "gregorian": "gregoriano"}
_ERA_AD = "d. C."
_ERA_BC = "a. C."
_FORMAT_TEMPLATE = "{day} {month} {year} {era} (calendario {calendar})"

_DATE_PATTERN = re.compile(
    r"^([+-]?\d+)(bce|bc|ac|ce|ad|dc)?[-/](\d{1,2})[-/](\d{1,2})$")


# ----------------------------------------------------------------------------
# Validation helpers
# ----------------------------------------------------------------------------

def _as_int(name: str, value) -> int:
    try:
        return operator.index(value)
    except TypeError:
        raise TypeError(f"{name} must be an integer, got {value!r}") from None


def _check_calendar(calendar: str) -> None:
    if calendar not in _CALENDARS:
        raise ValueError(f"calendar must be one of {_CALENDARS}, got {calendar!r}")


def _is_leap(year: int, calendar: str) -> bool:
    if year % 4 != 0:
        return False
    if calendar == "julian":
        return True
    return year % 100 != 0 or year % 400 == 0


def _days_in_month(year: int, month: int, calendar: str) -> int:
    if month == 2 and _is_leap(year, calendar):
        return 29
    return _DAYS_IN_MONTH[month - 1]


def _resolve_calendar_for_date(year: int, month: int, day: int,
                               calendar: str) -> str:
    if calendar != "auto":
        return calendar
    key = (year, month, day)
    if key < (1582, 10, 5):
        return "julian"
    if key >= (1582, 10, 15):
        return "gregorian"
    raise ValueError(
        "1582-10-05 to 1582-10-14 do not exist in the Gregorian reform "
        "(calendar='auto')")


# ----------------------------------------------------------------------------
# Integer algorithms (floor division, valid for any integer day number)
# ----------------------------------------------------------------------------

def _jdn_from_julian(y: int, m: int, d: int) -> int:
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - 32083


def _jdn_from_gregorian(y: int, m: int, d: int) -> int:
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return (d + (153 * mm + 2) // 5 + 365 * yy + yy // 4
            - yy // 100 + yy // 400 - 32045)


def _julian_from_jdn(jdn: int) -> Tuple[int, int, int]:
    c = jdn + 32082
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    return d - 4800 + m // 10, m + 3 - 12 * (m // 10), e - (153 * m + 2) // 5 + 1


def _gregorian_from_jdn(jdn: int) -> Tuple[int, int, int]:
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    return (100 * b + d - 4800 + m // 10, m + 3 - 12 * (m // 10),
            e - (153 * m + 2) // 5 + 1)


# ----------------------------------------------------------------------------
# Era, parsing and formatting
# ----------------------------------------------------------------------------

def bc_to_astronomical(year_bc: int) -> int:
    """Convert a BC year (3102 for 3102 BC) to astronomical numbering (-3101)."""
    year_bc = _as_int("year_bc", year_bc)
    if year_bc < 1:
        raise ValueError("year_bc must be >= 1 (there is no year 0 BC)")
    return 1 - year_bc


def parse_date(text: str) -> Tuple[int, int, int]:
    """
    Parse 'YYYY ERA-MM-DD' into (astronomical year, month, day).

    Accepted eras (case-insensitive, spaces and dots ignored): BC, BCE, AC,
    a. C. for BC and AD, CE, DC, d. C. for AD. Without an era, a positive year
    is AD and a year <= 0 or with an explicit sign is already astronomical.
    Separators between year, month and day: '-' or '/'. Examples:
    '3014 AC - 02 - 07', '3102 BC-02-18', '-3101-02-18', '2026-11-02'.

    The calendar is not decided here; pass the result to the converters.
    """
    cleaned = re.sub(r"\s+", "", str(text).lower()).replace(".", "")
    match = _DATE_PATTERN.match(cleaned)
    if not match:
        raise ValueError(f"cannot parse date {text!r}; expected e.g. '3014 BC-02-07'")
    year_text, era, month, day = match.groups()
    if not 1 <= int(month) <= 12 or not 1 <= int(day) <= 31:
        raise ValueError(f"month or day out of range in {text!r}")
    year = int(year_text)
    if era in ("bc", "bce", "ac"):
        if year_text[0] in "+-":
            raise ValueError("BC years must be written without a sign")
        year = bc_to_astronomical(year)
    elif era in ("ad", "ce", "dc"):
        if year < 1:
            raise ValueError("AD years must be >= 1")
    return year, int(month), int(day)


def format_date(year: int, month: int, day, calendar: str = "auto") -> str:
    """Format a date in Spanish, e.g. '18 feb 3102 a. C. (calendario juliano)'."""
    _check_calendar(calendar)
    year, month = _as_int("year", year), _as_int("month", month)
    whole_day = math.floor(day)
    resolved = _resolve_calendar_for_date(year, month, whole_day, calendar)
    if not 1 <= month <= 12:
        raise ValueError("month must be in 1..12")
    if year > 0:
        year_text, era = str(year), _ERA_AD
    else:
        year_text, era = str(1 - year), _ERA_BC
    return _FORMAT_TEMPLATE.format(
        day=whole_day, month=_MONTH_ABBREVIATIONS[month - 1], year=year_text,
        era=era, calendar=_CALENDAR_NAMES[resolved])


# ----------------------------------------------------------------------------
# Date <-> Julian Day
# ----------------------------------------------------------------------------

def date_to_julian_day_number(year: int, month: int, day: int,
                              calendar: str = "auto") -> int:
    """Integer Julian Day Number of a civil date (JD of its noon)."""
    _check_calendar(calendar)
    year, month, day = (_as_int("year", year), _as_int("month", month),
                        _as_int("day", day))
    if not 1 <= month <= 12:
        raise ValueError("month must be in 1..12")
    resolved = _resolve_calendar_for_date(year, month, day, calendar)
    if not 1 <= day <= _days_in_month(year, month, resolved):
        raise ValueError(
            f"day {day} does not exist in month {month} of year {year} "
            f"({resolved} calendar)")
    if resolved == "julian":
        return _jdn_from_julian(year, month, day)
    return _jdn_from_gregorian(year, month, day)


def calendar_for_julian_day(jd: float, calendar: str = "auto") -> str:
    """Calendar ('julian' or 'gregorian') used to express ``jd``."""
    _check_calendar(calendar)
    if calendar != "auto":
        return calendar
    return "julian" if math.floor(jd + 0.5) < _GREGORIAN_REFORM_JDN else "gregorian"


def julian_day_number_to_date(jdn: int, calendar: str = "auto") -> Tuple[int, int, int]:
    """Civil date (year, month, day) whose noon has Julian Day Number ``jdn``."""
    jdn = _as_int("jdn", jdn)
    if calendar_for_julian_day(jdn, calendar) == "julian":
        return _julian_from_jdn(jdn)
    return _gregorian_from_jdn(jdn)


def date_to_julian_day(year: int, month: int, day: float = 1.0,
                       calendar: str = "auto") -> float:
    """Julian Day of a date; ``day`` may have a fraction (1.5 = noon on the 1st)."""
    whole = math.floor(day)
    fraction = day - whole
    return date_to_julian_day_number(year, month, whole, calendar) - 0.5 + fraction


def julian_day_to_date(jd: float, calendar: str = "auto") -> Tuple[int, int, float]:
    """(year, month, day) for a Julian Day; ``day`` includes the day fraction."""
    jd = float(jd)
    if not math.isfinite(jd):
        raise ValueError("jd must be finite")
    jdn = math.floor(jd + 0.5)
    fraction = jd + 0.5 - jdn
    year, month, day = julian_day_number_to_date(jdn, calendar)
    return year, month, day + fraction


# ----------------------------------------------------------------------------
# Julian Day <-> decimal year, and dates <-> decimal year
# ----------------------------------------------------------------------------

def julian_day_to_year(jd: float) -> float:
    """Decimal year in Julian years anchored at J2000.0."""
    return 2000.0 + (jd - JD_J2000) / DAYS_PER_JULIAN_YEAR


def year_to_julian_day(year: float) -> float:
    """Julian Day of a decimal year (inverse of ``julian_day_to_year``)."""
    year = float(year)
    if not math.isfinite(year):
        raise ValueError("year must be finite")
    return JD_J2000 + (year - 2000.0) * DAYS_PER_JULIAN_YEAR


def date_to_year(year: int, month: int, day: float = 1.0,
                 calendar: str = "auto") -> float:
    """Decimal year (Julian years from J2000.0) of a calendar date."""
    return julian_day_to_year(date_to_julian_day(year, month, day, calendar))


def year_to_date(year: float, calendar: str = "auto") -> Tuple[int, int, float]:
    """Calendar date (year, month, day with fraction) of a decimal year."""
    return julian_day_to_date(year_to_julian_day(year), calendar)


# ----------------------------------------------------------------------------
# Time of day
# ----------------------------------------------------------------------------

def day_with_time(day, hour: int = 0, minute: int = 0, second: float = 0.0) -> float:
    """
    Day of the month plus the fraction of the day for a time of day, as the
    ``day`` argument of ``date_to_year``, ``date_to_julian_day``, etc. expect
    (origin at 0 h): ``day_with_time(7, 1, 51)`` is 7.0771 (1 h 51 min).

    The time is taken as UT, exactly as given; for a local time or a civil time
    zone use ``date_time_to_julian_day`` (it may cross to the previous or the
    next day, which a plain fraction cannot represent).
    """
    day = float(day)
    hour, minute, second = float(hour), float(minute), float(second)
    if not all(math.isfinite(v) for v in (day, hour, minute, second)):
        raise ValueError("day and time must be finite")
    if not (0.0 <= hour < 24.0 and 0.0 <= minute < 60.0 and 0.0 <= second < 60.0):
        raise ValueError("need 0 <= hour < 24, 0 <= minute < 60 and 0 <= second < 60")
    return day + (hour + minute / 60.0 + second / 3600.0) / 24.0


def split_day(day: float) -> Tuple[int, int, int, float]:
    """
    Inverse of ``day_with_time``: split a fractional day (for example the third
    value returned by ``julian_day_to_date`` or ``year_to_date``) into
    (day, hour, minute, second). Seconds are rounded to a microsecond, which
    removes floating-point noise; the day carries over when that rounding
    reaches 24 h.
    """
    day = float(day)
    if not math.isfinite(day):
        raise ValueError("day must be finite")
    whole = math.floor(day)
    total = round((day - whole) * 86400.0, 6)
    if total >= 86400.0:
        whole += 1
        total -= 86400.0
    hour = int(total // 3600)
    minute = int((total - 3600 * hour) // 60)
    return int(whole), hour, minute, round(total - 3600 * hour - 60 * minute, 6)


def date_time_to_julian_day(year: int, month: int, day: int, hour: int = 0,
                            minute: int = 0, second: float = 0.0,
                            calendar: str = "auto",
                            utc_offset_hours: float = 0.0) -> float:
    """
    Julian Day (in UT) of a calendar date and time of day.

    ``utc_offset_hours`` is the offset of the given time from UT, positive
    towards the east: UT = time - offset. Use 5.5 for a clock 5 h 30 min ahead
    of UT, or ``longitude_east_deg / 15`` for local mean solar time at a place.
    Because the offset is applied to the Julian Day, the result may fall on the
    previous or the next calendar day. ``day`` is the integer day of the month
    (validated); the calendar is chosen as in ``date_to_year``.
    """
    offset = float(utc_offset_hours)
    if not math.isfinite(offset):
        raise ValueError("utc_offset_hours must be finite")
    fraction = day_with_time(0, hour, minute, second)
    return (date_to_julian_day_number(year, month, day, calendar) - 0.5
            + fraction - offset / 24.0)


# ----------------------------------------------------------------------------
# Time scales: UT <-> TDB
# ----------------------------------------------------------------------------

def _horner(coefficients, x: float) -> float:
    """Evaluate a polynomial given in increasing powers of x."""
    result = 0.0
    for c in reversed(coefficients):
        result = result * x + c
    return result


def delta_t_seconds(year: float) -> float:
    """
    DeltaT = TT - UT in seconds for a decimal year (Espenak & Meeus polynomial
    expressions, NASA). Observed values back to about -700; before that, and
    after the present, the result is an extrapolation (see the module
    docstring). A warning is issued outside -1999..3000.

    ``year`` is a decimal calendar year (e.g. 2026.84); astronomical numbering.
    """
    y = float(year)
    if not math.isfinite(y):
        raise ValueError("year must be finite")
    if y < -1999.0 or y > 3000.0:
        warnings.warn("delta_t_seconds: the polynomial expressions are valid for "
                      "-1999..3000; this is a parabolic extrapolation",
                      stacklevel=2)
    if y < -500.0:
        u = (y - 1820.0) / 100.0
        return -20.0 + 32.0 * u * u
    if y < 500.0:
        return _horner((10583.6, -1014.41, 33.78311, -5.952053, -0.1798452,
                        0.022174192, 0.0090316521), y / 100.0)
    if y < 1600.0:
        return _horner((1574.2, -556.01, 71.23472, 0.319781, -0.8503463,
                        -0.005050998, 0.0083572073), (y - 1000.0) / 100.0)
    if y < 1700.0:
        t = y - 1600.0
        return 120.0 - 0.9808 * t - 0.01532 * t * t + t**3 / 7129.0
    if y < 1800.0:
        t = y - 1700.0
        return (8.83 + 0.1603 * t - 0.0059285 * t * t + 0.00013336 * t**3
                - t**4 / 1174000.0)
    if y < 1860.0:
        return _horner((13.72, -0.332447, 0.0068612, 0.0041116, -0.00037436,
                        0.0000121272, -0.0000001699, 0.000000000875), y - 1800.0)
    if y < 1900.0:
        t = y - 1860.0
        return (7.62 + 0.5737 * t - 0.251754 * t * t + 0.01680668 * t**3
                - 0.0004473624 * t**4 + t**5 / 233174.0)
    if y < 1920.0:
        return _horner((-2.79, 1.494119, -0.0598939, 0.0061966, -0.000197),
                       y - 1900.0)
    if y < 1941.0:
        return _horner((21.20, 0.84493, -0.076100, 0.0020936), y - 1920.0)
    if y < 1961.0:
        t = y - 1950.0
        return 29.07 + 0.407 * t - t * t / 233.0 + t**3 / 2547.0
    if y < 1986.0:
        t = y - 1975.0
        return 45.45 + 1.067 * t - t * t / 260.0 - t**3 / 718.0
    if y < 2005.0:
        return _horner((63.86, 0.3345, -0.060374, 0.0017275, 0.000651814,
                        0.00002373599), y - 2000.0)
    if y < 2050.0:
        return _horner((62.92, 0.32217, 0.005589), y - 2000.0)
    u = (y - 1820.0) / 100.0
    if y < 2150.0:
        return -20.0 + 32.0 * u * u - 0.5628 * (2150.0 - y)
    return -20.0 + 32.0 * u * u


def _tdb_minus_tt_seconds(jd_tt: float) -> float:
    """Principal periodic term of TDB - TT (seconds; amplitude 1.657 ms)."""
    t = (jd_tt - JD_J2000) / 36525.0
    return 0.001657 * math.sin(6.2401 + 628.3076 * t)


def ut_to_tdb(jd_ut: float) -> float:
    """Julian Day in TDB for a Julian Day in UT (TDB = UT + DeltaT + periodic term)."""
    jd_ut = float(jd_ut)
    year = 2000.0 + (jd_ut - JD_J2000) / DAYS_PER_JULIAN_YEAR
    jd_tt = jd_ut + delta_t_seconds(year) / 86400.0
    return jd_tt + _tdb_minus_tt_seconds(jd_tt) / 86400.0


def tdb_to_ut(jd_tdb: float) -> float:
    """Julian Day in UT for a Julian Day in TDB (inverse of ``ut_to_tdb``)."""
    jd_tdb = float(jd_tdb)
    jd_ut = jd_tdb
    for _ in range(6):                       # DeltaT varies very slowly: converges at once
        jd_ut = jd_tdb - (ut_to_tdb(jd_ut) - jd_ut)
    return jd_ut


def date_to_tdb_year(year: int, month: int, day: float = 1.0,
                     calendar: str = "auto") -> float:
    """
    Decimal year in TDB (what the ephemerides and the plotting functions
    expect) of a civil date given in UT. ``day`` may carry a fraction of a day
    (0 h UT origin), and the calendar is chosen as in ``date_to_year``.
    """
    return julian_day_to_year(ut_to_tdb(date_to_julian_day(year, month, day, calendar)))


def tdb_year_to_date(year: float, calendar: str = "auto") -> Tuple[int, int, float]:
    """Civil date (UT) of a decimal year given in TDB (inverse of ``date_to_tdb_year``)."""
    return julian_day_to_date(tdb_to_ut(year_to_julian_day(year)), calendar)
