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
    CMYK_KEYS, COLOR_KEYS, DEFAULT_BASES, DEFAULT_COLOR_KEY, DEFAULT_SCALES, TETRAHEDRON_COLORS, Level, compute_level,
    level_colors,
)
from cycles.functions.color import color_parameter_problems
from cycles.functions.division import COLOR_PARAMETER_EFFECTS
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
# Color of the highlight of the subcycles that contain the sky moment
MOMENT_COLOR = '#ff7f0e'
# How subcycles are labelled in the navigator
LABEL_MODES = {'names': 'Names', 'dots': 'Dots (4, 3, 2, 1)', 'both': 'Names and dots', 'none': 'None'}
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
    """Levels and their colors, computed with the given parameters (see ``compute_level``) on first use."""

    def __init__(self, bases=DEFAULT_BASES, scales=DEFAULT_SCALES, colors=TETRAHEDRON_COLORS):
        self.bases, self.scales = list(bases), list(scales)
        self.vertices = np.asarray(colors, dtype=float)    # of the tetrahedron coloring
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
        """RGB colors (N, 3) of the subcycles of ``depth`` for the color name ``key``."""
        if depth not in self._colors:
            self._colors[depth] = level_colors(self.level(depth))
        return self._colors[depth][key]

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
    colorParametersChanged = Signal(frozenset)   # names of the colorings that changed (COLOR_PARAMETER_EFFECTS)
    dateChanged = Signal(object)        # the marked date (decimal year), or None
    skyTimeChanged = Signal(object)     # the moment of the sky chart (decimal year), or None
    permutationChanged = Signal()       # the σ of the Permutations panel
    bookmarksChanged = Signal()
    notesChanged = Signal()             # the notes of the session
    eventsChanged = Signal()            # the planetary events shown in the navigator

    def __init__(self, cache: LevelCache | None = None, presets: dict[str, CycleModel] | None = None):
        super().__init__()
        self.cache = cache or LevelCache()
        self.presets = presets if presets is not None else load_presets()
        self.model: CycleModel | None = self.presets.get(DEFAULT_PRESET) or next(iter(self.presets.values()), None)
        self._time_map = self.model.time_map() if self.model is not None else None
        self.date: float | None = current_year()
        self.sky_time: float | None = None
        self.follow: bool = True        # the plots highlight their subcycle containing the sky moment
        self.focus: tuple = ()
        self.selection: tuple | None = None
        self.color_key: str = DEFAULT_COLOR_KEY
        self.rows: int = 5
        self.spacing: str = 'time'      # 'time' (widths by duration) or 'index' (equal widths)
        self.names: tuple = YUGA_NAMES
        self.highlight: str = 'none'    # a key of HIGHLIGHTS
        self.compare_criteria: bool = False   # the navigator shows where the other division criterion puts boundaries
        self._criteria: dict = {}       # (model, depth) -> boundaries by criterion
        self.permutation: tuple | None = None   # (σ, first permuted position) of the Permutations panel
        self.borders: bool = False
        self.labels: str = 'none'       # 'names', 'dots' (4, 3, 2, 1 for the four ages), 'both' or 'none'
        self.bookmarks: list[dict] = []    # {'address': tuple, 'label': str, 'note': str}
        self.notes: str = ''
        self.event_marks: tuple | None = None   # (years in UT, label) of the Events panel, or None

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
        # the navigator shows the levels below the zoom, so the zoom must be above the address
        if address[:len(focus)] != focus or len(address) <= len(focus):
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

    def set_highlight(self, mode: str) -> None:
        if mode not in HIGHLIGHTS:
            raise ValueError(f"unknown highlight {mode!r}")
        self._set('highlight', mode)

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

    def measure_values(self, depth: int, key: str) -> np.ndarray | None:
        """
        Values (N,) of the measure ``key`` (``measure.MEASURES``) for the subcycles of ``depth``; None for a measure
        of the cycle model when there is none.
        """
        from cycles.functions.measure import MEASURES
        if MEASURES[key]['parameter'] != 'model':
            return self.cache.measure(depth, key)
        if self.model is None or self.time_map is None:
            return None
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
        level = self.cache.level(len(address))
        if self.highlight == 'duration':
            return equal_duration_indices(level, tcoord(address))
        if self.highlight == 'composition':
            return same_composition_indices(level, address)
        orbit = self.permutation_orbit(address)
        return None if orbit is None else np.array(sorted(tcoord(a) for a in orbit))

    @property
    def color_parameters(self) -> tuple:
        """``(bases, scales, tetrahedron colors)`` of the colorings and measures, as tuples."""
        return (tuple(self.cache.bases), tuple(self.cache.scales),
                tuple(tuple(float(c) for c in row) for row in self.cache.vertices))

    def set_color_parameters(self, bases, scales, colors=None) -> None:
        """
        Use new bases, scales and tetrahedron vertex colors (the current ones
        if not given) for the colorings and measures. ``ValueError`` if they
        could give repeated colors (see ``color_parameter_problems``).
        """
        colors = self.cache.vertices if colors is None else np.asarray(colors, dtype=float)
        problems = color_parameter_problems(bases, scales, colors)
        if problems:
            raise ValueError('; '.join(problems))
        new = (tuple(bases), tuple(scales), tuple(tuple(float(c) for c in row) for row in colors))
        old = self.color_parameters
        if new == old:
            return
        changed = self._named_parameters(*old).items() ^ self._named_parameters(*new).items()
        affected = frozenset(key for name, _ in changed for key in COLOR_PARAMETER_EFFECTS[name])
        self.cache = LevelCache(bases, scales, colors)     # levels are recomputed when next needed
        self.colorParametersChanged.emit(affected)

    @staticmethod
    def _named_parameters(bases, scales, colors) -> dict:
        """The parameters by the names of ``COLOR_PARAMETER_EFFECTS``."""
        return {'color_base': bases[1], 'purity_base': bases[2], 'cmyk_scale': scales[0],
                'black_scale': scales[1], 'tetrahedron_step': scales[2], 'tetrahedron_colors': tuple(colors)}

    def parameters_of(self, key: str) -> tuple:
        """Values of the parameters that the coloring (or measure) ``key`` depends on."""
        named = self._named_parameters(*self.color_parameters)
        return tuple(value for name, value in named.items() if key in COLOR_PARAMETER_EFFECTS[name])

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
