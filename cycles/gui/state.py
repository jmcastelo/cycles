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
    CMYK_KEYS, COLOR_KEYS, MEASURE_COLOR_KEYS, MODEL_COLOR_KEYS, SKY_COLOR_KEYS, STATE_COLOR_KEYS, DEFAULT_BASES, DEFAULT_COLOR_KEY, DEFAULT_SCALES, TETRAHEDRON_COLORS, Level, compute_level,
    level_colors,
)
from cycles.functions.color import DEFAULT_COLOR_MAPS, color_parameter_problems
from cycles.functions.division import COLOR_PARAMETER_EFFECTS
from cycles.functions.astro_dates import (
    date_time_to_julian_day, date_to_year, julian_day_to_year, parse_date, year_to_date,
)
from cycles.functions.division import find_lcoords
from cycles.functions.duration import count_digits
from cycles.functions.cycle_model import DEFAULT_PRESET, CycleModel, load_presets
from cycles.functions.timescale import AGE_NAMES, YUGA_NAMES, TimeMap

# Deepest level the GUI computes (4^9 = 262,144 subcycles, a quarter of a second the first time)
MAX_DEPTH = 9
# Name sets for the four ages
NAME_SETS = {'Yugas': YUGA_NAMES, 'Ages': AGE_NAMES}
# One color per role, in the navigator and in every plot
SELECTION_COLOR = '#1f77b4'     # the selected subcycle (and, thinner, its parents): blue
MOMENT_COLOR = '#ff7f0e'        # the moment of the sky chart: its cursor and tag, and the subcycles with Follow
DATE_COLOR = '#d62728'          # the marked date: its cursor and tag
# How subcycles are labelled in the navigator
LABEL_MODES = {'names': 'Names', 'dots': 'Dots (4, 3, 2, 1)', 'both': 'Names and dots', 'none': 'None'}
NO_MODEL_GRAY = 0.85     # the colorings of the cycle model without one
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


# -- the navigator's coordinates: normalized time (widths by duration) or the index position (equal widths)

_SHARES = (0.4, 0.3, 0.2, 0.1)
_STARTS = (0.0, 0.4, 0.7, 0.9)
_LEVELS = 40                     # enough for float precision in both coordinates


def _age_at(x: float) -> int:
    return 3 if x >= 0.9 else 2 if x >= 0.7 else 1 if x >= 0.4 else 0


def index_to_time(v: float) -> float:
    """The normalized time of the index position ``v`` (Σ a_i 4^−i): the same point of the cycle."""
    x, u, scale = min(max(float(v), 0.0), 1.0), 0.0, 1.0
    for _ in range(_LEVELS):
        k = min(3, int(x * 4))
        x = x * 4 - k
        u += _STARTS[k] * scale
        scale *= _SHARES[k]
    return u + x * scale


def time_to_index(u: float) -> float:
    """The index position of the normalized time ``u`` (the inverse of ``index_to_time``)."""
    x, v, scale = min(max(float(u), 0.0), 1.0), 0.0, 1.0
    for _ in range(_LEVELS):
        k = _age_at(x)
        x = min(max((x - _STARTS[k]) / _SHARES[k], 0.0), 1.0)
        scale /= 4
        v += k * scale
    return v + x * scale


def coordinate_digits(x: float, spacing: str, depth: int) -> tuple:
    """The address, ``depth`` digits long, of the subcycle at the coordinate ``x`` (in ``spacing``)."""
    x = min(max(float(x), 0.0), 1.0)
    digits = []
    for _ in range(depth):
        if spacing == 'time':
            k = _age_at(x)
            x = min(max((x - _STARTS[k]) / _SHARES[k], 0.0), 1.0)
        else:
            k = min(3, int(x * 4))
            x = x * 4 - k
        digits.append(k)
    return tuple(digits)


def coordinate_extent(address: tuple, spacing: str) -> tuple[float, float]:
    """Where the subcycle ``address`` starts and ends, in the coordinate of ``spacing``."""
    start, scale = 0.0, 1.0
    for k in address:
        if spacing == 'time':
            start += _STARTS[k] * scale
            scale *= _SHARES[k]
        else:
            scale /= 4
            start += k * scale
    return start, start + scale


def children_range(address: tuple, depth: int) -> range:
    """Indices, at ``depth``, of the subcycles inside ``address`` (a contiguous range)."""
    span = 4 ** (depth - len(address))
    first = tcoord(address) * span
    return range(first, first + span)


class LevelCache:
    """Levels and their colors, computed with the given parameters (see ``compute_level``) on first use."""

    def __init__(self, bases=DEFAULT_BASES, scales=DEFAULT_SCALES, colors=TETRAHEDRON_COLORS,
                 maps=DEFAULT_COLOR_MAPS):
        self.bases, self.scales = list(bases), list(scales)
        self.vertices = np.asarray(colors, dtype=float)    # of the tetrahedron coloring
        self.maps = tuple(maps)                             # color maps of the measures: (sequential, diverging)
        self._levels: dict[int, Level] = {}
        self._colors: dict[int, dict[str, np.ndarray]] = {}
        self._measures: dict[int, dict[str, np.ndarray]] = {}

    def has(self, depth: int) -> bool:
        return depth in self._levels

    def level(self, depth: int) -> Level:
        if depth not in self._levels:
            self._levels[depth] = compute_level(depth, self.bases, self.scales, self.vertices)
        return self._levels[depth]

    def colors(self, depth: int, key: str) -> np.ndarray:
        """
        RGB colors (N, 3) of the subcycles of ``depth`` for the coloring ``key`` (those of ``LEVEL_COLOR_KEYS``
        and ``MEASURE_COLOR_KEYS``; the cycle model's are in ``CycleState.colors``).
        """
        if depth not in self._colors:
            self._colors[depth] = level_colors(self.level(depth), self.maps)
        colors = self._colors[depth]
        if key not in colors and key in MEASURE_COLOR_KEYS:
            from cycles.functions.color import measure_colors
            colors[key] = measure_colors(self.measure(depth, key), key, self.maps)[0]
        return colors[key]

    def set_maps(self, maps) -> None:
        """Use other color maps for the measures: only their colors are made again, not the levels."""
        self.maps = tuple(maps)
        for colors in self._colors.values():
            for key in MEASURE_COLOR_KEYS:
                colors.pop(key, None)

    def measure(self, depth: int, key: str) -> np.ndarray:
        """Values (N,) of the measure ``key`` of ``measure.ADDRESS_MEASURES`` for the subcycles of ``depth``."""
        if depth not in self._measures:
            from cycles.functions.measure import address_measures
            level = self.level(depth)
            self._measures[depth] = address_measures(level.lcoords, level.durations, level.dharmas,
                                                     level.purities, self.bases)
        return self._measures[depth][key]


def equal_duration_indices(level: Level, index: int) -> np.ndarray:
    """Indices of the subcycles of ``level`` with the same duration as subcycle ``index``."""
    return np.flatnonzero(np.isclose(level.durations, level.durations[index], rtol=1e-9, atol=0.0))


def same_composition_indices(level: Level, address: tuple) -> np.ndarray:
    """Indices of the subcycles of ``level`` whose addresses are digit permutations of ``address``."""
    lcoords = np.asarray(level.lcoords)
    counts = np.stack([(lcoords == k).sum(axis=1) for k in range(4)], axis=1)
    return np.flatnonzero(np.all(counts == count_digits(np.array(address)), axis=1))


def measure_breakdown(level: Level, address: tuple, bases) -> dict:
    """
    How the levels of ``address`` make up its dharma and purity (``measure.py``):

    * dharma = Σ_k w_k v_k, with v_k = (4 - a_k) / 4 the virtue of the age of
      digit k (1, 3/4, 1/2, 1/4) and w_k the weights base⁻ᵏ of ``bases[1]``,
      normalized to add up to 1;
    * purity = the largest minus the smallest share of an age, the share of
      an age being the sum of the weights (of ``bases[2]``) of its digits.

    Also the range of both over the orderings of its ages (the subcycles of
    the same composition): equal weights (base 1) would make it a single value.
    """
    from cycles.functions.division import weights
    digits = np.array(address)
    depth = len(digits)
    dharma_weights = weights(bases[1], depth)
    dharma_weights = dharma_weights / dharma_weights.sum()
    virtues = (4 - digits) / 4
    purity_weights = weights(bases[2], depth)
    purity_weights = purity_weights / purity_weights.sum()
    shares = np.array([purity_weights[digits == k].sum() for k in range(4)])
    same = same_composition_indices(level, address)
    return dict(
        dharma_weights=dharma_weights, virtues=virtues, dharma_parts=dharma_weights * virtues,
        dharma=float(np.dot(dharma_weights, virtues)),
        purity_weights=purity_weights, shares=shares, purity=float(shares.max() - shares.min()),
        orderings=len(same),
        dharma_range=(float(level.dharmas[same].min()), float(level.dharmas[same].max())),
        purity_range=(float(level.purities[same].min()), float(level.purities[same].max())),
    )


def permuted_address(address: tuple, sigma: tuple, first: int) -> tuple:
    """``address`` with its digits from position ``first`` on permuted by ``σ`` (``a ∘ σ``)."""
    tail = address[first:]
    return tuple(address[:first]) + tuple(tail[i] for i in sigma)


PERMUTATION_COLOR = '#9467bd'   # the image of the selection under σ
BOOKMARK_COLOR = '#2ca02c'      # bookmarked subcycles
EVENT_COLOR = '#e377c2'         # planetary events shown in the navigator (Events panel)

# What the views highlight around the selection
HIGHLIGHTS = {
    'none': 'No highlight',
    'duration': 'Equal durations',
    'composition': 'Same composition',
    'orbit': '⟨σ⟩ orbit',
    'query': 'Matching the query',
}


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
        composition_rank=int(np.searchsorted(same_composition_indices(level, address), index)) + 1,
        dharma=float(level.dharmas[index]),
        purity=float(level.purities[index]),
        cmyk={key: level.cmyks[index, k] for k, key in enumerate(CMYK_KEYS)},
        rgb={key: cache.colors(depth, key)[index] for key in COLOR_KEYS if key not in STATE_COLOR_KEYS},
    )


class CycleState(QObject):
    """
    What the views show: the zoomed subcycle (``focus``), the selected one,
    the coloring, how many levels the navigator draws, their spacing, the
    names of the ages, and whether subcycles of equal duration are highlighted.
    """

    focusChanged = Signal(tuple)
    windowChanged = Signal(bool)        # the part of the cycle the navigator shows (True: glide to it)
    selectionChanged = Signal(object)   # tuple, or None
    viewChanged = Signal()              # coloring, rows, spacing, names, highlight or cycle model
    modelChanged = Signal(object)       # the cycle model, or None (normalized time)
    presetsChanged = Signal()
    colorParametersChanged = Signal(frozenset)   # names of the colorings that changed (COLOR_PARAMETER_EFFECTS)
    dateChanged = Signal(object)        # the marked date (decimal year), or None
    skyTimeChanged = Signal(object)     # the moment of the sky chart (decimal year), or None
    permutationChanged = Signal()       # the σ of the Permutations panel
    bookmarksChanged = Signal()
    notesChanged = Signal()             # the notes of the session
    eventsChanged = Signal()            # the planetary events shown in the navigator
    busy = Signal(str)                  # a message while something slow is computed ('' when done)

    def __init__(self, cache: LevelCache | None = None, presets: dict[str, CycleModel] | None = None):
        super().__init__()
        self.cache = cache or LevelCache()
        self.presets = presets if presets is not None else load_presets()
        self.model: CycleModel | None = self.presets.get(DEFAULT_PRESET) or next(iter(self.presets.values()), None)
        self._time_map = self.model.time_map() if self.model is not None else None
        self.date: float | None = current_year()
        self.sky_time: float | None = None
        self.follow: bool = True        # the plots highlight their subcycle containing the sky moment
        self.focus: tuple = ()          # the smallest subcycle that contains the window
        self.window: tuple = (0.0, 1.0)  # the part of the cycle in view, in the coordinate of the spacing
        self.selection: tuple | None = None
        self.color_key: str = DEFAULT_COLOR_KEY
        self._visible_depths = range(1, 6)  # the depths of the rows in view (the navigator says which)
        self.spacing: str = 'time'      # 'time' (widths by duration) or 'index' (equal widths)
        self.names: tuple = YUGA_NAMES
        self.highlight: str = 'none'    # a key of HIGHLIGHTS
        self.compare_criteria: bool = False   # the navigator shows where the other division criterion puts boundaries
        self._criteria: dict = {}       # (model, depth) -> boundaries by criterion; measures and colors of the model
        self.ephemeris = None           # (tables, folder) of the Sky panel, for the measures and colors of the sky
        self.query: str = ''            # a condition on the subcycles (functions.query), for the highlight 'query'
        self.query_problem: str = ''    # why the query could not be evaluated at some depth ('' if it could)
        self._query_cache: dict = {}
        self._sky: dict = {}            # what is computed with the ephemeris
        self.permutation: tuple | None = None   # (σ, first permuted position) of the Permutations panel
        self.borders: bool = False
        self.labels: str = 'none'       # 'names', 'dots' (4, 3, 2, 1 for the four ages), 'both' or 'none'
        self.bookmarks: list[dict] = []    # {'address': tuple, 'label': str, 'note': str}
        self.notes: str = ''
        self.event_marks: tuple | None = None   # (years in UT, label) of the Events panel, or None

    # -- focus and selection

    def set_focus(self, address, animate: bool = True) -> None:
        """Show the subcycle ``address`` filling the navigator (and so zoom into it)."""
        address = tuple(address)[:MAX_DEPTH - 1]
        self.set_window(*coordinate_extent(address, self.spacing), animate=animate, focus=address)

    def min_width_at(self, x: float) -> float:
        """The narrowest window around the coordinate ``x``: the deepest subcycle a zoom can be (depth 8) there."""
        return float(np.subtract(*coordinate_extent(coordinate_digits(x, self.spacing, MAX_DEPTH - 1),
                                                    self.spacing)[::-1]))

    def set_window(self, a: float, b: float, animate: bool = False, focus: tuple | None = None) -> None:
        """
        Show the part (``a``, ``b``) of the cycle, in the coordinate of the spacing (normalized time, or the index
        position with equal widths): kept inside the cycle and no narrower than ``min_width_at``. The focus becomes
        the smallest subcycle that contains it (or ``focus``, the subcycle that the window is exactly).
        """
        a, b = float(a), float(b)
        width = min(1.0, max(b - a, self.min_width_at((a + b) / 2)))
        centre = (a + b) / 2
        a = min(max(centre - width / 2, 0.0), 1.0 - width)
        window = (a, a + width)
        if focus is None:
            tiny = width * 1e-9
            first = coordinate_digits(a + tiny, self.spacing, MAX_DEPTH - 1)
            last = coordinate_digits(a + width - tiny, self.spacing, MAX_DEPTH - 1)
            common = 0
            while common < len(first) and first[common] == last[common]:
                common += 1
            focus = first[:common]
        if window != self.window or animate:
            self.window = window
            self.windowChanged.emit(animate)
        if focus != self.focus:
            self.focus = focus
            self.focusChanged.emit(focus)

    def window_time(self) -> tuple[float, float]:
        """The window in normalized time."""
        a, b = self.window
        return (a, b) if self.spacing == 'time' else (index_to_time(a), index_to_time(b))

    def set_window_time(self, a: float, b: float) -> None:
        """Show the part (``a``, ``b``) of the cycle given in normalized time."""
        if self.spacing == 'time':
            self.set_window(a, b)
        else:
            self.set_window(time_to_index(a), time_to_index(b))

    def zoom_in(self, address) -> None:
        """Zoom into ``address`` (if it has subdivisions to show) and select it."""
        address = tuple(address)
        if len(address) < MAX_DEPTH:
            self.set_focus(address)
        self.select(address)

    def zoom_out(self) -> None:
        """Show the subcycle above the zoom (or the whole cycle)."""
        self.set_focus(self.focus[:-1] if self.focus else ())

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
        # the navigator shows the levels below the zoom, so the zoom must be above the address
        if address[:len(focus)] != focus or len(address) <= len(focus):
            focus = address[:min(len(focus), max(0, len(address) - 1))]
        if focus != self.focus:
            self.set_focus(focus)
        else:
            # the same zoom: move the window over the address if it is out of view
            a, b = self.window
            start, end = coordinate_extent(address, self.spacing)
            if end <= a or start >= b:
                width = b - a
                centre = (start + end) / 2
                self.set_window(centre - width / 2, centre + width / 2, animate=True)
        self.select(address)

    def visible_depths(self) -> range:
        """Depths of the rows that the navigator has in view."""
        return self._visible_depths

    def set_visible_depths(self, depths: range) -> None:
        """What the navigator has in view (no signal: it is what follows from the zoom and the scrolling)."""
        self._visible_depths = depths

    # -- view options

    def _set(self, name: str, value) -> None:
        if getattr(self, name) != value:
            setattr(self, name, value)
            self.viewChanged.emit()

    def set_color_key(self, key: str) -> None:
        if key not in COLOR_KEYS:
            raise ValueError(f"unknown color key {key!r}")
        self._set('color_key', key)

    def set_spacing(self, spacing: str) -> None:
        if spacing not in ('time', 'index'):
            raise ValueError("spacing must be 'time' or 'index'")
        if spacing == self.spacing:
            return
        # the same part of the cycle, in the other coordinate
        convert = time_to_index if spacing == 'index' else index_to_time
        a, b = self.window
        self.window = (convert(a), convert(b))
        self._set('spacing', spacing)
        self.windowChanged.emit(False)

    def set_names(self, names: tuple) -> None:
        self._set('names', tuple(names))

    def set_highlight(self, mode: str) -> None:
        if mode not in HIGHLIGHTS:
            raise ValueError(f"unknown highlight {mode!r}")
        self._set('highlight', mode)

    # -- the query

    def set_query(self, text: str) -> None:
        """
        Use the condition ``text`` (``functions.query``; '' for none) for the highlight 'query'. ``QueryError`` if it
        cannot be read or uses unknown names.
        """
        from cycles.functions.measure import MEASURES
        from cycles.functions.query import OTHER_NAMES, QueryError, age_names, names_in, parse
        text = ' '.join(text.split())
        if text:
            unknown = names_in(parse(text)) - set(MEASURES) - set(OTHER_NAMES) - set(age_names(MAX_DEPTH))
            if unknown:
                raise QueryError(f"unknown name{'s' if len(unknown) > 1 else ''} in the query: "
                                 f"{', '.join(sorted(unknown))}")
        if text != self.query:
            self.query = text
            self.viewChanged.emit()

    def query_matches(self, depth: int) -> np.ndarray | None:
        """
        Which subcycles of ``depth`` satisfy the query (a boolean array), or None without one. If something it
        needs is missing (a cycle model, the ephemeris), none match and ``query_problem`` says why.
        """
        if not self.query or depth < 1:
            return None
        key = (self.query, depth, self.color_parameters, self.model,
               None if self.ephemeris is None else id(self.ephemeris[0]))
        if key not in self._query_cache:
            if len(self._query_cache) > 32:
                self._query_cache.clear()
            self._query_cache[key] = (self._evaluate_query(depth), self.query_problem)
        matches, self.query_problem = self._query_cache[key]
        return matches

    def _evaluate_query(self, depth: int) -> np.ndarray:
        from cycles.functions.cycle_analysis import dense_years
        from cycles.functions.measure import MEASURES
        from cycles.functions.query import QueryError, evaluate, names_in, parse
        tree = parse(self.query)
        level = self.cache.level(depth)
        values = {}
        self.query_problem = ''
        try:
            for name in names_in(tree):
                if name in MEASURES:
                    values[name] = self.measure_values(depth, name)
                    if values[name] is None:
                        raise QueryError(f"{name} {self.missing_for(name)}")
                elif name in ('year', 'years'):
                    if self.time_map is None:
                        raise QueryError(f"{name} needs a cycle model")
                    starts = self._start_years(depth)
                    values['year'] = starts
                    values['years'] = dense_years(self.time_map, level.starts + level.durations) - starts
                elif name == 'duration':
                    values[name] = level.durations
                elif name == 'start':
                    values[name] = level.starts
                elif name == 'index':
                    values[name] = np.arange(len(level.starts))
                elif name == 'depth':
                    values[name] = depth
                elif name in ('first', 'last'):
                    values[name] = level.lcoords[:, 0 if name == 'first' else -1]
                else:                                       # a1, a2, …: no such digit above the depth matches nothing
                    k = int(name[1:])
                    values[name] = level.lcoords[:, k - 1].astype(float) if k <= depth else np.full(len(level.starts),
                                                                                                    np.nan)
            return evaluate(tree, values, level.lcoords)
        except QueryError as error:
            self.query_problem = str(error)
            return np.zeros(len(level.starts), dtype=bool)

    def highlighted(self, depth: int) -> np.ndarray | None:
        """
        Indices of the subcycles of ``depth`` to keep bright with the current highlight, or None for none there:
        those matching the query (at every depth), or the class of the selection (at its depth).
        """
        if self.highlight == 'query':
            matches = self.query_matches(depth)
            return None if matches is None else np.flatnonzero(matches)
        selection = self.selection
        if selection is None or len(selection) != depth:
            return None
        return self.highlight_indices(selection)

    def set_compare_criteria(self, on: bool) -> None:
        self._set('compare_criteria', bool(on))

    def criteria_boundaries(self, depth: int) -> dict | None:
        """
        Where the two criteria for dividing the cycle put the starts of the
        subcycles of ``depth`` (and the end), as years and as normalized time
        of the current model (the navigator's coordinate): ``'angle'``, 4:3:2:1
        of the precession arc, and ``'time'``, 4:3:2:1 of the years. One of them
        is the model's own division (for the hybrid one, neither below the ages).
        None without a cycle model.
        """
        model, time_map = self.model, self.time_map
        if model is None or time_map is None:
            return None
        key = (model, depth)
        if key not in self._criteria:
            from cycles.functions.cycle_analysis import boundary_fractions
            fractions = boundary_fractions(depth)
            if (model, 'angle') not in self._criteria:
                # the arc of this model's own span, divided 4:3:2:1
                from cycles.plotting.equinoctial_precession import precession_time_map
                solution = model.solve()
                self._criteria[(model, 'angle')] = precession_time_map(solution['start'], solution['turns'],
                                                                       **model._precession_options())
            years = {
                'angle': np.asarray(self._criteria[(model, 'angle')].to_physical(fractions), dtype=float),
                'time': time_map.start + fractions * (time_map.end - time_map.start),
            }
            self._criteria[key] = {name: dict(years=y, normalized=np.asarray(time_map.to_normalized(y), dtype=float))
                                   for name, y in years.items()}
        return self._criteria[key]

    def colors(self, depth: int, key: str) -> np.ndarray:
        """
        RGB colors (N, 3) of the subcycles of ``depth`` for the coloring ``key``: those of the cycle model
        (``MODEL_COLOR_KEYS``: the angular density, the sign and the element of the vernal point at each start)
        and of the sky (``SKY_COLOR_KEYS``: the gathering of the planets and the trigon of the great conjunctions
        at each start) here, light gray without what they need; the others from the level cache.
        """
        if key not in STATE_COLOR_KEYS:
            return self.cache.colors(depth, key)
        if not self.can_color(key):
            return np.full((4 ** depth, 3), NO_MODEL_GRAY)
        cached = ('colors', self.model, depth, key)          # apart from the measure values of the same name
        store = self._sky if key in SKY_COLOR_KEYS else self._criteria
        if cached not in store:
            from cycles.functions.color import ELEMENT_COLORS, measure_colors, vernal_colors
            if key in ('density', 'gathering'):
                colors = measure_colors(self.measure_values(depth, key), key, self.cache.maps)[0]
            elif key.startswith('vernal'):
                from cycles.functions.cycle_analysis import dense_ayanamsa
                colors = vernal_colors(dense_ayanamsa(self.model, self._start_years(depth)), key.split('_')[1])
            else:
                from cycles.functions.events import trigon_in_force
                elements = trigon_in_force(self.great_conjunctions(), key.split('_')[1], self._tdb_starts(depth))
                colors = np.where(elements[:, None] >= 0, ELEMENT_COLORS[np.clip(elements, 0, 3)], NO_MODEL_GRAY)
            store[cached] = colors
        return store[cached]

    def can_color(self, key: str) -> bool:
        """Whether the coloring (or measure) ``key`` can be computed now: with a model, and the ephemeris for the sky."""
        from cycles.functions.measure import MEASURES
        sky = key in SKY_COLOR_KEYS or MEASURES.get(key, {}).get('parameter') == 'sky'
        model = sky or key in MODEL_COLOR_KEYS or MEASURES.get(key, {}).get('parameter') == 'model'
        if model and (self.model is None or self.time_map is None):
            return False
        return not sky or self.ephemeris is not None

    def missing_for(self, key: str) -> str:
        """What the coloring (or measure) ``key`` still needs, as a phrase ('' if nothing)."""
        from cycles.functions.measure import MEASURES
        if self.can_color(key):
            return ''
        sky = key in SKY_COLOR_KEYS or MEASURES.get(key, {}).get('parameter') == 'sky'
        return 'needs a cycle model and the ephemeris' if sky else 'needs a cycle model'

    def context_of(self, key: str) -> tuple:
        """
        What the coloring (or measure) ``key`` depends on beyond the color parameters, for the panels to know when
        to draw it again: the cycle model, and the ephemeris for the sky; () for the others.
        """
        from cycles.functions.measure import MEASURES
        sky = key in SKY_COLOR_KEYS or MEASURES.get(key, {}).get('parameter') == 'sky'
        if sky:
            return (self.model, None if self.ephemeris is None else id(self.ephemeris[0]))
        if key in MODEL_COLOR_KEYS or MEASURES.get(key, {}).get('parameter') == 'model':
            return (self.model,)
        return ()

    # -- the sky: the ephemeris of the Sky panel

    def set_ephemeris(self, tables, folder=None) -> None:
        """Use the ephemeris ``tables`` (from ``folder``) for the measures and colors of the sky; None: none."""
        value = None if not tables else (tables, folder)
        if value is None and self.ephemeris is None:
            return
        self.ephemeris = value
        self._sky = {}
        self.viewChanged.emit()

    def _start_years(self, depth: int) -> np.ndarray:
        """Years (UT) of the starts of the subcycles of ``depth`` (interpolated for large levels: ``dense_years``)."""
        cached = ('years', self.model, depth)
        if cached not in self._criteria:
            from cycles.functions.cycle_analysis import dense_years
            self._criteria[cached] = dense_years(self.time_map, self.cache.level(depth).starts)
        return self._criteria[cached]

    @staticmethod
    def _to_tdb(years) -> np.ndarray:
        """UT years to TDB: ΔT changes slowly, so a grid is converted and interpolated."""
        from cycles.functions.events import tdb_years
        years = np.atleast_1d(np.asarray(years, dtype=float))
        if len(years) < 50:
            return tdb_years(years)
        grid = np.linspace(years.min() - 1, years.max() + 1, 2001)
        return years + np.interp(years, grid, tdb_years(grid) - grid)

    def _tdb_starts(self, depth: int) -> np.ndarray:
        """TDB years of the starts of the subcycles of ``depth`` (the model's years are UT)."""
        cached = ('tdb', self.model, depth)
        if cached not in self._sky:
            self._sky[cached] = self._to_tdb(self._start_years(depth))
        return self._sky[cached]

    # -- one subcycle (the inspector): without computing its whole level when that is slow

    def subcycle_measure(self, address: tuple, key: str) -> float | None:
        """
        The measure ``key`` of the subcycle ``address`` (None if it cannot be computed now). Those of the sky are
        computed for this subcycle alone unless its level is already done.
        """
        from cycles.functions.measure import MEASURES
        depth, index = len(address), tcoord(address)
        if MEASURES[key]['parameter'] != 'sky' or ('measure', self.model, depth, key) in self._sky:
            values = self.measure_values(depth, key)
            return None if values is None else float(values[index])
        if not self.can_color(key):
            return None
        from cycles.functions.events import CLASSICAL, around_point
        start = self.time_map.to_physical(self.cache.level(depth).starts[index])
        spread = around_point(self.ephemeris[0], self._to_tdb([start]), CLASSICAL)['spread'][0]
        return float(1 - spread / 360.0)

    def subcycle_color(self, address: tuple, key: str) -> np.ndarray | None:
        """
        The color (RGB) of the subcycle ``address`` in the coloring ``key`` (None if it cannot be computed now).
        Those of the sky are computed for this subcycle alone unless its level is already done.
        """
        depth, index = len(address), tcoord(address)
        if key not in SKY_COLOR_KEYS or ('colors', self.model, depth, key) in self._sky:
            return None if key in STATE_COLOR_KEYS and not self.can_color(key) else self.colors(depth, key)[index]
        if not self.can_color(key):
            return None
        from cycles.functions.color import ELEMENT_COLORS, measure_colors
        if key == 'gathering':
            return measure_colors(np.array([self.subcycle_measure(address, key)]), key, self.cache.maps)[0][0]
        from cycles.functions.events import trigon_in_force
        start = self.time_map.to_physical(self.cache.level(depth).starts[index])
        element = int(trigon_in_force(self.great_conjunctions(), key.split('_')[1], self._to_tdb([start]))[0])
        return ELEMENT_COLORS[element] if element >= 0 else np.full(3, NO_MODEL_GRAY)

    def great_conjunctions(self) -> dict:
        """The Jupiter–Saturn conjunctions over the whole ephemeris (as the Events panel's map; kept on disk)."""
        if 'great' not in self._sky:
            from cycles.functions.events import cached_conjunctions, table_span
            tables, folder = self.ephemeris
            start, end = table_span(tables)
            self.busy.emit('Computing the Jupiter–Saturn conjunctions over the whole ephemeris (once; then kept '
                           'on disk)…')
            try:
                self._sky['great'] = cached_conjunctions(tables, folder, 'jupiter', 'saturn', start + 1, end - 1)
            finally:
                self.busy.emit('')
        return self._sky['great']

    def measure_values(self, depth: int, key: str) -> np.ndarray | None:
        """
        Values (N,) of the measure ``key`` (``measure.MEASURES``) for the subcycles of ``depth``; None for a measure
        of the cycle model when there is none, or of the sky without the ephemeris.
        """
        from cycles.functions.measure import MEASURES
        if MEASURES[key]['parameter'] not in ('model', 'sky'):
            return self.cache.measure(depth, key)
        if not self.can_color(key):
            return None
        if MEASURES[key]['parameter'] == 'sky':
            cached = ('measure', self.model, depth, key)
            if cached not in self._sky:
                from cycles.functions.events import CLASSICAL, around_point
                spread = around_point(self.ephemeris[0], self._tdb_starts(depth), CLASSICAL)['spread']
                self._sky[cached] = 1 - spread / 360.0
            return self._sky[cached]
        cached = (self.model, depth, key)
        if cached not in self._criteria:
            from cycles.functions.cycle_analysis import angular_density
            level = self.cache.level(depth)
            self._criteria[cached] = angular_density(self.model, level.starts, level.durations, self.time_map)
        return self._criteria[cached]

    def set_permutation(self, sigma: tuple | None, first: int = 0) -> None:
        value = None if sigma is None else (tuple(sigma), int(first))
        if value != self.permutation:
            self.permutation = value
            self.permutationChanged.emit()

    def permutation_orbit(self, address: tuple) -> list[tuple] | None:
        """
        The orbit of ``address`` under the powers of the panel's σ (starting
        with ``address``), or None if σ does not act on addresses of its depth.
        """
        if self.permutation is None or address is None:
            return None
        sigma, first = self.permutation
        if len(address) != first + len(sigma):
            return None
        orbit = [tuple(address)]
        while True:
            image = permuted_address(orbit[-1], sigma, first)
            if image == orbit[0]:
                return orbit
            orbit.append(image)

    def highlight_indices(self, address: tuple | None) -> np.ndarray | None:
        """
        Indices, in the level of ``address``, of the subcycles to keep bright
        with the current highlight; None if nothing is highlighted.
        """
        if address is None or not address or self.highlight == 'none':
            return None
        if self.highlight == 'query':
            return self.highlighted(len(address))
        level = self.cache.level(len(address))
        if self.highlight == 'duration':
            return equal_duration_indices(level, tcoord(address))
        if self.highlight == 'composition':
            return same_composition_indices(level, address)
        orbit = self.permutation_orbit(address)
        return None if orbit is None else np.array(sorted(tcoord(a) for a in orbit))

    def highlight_links(self, address: tuple | None) -> tuple[str, np.ndarray] | None:
        """
        How the highlighted subcycles around ``address`` are joined in the plots, as ``(kind, pairs)`` with
        ``pairs`` an (n, 2) array of indices in the level of ``address``:

        * ``'orbit'`` (highlight ⟨σ⟩ orbit): the steps of the orbit in order, ``address`` → its image under σ →
          … → back to ``address``;
        * ``'swaps'`` (highlight Same composition): the orderings of its ages that differ by swapping two
          neighbouring digits, each pair once.

        None for the other highlights, or when there is nothing to join.
        """
        if address is None or not address:
            return None
        if self.highlight == 'orbit':
            orbit = self.permutation_orbit(address)
            if orbit is None or len(orbit) < 2:
                return None
            steps = [tcoord(a) for a in orbit]
            return 'orbit', np.array([steps, steps[1:] + steps[:1]]).T
        if self.highlight == 'composition':
            level = self.cache.level(len(address))
            lcoords = np.asarray(level.lcoords)[same_composition_indices(level, address)]
            powers = 4 ** np.arange(lcoords.shape[1] - 1, -1, -1)
            pairs = []
            for k in range(lcoords.shape[1] - 1):
                rising = lcoords[:, k] < lcoords[:, k + 1]          # each swap once
                if rising.any():
                    swapped = lcoords[rising].copy()
                    swapped[:, [k, k + 1]] = swapped[:, [k + 1, k]]
                    pairs.append(np.stack([lcoords[rising] @ powers, swapped @ powers], axis=1))
            return ('swaps', np.concatenate(pairs)) if pairs else None
        return None

    @property
    def color_parameters(self) -> tuple:
        """
        ``(bases, scales, tetrahedron colors, color maps)`` of the colorings and measures, as tuples; the maps
        are those of the measures, ``(sequential, diverging)``.
        """
        return (tuple(self.cache.bases), tuple(self.cache.scales),
                tuple(tuple(float(c) for c in row) for row in self.cache.vertices), tuple(self.cache.maps))

    def set_color_parameters(self, bases, scales, colors=None, maps=None) -> None:
        """
        Use new bases, scales, tetrahedron vertex colors and color maps of the
        measures (the current ones if not given) for the colorings and measures.
        ``ValueError`` if they could give repeated colors, or the maps are not
        known (see ``color_parameter_problems``). Other maps alone recolor the
        measures without computing the levels again.
        """
        colors = self.cache.vertices if colors is None else np.asarray(colors, dtype=float)
        maps = self.cache.maps if maps is None else tuple(maps)
        problems = color_parameter_problems(bases, scales, colors, maps)
        if problems:
            raise ValueError('; '.join(problems))
        new = (tuple(bases), tuple(scales), tuple(tuple(float(c) for c in row) for row in colors), tuple(maps))
        old = self.color_parameters
        if new == old:
            return
        changed = self._named_parameters(*old).items() ^ self._named_parameters(*new).items()
        affected = frozenset(key for name, _ in changed for key in COLOR_PARAMETER_EFFECTS[name])
        if new[:3] == old[:3]:
            self.cache.set_maps(maps)
        else:
            self.cache = LevelCache(bases, scales, colors, maps)     # levels are recomputed when next needed
        for store in (self._criteria, self._sky):
            for cached in [k for k in store if k[0] == 'colors']:
                del store[cached]                                     # the colorings of the model and the sky
        self.colorParametersChanged.emit(affected)

    @staticmethod
    def _named_parameters(bases, scales, colors, maps=DEFAULT_COLOR_MAPS) -> dict:
        """The parameters by the names of ``COLOR_PARAMETER_EFFECTS``."""
        return {'color_base': bases[1], 'purity_base': bases[2], 'cmyk_scale': scales[0],
                'black_scale': scales[1], 'tetrahedron_step': scales[2], 'tetrahedron_colors': tuple(colors),
                'sequential_map': maps[0], 'diverging_map': maps[1]}

    def parameters_of(self, key: str) -> tuple:
        """Values of the parameters that the coloring (or measure) ``key`` depends on, color maps included."""
        named = self._named_parameters(*self.color_parameters)
        return tuple(value for name, value in named.items() if key in COLOR_PARAMETER_EFFECTS[name])

    def measure_parameters_of(self, key: str) -> tuple:
        """Values of the parameters that the values of the measure ``key`` depend on (not the color maps)."""
        named = self._named_parameters(*self.color_parameters)
        return tuple(value for name, value in named.items()
                     if key in COLOR_PARAMETER_EFFECTS[name] and not name.endswith('_map'))

    def set_borders(self, on: bool) -> None:
        self._set('borders', bool(on))

    def set_labels(self, labels: str) -> None:
        if labels not in LABEL_MODES:
            raise ValueError(f"labels must be one of {list(LABEL_MODES)}")
        self._set('labels', labels)

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

    def set_follow(self, on: bool) -> None:
        if bool(on) != self.follow:
            self.follow = bool(on)
            self.skyTimeChanged.emit(self.sky_time)      # the plots redraw their highlight

    def moment_index(self, depth: int) -> int | None:
        """
        Index, at ``depth``, of the subcycle that contains the sky moment, if the
        plots follow it (``None`` otherwise, or outside the cycle).
        """
        if not self.follow:
            return None
        address = self.subcycle_at(self.sky_time, depth)
        return None if address is None else tcoord(address)

    # -- planetary events

    def set_event_marks(self, years, label: str = '') -> None:
        """Show the events at ``years`` (UT) in the navigator, or none with ``None``."""
        marks = None if years is None else (np.asarray(years, dtype=float), str(label))
        if marks is None and self.event_marks is None:
            return
        self.event_marks = marks
        self.eventsChanged.emit()

    # -- notes and bookmarks

    def set_notes(self, text: str) -> None:
        if text != self.notes:
            self.notes = text
            self.notesChanged.emit()

    @staticmethod
    def _bookmark(address, label: str = '', note: str = '') -> dict:
        address = tuple(int(d) for d in address)
        if not address or any(d not in (0, 1, 2, 3) for d in address):
            raise ValueError(f"not an address: {address}")
        return {'address': address, 'label': str(label), 'note': str(note)}

    def set_bookmarks(self, bookmarks) -> None:
        """Replace the bookmarks (dicts with an address, and optionally a label and a note)."""
        self.bookmarks = [self._bookmark(b['address'], b.get('label', ''), b.get('note', '')) for b in bookmarks]
        self.bookmarksChanged.emit()

    def add_bookmark(self, address, label: str = '', note: str = '') -> int:
        """Bookmark ``address``; returns its row."""
        self.bookmarks.append(self._bookmark(address, label, note))
        self.bookmarksChanged.emit()
        return len(self.bookmarks) - 1

    def update_bookmark(self, row: int, **fields) -> None:
        bookmark = self.bookmarks[row]
        changed = {key: str(value) for key, value in fields.items() if key in ('label', 'note')
                   and str(value) != bookmark[key]}
        if changed:
            bookmark.update(changed)
            self.bookmarksChanged.emit()

    def remove_bookmark(self, row: int) -> None:
        del self.bookmarks[row]
        self.bookmarksChanged.emit()

    def bookmarks_of(self, address) -> list[dict]:
        address = tuple(address) if address is not None else None
        return [b for b in self.bookmarks if b['address'] == address]

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

    def subcycle_at(self, year: float | None, depth: int) -> tuple | None:
        """Address of the subcycle of ``depth`` containing ``year`` (``None`` outside the cycle or without a model)."""
        u = self.position(year)
        if u is None:
            return None
        return tuple(int(d) for d in find_lcoords(min(u, 1 - 1e-15), depth))

    def subcycle_of_date(self, depth: int) -> tuple | None:
        """Address of the subcycle of ``depth`` containing the marked date."""
        return self.subcycle_at(self.date, depth)

    def go_to_date(self, year: float, depth: int) -> None:
        """Mark ``year`` and select the subcycle of ``depth`` containing it."""
        self.set_date(year)
        address = self.subcycle_of_date(depth)
        if address is not None:
            self.reveal(address)
