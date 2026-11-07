"""
The sky of a class of subcycles: small sky charts at the starts (or middles,
or ends) of the subcycles that share the selection's composition, its
duration or its ⟨σ⟩ orbit, or of the selection's parts, and how concentrated
each body's sidereal longitude is across all of them.

The concentration of n longitudes is the length R of their mean unit vector:
1 if they are all equal, about √(π / 4n) for n random ones; so R well above
that value means the class tends to begin with that body in the same place.
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
    CycleState, address_of, children_range, date_text, equal_duration_indices, same_composition_indices, tcoord,
)

CLASSES = {
    'composition': 'Same composition',
    'duration': 'Equal duration',
    'orbit': '⟨σ⟩ orbit',
    'children': 'Parts of the selection',
}
MOMENTS = {'start': 'starts', 'middle': 'middles', 'end': 'ends'}
MAX_POSITIONS = 5000        # members whose positions are computed for the statistics
BODY_NAMES = {'sun': 'Sun', 'mercury': 'Mercury', 'venus': 'Venus', 'mars': 'Mars', 'jupiter': 'Jupiter',
              'saturn': 'Saturn', 'uranus': 'Uranus', 'neptune': 'Neptune', 'pluto': 'Pluto'}
SIGNS = ['Ari', 'Tau', 'Gem', 'Can', 'Leo', 'Vir', 'Lib', 'Sco', 'Sag', 'Cap', 'Aqu', 'Pis']


def concentration(longitudes_deg: np.ndarray) -> tuple[float, float]:
    """(circular mean in degrees, mean resultant length R) of longitudes."""
    angles = np.radians(np.asarray(longitudes_deg, dtype=float))
    c, s = np.cos(angles).mean(), np.sin(angles).mean()
    return float(np.degrees(np.arctan2(s, c)) % 360.0), float(np.hypot(c, s))


def random_concentration(n: int) -> float:
    """Expected R of ``n`` independent uniform longitudes (large n)."""
    return float(np.sqrt(np.pi / (4 * n))) if n else float('nan')


class SkyClassPanel(QWidget):
    """Sky charts of the subcycles of a class, and how concentrated each body is across them.

    Uses the ephemeris tables and the outer-planets option of the Sky panel."""

    saveRequested = Signal()     # the Save… button

    def __init__(self, sky_panel, state: CycleState, parent=None):
        super().__init__(parent)
        self.sky_panel = sky_panel
        self.state = state
        self._dirty = True
        self._members: list[tuple] = []         # (address, year) of the charts drawn
        self._axes = []
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.kind = QComboBox()
        for key, label in CLASSES.items():
            self.kind.addItem(label, key)
        if state.highlight in CLASSES:
            self.kind.setCurrentIndex(self.kind.findData(state.highlight))
        self.moment = QComboBox()
        for key, label in MOMENTS.items():
            self.moment.addItem(label, key)
        self.inside = QCheckBox('Only inside the zoom')
        self.charts = QSpinBox()
        self.charts.setRange(1, 64)
        self.charts.setValue(12)
        self.charts.setToolTip('How many charts to draw: evenly spread over the class when it has more subcycles')
        save_button = QToolButton()
        save_button.setText('Save…')
        save_button.setToolTip('Save this graph to a file (page size, resolution, format…)')
        save_button.clicked.connect(self.saveRequested)
        row.addWidget(QLabel('Class'))
        row.addWidget(self.kind)
        row.addWidget(QLabel('at their'))
        row.addWidget(self.moment)
        row.addWidget(self.inside)
        row.addWidget(QLabel('Charts'))
        row.addWidget(self.charts)
        row.addStretch(1)
        row.addWidget(save_button)
        layout.addLayout(row)
        self.heading = QLabel()
        self.heading.setWordWrap(True)
        layout.addWidget(self.heading)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.figure = Figure(figsize=(6, 5))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.mpl_connect('button_release_event', self._clicked)
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
        for widget in (self.kind, self.moment):
            widget.currentIndexChanged.connect(self._schedule)
        self.inside.toggled.connect(self._schedule)
        self.charts.valueChanged.connect(self._schedule)
        for signal in (state.selectionChanged, state.focusChanged, state.modelChanged, state.permutationChanged):
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
            return 'Sky of a class'
        names = ' › '.join(state.names[d] for d in state.selection)
        if self.kind.currentData() == 'children':
            return f"Sky of the parts of {names}"
        return f"Sky of the class: {self.kind.currentText().lower()} as {names}"

    # -- the class

    def members(self) -> tuple[np.ndarray, int, str]:
        """(indices, depth, explanation) of the subcycles of the chosen class, in time order."""
        state = self.state
        selection = state.selection
        if selection is None or not selection:
            return np.array([], dtype=int), 0, 'Select a subcycle.'
        kind = self.kind.currentData()
        depth = len(selection)
        level = state.cache.level(depth)
        if kind == 'composition':
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
        level = self.state.cache.level(depth)
        u = level.starts[indices] + {'start': 0.0, 'middle': 0.5, 'end': 1.0}[self.moment.currentData()] \
            * level.durations[indices]
        return np.asarray(self.state.time_map.to_physical(np.minimum(u, 1.0)), dtype=float)

    # -- drawing

    def render(self) -> None:
        self._dirty = False
        state = self.state
        self.figure.clear()
        self._axes, self._members = [], []
        self.table.setRowCount(0)
        tables = self.sky_panel.tables
        if state.time_map is None or not tables:
            self.heading.setText('Needs a cycle model and the ephemeris tables (see the Sky panel).')
            self.canvas.draw_idle()
            return
        indices, depth, problem = self.members()
        if not len(indices):
            self.heading.setText(problem or 'The class has no subcycles inside the zoom.')
            self.canvas.draw_idle()
            return
        from cycles.gui.sky import INNER_BODIES, OUTER_BODIES
        from cycles.plotting.equinoctial_precession import _PLANETS, _tdb_year, planet_positions
        bodies = INNER_BODIES + (OUTER_BODIES if self.sky_panel.outer.isChecked() else ())
        years = self.times(indices, depth)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            # every member (up to a limit) for the statistics
            step = max(1, int(np.ceil(len(indices) / MAX_POSITIONS)))
            longitudes = {body: [] for body in bodies}
            skipped = 0
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')          # DeltaT extrapolation outside -1999..3000
                for year in years[::step]:
                    try:
                        positions = planet_positions(_tdb_year(float(year), 'UT'), tables, bodies)
                    except ValueError:                   # outside the ephemeris
                        skipped += 1
                        continue
                    for body in bodies:
                        longitudes[body].append(positions[body]['sidereal'])
                self._draw_charts(indices, depth, years, bodies)
        finally:
            QApplication.restoreOverrideCursor()
        n = len(longitudes[bodies[0]])
        self.table.setRowCount(len(bodies))
        self.table.setMinimumHeight(self.table.horizontalHeader().sizeHint().height()
                                    + len(bodies) * self.table.verticalHeader().defaultSectionSize() + 4)
        expected = random_concentration(n)
        for row, body in enumerate(bodies):
            symbol = _PLANETS[body][1]
            name = BODY_NAMES.get(body, body)
            mean, r = concentration(longitudes[body]) if n else (float('nan'), float('nan'))
            sign, degrees = int(mean // 30) % 12, mean % 30
            items = [f"{symbol} {name}", f"{mean:.1f}°  ({degrees:.1f}° {SIGNS[sign]})", f"{r:.3f}",
                     f"{expected:.3f}"]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col == 2 and n > 1 and r > 3 * expected:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setToolTip('More than three times what random longitudes would give')
                self.table.setItem(row, col, item)
        names = ' › '.join(state.names[d] for d in state.selection)
        what = (f"the parts of {names}" if self.kind.currentData() == 'children'
                else f"{self.kind.currentText().lower()} as {names}")
        self.heading.setText(f"{len(indices)} subcycles of depth {depth} ({what}), at their "
                             f"{self.moment.currentText()}; {len(self._members)} charts.")
        notes = [f"Concentration over {n} of them" + (f" (one in {step})" if step > 1 else '') + '.',
                 'Bold: more than three times the value of random longitudes.']
        if skipped:
            notes.append(f"{skipped} outside the ephemeris tables.")
        notes.append('Click a chart to select its subcycle and show that moment in the Sky panel.')
        self.note.setText(' '.join(notes))

    def _draw_charts(self, indices: np.ndarray, depth: int, years: np.ndarray, bodies) -> None:
        from cycles.plotting.equinoctial_precession import plot_zodiac_with_planets
        state = self.state
        count = min(self.charts.value(), len(indices))
        chosen = np.unique(np.round(np.linspace(0, len(indices) - 1, count)).astype(int))
        columns = int(np.ceil(np.sqrt(len(chosen) * 1.3)))
        rows = int(np.ceil(len(chosen) / columns))
        selection = state.selection
        for k, position in enumerate(chosen):
            address = address_of(int(indices[position]), depth)
            year = float(years[position])
            ax = self.figure.add_subplot(rows, columns, k + 1, projection='polar')
            try:
                plot_zodiac_with_planets(year, self.sky_panel.tables, bodies=bodies, ax=ax, show=False, table=False,
                                         compact=True, time_scale='UT', epoch_display=(), sign_labels='symbol')
            except ValueError:
                ax.set_axis_off()
                ax.text(0.5, 0.5, 'outside the\nephemeris', transform=ax.transAxes, ha='center', fontsize=7)
            initials = ''.join(state.names[d][0] for d in address)
            ax.set_title('')
            # under its chart (a title would sit closer to the chart above)
            ax.text(0.5, -0.02, f"{initials}\n{date_text(year)}", transform=ax.transAxes, ha='center', va='top',
                    fontsize=7, color='#1f77b4' if address == selection else 'black',
                    fontweight='bold' if address == selection else 'normal')
            ax._class_member = (address, year)
            self._axes.append(ax)
            self._members.append((address, year))
        self.figure.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.06, wspace=0.05, hspace=0.3)
        self.canvas.draw_idle()

    # -- interaction

    def _clicked(self, event) -> None:
        if event.button != 1 or event.inaxes is None or not hasattr(event.inaxes, '_class_member'):
            return
        address, year = event.inaxes._class_member
        self.state.reveal(address)
        self.state.set_sky_time(year)
