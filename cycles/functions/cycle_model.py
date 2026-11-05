"""
Configurable model of the yuga cycle in physical time.

How the cycle sits in history is an open question: sources differ on the
moment of the start of the Kali Yuga and on the length of the whole cycle.
A ``CycleModel`` makes each choice explicit:

* **anchor**: a moment, given as a date and time (local mean time at a
  longitude, or UT) or as a value of the ayanamsa (a position of the vernal
  point), and the point of the cycle that falls on it (the start of Satya,
  Treta, Dvapara or Kali, or the end);
* **scale**: the total precession arc in turns, or the total length in years
  (setting one determines the other);
* **division**: what the 4:3:2:1 proportions divide, at every level: precession
  angle (``'angle'``), time (``'time'``), or angle for the four yugas and time
  inside them (``'hybrid'``);
* **precession**: the long-term model (Vondrák et al. 2011, varying rate) or a
  constant rate given by its period (``'constant'``). With a constant rate,
  dividing angle and dividing time give the same boundaries.

``model.time_map()`` gives the ``TimeMap`` (normalized time <-> decimal
years, UT) used everywhere else. Named presets are in ``BUILTIN_PRESETS``;
``load_presets`` adds those saved by the user in a JSON file.
"""

import dataclasses
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cycles.functions.astro_dates import date_time_to_julian_day, julian_day_to_year, parse_date
from cycles.functions.timescale import AGE_BOUNDARIES, TimeMap

# Points of the cycle an anchor can fix, by name: normalized time
ANCHOR_POINTS = {'satya': 0.0, 'treta': 0.4, 'dvapara': 0.7, 'kali': 0.9, 'end': 1.0}
ANCHOR_LABELS = {'satya': 'Start of Satya', 'treta': 'Start of Treta', 'dvapara': 'Start of Dvapara',
                 'kali': 'Start of Kali', 'end': 'End of Kali'}
DIVISIONS = ('angle', 'time', 'hybrid')
PRECESSION_MODELS = ('long_term', 'constant')
TURN_ARCSEC = 360 * 3600
# Meridian of Ujjain, the prime meridian of Indian astronomy (degrees east)
UJJAIN_LONGITUDE = 75.77
# File of the presets saved by the user ($CYCLES_PRESETS, or in the sandbox of the source tree)
USER_PRESETS_FILE = Path(os.environ.get('CYCLES_PRESETS')
                         or Path(__file__).resolve().parents[2] / 'sandbox' / 'cycle_presets.json')


def _parse_time(text: str) -> tuple[int, int, float]:
    """``'HH:MM'`` or ``'HH:MM:SS'`` -> (hour, minute, second)."""
    parts = [float(p) for p in str(text).strip().split(':')]
    if not 2 <= len(parts) <= 3 or not 0 <= parts[0] < 24 or not 0 <= parts[1] < 60:
        raise ValueError(f"time {text!r} must be HH:MM or HH:MM:SS")
    return int(parts[0]), int(parts[1]), parts[2] if len(parts) == 3 else 0.0


def _bisect(f, lo: float, hi: float, tolerance: float) -> float:
    """Root of the increasing function ``f``, after widening ``[lo, hi]`` until it brackets it."""
    for _ in range(60):
        if f(lo) <= 0:
            break
        lo /= 2
    for _ in range(60):
        if f(hi) >= 0:
            break
        hi *= 2
    if f(lo) > 0 or f(hi) < 0:
        raise ValueError("no solution: the requested scale is out of range")
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
        if hi - lo <= tolerance:
            break
    return (lo + hi) / 2


@dataclass(frozen=True)
class CycleModel:
    """
    Choices that place the yuga cycle in physical time (see the module docstring).

    Anchor: either ``anchor_date`` (``'3102 BC-02-18'``, ``'-3101-02-18'``...,
    Julian calendar before 1582) with ``anchor_time`` (``'HH:MM'``) as local
    mean time at ``anchor_longitude`` (degrees east; 0 for UT), or
    ``anchor_ayanamsa`` (degrees, accumulated as in ``long_term_ayanamsa``).
    ``anchor_point`` names the point of the cycle at the anchor (a key of
    ``ANCHOR_POINTS``).

    Scale: exactly one of ``turns`` (total precession arc) and ``years``.
    ``period`` is the length of one turn, in years, for ``precession='constant'``.
    """

    name: str = 'Custom'
    anchor_date: str | None = '3102 BC-02-18'
    anchor_time: str = '00:00'
    anchor_longitude: float = UJJAIN_LONGITUDE
    anchor_ayanamsa: float | None = None
    anchor_point: str = 'kali'
    turns: float | None = 2.5
    years: float | None = None
    division: str = 'angle'
    precession: str = 'long_term'
    period: float = 25772.0
    description: str = ''

    def __post_init__(self):
        if (self.anchor_date is None) == (self.anchor_ayanamsa is None):
            raise ValueError("give exactly one of anchor_date and anchor_ayanamsa")
        if self.anchor_point not in ANCHOR_POINTS:
            raise ValueError(f"anchor_point must be one of {list(ANCHOR_POINTS)}")
        if (self.turns is None) == (self.years is None):
            raise ValueError("give exactly one of turns and years")
        if (self.turns if self.turns is not None else self.years) <= 0:
            raise ValueError("the scale must be positive")
        if self.division not in DIVISIONS:
            raise ValueError(f"division must be one of {DIVISIONS}")
        if self.precession not in PRECESSION_MODELS:
            raise ValueError(f"precession must be one of {PRECESSION_MODELS}")
        if self.period <= 0:
            raise ValueError("period must be positive")

    # -- precession

    def _precession_options(self) -> dict:
        if self.precession == 'constant':
            return {'model': 'linear', 'rate_arcsec_per_year': TURN_ARCSEC / self.period}
        return {'model': 'long_term'}

    def ayanamsa(self, year):
        """Ayanamsa (degrees, accumulated) at ``year`` in this model's precession."""
        from cycles.plotting.equinoctial_precession import lahiri_ayanamsa, long_term_ayanamsa
        if self.precession == 'constant':
            return lahiri_ayanamsa(year, rate_arcsec_per_year=TURN_ARCSEC / self.period)
        return long_term_ayanamsa(year)

    def _year_after_turns(self, turns, reference_year: float):
        from cycles.plotting.equinoctial_precession import year_from_ayanamsa
        return year_from_ayanamsa(turns, unit='turns', reference_year=reference_year, **self._precession_options())

    # -- solving

    def anchor_year(self) -> float:
        """Decimal year (UT) of the anchor."""
        if self.anchor_date is not None:
            year, month, day = parse_date(self.anchor_date)
            hour, minute, second = _parse_time(self.anchor_time)
            return julian_day_to_year(date_time_to_julian_day(year, month, day, hour, minute, second,
                                                              utc_offset_hours=self.anchor_longitude / 15))
        from cycles.plotting.equinoctial_precession import year_from_ayanamsa
        return float(year_from_ayanamsa(self.anchor_ayanamsa, unit='degrees', **self._precession_options()))

    def solve(self) -> dict:
        """
        Start and end years and total arc of the cycle: ``{'start', 'end',
        'turns', 'years', 'anchor'}``.
        """
        anchor = self.anchor_year()
        u = ANCHOR_POINTS[self.anchor_point]
        by_angle = self.division in ('angle', 'hybrid')
        if by_angle:
            def span(turns):
                return (float(self._year_after_turns(-u * turns, anchor)),
                        float(self._year_after_turns((1 - u) * turns, anchor)))
            if self.turns is not None:
                turns = self.turns
            else:
                guess = self.years / 25772.0
                turns = _bisect(lambda n: (lambda s: s[1] - s[0])(span(n)) - self.years,
                                guess / 2, guess * 2, 1e-10 * guess)
            start, end = span(turns)
        else:
            def span(years):
                return anchor - u * years, anchor + (1 - u) * years
            if self.years is not None:
                years = self.years
            else:
                def arc(years):
                    s, e = span(years)
                    return (self.ayanamsa(e) - self.ayanamsa(s)) / 360.0
                guess = self.turns * 25772.0
                years = _bisect(lambda y: arc(y) - self.turns, guess / 2, guess * 2, 1e-9 * guess)
            start, end = span(years)
            turns = (self.ayanamsa(end) - self.ayanamsa(start)) / 360.0
        return {'start': start, 'end': end, 'turns': float(turns), 'years': end - start, 'anchor': anchor}

    def time_map(self) -> TimeMap:
        """The map between normalized time and decimal years (UT) of this model."""
        from cycles.plotting.equinoctial_precession import precession_time_map
        solution = self.solve()
        if self.division == 'time':
            return TimeMap.linear(solution['start'], solution['end'])
        angle_map = precession_time_map(solution['start'], solution['turns'], **self._precession_options())
        if self.division == 'angle':
            return angle_map
        return TimeMap.from_age_boundaries(angle_map.to_physical(AGE_BOUNDARIES))

    def boundaries(self) -> np.ndarray:
        """Years of the starts of Satya, Treta, Dvapara and Kali, and of the end."""
        return self.time_map().to_physical(AGE_BOUNDARIES)

    # -- presets

    def replace(self, **changes) -> 'CycleModel':
        """Copy with some fields changed (e.g. ``model.replace(division='time')``)."""
        return dataclasses.replace(self, **changes)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'CycleModel':
        fields = {f.name for f in dataclasses.fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in fields})


BUILTIN_PRESETS = {model.name: model for model in (
    CycleModel(
        name='Kali 3102 BC, midnight at Ujjain',
        anchor_date='3102 BC-02-18', anchor_time='00:00', anchor_longitude=UJJAIN_LONGITUDE,
        description="Surya Siddhanta and Aryabhata's midnight (ardharatrika) system: the Kali Yuga starts at "
                    "midnight between 17 and 18 Feb 3102 BC (Julian) on the meridian of Ujjain. The cycle is "
                    "2.5 turns of precession, divided by angle."),
    CycleModel(
        name='Kali 3102 BC, sunrise at Lanka',
        anchor_date='3102 BC-02-18', anchor_time='06:00', anchor_longitude=UJJAIN_LONGITUDE,
        description="Aryabhata's sunrise (audayika) system: the Kali Yuga starts at mean sunrise on Friday "
                    "18 Feb 3102 BC (Julian) at Lanka (the equator on the meridian of Ujjain). 2.5 turns, "
                    "divided by angle."),
    CycleModel(
        name='Kali 3104 BC, Abhyankar 1993',
        anchor_date='3104 BC-02-07', anchor_time='01:51', anchor_longitude=0.0,
        description="Abhyankar (1993), Bull. Astr. Soc. India 21, 475: sunrise at Ujjain on 7 Feb 3104 BC "
                    "(JD 587724.577), when the Moon and the five planets gathered within 25 degrees, proposed "
                    "as the observed origin of the Kali Yuga epoch. 2.5 turns, divided by angle."),
    CycleModel(
        name='Precession period at constant rate',
        anchor_date='3102 BC-02-18', anchor_time='00:00', anchor_longitude=UJJAIN_LONGITUDE,
        turns=None, years=2.5 * 25772.0, precession='constant', period=25772.0,
        description="Satya lasts one precession period of 25,772 years, at a constant rate, so the cycle is "
                    "64,430 years and 4:3:2:1 holds in years and in angle alike. Kali starts at midnight "
                    "17/18 Feb 3102 BC at Ujjain."),
)}
DEFAULT_PRESET = 'Kali 3102 BC, midnight at Ujjain'


def load_user_presets(path=USER_PRESETS_FILE) -> dict[str, CycleModel]:
    """Presets saved by the user (``{}`` if there is no file)."""
    path = Path(path)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    return {entry['name']: CycleModel.from_dict(entry) for entry in data.get('presets', [])}


def load_presets(path=USER_PRESETS_FILE) -> dict[str, CycleModel]:
    """Built-in presets, then the user's (which may replace a built-in one of the same name)."""
    return {**BUILTIN_PRESETS, **load_user_presets(path)}


def save_user_presets(presets: dict[str, CycleModel], path=USER_PRESETS_FILE) -> None:
    """Write the user's presets to ``path`` (JSON, readable and versionable)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {'presets': [model.to_dict() for model in presets.values()]}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def mean_rate(model: CycleModel, start: float, end: float) -> float:
    """Average precession rate (arcsec per year) between two years, in the model's precession."""
    if math.isclose(start, end):
        raise ValueError("empty interval")
    return (model.ayanamsa(end) - model.ayanamsa(start)) * 3600 / (end - start)
