"""
Sky panel: the zodiac with the planets at a moment of the selected subcycle,
from the N-body ephemeris tables, and a slider to move through the subcycle.

The chart is ``equinoctial_precession.plot_zodiac_with_planets``, drawn into
an embedded Matplotlib canvas. The ephemeris tables are looked for in
``$CYCLES_EPHEMERIS``, then in the folder chosen last time, then in
``sandbox/data/tabla70k70k`` of the source tree.
"""

import os
import warnings
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QSettings, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton, QSizePolicy,
    QSlider, QSplitter, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)

from cycles.gui.state import CycleState, date_text, datetime_text, span_text

INNER_BODIES = ('sun', 'mercury', 'venus', 'mars', 'jupiter', 'saturn')
OUTER_BODIES = ('uranus', 'neptune', 'pluto')
BODY_NAMES = {'sun': 'Sun', 'mercury': 'Mercury', 'venus': 'Venus', 'mars': 'Mars', 'jupiter': 'Jupiter',
              'saturn': 'Saturn', 'uranus': 'Uranus', 'neptune': 'Neptune', 'pluto': 'Pluto'}
SIGNS = ('Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn',
         'Aquarius', 'Pisces')
SLIDER_STEPS = 10000     # positions of the slider across the span
FRAME_DELAYS = {'Fast': 50, 'Normal': 120, 'Slow': 300}   # milliseconds between frames
STEP_UNITS = {'years': 1.0, 'days': 1 / 365.25, 'hours': 1 / 8766.0}   # in years
DEFAULT_TABLE = Path(__file__).resolve().parents[2] / 'sandbox' / 'data' / 'tabla70k70k'
SETTINGS_KEY = 'sky/ephemeris'


def ephemeris_parts(path) -> list[Path]:
    """
    Table folders of an ephemeris: ``path`` itself if it is one table (it holds
    ``meta.json``), else its ``back`` and ``forward`` subfolders that exist.
    """
    path = Path(path)
    if (path / 'meta.json').is_file():
        return [path]
    return [path / part for part in ('back', 'forward') if (path / part / 'meta.json').is_file()]


def find_ephemeris() -> Path | None:
    """The first usable ephemeris among the environment, the settings and the default location."""
    candidates = [os.environ.get('CYCLES_EPHEMERIS'), QSettings().value(SETTINGS_KEY), DEFAULT_TABLE]
    for candidate in candidates:
        if candidate and ephemeris_parts(candidate):
            return Path(candidate)
    return None


def degrees_text(degrees: float) -> str:
    """Degrees and minutes: ``12°34′``."""
    minutes = round(degrees * 60)
    return f"{minutes // 60}°{minutes % 60:02d}′"


class SkyPanel(QWidget):
    """
    Zodiac chart at a moment of the zoomed span (what the navigator shows). The
    slider and the playback cover that span; Shift+click on the navigator also
    sets the moment. With Follow on, every plot highlights its subcycle that
    contains the moment.
    """

    saveRequested = Signal()     # the Save… button
    compareRequested = Signal()  # the Compare… button: show the Sky comparison panel
    ephemerisChanged = Signal()

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        self.tables = None
        self.ephemeris_path: Path | None = None
        self._interval: tuple[float, float] | None = None
        self._span = None            # (zoomed address, cycle model) the slider covers
        self._dirty = True

        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.source = QLabel()
        self.source.setWordWrap(True)
        open_button = QPushButton('Ephemeris…')
        open_button.setToolTip('Folder of an ephemeris table (with back/ and forward/), '
                               'built with python -m cycles.functions.nbody_ephemeris')
        open_button.clicked.connect(self.choose_ephemeris)
        save_button = QToolButton()
        save_button.setText('Save…')
        save_button.setToolTip('Save this graph to a file (page size, resolution, format…)')
        save_button.clicked.connect(self.saveRequested)
        class_button = QToolButton()
        class_button.setText('Compare…')
        class_button.setToolTip('Open the Sky comparison panel: the skies of other subcycles (all of the '
                                'selection\'s depth,\nor its class), the closest to the selection\'s, and how '
                                'concentrated each body is across them')
        class_button.clicked.connect(self.compareRequested)
        row.addWidget(self.source, 1)
        row.addWidget(open_button)
        row.addWidget(class_button)
        row.addWidget(save_button)
        layout.addLayout(row)

        self.subcycle = QLabel()
        self.subcycle.setWordWrap(True)
        layout.addWidget(self.subcycle)
        self.inside = QLabel()
        self.inside.setWordWrap(True)
        self.inside.setToolTip('The subcycles that contain the moment, down to the deepest level shown')
        layout.addWidget(self.inside)

        row = QHBoxLayout()
        self.start_button = self._tool('⏮', 'Start of the span', lambda: self.slider.setValue(0))
        self.play_button = self._tool('▶', 'Play from the moment to the end of the span', self.toggle_play)
        self.end_button = self._tool('⏭', 'End of the span', lambda: self.slider.setValue(SLIDER_STEPS))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, SLIDER_STEPS)
        self.slider.setPageStep(SLIDER_STEPS // 20)
        self.slider.valueChanged.connect(self._slider_moved)
        row.addWidget(self.start_button)
        row.addWidget(self.play_button)
        row.addWidget(self.slider, 1)
        row.addWidget(self.end_button)
        layout.addLayout(row)

        row = QHBoxLayout()
        self.moment = QLabel()
        self.moment.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.to_date_button = QPushButton('To marked date')
        self.to_date_button.setToolTip('Move the chart to the marked date (if it is inside the span)')
        self.to_date_button.clicked.connect(self.go_to_marked_date)
        self.mark_button = QPushButton('Mark this moment')
        self.mark_button.setToolTip('Make this moment the marked date')
        self.mark_button.clicked.connect(lambda: state.set_date(state.sky_time))
        row.addWidget(self.moment, 1)
        row.addWidget(self.to_date_button)
        row.addWidget(self.mark_button)
        layout.addLayout(row)

        row = QHBoxLayout()
        self.follow = QCheckBox('Follow')
        self.follow.setChecked(state.follow)
        self.follow.setToolTip('Highlight, in every plot, its subcycle that contains the moment')
        self.follow.toggled.connect(state.set_follow)
        row.addWidget(self.follow)
        row.addSpacing(12)
        row.addWidget(QLabel('Step'))
        self.step = QDoubleSpinBox()
        self.step.setRange(0.001, 100000)
        self.step.setDecimals(3)
        self.step.setValue(10)
        self.step.setToolTip('How far the moment advances at each frame')
        self.step_unit = QComboBox()
        self.step_unit.addItems(list(STEP_UNITS))
        self.delay = QComboBox()
        for label, ms in FRAME_DELAYS.items():
            self.delay.addItem(label, ms)
        self.delay.setCurrentText('Normal')
        self.delay.setToolTip('Time between frames (the chart also takes about 0.1 s to draw)')
        self.delay.currentIndexChanged.connect(lambda _: self.play_timer.setInterval(self.delay.currentData()))
        self.step_label = QLabel()
        for widget in (self.step, self.step_unit, self.delay, self.step_label):
            row.addWidget(widget)
        self.step.valueChanged.connect(self._update_step)
        self.step_unit.currentIndexChanged.connect(self._update_step)
        row.addStretch(1)
        layout.addLayout(row)

        self.outer = QCheckBox('Uranus, Neptune and Pluto')
        self.outer.toggled.connect(self._schedule)
        layout.addWidget(self.outer)

        self.figure = Figure(figsize=(5, 5), layout=None)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.mpl_connect('resize_event', self.fit_chart)
        self.ax = None
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setMinimumSize(260, 260)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['Body', 'Sidereal', 'Sign', 'Nakshatra'])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        header = self.table.horizontalHeader()
        for col in range(3):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.table)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        self.table.setMinimumHeight(self.table.verticalHeader().defaultSectionSize() * 4
                                    + self.table.horizontalHeader().sizeHint().height())
        layout.addWidget(splitter, 1)

        self.play_timer = QTimer(self)
        self.play_timer.setInterval(FRAME_DELAYS['Normal'])
        self.play_timer.timeout.connect(self._play_step)
        # Coalesce quick changes (dragging the slider) into one redraw
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(0)
        self.render_timer.timeout.connect(self.render)

        state.focusChanged.connect(self._retarget)
        state.viewChanged.connect(self._retarget)        # the cycle model, the names
        state.dateChanged.connect(self._update_buttons)
        state.skyTimeChanged.connect(self._sky_time_changed)

        self.load_ephemeris(find_ephemeris())
        self._retarget()

    @staticmethod
    def _tool(text: str, tip: str, slot) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tip)
        button.clicked.connect(slot)
        return button

    # -- ephemeris

    def load_ephemeris(self, path) -> None:
        import cycles.functions.nbody_ephemeris as nbe
        self.tables = None
        self.ephemeris_path = None
        if path is not None:
            try:
                self.tables = [nbe.load_ephemeris(part) for part in ephemeris_parts(path)] or None
                self.ephemeris_path = Path(path) if self.tables else None
            except (OSError, ValueError, KeyError) as error:
                self.source.setText(f"Cannot read the ephemeris in {path}: {error}")
                self._schedule()
                self.ephemerisChanged.emit()
                return
        self.state.set_ephemeris(self.tables, self.ephemeris_path)
        if self.tables:
            self.source.setText(f"Ephemeris: {self.ephemeris_path.name}")
            self.source.setToolTip(str(self.ephemeris_path))
        else:
            self.source.setText('No ephemeris found. Build one (see the README) or choose its folder.')
        self._schedule()
        self.ephemerisChanged.emit()

    def choose_ephemeris(self) -> None:
        start = str(self.ephemeris_path or DEFAULT_TABLE.parent)
        path = QFileDialog.getExistingDirectory(self, 'Ephemeris folder', start)
        if not path:
            return
        if not ephemeris_parts(path):
            self.source.setText(f"{path} holds no ephemeris table (meta.json, or back/ and forward/).")
            return
        QSettings().setValue(SETTINGS_KEY, path)
        self.load_ephemeris(path)

    # -- the span and the moment

    def _retarget(self, *_) -> None:
        """When the zoom or the cycle model changes, cover the new span (keeping the moment if it is inside)."""
        state = self.state
        span = (state.focus, state.model)
        if span == self._span:
            self._update_buttons()       # the names may have changed
            return
        self._span = span
        self._interval = state.physical_interval(state.focus)
        names = ' › '.join(state.names[d] for d in state.focus) or 'Whole cycle'
        if self._interval is None:
            self.stop()
            self.subcycle.setText(names)
            state.set_sky_time(None)
        else:
            t0, t1 = self._interval
            self.subcycle.setText(f"<b>{names}</b>: {date_text(t0)} to {date_text(t1)} ({span_text(t1 - t0)})")
            moment = state.sky_time
            if moment is None or not t0 <= moment <= t1:
                moment = state.date if state.date is not None and t0 <= state.date <= t1 else t0
                self.stop()
            if moment == state.sky_time:
                self._sky_time_changed(moment)       # no signal comes: update the slider directly
            else:
                state.set_sky_time(moment)
        for widget in (self.slider, self.start_button, self.end_button, self.play_button):
            widget.setEnabled(self._interval is not None)
        self._update_buttons()
        self._update_step()
        self._schedule()

    def _slider_moved(self, value: int) -> None:
        if self._interval is not None:
            t0, t1 = self._interval
            self.state.set_sky_time(t0 + (t1 - t0) * value / SLIDER_STEPS)

    def _sky_time_changed(self, year) -> None:
        if year is not None and self._interval is not None:
            t0, t1 = self._interval
            self.slider.blockSignals(True)
            self.slider.setValue(round((year - t0) / (t1 - t0) * SLIDER_STEPS) if t1 > t0 else 0)
            self.slider.blockSignals(False)
        self._update_buttons()
        self._update_step()
        self._schedule()

    def step_years(self) -> float:
        """The time step of the animation, in years."""
        return self.step.value() * STEP_UNITS[self.step_unit.currentText()]

    def _update_step(self, *_) -> None:
        if self._interval is None or self.state.sky_time is None:
            self.step_label.setText('')
            return
        frames = (self._interval[1] - self.state.sky_time) / self.step_years()
        self.step_label.setText(f"{frames:,.0f} frames to the end of the span")

    def _update_buttons(self, *_) -> None:
        state = self.state
        inside = (self._interval is not None and state.date is not None
                  and self._interval[0] <= state.date <= self._interval[1])
        self.to_date_button.setEnabled(inside)
        self.mark_button.setEnabled(state.sky_time is not None)
        if state.sky_time is None:
            self.moment.setText('Choose a cycle model (not normalized time) to see the sky.' if self._interval is None else '')
            self.inside.setText('')
            return
        self.moment.setText(f"<b>{datetime_text(state.sky_time)}</b>  ({state.sky_time:.4f})")
        depths = state.visible_depths()
        address = state.subcycle_at(state.sky_time, depths[-1]) if len(depths) else None
        self.inside.setText('In ' + ' › '.join(state.names[d] for d in address) if address else '')

    def go_to_marked_date(self) -> None:
        self.state.set_sky_time(self.state.date)

    # -- playing

    def toggle_play(self) -> None:
        if self.play_timer.isActive():
            self.stop()
        elif self._interval is not None:
            t0, t1 = self._interval
            if self.state.sky_time is None or self.state.sky_time >= t1:
                self.state.set_sky_time(t0)
            self.play_timer.start()
            self.play_button.setText('⏸')

    def stop(self) -> None:
        self.play_timer.stop()
        self.play_button.setText('▶')

    def _play_step(self) -> None:
        """Advance the moment by one time step, up to the end of the span."""
        if self._interval is None or self.state.sky_time is None:
            self.stop()
            return
        t1 = self._interval[1]
        year = min(t1, self.state.sky_time + self.step_years())
        self.state.set_sky_time(year)
        if year >= t1:
            self.stop()

    # -- drawing

    def _schedule(self, *_) -> None:
        self._dirty = True
        if self.isVisible():
            self.render_timer.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._dirty:
            self.render_timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.stop()

    def fit_chart(self, *_) -> None:
        """
        Make the disk as large as the canvas allows, keeping the labels around
        it (which keep their size in points) inside: measure how far they reach
        beyond the disk, size the disk to fit, and repeat once with the new size.
        """
        ax = getattr(self, 'ax', None)
        if ax is None or ax.figure is not self.figure:
            return
        width, height = self.figure.bbox.width, self.figure.bbox.height
        if width < 10 or height < 10:
            return
        renderer = self.canvas.get_renderer()
        side = 0.6 * min(width, height)
        x0, y0 = (width - side) / 2, (height - side) / 2
        for _ in range(3):
            ax.set_position([x0 / width, y0 / height, side / width, side / height])
            disk = ax.get_window_extent(renderer)
            labels = ax.get_tightbbox(renderer)
            left, right = disk.x0 - labels.x0, labels.x1 - disk.x1
            bottom, top = disk.y0 - labels.y0, labels.y1 - disk.y1
            pad = 4.0
            side = max(20.0, min(width - left - right - 2 * pad, height - bottom - top - 2 * pad))
            # centre the disk with its labels in the canvas
            x0 = (width - (side + left + right)) / 2 + left
            y0 = (height - (side + bottom + top)) / 2 + bottom
        ax.set_position([x0 / width, y0 / height, side / width, side / height])
        self.canvas.draw_idle()

    def _message(self, text: str) -> None:
        self.ax = None
        self.figure.clear()
        self.figure.text(0.5, 0.5, text, ha='center', va='center', wrap=True, color='#555555')
        self.canvas.draw_idle()
        self.table.setRowCount(0)

    def render(self) -> None:
        """Draw the chart and fill the table for the current moment."""
        from cycles.plotting.equinoctial_precession import _NAKSHATRAS, _PLANETS, plot_zodiac_with_planets

        self._dirty = False
        year = self.state.sky_time
        if year is None:
            self._message('Choose a cycle model\nto see the sky.')
            return
        if not self.tables:
            self._message('No ephemeris tables.\nUse "Ephemeris…" to choose their folder.')
            return
        bodies = INNER_BODIES + (OUTER_BODIES if self.outer.isChecked() else ())
        self.figure.clear()
        ax = self.figure.add_subplot(111, projection='polar')
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')      # DeltaT extrapolation outside -1999..3000
                _, _, positions = plot_zodiac_with_planets(
                    year, self.tables, bodies=bodies, ax=ax, show=False, table=False, time_scale='UT',
                    epoch_display=(), sign_labels='symbol')
        except (ValueError, KeyError, IndexError) as error:
            self._message(f"Cannot compute the sky at {date_text(year)}:\n{error}")
            return
        ax.set_title('')
        self.ax = ax
        self.fit_chart()
        self.canvas.draw_idle()

        self.table.setRowCount(len(positions))
        width = 360 / 27
        for row, (body, data) in enumerate(positions.items()):
            longitude = data['sidereal']
            sign, offset = divmod(longitude, 30)
            nakshatra = int(longitude // width)
            pada = int((longitude % width) // (width / 4)) + 1
            symbol = _PLANETS.get(body, ('', '', ''))[1]
            items = [f"{symbol} {BODY_NAMES.get(body, body)}", degrees_text(longitude),
                     f"{SIGNS[int(sign)]} {degrees_text(offset)}", f"{_NAKSHATRAS[nakshatra]} ({pada})"]
            for col, text in enumerate(items):
                self.table.setItem(row, col, QTableWidgetItem(text))
