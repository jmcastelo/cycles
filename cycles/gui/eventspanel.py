"""
Events panel: planetary events (conjunctions, trigon changes, the planets at the start of Aries) against the
boundaries of the subcycles, with a significance test: the boundaries are compared with rigid rotations of them
(the same spacing, placed anywhere in the span), see ``cycles.functions.significance``.

The events in the zoomed span are listed (clicking one moves the sky moment there and selects its subcycle) and
can be shown in the navigator. The catalogues of conjunctions are computed once from the ephemeris of the Sky
panel and kept on disk (``cycles.functions.events.DEFAULT_CACHE``), shared with ``study_of_events.py``.
"""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QLabel, QSpinBox, QSplitter,
    QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)

from cycles.functions.cycle_analysis import anchor_fields, boundary_fractions, boundary_grid
from cycles.functions.events import (
    CLASSICAL, ELEMENTS, SIGN_NAMES, ZODIACS, around_point, cached_conjunctions, element_of, first_of_series,
    sign_of, table_span, tdb_years, trigon_changes, ut_years,
)
from cycles.functions.significance import proximity_test, scan_models, value_test
from cycles.gui.state import MAX_DEPTH, CycleState, children_range, date_text, datetime_text, tcoord

# Tests: key -> (label, kind, pair or zodiac)
TESTS = {
    'great': ('Jupiter–Saturn conjunctions', 'conjunctions', ('jupiter', 'saturn')),
    'trigon_sidereal': ('Trigon changes of the great conjunctions (sidereal)', 'trigon', 'sidereal'),
    'trigon_tropical': ('Trigon changes of the great conjunctions (tropical)', 'trigon', 'tropical'),
    'uranus_neptune': ('Uranus–Neptune conjunctions', 'conjunctions', ('uranus', 'neptune')),
    'neptune_pluto': ('Neptune–Pluto conjunctions', 'conjunctions', ('neptune', 'pluto')),
    'aries_sidereal': ('Sun…Saturn at 0° Aries (sidereal, Sūrya Siddhānta)', 'aries', 'sidereal'),
    'aries_tropical': ('Sun…Saturn at 0° Aries (tropical: the vernal point)', 'aries', 'tropical'),
}
MARGIN = 200.0                     # years of events beyond the cycle (as in study_of_events)
MAX_POSITIONS = 400_000            # boundaries × rotations whose sky is computed in a test of the planets at 0° Aries
MAX_ROWS = 2000                    # events listed
VIEWS = {'model': 'This model', 'models': 'Over the models'}
MAP_ANCHORS = (30000.0, 1000.0)    # the map: anchors around the model's (half-width, step, years)
MAP_TURNS = (1.0, 4.0, 0.25)       # arcs (from, to, step, turns)
MAP_ROWS = 20                      # closest models listed
AUTO_RENDER = True                 # draw when shown (the tests turn it off: offscreen, hidden tabs count as shown)


def sign_text(longitude: float) -> str:
    return f"{longitude % 30:4.1f}° {SIGN_NAMES[int(sign_of(longitude))]}"


class EventsPanel(QWidget):
    """Planetary events against the boundaries of the subcycles, with a significance test."""

    saveRequested = Signal()     # the Save… button

    def __init__(self, sky_panel, state: CycleState, parent=None):
        super().__init__(parent)
        self.sky_panel = sky_panel
        self.state = state
        self._dirty = True
        self._catalogs: dict = {}
        self._result_key = None
        self.result: dict | None = None
        self._rows: list[float] = []        # UT year of each row of the table
        self._listed = (0, 0)               # (rows listed, events in view)
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.kind = QComboBox()
        for key, (label, _, _) in TESTS.items():
            self.kind.addItem(label, key)
        self.depth = QSpinBox()
        self.depth.setRange(1, 6)
        self.depth.setToolTip('Depth of the subcycles whose boundaries (starts, and the end) are tested')
        save_button = QToolButton()
        save_button.setText('Save…')
        save_button.setToolTip('Save this graph to a file (page size, resolution, format…)')
        save_button.clicked.connect(self.saveRequested)
        self.view = QComboBox()
        for key, label in VIEWS.items():
            self.view.addItem(label, key)
        self.view.setToolTip('This model: its boundaries against rotations of them.\nOver the models: every '
                             'anchor × arc (dividing the arc), with a global p that takes the search into account')
        row.addWidget(self.kind, 1)
        row.addWidget(self.view)
        row.addWidget(QLabel('Depth'))
        row.addWidget(self.depth)
        row.addWidget(save_button)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.inside = QCheckBox('Only inside the zoom')
        self.inside.setToolTip('Test the boundaries inside the zoomed subcycle, rotated within it')
        self.rotations = QSpinBox()
        self.rotations.setRange(200, 20000)
        self.rotations.setSingleStep(500)
        self.rotations.setValue(5000)
        self.rotations.setToolTip('Rigid rotations of the boundaries (the null model)')
        self.show_marks = QCheckBox('Show in navigator')
        self.show_marks.setChecked(True)
        row.addWidget(self.inside)
        row.addWidget(QLabel('Rotations'))
        row.addWidget(self.rotations)
        row.addWidget(self.show_marks)
        row.addStretch(1)
        layout.addLayout(row)
        self.heading = QLabel()
        self.heading.setWordWrap(True)
        layout.addWidget(self.heading)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.figure = Figure(figsize=(6, 3.2))
        self.canvas = FigureCanvasQTAgg(self.figure)
        splitter.addWidget(self.canvas)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['When (UT)', 'Event', 'Sidereal', 'Tropical'])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        header = self.table.horizontalHeader()
        for col in range(3):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.table.cellClicked.connect(lambda r, _: self.go_to(r))
        self.canvas.mpl_connect('button_press_event', self._map_clicked)
        splitter.addWidget(self.table)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setStyleSheet('color: palette(placeholder-text)')
        layout.addWidget(self.note)

        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(100)
        self.render_timer.timeout.connect(self.render)
        self.kind.currentIndexChanged.connect(self._schedule)
        self.view.currentIndexChanged.connect(self._schedule)
        for box in (self.depth, self.rotations):
            box.valueChanged.connect(self._schedule)
        self.inside.toggled.connect(self._schedule)
        self.show_marks.toggled.connect(self._update_marks)
        for signal in (state.focusChanged, state.modelChanged):
            signal.connect(self._schedule)
        self.sky_panel.ephemerisChanged.connect(self._ephemeris_changed)

    # -- scheduling

    def _schedule(self, *_) -> None:
        self._dirty = True
        if self.isVisible() and AUTO_RENDER:
            self.render_timer.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._dirty and AUTO_RENDER:
            self.render_timer.start()

    def _ephemeris_changed(self) -> None:
        self._catalogs.clear()
        self._result_key = None
        self._schedule()

    def title(self) -> str:
        over = ', over the models' if self.view.currentData() == 'models' else ''
        return f"{self.kind.currentText()}, depth {self.depth.value()}{over}"

    # -- data

    def span(self) -> tuple[float, float] | None:
        """UT years of the tested span: the zoomed subcycle, or the whole cycle."""
        state = self.state
        if state.time_map is None:
            return None
        if self.inside.isChecked() and state.focus:
            return tuple(float(t) for t in state.time_map.interval(state.focus))
        return float(state.time_map.start), float(state.time_map.end)

    def boundaries_ut(self) -> np.ndarray | None:
        """UT years of the boundaries tested: the starts of the subcycles of the depth in the span, and its end."""
        state = self.state
        depth = self.depth.value()
        if self.inside.isChecked() and state.focus:
            if depth <= len(state.focus):
                return None
            span = children_range(state.focus, depth)
            level = state.cache.level(depth) if depth <= MAX_DEPTH else None
            starts = level.starts[span.start:span.stop]
            end = state.cache.level(len(state.focus))
            i = tcoord(state.focus)
            u = np.append(starts, min(1.0, end.starts[i] + end.durations[i]))
        else:
            u = boundary_fractions(depth)
        return np.asarray(state.time_map.to_physical(u), dtype=float)

    def catalog(self, a: str, b: str) -> dict:
        """The conjunctions of a pair over the whole cycle (TDB), from memory, the disk cache or computed."""
        state = self.state
        start, end = tdb_years([state.time_map.start, state.time_map.end])
        key = (a, b, round(float(start), 3), round(float(end), 3))
        if key not in self._catalogs:
            window = self.window()
            if hasattr(window, 'statusBar'):
                window.statusBar().showMessage(f"Computing the {a}–{b} conjunctions over the cycle (once; then "
                                               f"kept on disk)…")
                window.statusBar().repaint()
            self._catalogs[key] = cached_conjunctions(self.sky_panel.tables, self.sky_panel.ephemeris_path, a, b,
                                                      float(start) - MARGIN, float(end) + MARGIN)
            if hasattr(window, 'statusBar'):
                window.statusBar().clearMessage()
        return self._catalogs[key]

    def events_tdb(self) -> tuple[np.ndarray, list] | None:
        """(TDB years, rows for the table) of the chosen events; None for the test of the planets at 0° Aries."""
        label, kind, what = TESTS[self.kind.currentData()]
        if kind == 'conjunctions':
            data = self.catalog(*what)
            first = first_of_series(data)
            sizes = np.bincount(data['series'])
            starts = set(first.tolist())
            rows = [(t, 'conjunction' + (f" (1 of {sizes[s]})" if sizes[s] > 1 and k in starts else
                                          ' (repeated)' if sizes[s] > 1 else ''),
                     data['sidereal'][k], data['tropical'][k])
                    for k, (t, s) in enumerate(zip(data['times'], data['series']))]
            return data['times'][first], rows
        if kind == 'trigon':
            data = self.catalog('jupiter', 'saturn')
            changes = trigon_changes(data, what)
            index = {t: k for k, t in enumerate(data['times'])}
            rows = []
            for t in changes:
                k = index[t]
                element = ELEMENTS[int(element_of(data[what][k]))]
                rows.append((t, f"trigon change to {element} ({what})", data['sidereal'][k], data['tropical'][k]))
            return changes, rows
        return None

    # -- the test

    def render(self) -> None:
        self._dirty = False
        state = self.state
        self.figure.clear()
        self.table.setRowCount(0)
        self._rows = []
        if state.time_map is None or not self.sky_panel.tables:
            self._message('Needs a cycle model and the ephemeris tables (see the Sky panel).')
            return
        if self.view.currentData() == 'models':
            self.table.setHorizontalHeaderLabels(['Anchor (UT)', 'Arc', 'Distance / random', 'Rank'])
            self._render_map()
            return
        self.table.setHorizontalHeaderLabels(['When (UT)', 'Event', 'Sidereal', 'Tropical'])
        boundaries = self.boundaries_ut()
        if boundaries is None:
            self._message('Choose a depth below the zoom, or test the whole cycle.')
            return
        key = (self.kind.currentData(), self.depth.value(), self.inside.isChecked(),
               state.focus if self.inside.isChecked() else (), self.rotations.value(), state.model,
               str(self.sky_panel.ephemeris_path))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            events = self.events_tdb()
            if key != self._result_key:
                self.result = self._test(boundaries, events)
                self._result_key = key
            self._fill_table(events, boundaries)
        finally:
            QApplication.restoreOverrideCursor()
        self._draw()
        self._update_marks()

    def _test(self, boundaries_ut: np.ndarray, events) -> dict:
        start, end = (float(t) for t in tdb_years(self.span()))
        boundaries = tdb_years(boundaries_ut)
        n = self.rotations.value()
        if events is not None:
            result = proximity_test(boundaries, events[0], start, end, n)
            result['unit'] = 'years'
            result['statistic'] = 'mean distance from the boundaries to the nearest event'
        else:
            zodiac = TESTS[self.kind.currentData()][2]
            n = max(200, min(n, MAX_POSITIONS // len(boundaries)))

            def value(times):
                return around_point(self.sky_panel.tables, times, CLASSICAL, 0.0, zodiac)['mean_distance']
            result = value_test(boundaries, value, start, end, n)
            result['unit'] = '°'
            result['statistic'] = 'mean angle of Sun…Saturn from 0° Aries at the boundaries'
        result['rotations'] = n
        result['count'] = len(boundaries)
        return result

    def _draw(self) -> None:
        r = self.result
        ax = self.figure.add_subplot(111)
        ax.hist(r['null'], bins=60, color='0.75', label=f"{r['rotations']} rotations")
        ax.axvline(r['observed'], color='#d62728', lw=2, label=f"the boundaries: {r['observed']:.2f} {r['unit']}")
        ax.axvline(r['expected'], color='0.35', lw=1, ls='--', label=f"mean of the rotations: {r['expected']:.2f}")
        ax.set_xlabel(f"{r['statistic']} ({r['unit']})", fontsize=8)
        ax.set_title(f"{self.kind.currentText()}, depth {self.depth.value()}: p = {r['p']:.3f}", fontsize=9)
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=7)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')     # a very small panel cannot fit the labels
            self.figure.tight_layout()
        self.canvas.draw_idle()
        span = 'inside the zoom' if self.inside.isChecked() and self.state.focus else 'over the whole cycle'
        verdict = ('closer than most rotations' if r['p'] < 0.05 else 'not closer than the rotations would be')
        self.heading.setText(f"{r['count']} boundaries of depth {self.depth.value()} {span}: {verdict} "
                             f"(observed {r['observed']:.2f} {r['unit']}, rotations {r['expected']:.2f}; "
                             f"p = {r['p']:.3f}).")
        self.note.setText(
            'The boundaries are compared with rigid rotations of them (the same spacing, placed anywhere in the '
            'span), which keeps the rhythm of the events out of the result; p is one-sided (closer than chance). '
            'One test of many: with several, some come out below 0.05 by chance alone (study_of_events.py '
            'corrects the family with Holm\'s method). Click an event to show that moment in the Sky panel.'
            + (f" The table lists the first {self._listed[0]} of the {self._listed[1]} in view: zoom in for the rest."
               if self._listed[1] > self._listed[0] else ''))

    def _fill_table(self, events, boundaries_ut: np.ndarray) -> None:
        state = self.state
        lo, hi = state.time_map.interval(state.focus) if state.focus else (state.time_map.start,
                                                                           state.time_map.end)
        rows = []
        if events is not None:
            times, entries = events
            years = ut_years([e[0] for e in entries]) if entries else np.zeros(0)
            for year, (_, what, sidereal, tropical) in zip(years, entries):
                if lo <= year <= hi:
                    rows.append((year, what, sign_text(sidereal), sign_text(tropical)))
        else:
            zodiac = TESTS[self.kind.currentData()][2]
            inside = boundaries_ut[(boundaries_ut >= lo) & (boundaries_ut <= hi)][:MAX_ROWS]
            if len(inside):
                at = around_point(self.sky_panel.tables, tdb_years(inside), CLASSICAL, 0.0, zodiac)
                for year, d, spread in zip(inside, at['mean_distance'], at['spread']):
                    rows.append((year, 'boundary', f"mean angle {d:.1f}° ({zodiac})", f"all within {spread:.1f}°"))
        self._listed = (min(len(rows), MAX_ROWS), len(rows))
        rows = rows[:MAX_ROWS]
        self.table.setRowCount(len(rows))
        for r, (year, what, a, b) in enumerate(rows):
            for c, text in enumerate((datetime_text(year), what, a, b)):
                self.table.setItem(r, c, QTableWidgetItem(text))
        self._rows = [row[0] for row in rows]

    def _update_marks(self, *_) -> None:
        state = self.state
        if not self.show_marks.isChecked() or self.result is None or state.time_map is None:
            state.set_event_marks(None)
            return
        events = None
        try:
            events = self.events_tdb()
        except (ValueError, OSError):
            pass
        if events is None:
            state.set_event_marks(None)
            return
        times = events[0]
        lo, hi = tdb_years([state.time_map.start, state.time_map.end])
        times = times[(times >= lo - 1) & (times <= hi + 1)]
        state.set_event_marks(ut_years(times), TESTS[self.kind.currentData()][0])

    def _message(self, text: str) -> None:
        self.result = None
        self.heading.setText(text)
        self.note.setText('')
        self.canvas.draw_idle()
        self.state.set_event_marks(None)

    # -- over the models

    def map_grid(self):
        solution = self.state.model.solve()
        half, step = MAP_ANCHORS
        anchors = np.arange(solution['anchor'] - half, solution['anchor'] + half + 1, step)
        turns = np.arange(MAP_TURNS[0], MAP_TURNS[1] + 1e-9, MAP_TURNS[2])
        return anchors, turns, solution

    def wide_events(self):
        """The chosen events over the whole span of the ephemeris (TDB), for models placed anywhere in it."""
        label, kind, what = TESTS[self.kind.currentData()]
        start, end = table_span(self.sky_panel.tables)
        pair = what if kind == 'conjunctions' else ('jupiter', 'saturn')
        key = ('wide',) + tuple(pair)
        if key not in self._catalogs:
            window = self.window()
            if hasattr(window, 'statusBar'):
                window.statusBar().showMessage(f"Computing the {pair[0]}–{pair[1]} conjunctions over the whole "
                                               f"ephemeris (once; then kept on disk)…")
                window.statusBar().repaint()
            self._catalogs[key] = cached_conjunctions(self.sky_panel.tables, self.sky_panel.ephemeris_path,
                                                      pair[0], pair[1], start + 1, end - 1)
            if hasattr(window, 'statusBar'):
                window.statusBar().clearMessage()
        data = self._catalogs[key]
        events = data['times'][first_of_series(data)] if kind == 'conjunctions' else trigon_changes(data, what)
        return events, (start, end)

    def _render_map(self) -> None:
        state = self.state
        if TESTS[self.kind.currentData()][1] == 'aries':
            self._message('The map over the models is for events (conjunctions, trigon changes); the planets at '
                          '0° Aries are tested on this model only.')
            return
        key = ('map', self.kind.currentData(), self.depth.value(), self.rotations.value(), state.model,
               str(self.sky_panel.ephemeris_path))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if key != self._result_key:
                anchors, turns, solution = self.map_grid()
                events, span = self.wide_events()
                grid = boundary_grid(state.model, anchors, turns, self.depth.value())
                finite = np.isfinite(grid)
                tdb = np.full(grid.shape, np.nan)
                tdb[finite] = tdb_years(grid[finite])
                scan = scan_models(tdb, events, span, self.rotations.value())
                own = tdb_years(boundary_grid(state.model, [solution['anchor']], [solution['turns']],
                                              self.depth.value())[0, 0])
                own_scan = scan_models(own[None, :], events, span, 0)
                observed = scan['observed'][np.isfinite(scan['observed'])]
                self.result = {'map': scan, 'anchors': anchors, 'turns': turns, 'solution': solution,
                               'own_ratio': float(own_scan['ratio'][0]),
                               'own_rank': float(np.mean(observed <= own_scan['observed'][0])),
                               'shifts': self.rotations.value()}
                self._result_key = key
        finally:
            QApplication.restoreOverrideCursor()
        self._draw_map()
        self._fill_map_table()
        self._update_marks()

    def _draw_map(self) -> None:
        r = self.result
        scan, anchors, turns, solution = r['map'], r['anchors'], r['turns'], r['solution']
        ax = self.figure.add_subplot(111)
        da, dt = MAP_ANCHORS[1] / 2, MAP_TURNS[2] / 2
        image = ax.imshow(scan['ratio'].T, origin='lower', aspect='auto', cmap='RdBu_r', vmin=0.5, vmax=1.5,
                          extent=(anchors[0] - da, anchors[-1] + da, turns[0] - dt, turns[-1] + dt))
        ax.scatter([solution['anchor']], [solution['turns']], s=60, facecolors='white', edgecolors='black',
                   zorder=3, label='this model')
        if scan['best'] is not None:
            i, j = scan['best']
            ax.scatter([anchors[i]], [turns[j]], marker='*', s=110, color='yellow', edgecolors='black', zorder=3,
                       label='closest')
        bar = self.figure.colorbar(image, ax=ax)
        bar.set_label('mean distance to the events / that of a random moment', fontsize=7)
        bar.ax.tick_params(labelsize=7)
        point = self.state.model.anchor_point
        ax.set_xlabel(f"start of {point} (year)" if point != 'end' else 'end of the cycle (year)', fontsize=8)
        ax.set_ylabel('arc (turns)', fontsize=8)
        ax.set_title(f"{self.kind.currentText()}, depth {self.depth.value()}: global p = {scan['p_global']:.3f}",
                     fontsize=9)
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=7, loc='upper left')
        self._map_axes = ax
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self.figure.tight_layout()
        self.canvas.draw_idle()
        models = int(np.sum(scan['valid']))
        best = ''
        if scan['best'] is not None:
            i, j = scan['best']
            best = (f" The closest: {date_text(anchors[i])}, {turns[j]:g} turns (ratio "
                    f"{scan['ratio'][i, j]:.2f}).")
        verdict = ('some model comes closer than chance would allow' if scan['p_global'] < 0.05
                   else 'no model comes closer than chance would allow')
        self.heading.setText(f"{models} models (anchor × arc) within the ephemeris: {verdict} "
                             f"(global p = {scan['p_global']:.3f}).{best} This model: ratio {r['own_ratio']:.2f}, "
                             f"{100 * r['own_rank']:.0f} % of the models come as close.")
        self.note.setText(
            'Each model divides the arc of precession from its anchor; blue: its boundaries come closer to the '
            f"events than random moments would, red: farther. The global p comes from {r['shifts']} rigid shifts "
            'of the events (their rhythm kept): how often the best model then comes as close as the real best, '
            'which takes the search over all the models into account. Double-click the map, or click a row, to '
            'place the cycle there.')

    def _fill_map_table(self) -> None:
        r = self.result
        scan = r['map']
        ratio = scan['ratio']
        order = np.argsort(np.where(np.isfinite(ratio), ratio, np.inf), axis=None)[:MAP_ROWS]
        finite = ratio[np.isfinite(ratio)]
        rows = []
        for flat in order:
            i, j = np.unravel_index(flat, ratio.shape)
            if not np.isfinite(ratio[i, j]):
                break
            rows.append((r['anchors'][i], r['turns'][j], ratio[i, j], np.mean(finite <= ratio[i, j])))
        self.table.setRowCount(len(rows))
        for k, (anchor, turns, value, rank) in enumerate(rows):
            for c, text in enumerate((date_text(anchor), f"{turns:g} turns", f"{value:.2f}",
                                      f"{100 * rank:.1f} %")):
                self.table.setItem(k, c, QTableWidgetItem(text))
        self._map_rows = [(a, t) for a, t, _, _ in rows]
        self._rows = []

    def _map_clicked(self, event) -> None:
        if (self.view.currentData() != 'models' or not event.dblclick or event.button != 1
                or event.inaxes is not getattr(self, '_map_axes', None) or event.xdata is None):
            return
        self.move_model(event.xdata, event.ydata)

    def move_model(self, anchor: float, turns: float) -> None:
        """Place the cycle with its anchor point at ``anchor`` (UT) and an arc of ``turns`` (as the landscape)."""
        model = self.state.model
        date, time = anchor_fields(float(anchor))
        try:
            self.state.set_model(model.replace(anchor_date=date, anchor_time=time, anchor_longitude=0.0,
                                               anchor_ayanamsa=None, turns=round(float(turns), 4), years=None))
        except ValueError as error:
            self.heading.setText(f"Cannot place the cycle there: {error}")

    # -- interaction

    def go_to(self, row: int) -> None:
        """Move the sky moment to an event and select the subcycle of the panel's depth that contains it."""
        if self.view.currentData() == 'models':
            rows = getattr(self, '_map_rows', [])
            if 0 <= row < len(rows):
                self.move_model(*rows[row])
            return
        if not 0 <= row < len(self._rows):
            return
        year = self._rows[row]
        state = self.state
        address = tuple(int(d) for d in state.time_map.subcycle_at(year, self.depth.value()))
        state.reveal(address)
        state.set_sky_time(year)
