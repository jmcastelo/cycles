"""
Measures panel: dharma and purity of the subcycles of one level, linked with
the navigator, in 2D (against each other, time or index) or in 3D (dharma,
purity and time or index; drag to rotate). The selected subcycle is ringed;
with "Equal durations" on, so are those with its duration. Clicking a point
selects that subcycle.
"""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QSpinBox, QToolTip, QToolButton, QVBoxLayout, QWidget

from cycles.gui.state import MAX_DEPTH, MOMENT_COLOR, CycleState, address_of, children_range, tcoord
from cycles.plotting.generic import plot_y_vs_x
from cycles.plotting.measure import plot_purity_and_dharma, plot_quality_scatter_3d

# Plot kinds: label -> (y measure, x axis); x is 'dharma', 'index' or 'time'.
# The 3D kinds have y = '3d' and x the third axis (dharma and purity are the other two).
KINDS = {
    'Purity vs dharma': ('purity', 'dharma'),
    'Dharma vs time': ('dharma', 'time'),
    'Purity vs time': ('purity', 'time'),
    'Dharma vs index': ('dharma', 'index'),
    'Purity vs index': ('purity', 'index'),
    'Dharma, purity and time (3D)': ('3d', 'time'),
    'Dharma, purity and index (3D)': ('3d', 'index'),
}
# Camera presets of the 3D plots (dharma along x, purity along y, time or index along z),
# and the axis each one sees edge-on (its ticks are hidden)
EDGE_ON = {'top': 'z', 'dharma': 'y', 'purity': 'x'}
VIEWS_3D = {
    'oblique': ('Oblique', (22, -55, 0)),
    'top': ('Down the time axis: purity vs dharma', (90, -90, 0)),
    'dharma': ('From the side: dharma vs time', (0, -90, 0)),
    'purity': ('From the side: purity vs time', (0, 0, 0)),
}
PICK_RADIUS = 10    # pixels
DRAG_THRESHOLD = 4  # pixels moved between press and release that make it a rotation, not a click


class MeasuresPanel(QWidget):
    """Dharma and purity plots of the level of the selection (or a chosen depth)."""

    saveRequested = Signal()     # the Save… button

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        self._base = None            # what the drawn plot shows, to redraw only when it changes
        self._x = self._y = self._z = None
        self._press = None
        self.ax = None
        self._indices = np.array([], dtype=int)
        self._dirty = True

        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.kind = QComboBox()
        self.kind.addItems(list(KINDS))
        self.kind.currentIndexChanged.connect(self._schedule)
        row.addWidget(self.kind)
        row.addWidget(QLabel('Depth'))
        self.depth = QSpinBox()
        self.depth.setRange(0, MAX_DEPTH)
        self.depth.setSpecialValueText('auto')
        self.depth.setToolTip('Auto: the depth of the selection, or the level below the zoom')
        self.depth.valueChanged.connect(self._schedule)
        row.addWidget(self.depth)
        self.inside = QCheckBox('Only inside the zoom')
        self.inside.setChecked(True)
        self.inside.toggled.connect(self._schedule)
        row.addWidget(self.inside)
        self.sized = QCheckBox('Size by duration')
        self.sized.setChecked(True)
        self.sized.setToolTip('Point areas proportional to the durations of the subcycles')
        self.sized.toggled.connect(self._schedule)
        row.addWidget(self.sized)
        row.addStretch(1)
        self.view_label = QLabel('View')
        self.view = QComboBox()
        self.view.addItem('Free (drag to rotate)', None)
        for key, (label, _) in VIEWS_3D.items():
            self.view.addItem(label, key)
        self.view.setCurrentIndex(self.view.findData('oblique'))
        self.view.currentIndexChanged.connect(self._apply_view)
        row.addWidget(self.view_label)
        row.addWidget(self.view)
        save_button = QToolButton()
        save_button.setText('Save…')
        save_button.setToolTip('Save this graph to a file (page size, resolution, format…)')
        save_button.clicked.connect(self.saveRequested)
        row.addWidget(save_button)
        layout.addLayout(row)

        self.figure = Figure(figsize=(5, 4), layout='constrained')
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumSize(260, 220)
        self.canvas.mpl_connect('button_press_event', self._pressed)
        self.canvas.mpl_connect('button_release_event', self._released)
        self.canvas.mpl_connect('motion_notify_event', self._hovered)
        layout.addWidget(self.canvas, 1)
        self.info = QLabel()
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(0)
        self.render_timer.timeout.connect(self.render)
        for signal in (state.selectionChanged, state.focusChanged, state.viewChanged,
                       state.colorParametersChanged, state.skyTimeChanged, state.permutationChanged):
            signal.connect(self._schedule)

    # -- what to plot

    def plot_depth(self) -> int:
        state = self.state
        if self.depth.value():
            return self.depth.value()
        if state.selection is not None and len(state.selection) > len(state.focus):
            return len(state.selection)
        return min(MAX_DEPTH, len(state.focus) + 1)

    def scope(self, depth: int) -> tuple:
        """
        Address whose subcycles are plotted: the zoom (or, if ``depth`` is not
        below it, its ancestor one level above ``depth``), or the whole cycle.
        """
        focus = self.state.focus
        return focus[:min(len(focus), depth - 1)] if self.inside.isChecked() else ()

    # -- drawing

    def _schedule(self, *_) -> None:
        self._dirty = True
        if self.isVisible():
            self.render_timer.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._dirty:
            self.render_timer.start()

    def render(self) -> None:
        self._dirty = False
        state = self.state
        depth = self.plot_depth()
        scope = self.scope(depth)
        # redraw the plot only if what it shows changed: the point colors, and dharma or purity
        y_name, x_name = KINDS[self.kind.currentText()]
        measures = {'dharma', 'purity'} if y_name == '3d' else {y_name, x_name} & {'dharma', 'purity'}
        self.view_label.setVisible(y_name == '3d')
        self.view.setVisible(y_name == '3d')
        parameters = (state.parameters_of(state.color_key), *(state.parameters_of(m) for m in sorted(measures)))
        base = (self.kind.currentText(), depth, scope, state.color_key, state.model, state.names, parameters,
                self.sized.isChecked())
        if base != self._base:
            self._draw_base(depth, scope)
            self._base = base
        self._draw_highlights(depth)
        self.canvas.draw_idle()

    def point_sizes(self, durations: np.ndarray, scatter: bool):
        """
        Point areas: proportional to the durations (the longest gets the largest
        area) or all equal, smaller when there are many points. ``scatter``: the
        purity-dharma plot, whose points overlap less and can be larger.
        """
        many = len(durations) > 256
        if self.sized.isChecked():
            largest = (300 if scatter else 120) if not many else (150 if scatter else 60)
            return largest * durations / durations.max()
        return (40 if scatter else 16) if not many else (10 if scatter else 4)

    def _draw_base(self, depth: int, scope: tuple) -> None:
        state = self.state
        level = state.cache.level(depth)
        indices = np.arange(children_range(scope, depth).start, children_range(scope, depth).stop)
        part = level.subset(indices)
        colors = state.cache.colors(depth, state.color_key)[indices]
        y_name, x_name = KINDS[self.kind.currentText()]
        where = ' › '.join(state.names[d] for d in scope) or 'whole cycle'
        title = f"{self.kind.currentText()}, depth {depth} ({where})"

        camera = ((self.ax.elev, self.ax.azim, self.ax.roll) if self.ax is not None and self._z is not None
                  else self.__dict__.pop('_saved_camera', None))
        self.figure.clear()
        self._z = None
        sizes = self.point_sizes(part.durations, scatter=x_name == 'dharma' or y_name == '3d')
        if y_name == '3d':
            ax = self.figure.add_subplot(111, projection='3d')
            if x_name == 'index':
                z = indices.astype(float)
            else:
                z = part.starts + part.durations / 2
                if state.time_map is not None:
                    z = state.time_map.to_physical(z)
            plot_quality_scatter_3d(part, ax=ax, show=False, axis=x_name,
                                    values=z if x_name == 'index' or state.time_map is not None else None,
                                    colors=colors, sizes=sizes, path=True, alpha=0.9)
            ax.set_title(title, fontsize=9)
            ax.zaxis.set_major_locator(MaxNLocator(5))
            # plain numbers: the Unicode minus may be missing from the font at some angles
            ax.zaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}" if abs(v) >= 10 else f"{v:g}"))
            ax.tick_params(axis='z', pad=8)
            ax.zaxis.labelpad = 14
            edge_on = EDGE_ON.get(self.view.currentData())
            if edge_on:
                getattr(ax, f"set_{edge_on}ticklabels")([])
                getattr(ax, f"set_{edge_on}label")('')
            view = VIEWS_3D.get(self.view.currentData())
            ax.view_init(*(view[1] if view else camera if camera else VIEWS_3D['oblique'][1]))
            x, y = part.dharmas, part.purities
            self._z = np.asarray(z, dtype=float)
        elif x_name == 'dharma':
            ax = self.figure.add_subplot(111)
            plot_purity_and_dharma(ax, part, colors=colors, sizes=sizes)
            ax.set_title(title, fontsize=9)
            x, y = part.dharmas, part.purities
        else:
            y = part.dharmas if y_name == 'dharma' else part.purities
            if x_name == 'index':
                x, xlabel = indices.astype(float), 'Index'
            else:
                x = part.starts + part.durations / 2
                xlabel = 'Normalized time'
                if state.time_map is not None:
                    x, xlabel = state.time_map.to_physical(x), 'Year'
            ax = self.figure.add_subplot(111)
            plot_y_vs_x(x, y, (None, None), title, xlabel, y_name.capitalize(), ax=ax, show=False,
                        colors=colors, size=sizes)
            ax.title.set_fontsize(9)
            ax.xaxis.set_major_locator(MaxNLocator(5))
        self.ax = ax
        self._x, self._y, self._indices = np.asarray(x, dtype=float), np.asarray(y, dtype=float), indices
        self._highlights = []
        self.info.setText(f"{len(indices)} subcycles. Click a point to select it"
                          + ('; drag to rotate.' if self._z is not None else '.'))

    def _apply_view(self, *_) -> None:
        """A new camera preset: redraw (the axis seen edge-on changes)."""
        if self._z is not None:
            self._base = None
            self._schedule()

    def _draw_highlights(self, depth: int) -> None:
        state = self.state
        for artist in self._highlights:
            artist.remove()
        self._highlights = []
        positions = {int(i): k for k, i in enumerate(self._indices)}
        moment = positions.get(state.moment_index(depth))
        if moment is not None:
            self._highlights.append(self._ring([moment], s=200, color=MOMENT_COLOR, width=2.0))
        selection = state.selection
        if selection is None or len(selection) != depth:
            return
        bright = state.highlight_indices(selection)
        if bright is not None:
            equal = [positions[int(i)] for i in bright if int(i) in positions]
            if equal:
                self._highlights.append(self._ring(equal, s=90, color='black', width=0.8))
        k = positions.get(tcoord(selection))
        if k is not None:
            self._highlights.append(self._ring([k], s=260, color='#1f77b4', width=2.5))

    def _ring(self, points: list[int], s: float, color: str, width: float):
        """Hollow markers around the plotted points at positions ``points`` (2D or 3D)."""
        if self._z is not None:
            return self.ax.scatter(self._x[points], self._y[points], self._z[points], s=s, facecolors='none',
                                   edgecolors=color, linewidths=width, depthshade=False)
        return self.ax.scatter(self._x[points], self._y[points], s=s, facecolors='none', edgecolors=color,
                               linewidths=width, zorder=4)

    # -- interaction

    def _nearest(self, event) -> int | None:
        """Position in the plotted arrays of the point nearest the mouse (within ``PICK_RADIUS``)."""
        if self._x is None or self.ax is None or event.inaxes is not self.ax or not len(self._x):
            return None
        if self._z is not None:
            from mpl_toolkits.mplot3d import proj3d
            x, y, _ = proj3d.proj_transform(self._x, self._y, self._z, self.ax.get_proj())
            points = self.ax.transData.transform(np.column_stack([x, y]))
        else:
            points = self.ax.transData.transform(np.column_stack([self._x, self._y]))
        distances = np.hypot(points[:, 0] - event.x, points[:, 1] - event.y)
        k = int(np.argmin(distances))
        return k if distances[k] <= PICK_RADIUS * self.canvas.devicePixelRatioF() else None

    def _address(self, k: int) -> tuple:
        return address_of(int(self._indices[k]), self.plot_depth())

    def _pressed(self, event) -> None:
        self._press = (event.x, event.y) if event.button == 1 else None

    def _released(self, event) -> None:
        if self._press is None or event.button != 1:
            return
        moved = np.hypot(event.x - self._press[0], event.y - self._press[1])
        self._press = None
        if moved > DRAG_THRESHOLD:
            if self._z is not None and self.view.currentData() is not None:
                self.view.blockSignals(True)       # the user rotated the 3D view: it is now free
                self.view.setCurrentIndex(0)
                self.view.blockSignals(False)
            return
        k = self._nearest(event)
        if k is not None:
            self.state.reveal(self._address(k))

    def _hovered(self, event) -> None:
        if self._press is not None:
            return
        k = self._nearest(event)
        if k is None:
            QToolTip.hideText()
            return
        address = self._address(k)
        QToolTip.showText(QCursor.pos(), ' › '.join(self.state.names[d] for d in address)
                          + f"\ndharma {self.state.cache.level(len(address)).dharmas[self._indices[k]]:.4f}, "
                          f"purity {self.state.cache.level(len(address)).purities[self._indices[k]]:.4f}",
                          self.canvas)

    def camera(self) -> tuple | None:
        """(elevation, azimuth, roll) of the 3D view, or None."""
        ax = self.ax
        if ax is None or not hasattr(ax, 'elev') or self._z is None:
            return getattr(self, '_saved_camera', None)
        return (float(ax.elev), float(ax.azim), float(ax.roll))

    def restore_camera(self, camera) -> None:
        """Turn the 3D view to ``camera`` now, or when it is next drawn."""
        camera = tuple(float(c) for c in camera) if camera else None
        ax = self.ax
        if camera and ax is not None and hasattr(ax, 'elev') and self._z is not None:
            ax.view_init(*camera)
            self.canvas.draw_idle()
        else:
            self._saved_camera = camera
