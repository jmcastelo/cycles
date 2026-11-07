"""
Sky comparison: the sky at the starts (or middles, or ends) of a set of
subcycles — every subcycle of the selection's depth, or those that share its
composition, its duration or its ⟨σ⟩ orbit, or the selection's parts — and
how it compares with the sky of the selection.

Two measures:

- The concentration of each body over the set: the length R of the mean unit
  vector of its sidereal longitudes, 1 if they are all equal and about
  √(π / 4n) for n random ones; so R well above that value means the set tends
  to begin with that body in the same place.
- The distance Δ of each member's sky to the selection's: the mean, over the
  compared bodies, of the angle between their sidereal longitudes (0° for the
  same sky, 90° on average for unrelated ones). It is compared with the
  distances of random moments in the same span, which says whether subcycles
  come closer to the selection's sky than time alone would bring them.
"""

import warnings

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QLabel, QSpinBox, QSplitter,
    QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)

from cycles.gui.state import (
    CycleState, address_of, children_range, date_text, equal_duration_indices,
    same_composition_indices, tcoord,
)

SETS = {
    'all': 'All of its depth',
    'composition': 'Same composition',
    'duration': 'Equal duration',
    'orbit': '⟨σ⟩ orbit',
    'children': 'Parts of the selection',
}
MOMENTS = {'start': 'starts', 'middle': 'middles', 'end': 'ends'}
ORDERS = {'time': 'In time order', 'similar': 'Most similar first'}
COMPARED = {'slow': 'Slow bodies', 'all': 'All bodies'}
SLOW_BODIES = ('mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto')
MAX_POSITIONS = 100_000     # members whose positions are computed (evenly sampled beyond)
RANDOM_MOMENTS = 20_000     # random moments of the span, for the reference distances
BODY_NAMES = {'sun': 'Sun', 'mercury': 'Mercury', 'venus': 'Venus', 'mars': 'Mars', 'jupiter': 'Jupiter',
              'saturn': 'Saturn', 'uranus': 'Uranus', 'neptune': 'Neptune', 'pluto': 'Pluto'}
SIGNS = ['Ari', 'Tau', 'Gem', 'Can', 'Leo', 'Vir', 'Lib', 'Sco', 'Sag', 'Cap', 'Aqu', 'Pis']
SELECTION_COLOR = '#1f77b4'
MARKED_COLOR = '#d62728'    # members highlighted in the navigator, on the strip
CHART_PAD = 6.0             # pixels between neighbouring charts
STRIP_SHARE, STRIP_MIN, STRIP_MAX = 0.2, 50.0, 150.0     # height of the strip: share of the canvas, in pixels
STRIP_LEFT, STRIP_BELOW = 46.0, 24.0                    # its margins for the axis labels, in pixels


def concentration(longitudes_deg) -> tuple[float, float]:
    """(circular mean in degrees, mean resultant length R) of longitudes (NaN ignored)."""
    angles = np.radians(np.asarray(longitudes_deg, dtype=float))
    angles = angles[np.isfinite(angles)]
    if not len(angles):
        return float('nan'), float('nan')
    c, s = np.cos(angles).mean(), np.sin(angles).mean()
    return float(np.degrees(np.arctan2(s, c)) % 360.0), float(np.hypot(c, s))


def random_concentration(n: int) -> float:
    """Expected R of ``n`` independent uniform longitudes (large n)."""
    return float(np.sqrt(np.pi / (4 * n))) if n else float('nan')


def sky_distance(longitudes: dict, reference: dict, bodies) -> np.ndarray:
    """
    Mean over ``bodies`` of the angle (0° to 180°) between ``longitudes[body]``
    (arrays) and ``reference[body]`` (a longitude): 90° on average for
    unrelated skies.
    """
    angles = [np.abs((np.asarray(longitudes[b], dtype=float) - reference[b] + 180.0) % 360.0 - 180.0)
              for b in bodies]
    return np.mean(angles, axis=0)


def expected_closest(random_distances: np.ndarray, n: int) -> float:
    """About the smallest of ``n`` distances drawn like ``random_distances``."""
    random_distances = random_distances[np.isfinite(random_distances)]
    if not len(random_distances) or n < 1:
        return float('nan')
    return float(np.quantile(random_distances, 1.0 / (n + 1)))


def tdb_years(years_ut: np.ndarray) -> np.ndarray:
    from cycles.plotting.equinoctial_precession import _tdb_year
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')          # DeltaT extrapolation outside -1999..3000
        return np.array([_tdb_year(float(y), 'UT') for y in years_ut])


class SkyComparisonPanel(QWidget):
    """The skies of a set of subcycles, and how close they come to the selection's.

    Uses the ephemeris tables and the outer-planets option of the Sky panel."""

    saveRequested = Signal()     # the Save… button

    def __init__(self, sky_panel, state: CycleState, parent=None):
        super().__init__(parent)
        self.sky_panel = sky_panel
        self.state = state
        self._dirty = True
        self._members: list[tuple] = []         # (address, year, distance) of the charts drawn
        self._axes = []
        self._strip = None                       # (axes, years, distances, indices, depth)
        self.chart_layout: dict = {}                 # columns, rows and side (pixels) of the charts
        self._positions_cache: dict = {}
        self._random_cache: dict = {}
        self.summary: dict = {}
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.kind = QComboBox()
        for key, label in SETS.items():
            self.kind.addItem(label, key)
        self.kind.setToolTip('Which subcycles to compare with the selection')
        self.moment = QComboBox()
        for key, label in MOMENTS.items():
            self.moment.addItem(label, key)
        self.inside = QCheckBox('Only inside the zoom')
        row.addWidget(QLabel('Subcycles'))
        row.addWidget(self.kind)
        row.addWidget(QLabel('at their'))
        row.addWidget(self.moment)
        row.addWidget(self.inside)
        row.addStretch(1)
        layout.addLayout(row)

        row = QHBoxLayout()
        self.order = QComboBox()
        for key, label in ORDERS.items():
            self.order.addItem(label, key)
        self.order.setToolTip('Charts evenly spread over the subcycles in time, or the ones whose sky is '
                              'closest to the selection\'s')
        self.compared = QComboBox()
        for key, label in COMPARED.items():
            self.compared.addItem(label, key)
        self.compared.setToolTip('Bodies whose longitudes enter the distance Δ to the selection\'s sky.\n'
                                 'Slow bodies: Mars and beyond. Over years and more, the Sun, Mercury and '
                                 'Venus are set\nby the time of the year rather than by the cycle')
        self.charts = QSpinBox()
        self.charts.setRange(1, 64)
        self.charts.setValue(12)
        self.charts.setToolTip('How many charts to draw')
        save_button = QToolButton()
        save_button.setText('Save…')
        save_button.setToolTip('Save this graph to a file (page size, resolution, format…)')
        save_button.clicked.connect(self.saveRequested)
        row.addWidget(QLabel('Charts'))
        row.addWidget(self.charts)
        row.addWidget(self.order)
        row.addWidget(QLabel('Δ over'))
        row.addWidget(self.compared)
        row.addStretch(1)
        row.addWidget(save_button)
        layout.addLayout(row)
        self.heading = QLabel()
        self.heading.setWordWrap(True)
        layout.addWidget(self.heading)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.figure = Figure(figsize=(6, 6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.mpl_connect('button_release_event', self._clicked)
        self.canvas.mpl_connect('resize_event', self.fit_charts)
        splitter.addWidget(self.canvas)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['Body', 'Mean sidereal longitude', 'Concentration R',
                                              'Random would give'])
        self.table.horizontalHeaderItem(2).setToolTip('Length of the mean unit vector of the longitudes: 1 if '
                                                      'they are all equal, near 0 if spread evenly')
        self.table.horizontalHeaderItem(3).setToolTip('About √(π / 4n) for n random longitudes')
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        splitter.addWidget(self.table)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setStyleSheet('color: palette(placeholder-text)')
        layout.addWidget(self.note)

        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(150)
        self.render_timer.timeout.connect(self.render)
        for widget in (self.kind, self.moment, self.order, self.compared):
            widget.currentIndexChanged.connect(self._schedule)
        self.inside.toggled.connect(self._schedule)
        self.charts.valueChanged.connect(self._schedule)
        for signal in (state.selectionChanged, state.focusChanged, state.modelChanged, state.permutationChanged,
                       state.viewChanged):
            signal.connect(self._schedule)
        self.sky_panel.outer.toggled.connect(self._schedule)
        self.sky_panel.ephemerisChanged.connect(self._schedule)

    def _schedule(self, *_) -> None:
        self._dirty = True
        if self.isVisible():
            self.render_timer.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._dirty:
            self.render_timer.start()

    def title(self) -> str:
        state = self.state
        if not state.selection:
            return 'Sky comparison'
        names = ' › '.join(state.names[d] for d in state.selection)
        kind = self.kind.currentData()
        what = {'all': 'all subcycles of its depth', 'children': 'its parts'}.get(
            kind, self.kind.currentText().lower())
        return f"Sky of {names} and {what}, at their {self.moment.currentText()}"

    # -- the set

    def members(self) -> tuple[np.ndarray, int, str]:
        """(indices, depth, explanation) of the subcycles of the chosen set, in time order."""
        state = self.state
        selection = state.selection
        if selection is None or not selection:
            return np.array([], dtype=int), 0, 'Select a subcycle.'
        kind = self.kind.currentData()
        depth = len(selection)
        level = state.cache.level(depth)
        if kind == 'all':
            indices = np.arange(4 ** depth)
        elif kind == 'composition':
            indices = same_composition_indices(level, selection)
        elif kind == 'duration':
            indices = equal_duration_indices(level, tcoord(selection))
        elif kind == 'orbit':
            orbit = state.permutation_orbit(selection)
            if orbit is None:
                return np.array([], dtype=int), depth, ('The σ of the Permutations panel does not act on '
                                                        'subcycles of this depth.')
            indices = np.array(sorted(tcoord(a) for a in orbit))
        else:
            depth += 1
            span = children_range(selection, depth)
            indices = np.arange(span.start, span.stop)
        if self.inside.isChecked() and state.focus and len(state.focus) < depth:
            span = children_range(state.focus, depth)
            indices = indices[(indices >= span.start) & (indices < span.stop)]
        return np.asarray(indices, dtype=int), depth, ''

    def times(self, indices: np.ndarray, depth: int) -> np.ndarray:
        """Years (UT) of the chosen moment of subcycles of ``depth``."""
        level = self.state.cache.level(depth)
        u = level.starts[indices] + {'start': 0.0, 'middle': 0.5, 'end': 1.0}[self.moment.currentData()] \
            * level.durations[indices]
        return np.asarray(self.state.time_map.to_physical(np.minimum(u, 1.0)), dtype=float)

    def span(self) -> tuple[float, float]:
        """Years (UT) spanned by the set: the selection for its parts, the zoom, or the whole cycle."""
        state = self.state
        if self.kind.currentData() == 'children':
            address = state.selection
        elif self.inside.isChecked() and state.focus:
            address = state.focus
        else:
            address = ()
        if address:
            level = state.cache.level(len(address))
            i = tcoord(address)
            u0, u1 = level.starts[i], min(1.0, level.starts[i] + level.durations[i])
        else:
            u0, u1 = 0.0, 1.0
        lo, hi = state.time_map.to_physical(np.array([u0, u1]))
        return float(lo), float(hi)

    def positions(self, years_ut: np.ndarray, bodies) -> dict:
        """Sidereal longitudes (NaN outside the ephemeris) of ``bodies`` at ``years_ut``, cached."""
        from cycles.plotting.equinoctial_precession import planet_positions_many
        tables = self.sky_panel.tables
        key = (hash(np.ascontiguousarray(years_ut).tobytes()), len(years_ut), tuple(bodies), id(tables))
        if key not in self._positions_cache:
            if len(self._positions_cache) > 8:
                self._positions_cache.clear()
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                result = planet_positions_many(tdb_years(years_ut), tables, bodies)
            self._positions_cache[key] = {b: result[b]['sidereal'] for b in bodies}
        return self._positions_cache[key]

    def random_longitudes(self, bodies) -> dict:
        """Longitudes at random moments of the set's span (the same ones each time, for stable figures)."""
        lo, hi = self.span()
        key = (lo, hi, tuple(bodies), id(self.sky_panel.tables))
        if key not in self._random_cache:
            if len(self._random_cache) > 8:
                self._random_cache.clear()
            years = np.random.default_rng(0).uniform(lo, hi, RANDOM_MOMENTS)
            self._random_cache[key] = self.positions(years, bodies)
        return self._random_cache[key]

    # -- drawing

    def render(self) -> None:
        self._dirty = False
        state = self.state
        self.figure.clear()
        self._axes, self._members, self._strip = [], [], None
        self.summary = {}
        self.table.setRowCount(0)
        self.note.setText('')
        tables = self.sky_panel.tables
        if state.time_map is None or not tables:
            self.heading.setText('Needs a cycle model and the ephemeris tables (see the Sky panel).')
            self.canvas.draw_idle()
            return
        indices, depth, problem = self.members()
        if not len(indices):
            self.heading.setText(problem or 'No subcycles of this set inside the zoom.')
            self.canvas.draw_idle()
            return
        from cycles.gui.sky import INNER_BODIES, OUTER_BODIES
        from cycles.plotting.equinoctial_precession import _PLANETS
        bodies = INNER_BODIES + (OUTER_BODIES if self.sky_panel.outer.isChecked() else ())
        compared = [b for b in bodies if b in SLOW_BODIES] if self.compared.currentData() == 'slow' else bodies
        selection = state.selection
        step = max(1, int(np.ceil(len(indices) / MAX_POSITIONS)))
        sampled = indices[::step]

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            years = self.times(sampled, depth)
            longitudes = self.positions(years, bodies)
            reference_year = float(self.times(np.array([tcoord(selection)]), len(selection))[0])
            reference = {b: float(v[0]) for b, v in self.positions(np.array([reference_year]), bodies).items()}
            distances = random_distances = None
            if np.isfinite(list(reference.values())).all():
                distances = sky_distance(longitudes, reference, compared)
                random_distances = sky_distance(self.random_longitudes(bodies), reference, compared)
            is_selection = (sampled == tcoord(selection)) if depth == len(selection) else np.zeros(len(sampled),
                                                                                                  bool)
            charts = self._choose(sampled, depth, years, distances, is_selection, reference_year)
            self._draw(charts, sampled, depth, years, distances, random_distances, is_selection)
        finally:
            QApplication.restoreOverrideCursor()

        valid = np.isfinite(longitudes[bodies[0]])
        n = int(valid.sum())
        self.table.setRowCount(len(bodies))
        self.table.setMinimumHeight(self.table.horizontalHeader().sizeHint().height()
                                    + len(bodies) * self.table.verticalHeader().defaultSectionSize() + 4)
        expected = random_concentration(n)
        for row, body in enumerate(bodies):
            mean, r = concentration(longitudes[body])
            sign, degrees = (int(mean // 30) % 12, mean % 30) if np.isfinite(mean) else (0, float('nan'))
            items = [f"{_PLANETS[body][1]} {BODY_NAMES.get(body, body)}",
                     f"{mean:.1f}°  ({degrees:.1f}° {SIGNS[sign]})" if np.isfinite(mean) else '—',
                     f"{r:.3f}", f"{expected:.3f}"]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col == 2 and n > 1 and r > 3 * expected:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setToolTip('More than three times what random longitudes would give')
                self.table.setItem(row, col, item)

        names = ' › '.join(state.names[d] for d in selection)
        what = {'all': f"all of depth {depth}", 'children': f"the parts of {names}"}.get(
            self.kind.currentData(), f"{self.kind.currentText().lower()} as {names}")
        self.heading.setText(f"{len(indices)} subcycles ({what}), at their {self.moment.currentText()}; "
                             f"{len(self._members)} charts, {self.order.currentText().lower()}.")
        notes = []
        if step > 1:
            notes.append(f"Computed for one in {step} of them ({len(sampled)}).")
        if n < len(sampled):
            notes.append(f"{len(sampled) - n} outside the ephemeris tables.")
        notes.append(f"Concentration over {n} of them; bold: more than three times that of random longitudes.")
        others = distances[~is_selection & np.isfinite(distances)] if distances is not None else np.array([])
        if len(others):
            closest = float(others.min())
            chance = expected_closest(random_distances, len(others))
            below = float(np.quantile(random_distances[np.isfinite(random_distances)], 0.05))
            share = float((others < below).mean())
            self.summary = {'closest': closest, 'chance': chance, 'median': float(np.median(others)),
                            'random_median': float(np.nanmedian(random_distances)), 'share_below_5': share,
                            'n': len(others)}
            notes.append(
                f"Δ: mean angle between the {'slow ' if self.compared.currentData() == 'slow' else ''}bodies' "
                f"sidereal longitudes and the selection's. Closest {closest:.1f}°, where the closest of "
                f"{len(others)} random moments of the span would be about {chance:.1f}°; median {np.median(others):.0f}° "
                f"(random {self.summary['random_median']:.0f}°); {100 * share:.1f} % below the 5 % of random "
                f"moments (dashed line).")
        elif distances is None:
            notes.append('The selection\'s moment is outside the ephemeris: no distances.')
        notes.append('Click a chart or a point of the strip to select its subcycle and show that moment in the '
                     'Sky panel.')
        self.note.setText(' '.join(notes))

    def _choose(self, sampled, depth, years, distances, is_selection, reference_year) -> list[tuple]:
        """(address, year, distance, is the selection) of the charts to draw, in order."""
        state = self.state
        count = min(self.charts.value(), len(sampled))
        if self.order.currentData() == 'similar' and distances is not None:
            charts = [(state.selection, reference_year, 0.0, True)]
            candidates = np.flatnonzero(~is_selection & np.isfinite(distances))
            best = candidates[np.argsort(distances[candidates], kind='stable')[:max(0, count - 1)]]
            positions = list(best)
        else:
            charts = []
            positions = list(np.unique(np.round(np.linspace(0, len(sampled) - 1, count)).astype(int)))
        for p in positions:
            d = float(distances[p]) if distances is not None else float('nan')
            charts.append((address_of(int(sampled[p]), depth), float(years[p]), d, bool(is_selection[p])))
        return charts

    def _draw(self, charts, sampled, depth, years, distances, random_distances, is_selection) -> None:
        from cycles.gui.sky import INNER_BODIES, OUTER_BODIES
        from cycles.plotting.equinoctial_precession import plot_zodiac_with_planets
        state = self.state
        bodies = INNER_BODIES + (OUTER_BODIES if self.sky_panel.outer.isChecked() else ())
        strip = distances is not None
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for k, (address, year, distance, own) in enumerate(charts):
                # placed by fit_charts
                ax = self.figure.add_axes((0.0, 0.0, 0.1, 0.1), projection='polar')
                try:
                    plot_zodiac_with_planets(year, self.sky_panel.tables, bodies=bodies, ax=ax, show=False,
                                             table=False, compact=True, time_scale='UT', epoch_display=(),
                                             sign_labels='symbol')
                except ValueError:
                    ax.set_axis_off()
                    ax.text(0.5, 0.5, 'outside the\nephemeris', transform=ax.transAxes, ha='center', fontsize=7)
                initials = ''.join(state.names[d][0] for d in address)
                third = 'selection' if own else (f"Δ {distance:.1f}°" if np.isfinite(distance) else '')
                ax.set_title('')
                # under its chart (a title would sit closer to the chart above); fit_charts sets its offset
                ax._class_label = ax.annotate(
                    f"{initials}\n{date_text(year)}" + (f"\n{third}" if third else ''), xy=(0.5, 0.0),
                    xycoords='axes fraction', xytext=(0, -2), textcoords='offset pixels', ha='center', va='top',
                    fontsize=7, color=SELECTION_COLOR if own else 'black', fontweight='bold' if own else 'normal',
                    annotation_clip=False)
                ax._class_member = (address, year)
                self._axes.append(ax)
                self._members.append((address, year, distance))
        if strip:
            self._draw_strip(self.figure.add_axes((0.08, 0.06, 0.74, 0.18)), charts, sampled, depth, years,
                             distances, random_distances, is_selection)
        self.fit_charts()

    def fit_charts(self, *_) -> None:
        """
        Lay the charts out as large as the canvas allows: the strip at the
        bottom with fixed margins for its axis and legend, and above it the
        number of columns that gives the largest charts, each with its sign
        symbols and its label (which keep their size in points) inside its cell.
        """
        axes = self._axes
        width, height = self.figure.bbox.width, self.figure.bbox.height
        if not axes or width < 40 or height < 40:
            return
        renderer = self.canvas.get_renderer()
        top, bottom = height - CHART_PAD / 2, CHART_PAD / 2
        if self._strip is not None:
            strip = self._strip[0]
            legend = strip.get_legend()
            legend_width = legend.get_window_extent(renderer).width if legend is not None else 0.0
            strip_height = min(STRIP_MAX, max(STRIP_MIN, STRIP_SHARE * height))
            strip.set_position([STRIP_LEFT / width, STRIP_BELOW / height,
                                max(20.0, width - STRIP_LEFT - legend_width - 14) / width, strip_height / height])
            bottom = STRIP_BELOW + strip_height + 2 * CHART_PAD
        area_width, area_height = width - CHART_PAD, top - bottom
        if area_height < 20:
            return
        labels = [ax._class_label for ax in axes]
        extents = [label.get_window_extent(renderer) for label in labels]
        label_width = max(e.width for e in extents)
        label_height = max(e.height for e in extents)
        reference = next((ax for ax in axes if ax.axison), axes[0])
        n = len(axes)
        side = 0.5 * min(area_width, area_height)
        for _ in range(2):
            # how far the sign symbols reach beyond the disk (constant in points), at the current size
            reference.set_position([0.0, 0.0, side / width, side / height])
            reference._class_label.set_visible(False)
            disk, tight = reference.get_window_extent(renderer), reference.get_tightbbox(renderer)
            reference._class_label.set_visible(True)
            left, right = max(0.0, disk.x0 - tight.x0), max(0.0, tight.x1 - disk.x1)
            above, below = max(0.0, tight.y1 - disk.y1), max(0.0, disk.y0 - tight.y0)
            extra_w, extra_h = left + right + CHART_PAD, above + below + label_height + 2 + CHART_PAD
            best = None
            for columns in range(1, n + 1):
                rows = -(-n // columns)
                cell_w, cell_h = area_width / columns, area_height / rows
                size = min(cell_w - extra_w, cell_h - extra_h)
                fits = label_width + CHART_PAD <= cell_w            # labels of neighbours do not overlap
                key = (fits, size)
                if best is None or key > best[0]:
                    best = (key, columns, rows, cell_w, cell_h, size)
            _, columns, rows, cell_w, cell_h, side = best
            side = max(12.0, side)
        block_w, block_h = side + left + right, above + side + below + label_height + 2
        for k, ax in enumerate(axes):
            row, col = divmod(k, columns)
            in_row = min(columns, n - row * columns)
            x_cell = CHART_PAD / 2 + (col + (columns - in_row) / 2) * cell_w      # the last row centred
            y_top = top - row * cell_h - (cell_h - block_h) / 2
            x0 = x_cell + (cell_w - block_w) / 2 + left
            y0 = y_top - above - side
            ax.set_position([x0 / width, y0 / height, side / width, side / height])
            ax._class_label.xyann = (0, -(below + 2))
        self.chart_layout = {'columns': columns, 'rows': rows, 'side': side}
        self.canvas.draw_idle()

    def _draw_strip(self, ax, charts, sampled, depth, years, distances, random_distances, is_selection) -> None:
        """Each member's distance to the selection's sky along the span."""
        state = self.state
        ax.scatter(years, distances, s=4, color='#9a9a9a', linewidths=0, rasterized=len(years) > 2000,
                   label='subcycles')
        marked = None
        if depth == len(state.selection) and self.kind.currentData() == 'all':
            highlighted = state.highlight_indices(state.selection)
            if highlighted is not None:
                marked = np.isin(sampled, highlighted) & ~is_selection
                if marked.any():
                    ax.scatter(years[marked], distances[marked], s=10, color=MARKED_COLOR, linewidths=0,
                               label=f"same {state.highlight}" if state.highlight != 'orbit' else '⟨σ⟩ orbit',
                               zorder=3)
        shown = [y for (_, y, _, own) in charts if not own]
        shown_d = [d for (_, _, d, own) in charts if not own]
        if shown:
            ax.scatter(shown, shown_d, s=26, facecolors='none', edgecolors='black', linewidths=0.8,
                       label='charts', zorder=4)
        reference_year = float(self.times(np.array([tcoord(state.selection)]), len(state.selection))[0])
        ax.axvline(reference_year, color=SELECTION_COLOR, linewidth=1.2, label='selection')
        finite = random_distances[np.isfinite(random_distances)]
        if len(finite):
            ax.axhline(np.quantile(finite, 0.05), color='black', linestyle='--', linewidth=0.8,
                       label='random: 5 % below')
        ax.set_ylabel('Δ (°)', fontsize=8)
        ax.set_ylim(0, max(1.0, float(np.nanmax(distances)) * 1.05))
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=6, loc='center left', bbox_to_anchor=(1.01, 0.5), frameon=False, borderaxespad=0.2,
                  handletextpad=0.4, labelspacing=0.3)
        ax.margins(x=0.01)
        self._strip = (ax, years, distances, sampled, depth)

    # -- interaction

    def _clicked(self, event) -> None:
        if event.button != 1 or event.inaxes is None:
            return
        if self._strip is not None and event.inaxes is self._strip[0]:
            ax, years, distances, sampled, depth = self._strip
            points = ax.transData.transform(np.column_stack([years, distances]))
            gaps = np.hypot(points[:, 0] - event.x, points[:, 1] - event.y)
            gaps[~np.isfinite(gaps)] = np.inf
            k = int(np.argmin(gaps))
            if gaps[k] > 12:
                return
            address, year = address_of(int(sampled[k]), depth), float(years[k])
        elif hasattr(event.inaxes, '_class_member'):
            address, year = event.inaxes._class_member
        else:
            return
        self.state.reveal(address)
        self.state.set_sky_time(year)
