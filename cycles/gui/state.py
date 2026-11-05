"""
Shared state of the GUI and the data behind it.

``CycleState`` holds what the user is looking at (the zoomed subcycle, the
selected one, the coloring...) and emits a signal when any of it changes;
every view listens to it, so they stay linked. ``LevelCache`` computes each
``Level`` once, on first use.

Addresses are tuples of digits (0 to 3); ``()`` is the whole cycle.
"""

import datetime
from math import factorial

import numpy as np
from PySide6.QtCore import QObject, Signal

from cycles.functions.division import (
    CMYK_KEYS, COLOR_KEYS, DEFAULT_COLOR_KEY, Level, compute_level, level_colors,
)
from cycles.functions.astro_dates import (
    date_time_to_julian_day, date_to_year, julian_day_to_year, parse_date, year_to_date,
)
from cycles.functions.division import find_lcoords
from cycles.functions.duration import count_digits
from cycles.functions.cycle_model import DEFAULT_PRESET, CycleModel, load_presets
from cycles.functions.timescale import AGE_NAMES, YUGA_NAMES, TimeMap

# Deepest level the GUI computes (4^8 = 65536 subcycles, a few seconds the first time)
MAX_DEPTH = 8
# Name sets for the four ages
NAME_SETS = {'Yugas': YUGA_NAMES, 'Ages': AGE_NAMES}
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def current_year() -> float:
    """The present moment as a decimal year (UT)."""
    now = datetime.datetime.now(datetime.UTC)
    return julian_day_to_year(date_time_to_julian_day(now.year, now.month, now.day, now.hour, now.minute,
                                                      now.second, calendar='gregorian'))


def parse_year(text: str) -> float:
    """
    Decimal year of ``text``: either a decimal year (astronomical numbering,
    e.g. ``-3101.5``) or a date such as ``2026-11-05`` or ``3102 BC-02-18``
    (see ``astro_dates.parse_date``; Julian calendar before 1582).
    """
    text = text.strip()
    try:
        return float(text.replace('−', '-'))
    except ValueError:
        return date_to_year(*parse_date(text))


def year_text(year: float) -> str:
    """Year with its era, rounded to whole years: ``'AD 2026'``, ``'3103 BC'``."""
    y = round(year)
    return f"AD {y}" if y > 0 else f"{1 - y} BC"


def date_text(year: float) -> str:
    """Calendar date of a decimal year: ``'18 Feb 3102 BC'`` (Julian calendar before 1582)."""
    y, m, d = year_to_date(year)
    era = f"AD {y}" if y > 0 else f"{1 - y} BC"
    return f"{int(d)} {MONTHS[m - 1]} {era}"


def datetime_text(year: float) -> str:
    """Calendar date and time (UT) of a decimal year: ``'18 Feb 3102 BC, 06:30 UT'``."""
    y, m, d = year_to_date(year)
    minutes = round((d % 1) * 1440)
    if minutes == 1440:            # rounding reached midnight: show the next day
        return datetime_text(year + 0.5 / 525960)
    era = f"AD {y}" if y > 0 else f"{1 - y} BC"
    return f"{int(d)} {MONTHS[m - 1]} {era}, {minutes // 60:02d}:{minutes % 60:02d} UT"


def time_text(year: float, span: float) -> str:
    """A year, as a date when ``span`` (years) is short enough to need one."""
    return date_text(year) if span < 200 else year_text(year)


def span_text(years: float) -> str:
    """Length of a span of years, in the most readable unit."""
    if years >= 2:
        return f"{years:,.1f} years"
    if years * 365.25 >= 2:
        return f"{years * 365.25:.1f} days"
    return f"{years * 8766:.1f} hours"


def tcoord(address: tuple) -> int:
    """Time-order index of ``address`` among the subcycles of its depth (0 for the whole cycle)."""
    index = 0
    for digit in address:
        index = 4 * index + digit
    return index


def address_of(index: int, depth: int) -> tuple:
    """Address of the subcycle with time-order index ``index`` at ``depth``."""
    digits = []
    for _ in range(depth):
        index, digit = divmod(index, 4)
        digits.append(digit)
    return tuple(reversed(digits))


def children_range(address: tuple, depth: int) -> range:
    """Indices, at ``depth``, of the subcycles inside ``address`` (a contiguous range)."""
    span = 4 ** (depth - len(address))
    first = tcoord(address) * span
    return range(first, first + span)


class LevelCache:
    """Levels and their colors, computed with the default parameters on first use."""

    def __init__(self):
        self._levels: dict[int, Level] = {}
        self._colors: dict[int, dict[str, np.ndarray]] = {}

    def has(self, depth: int) -> bool:
        return depth in self._levels

    def level(self, depth: int) -> Level:
        if depth not in self._levels:
            self._levels[depth] = compute_level(depth)
        return self._levels[depth]

    def colors(self, depth: int, key: str) -> np.ndarray:
        """RGB colors (N, 3) of the subcycles of ``depth`` for the color name ``key``."""
        if depth not in self._colors:
            self._colors[depth] = level_colors(self.level(depth))
        return self._colors[depth][key]


def equal_duration_indices(level: Level, index: int) -> np.ndarray:
    """Indices of the subcycles of ``level`` with the same duration as subcycle ``index``."""
    return np.flatnonzero(np.isclose(level.durations, level.durations[index], rtol=1e-9, atol=0.0))


def subcycle_info(cache: LevelCache, address: tuple) -> dict:
    """Everything the inspector shows about the subcycle ``address`` (not the whole cycle)."""
    depth = len(address)
    level = cache.level(depth)
    index = tcoord(address)
    composition = count_digits(np.array(address))
    equal = equal_duration_indices(level, index)
    compositions = {tuple(count_digits(level.lcoords[i])) for i in equal}
    same_composition = factorial(depth)
    for n in composition:
        same_composition //= factorial(n)
    return dict(
        address=address,
        depth=depth,
        index=index,
        count=4 ** depth,
        start=float(level.starts[index]),
        duration=float(level.durations[index]),
        end=float(min(1.0, level.starts[index] + level.durations[index])),
        composition=composition,
        equal_duration=len(equal),
        equal_compositions=len(compositions),
        same_composition=same_composition,
        dharma=float(level.dharmas[index]),
        purity=float(level.purities[index]),
        cmyk={key: level.cmyks[index, k] for k, key in enumerate(CMYK_KEYS)},
        rgb={key: cache.colors(depth, key)[index] for key in COLOR_KEYS},
    )


class CycleState(QObject):
    """
    What the views show: the zoomed subcycle (``focus``), the selected one,
    the coloring, how many levels the navigator draws, their spacing, the
    names of the ages, and whether subcycles of equal duration are highlighted.
    """

    focusChanged = Signal(tuple)
    selectionChanged = Signal(object)   # tuple, or None
    viewChanged = Signal()              # coloring, rows, spacing, names, highlight or cycle model
    modelChanged = Signal(object)       # the cycle model, or None (normalized time)
    presetsChanged = Signal()
    dateChanged = Signal(object)        # the marked date (decimal year), or None
    skyTimeChanged = Signal(object)     # the moment of the sky chart (decimal year), or None

    def __init__(self, cache: LevelCache | None = None, presets: dict[str, CycleModel] | None = None):
        super().__init__()
        self.cache = cache or LevelCache()
        self.presets = presets if presets is not None else load_presets()
        self.model: CycleModel | None = self.presets.get(DEFAULT_PRESET) or next(iter(self.presets.values()), None)
        self._time_map = self.model.time_map() if self.model is not None else None
        self.date: float | None = current_year()
        self.sky_time: float | None = None
        self.focus: tuple = ()
        self.selection: tuple | None = None
        self.color_key: str = DEFAULT_COLOR_KEY
        self.rows: int = 4
        self.spacing: str = 'time'      # 'time' (widths by duration) or 'index' (equal widths)
        self.names: tuple = YUGA_NAMES
        self.highlight_equal: bool = False

    # -- focus and selection

    def set_focus(self, address) -> None:
        address = tuple(address)[:MAX_DEPTH - 1]
        if address != self.focus:
            self.focus = address
            self.focusChanged.emit(address)

    def zoom_in(self, address) -> None:
        """Zoom into ``address`` (if it has subdivisions to show) and select it."""
        address = tuple(address)
        if len(address) < MAX_DEPTH:
            self.set_focus(address)
        self.select(address)

    def zoom_out(self) -> None:
        if self.focus:
            self.set_focus(self.focus[:-1])

    def select(self, address) -> None:
        address = tuple(address) if address is not None else None
        if address == ():
            address = None
        if address != self.selection:
            self.selection = address
            self.selectionChanged.emit(address)

    def reveal(self, address) -> None:
        """Select ``address``, moving the zoom (keeping its depth if possible) so that it is in view."""
        address = tuple(address)
        focus = self.focus
        if address[:len(focus)] != focus or len(address) < len(focus):
            focus = address[:min(len(focus), max(0, len(address) - 1))]
        if len(address) > len(focus) + self.rows:
            focus = address[:len(address) - self.rows]
        self.set_focus(focus)
        self.select(address)

    def visible_depths(self) -> range:
        """Depths of the rows below the focus that the navigator draws."""
        return range(len(self.focus) + 1, min(MAX_DEPTH, len(self.focus) + self.rows) + 1)

    # -- view options

    def _set(self, name: str, value) -> None:
        if getattr(self, name) != value:
            setattr(self, name, value)
            self.viewChanged.emit()

    def set_color_key(self, key: str) -> None:
        if key not in COLOR_KEYS:
            raise ValueError(f"unknown color key {key!r}")
        self._set('color_key', key)

    def set_rows(self, rows: int) -> None:
        self._set('rows', max(1, int(rows)))

    def set_spacing(self, spacing: str) -> None:
        if spacing not in ('time', 'index'):
            raise ValueError("spacing must be 'time' or 'index'")
        self._set('spacing', spacing)

    def set_names(self, names: tuple) -> None:
        self._set('names', tuple(names))

    def set_highlight_equal(self, on: bool) -> None:
        self._set('highlight_equal', bool(on))

    # -- physical time

    @property
    def time_map(self) -> TimeMap | None:
        """The time map of the cycle model, or ``None`` for normalized time."""
        return self._time_map

    def set_model(self, model: CycleModel | None) -> None:
        """Use ``model`` (``None``: normalized time). Raises ``ValueError`` if it cannot be solved."""
        if model == self.model:
            return
        time_map = model.time_map() if model is not None else None
        self.model, self._time_map = model, time_map
        self.modelChanged.emit(model)
        self.viewChanged.emit()
        self.dateChanged.emit(self.date)   # its place in the cycle depends on the model

    def reload_presets(self) -> None:
        self.presets = load_presets()
        self.presetsChanged.emit()

    def set_date(self, year: float | None) -> None:
        if year != self.date:
            self.date = year
            self.dateChanged.emit(year)

    def set_sky_time(self, year: float | None) -> None:
        if year != self.sky_time:
            self.sky_time = year
            self.skyTimeChanged.emit(year)

    def position(self, year: float | None) -> float | None:
        """Normalized time of ``year``, or ``None`` (no year, no map, or outside the cycle)."""
        time_map = self.time_map
        if year is None or time_map is None or not time_map.start <= year <= time_map.end:
            return None
        return time_map.to_normalized(year)

    def date_position(self) -> float | None:
        """Normalized time of the marked date (see ``position``)."""
        return self.position(self.date)

    def physical_interval(self, address: tuple) -> tuple[float, float] | None:
        """Start and end of ``address`` in the current time map (``None`` for normalized time)."""
        time_map = self.time_map
        if time_map is None:
            return None
        if not address:
            return time_map.start, time_map.end
        return time_map.interval(address)

    def subcycle_of_date(self, depth: int) -> tuple | None:
        """Address of the subcycle of ``depth`` containing the marked date (see ``date_position``)."""
        u = self.date_position()
        if u is None:
            return None
        return tuple(int(d) for d in find_lcoords(min(u, 1 - 1e-15), depth))

    def go_to_date(self, year: float, depth: int) -> None:
        """Mark ``year`` and select the subcycle of ``depth`` containing it."""
        self.set_date(year)
        address = self.subcycle_of_date(depth)
        if address is not None:
            self.reveal(address)
