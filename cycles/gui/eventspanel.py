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

from cycles.functions.cycle_analysis import boundary_fractions
from cycles.functions.events import (
    CLASSICAL, ELEMENTS, SIGN_NAMES, ZODIACS, around_point, cached_conjunctions, element_of, first_of_series,
    sign_of, tdb_years, trigon_changes, ut_years,
)
from cycles.functions.significance import proximity_test, value_test
from cycles.gui.state import MAX_DEPTH, CycleState, children_range, datetime_text, tcoord

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
        row.addWidget(self.kind, 1)
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
        return f"{self.kind.currentText()}, depth {self.depth.value()}"

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

    # -- interaction

    def go_to(self, row: int) -> None:
        """Move the sky moment to an event and select the subcycle of the panel's depth that contains it."""
        if not 0 <= row < len(self._rows):
            return
        year = self._rows[row]
        state = self.state
        address = tuple(int(d) for d in state.time_map.subcycle_at(year, self.depth.value()))
        state.reveal(address)
        state.set_sky_time(year)
