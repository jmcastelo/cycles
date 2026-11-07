"""
The model landscape: how far the two criteria for dividing the cycle (4:3:2:1
of the precession arc and 4:3:2:1 of the years) disagree, for every anchor
and arc of the cycle model, with the current model as a point that can be
dragged (or moved with a double click) to place the cycle elsewhere: every
panel follows.

Below the map, the precession rate along the same years, with the span of the
current cycle: the mismatch repeats about every 20,000 years along the
anchors because the rate varies with the obliquity, about every 41,000 years,
and each yuga's share deviates one way while the rate rises and the other way
while it falls; the size of the deviation, without its sign, peaks twice per
period.
"""

import time

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.colors import LogNorm
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from cycles.functions.cycle_analysis import MEASURES, anchor_fields, mismatch_grid, precession_rate
from cycles.functions.cycle_model import ANCHOR_LABELS
from cycles.gui.state import CycleState, date_text

RESOLUTIONS = {'coarse': ('Coarse', 80, 30), 'medium': ('Medium', 160, 60), 'fine': ('Fine', 320, 120)}
YEAR_LIMIT = 190_000          # anchors (years from J2000, about) within the long-term precession model
MODEL_COLOR = '#1f77b4'
PICK_PIXELS = 10.0
FIRST_BATCH_DELAY = 250   # ms
BATCH_SECONDS = 0.08       # computing between redraws while the landscape fills in


def year_label(value, _=None) -> str:
    """Tick label of an astronomical year: thousands separated by thin spaces."""
    return f"{value:,.0f}".replace(',', ' ').replace('-', '−')


class LandscapePanel(QWidget):
    """The mismatch of the two division criteria over anchor × arc, with the model as a movable point."""

    saveRequested = Signal()     # the Save… button

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        self._dirty = True
        self._grid_key = None
        self.grid = None                        # (anchors, arcs) mismatch; NaN while pending
        self.anchors = self.turns = None
        self._pending: list[int] = []           # arc columns still to compute
        self._image = self._marker = self._best = None
        self.ax = self.rate_ax = None
        self._drag = None                       # the model's (anchor, turns) when a drag started
        self.best = None                        # (anchor, turns, value) of the smallest mismatch in the grid
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.depth = QSpinBox()
        self.depth.setRange(1, 3)
        self.depth.setToolTip('1: the four yugas; 2: also their parts; 3: one level more')
        self.measure = QComboBox()
        for key, label in MEASURES.items():
            self.measure.addItem(label, key)
        self.measure.setToolTip('Of the time shares from 0.4, 0.3, 0.2, 0.1 when dividing the arc, over the parts '
                                'of all subcycles at that depth')
        self.resolution = QComboBox()
        for key, (label, _, _) in RESOLUTIONS.items():
            self.resolution.addItem(label, key)
        self.resolution.setCurrentIndex(self.resolution.findData('medium'))
        save_button = QToolButton()
        save_button.setText('Save…')
        save_button.setToolTip('Save this graph to a file (page size, resolution, format…)')
        save_button.clicked.connect(self.saveRequested)
        row.addWidget(QLabel('Depth'))
        row.addWidget(self.depth)
        row.addWidget(self.measure)
        row.addWidget(QLabel('Resolution'))
        row.addWidget(self.resolution)
        row.addStretch(1)
        row.addWidget(save_button)
        layout.addLayout(row)

        row = QHBoxLayout()
        self.anchor_from, self.anchor_to = QSpinBox(), QSpinBox()
        for box, value in ((self.anchor_from, -60_000), (self.anchor_to, 60_000)):
            box.setRange(-YEAR_LIMIT, YEAR_LIMIT)
            box.setSingleStep(1000)
            box.setGroupSeparatorShown(True)
            box.setValue(value)
            box.setKeyboardTracking(False)
        self.turns_from, self.turns_to = QDoubleSpinBox(), QDoubleSpinBox()
        for box, value in ((self.turns_from, 0.5), (self.turns_to, 5.0)):
            box.setRange(0.1, 10.0)
            box.setSingleStep(0.25)
            box.setDecimals(2)
            box.setValue(value)
            box.setKeyboardTracking(False)
        around = QPushButton('Around the model')
        around.setToolTip('Anchors ±40,000 years and arcs ±1.5 turns around the current model')
        around.clicked.connect(self.around_model)
        self.anchor_label = QLabel('Anchor years')
        row.addWidget(self.anchor_label)
        row.addWidget(self.anchor_from)
        row.addWidget(QLabel('to'))
        row.addWidget(self.anchor_to)
        row.addWidget(QLabel('  Arc'))
        row.addWidget(self.turns_from)
        row.addWidget(QLabel('to'))
        row.addWidget(self.turns_to)
        row.addWidget(QLabel('turns'))
        row.addWidget(around)
        row.addStretch(1)
        layout.addLayout(row)

        self.readout = QLabel()
        self.readout.setWordWrap(True)
        layout.addWidget(self.readout)
        self.figure = Figure(figsize=(6, 5))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.canvas.mpl_connect('button_press_event', self._pressed)
        self.canvas.mpl_connect('motion_notify_event', self._moved)
        self.canvas.mpl_connect('button_release_event', self._released)
        self.canvas.mpl_connect('key_press_event', self._key)
        layout.addWidget(self.canvas, 1)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setStyleSheet('color: palette(placeholder-text)')
        layout.addWidget(self.note)

        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(0)
        self.render_timer.timeout.connect(self.render)
        self.compute_timer = QTimer(self)
        self.compute_timer.setSingleShot(True)
        self.compute_timer.setInterval(0)
        self.compute_timer.timeout.connect(self._compute_next)
        for widget in (self.measure, self.resolution):
            widget.currentIndexChanged.connect(self._schedule)
        for box in (self.depth, self.anchor_from, self.anchor_to, self.turns_from, self.turns_to):
            box.valueChanged.connect(self._schedule)
        state.modelChanged.connect(self._schedule)
        state.presetsChanged.connect(self._schedule)

    # -- scheduling

    def _schedule(self, *_) -> None:
        self._dirty = True
        if self.isVisible():
            self.render_timer.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._dirty:
            self.render_timer.start()
        elif self._pending:
            self.compute_timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.compute_timer.stop()             # resumed when shown again

    def title(self) -> str:
        model = self.state.model
        name = f" · {model.name}" if model is not None else ''
        return f"Model landscape: {self.measure.currentText().lower()} at depth {self.depth.value()}{name}"

    def around_model(self) -> None:
        position = self.model_position()
        if position is None:
            return
        anchor, turns = position
        boxes = (self.anchor_from, self.anchor_to, self.turns_from, self.turns_to)
        for box in boxes:
            box.blockSignals(True)
        self.anchor_from.setValue(int(round(anchor - 40_000, -3)))
        self.anchor_to.setValue(int(round(anchor + 40_000, -3)))
        self.turns_from.setValue(max(0.1, round(turns - 1.5, 2)))
        self.turns_to.setValue(round(turns + 1.5, 2))
        for box in boxes:
            box.blockSignals(False)
        self._schedule()

    # -- the grid

    def model_position(self) -> tuple[float, float] | None:
        """(anchor year, turns) of the current model, or None."""
        model = self.state.model
        if model is None:
            return None
        solution = model.solve()
        return float(solution['anchor']), float(solution['turns'])

    def _key_of_grid(self):
        model = self.state.model
        _, columns, rows = RESOLUTIONS[self.resolution.currentData()]
        a0, a1 = sorted((self.anchor_from.value(), self.anchor_to.value()))
        t0, t1 = sorted((self.turns_from.value(), self.turns_to.value()))
        return (model.anchor_point, model.precession, model.period, self.depth.value(), self.measure.currentData(),
                a0, a1, t0, t1, columns, rows)

    def _compute_next(self) -> None:
        """Compute the next arc column of the grid (keeps the window responsive)."""
        if not self._pending or self.state.model is None:
            return
        started = time.perf_counter()
        while self._pending and time.perf_counter() - started < BATCH_SECONDS:     # then one redraw
            j = self._pending.pop(0)
            self.grid[:, j] = mismatch_grid(self.state.model, self.anchors, self.turns[j:j + 1], self.depth.value(),
                                            self.measure.currentData())[:, 0]
        self._update_image()
        if self._pending:
            self.compute_timer.start(0)
        else:
            self._draw_best()
            self._show_summary()

    def finish(self) -> None:
        """Compute what is left of the grid at once (before saving)."""
        if self._dirty:
            self.render()
        if self.state.model is None or not self._pending:
            return
        columns = np.array(self._pending)
        self._pending = []
        self.grid[:, columns] = mismatch_grid(self.state.model, self.anchors, self.turns[columns],
                                              self.depth.value(), self.measure.currentData())
        self._update_image()
        self._draw_best()
        self._show_summary()

    # -- drawing

    def render(self) -> None:
        self._dirty = False
        state, model = self.state, self.state.model
        self.figure.clear()
        self.ax = self.rate_ax = self._image = self._marker = self._best = None
        self.compute_timer.stop()
        if model is None:
            self._pending = []
            self.readout.setText('Choose a cycle model (toolbar).')
            self.note.setText('')
            self.canvas.draw_idle()
            return
        self.anchor_label.setText(f"{ANCHOR_LABELS[model.anchor_point]}, years")
        if model.precession == 'constant':
            self._pending = []
            self.figure.text(0.5, 0.5, 'With a constant precession rate the two criteria coincide\n'
                                       'for every anchor and arc: there is no landscape.',
                             ha='center', va='center', color='#555555')
            self.readout.setText('')
            self.note.setText('')
            self.canvas.draw_idle()
            return
        key = self._key_of_grid()
        if key != self._grid_key:
            _, columns, rows = RESOLUTIONS[self.resolution.currentData()]
            a0, a1, t0, t1 = key[5:9]
            self.anchors = np.linspace(a0, a1, columns)
            self.turns = np.linspace(t0, t1, rows)
            self.grid = np.full((columns, rows), np.nan)
            self.best = None
            # from the model's arc outwards, so the part around it appears first
            position = self.model_position()
            centre = position[1] if position else (t0 + t1) / 2
            self._pending = list(np.argsort(np.abs(self.turns - centre), kind='stable'))
            self._grid_key = key
        self._draw()
        if self._pending:
            self.compute_timer.start(FIRST_BATCH_DELAY)       # the panel is painted first
        else:
            self._draw_best()
            self._show_summary()

    def _draw(self) -> None:
        state, model = self.state, self.state.model
        grid = self.figure.add_gridspec(2, 2, height_ratios=[4, 1], width_ratios=[40, 1], left=0.1, right=0.92,
                                        top=0.97, bottom=0.09, hspace=0.08, wspace=0.03)
        ax = self.ax = self.figure.add_subplot(grid[0, 0])
        rate_ax = self.rate_ax = self.figure.add_subplot(grid[1, 0], sharex=ax)
        cax = self.figure.add_subplot(grid[0, 1])
        da = (self.anchors[-1] - self.anchors[0]) / max(1, len(self.anchors) - 1)
        dt = (self.turns[-1] - self.turns[0]) / max(1, len(self.turns) - 1)
        extent = (self.anchors[0] - da / 2, self.anchors[-1] + da / 2, self.turns[0] - dt / 2,
                  self.turns[-1] + dt / 2)
        import matplotlib
        cmap = matplotlib.colormaps['viridis_r'].with_extremes(bad='#d9d9d9')
        self._image = ax.imshow(np.ma.masked_invalid(self.grid.T), origin='lower', extent=extent, aspect='auto',
                                cmap=cmap, norm=LogNorm(1e-4, 1e-2), interpolation='nearest')
        bar = self.figure.colorbar(self._image, cax=cax)
        bar.set_label(f"{self.measure.currentText()} of the time shares", fontsize=8)
        bar.ax.tick_params(labelsize=7)
        ax.set_ylabel('Arc (turns)', fontsize=8)
        ax.tick_params(labelsize=7, labelbottom=False)
        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])

        # the presets that share the model's anchor point and precession (named in the readout on hover:
        # several are often a few years apart, the same point at this scale)
        self._presets = []
        for name, preset in state.presets.items():
            if (preset.anchor_point != model.anchor_point or preset.precession != model.precession
                    or preset == model):
                continue
            try:
                solution = preset.solve()
            except ValueError:
                continue
            ax.scatter([solution['anchor']], [solution['turns']], marker='^', s=30, facecolors='white',
                       edgecolors='black', linewidths=0.8, zorder=4)
            self._presets.append((name, float(solution['anchor']), float(solution['turns'])))
        position = self.model_position()
        if position is not None:
            self._marker = ax.scatter([position[0]], [position[1]], s=90, facecolors='white',
                                      edgecolors=MODEL_COLOR, linewidths=2.2, zorder=6)

        # the precession rate along the same years, with the span of the cycle
        years = np.linspace(extent[0], extent[1], 1500)
        rate_ax.plot(years, precession_rate(model, years), color='#555555', linewidth=1)
        solution = model.solve()
        rate_ax.axvspan(solution['start'], solution['end'], color=MODEL_COLOR, alpha=0.12, linewidth=0)
        rate_ax.axvline(solution['anchor'], color=MODEL_COLOR, linewidth=1.2)
        rate_ax.set_ylabel('Rate (″/yr)', fontsize=8)
        rate_ax.set_xlabel(f"{ANCHOR_LABELS[model.anchor_point]} (year)", fontsize=8)
        rate_ax.tick_params(labelsize=7)
        rate_ax.xaxis.set_major_formatter(FuncFormatter(year_label))
        self._update_image(draw=False)
        self._show_readout(None)
        self.note.setText(
            'Drag the model (blue circle) or double-click to place the cycle there: every panel follows; Escape '
            'cancels a drag. Yellow: closest to 4:3:2:1 in both criteria. Triangles: presets (named when the '
            'pointer is over them); star: the best point in the range. Grey: the cycle leaves the range of the precession model. Below: '
            'the precession rate, with the span of the current cycle. The landscape repeats about every 20,000 '
            'years along the anchors: the rate varies with the obliquity, about every 41,000 years, and each '
            'yuga\'s share deviates one way while the rate rises and the other way while it falls; the size of '
            'the deviation peaks twice per period.')
        self.canvas.draw_idle()

    def _update_image(self, draw: bool = True) -> None:
        if self._image is None:
            return
        self._image.set_data(np.ma.masked_invalid(self.grid.T))
        finite = self.grid[np.isfinite(self.grid) & (self.grid > 0)]
        if len(finite):
            low, high = max(float(finite.min()), 1e-7), float(finite.max())
            self._image.set_norm(LogNorm(low, max(high, low * 1.0001)))
        progress = 1 - len(self._pending) / max(1, len(self.turns))
        if self._pending:
            self.readout.setText(f"Computing the landscape… {100 * progress:.0f} %")
        if draw:
            self.canvas.draw_idle()

    def _draw_best(self) -> None:
        if self.ax is None or self.grid is None:
            return
        values = np.where(np.isfinite(self.grid), self.grid, np.inf)
        if not np.isfinite(values).any():
            return
        i, j = np.unravel_index(np.argmin(values), values.shape)
        if self._best is not None:
            self._best.remove()
        self._best = self.ax.scatter([self.anchors[i]], [self.turns[j]], marker='*', s=120, color='white',
                                     edgecolors='black', linewidths=0.8, zorder=5)
        self.best = (float(self.anchors[i]), float(self.turns[j]), float(values[i, j]))
        self.canvas.draw_idle()

    def value_at(self, anchor: float, turns: float) -> float:
        """The mismatch at a point, computed exactly (not read from the grid)."""
        return float(mismatch_grid(self.state.model, np.array([anchor]), np.array([turns]), self.depth.value(),
                                   self.measure.currentData())[0, 0])

    def _describe(self, anchor: float, turns: float) -> str:
        value = self.value_at(anchor, turns)
        shown = 'outside the precession model' if not np.isfinite(value) else f"{value:.4f}"
        return f"{ANCHOR_LABELS[self.state.model.anchor_point]} {date_text(anchor)}, {turns:.2f} turns: {shown}"

    def _show_readout(self, point) -> None:
        if self.state.model is None or self._pending:
            return
        if point is None:
            position = self.model_position()
            self.readout.setText(f"Model: {self._describe(*position)}" if position else '')
        else:
            near = self.presets_near(point)
            self.readout.setText(self._describe(*point) + (f" · preset{'s' if len(near) > 1 else ''}: "
                                                           f"{', '.join(near)}" if near else ''))

    def _show_summary(self) -> None:
        self._show_readout(None)
        if getattr(self, 'best', None) is not None:
            anchor, turns, value = self.best
            self.readout.setText(self.readout.text() + f" · best in this range ★: {date_text(anchor)}, "
                                                       f"{turns:.2f} turns: {value:.4f}")

    def presets_near(self, point) -> list[str]:
        """Names of the presets drawn within a few pixels of ``point`` (data coordinates)."""
        if self.ax is None:
            return []
        x, y = self.ax.transData.transform(point)
        names = []
        for name, anchor, turns in getattr(self, '_presets', []):
            px, py = self.ax.transData.transform((anchor, turns))
            if np.hypot(px - x, py - y) <= PICK_PIXELS:
                names.append(name)
        return names

    # -- moving the model

    def _near_marker(self, event) -> bool:
        if self._marker is None:
            return False
        x, y = self.ax.transData.transform(self._marker.get_offsets()[0])
        return np.hypot(event.x - x, event.y - y) <= PICK_PIXELS

    def _inside(self, event) -> tuple[float, float] | None:
        if event.inaxes is not self.ax or event.xdata is None:
            return None
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        return float(np.clip(event.xdata, x0, x1)), float(np.clip(event.ydata, max(y0, 0.05), y1))

    def _pressed(self, event) -> None:
        if event.button != 1 or event.inaxes is not self.ax:
            return
        if event.dblclick:
            point = self._inside(event)
            if point is not None:
                self.move_model(*point)
            return
        if self._near_marker(event):
            self._drag = tuple(self._marker.get_offsets()[0])

    def _moved(self, event) -> None:
        point = self._inside(event)
        if self._drag is not None and point is not None:
            self._marker.set_offsets([point])
            self.canvas.draw_idle()
        if point is not None and not self._pending:
            self._show_readout(point)

    def _released(self, event) -> None:
        if self._drag is None:
            return
        start, self._drag = self._drag, None
        point = self._inside(event)
        if point is None or np.allclose(point, start):
            self._marker.set_offsets([start])
            self.canvas.draw_idle()
            return
        self.move_model(*point)

    def _key(self, event) -> None:
        if event.key == 'escape' and self._drag is not None:
            self._marker.set_offsets([self._drag])
            self._drag = None
            self.canvas.draw_idle()
            self._show_readout(None)

    def move_model(self, anchor: float, turns: float) -> None:
        """Place the cycle with its anchor point at ``anchor`` (UT) and an arc of ``turns``."""
        model = self.state.model
        date, time = anchor_fields(anchor)
        moved = model.replace(anchor_date=date, anchor_time=time, anchor_longitude=0.0, anchor_ayanamsa=None,
                              turns=round(float(turns), 4), years=None)
        try:
            self.state.set_model(moved)
        except ValueError as error:
            self.readout.setText(f"Cannot place the cycle there: {error}")
            self._schedule()
