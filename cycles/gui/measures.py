"""
Measures panel: any two measures of the subcycles of one level (``measure.MEASURES``: dharma, purity, mixture,
tension, trend, roughness, contrast, balance, angular density) linked with the navigator, in 2D (against each
other, time or index) or in 3D (both and time or index; drag to rotate). The points take the subcycles' colors or
the values of a measure. The selected subcycle is ringed; with a highlight on, so is its class. Clicking a point
selects that subcycle.
"""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QSpinBox, QToolTip, QToolButton, QVBoxLayout, QWidget

from cycles.functions.color import measure_colors
from cycles.functions.measure import MEASURES
from cycles.gui.links import draw_links
from cycles.gui.state import MAX_DEPTH, MOMENT_COLOR, CycleState, address_of, children_range, tcoord
from cycles.plotting.generic import plot_y_vs_x

# Plot kinds: key -> label; Y against X, against time or index, or X and Y with time or index as a third axis
KINDS = {
    'scatter': 'Y against X',
    'time': 'Y against time',
    'index': 'Y against index',
    '3d_time': 'X, Y and time (3D)',
    '3d_index': 'X, Y and index (3D)',
}
# Camera presets of the 3D plots (X along x, Y along y, time or index along z), and the axis each sees edge-on
# (its ticks are hidden)
EDGE_ON = {'top': 'z', 'x': 'y', 'y': 'x'}
VIEWS_3D = {
    'oblique': ('Oblique', (22, -55, 0)),
    'top': ('Down the third axis: Y against X', (90, -90, 0)),
    'x': ('From the side: X against the third axis', (0, -90, 0)),
    'y': ('From the side: Y against the third axis', (0, 0, 0)),
}
SUBCYCLE_COLORS = 'subcycle'


class MeasuresPanel(QWidget):
    """Plots of two measures of the level of the selection (or a chosen depth)."""

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
        measures_row = QHBoxLayout()
        self.kind = QComboBox()
        for key, label in KINDS.items():
            self.kind.addItem(label, key)
        self.kind.currentIndexChanged.connect(self._schedule)
        measures_row.addWidget(self.kind)
        self.x_label = QLabel('X')
        self.x_measure = self._measure_box('dharma')
        self.y_measure = self._measure_box('purity')
        self.color_by = QComboBox()
        self.color_by.addItem('Subcycle colors', SUBCYCLE_COLORS)
        for key, m in MEASURES.items():
            self.color_by.addItem(f"Color by {m['label'].lower()}", key)
        self.color_by.setToolTip('Fill the points with the colors of the subcycles, or by the value of a measure')
        self.color_by.currentIndexChanged.connect(self._schedule)
        measures_row.addWidget(self.x_label)
        measures_row.addWidget(self.x_measure)
        measures_row.addWidget(QLabel('Y'))
        measures_row.addWidget(self.y_measure)
        measures_row.addWidget(self.color_by)
        measures_row.addStretch(1)
        layout.addLayout(measures_row)
        row = QHBoxLayout()
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
        self.join = QCheckBox('Join')
        self.join.setChecked(True)
        self.join.setToolTip('Join the highlighted subcycles: the steps of the ⟨σ⟩ orbit of the selection, with arrows, or the swaps of neighbouring digits between the orderings of its ages (Same composition)')
        self.join.toggled.connect(self._schedule)
        row.addWidget(self.join)
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

    def _measure_box(self, key: str) -> QComboBox:
        box = QComboBox()
        for name, m in MEASURES.items():
            box.addItem(m['label'], name)
            box.setItemData(box.count() - 1, m['description'], 3)      # Qt.ToolTipRole
        box.setCurrentIndex(box.findData(key))
        box.currentIndexChanged.connect(self._schedule)
        return box

    # -- what to plot

    def graph_name(self) -> str:
        """Short name of what is plotted (for file names)."""
        x_key, y_key = self.measures()
        kind = self.kind.currentData()
        if kind in ('time', 'index'):
            return f"{MEASURES[y_key]['label']} vs {kind}"
        third = f" and {kind[3:]} (3D)" if kind.startswith('3d') else ''
        return f"{MEASURES[y_key]['label']} vs {MEASURES[x_key]['label']}{third}"

    def measures(self) -> tuple[str, str]:
        """Keys of the X and Y measures."""
        return self.x_measure.currentData(), self.y_measure.currentData()

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
        # redraw the plot only if what it shows changed: the point colors and the measures
        kind = self.kind.currentData()
        x_key, y_key = self.measures()
        three_d = kind.startswith('3d')
        self.view_label.setVisible(three_d)
        self.view.setVisible(three_d)
        self.x_label.setVisible(kind not in ('time', 'index'))
        self.x_measure.setVisible(kind not in ('time', 'index'))
        coloring = self.color_by.currentData()
        used = {y_key, coloring} | ({x_key} if kind not in ('time', 'index') else set())
        used.discard(SUBCYCLE_COLORS)
        parameters = (state.parameters_of(state.color_key), *(state.parameters_of(m) for m in sorted(used)))
        base = (kind, x_key, y_key, coloring, depth, scope, state.color_key, state.model, state.names, parameters,
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
        kind = self.kind.currentData()
        x_key, y_key = self.measures()
        where = ' › '.join(state.names[d] for d in scope) or 'whole cycle'
        x_label, y_label = MEASURES[x_key]['label'], MEASURES[y_key]['label']
        names = {'scatter': f"{y_label} against {x_label.lower()}", 'time': f"{y_label} against time",
                 'index': f"{y_label} against index", '3d_time': f"{x_label}, {y_label.lower()} and time",
                 '3d_index': f"{x_label}, {y_label.lower()} and index"}
        title = f"{names[kind]}, depth {depth} ({where})"

        camera = ((self.ax.elev, self.ax.azim, self.ax.roll) if self.ax is not None and self._z is not None
                  else self.__dict__.pop('_saved_camera', None))
        self.figure.clear()
        self._z = None
        self.ax = None
        self._x = self._y = None
        self._indices = indices
        self._highlights = []
        missing = [MEASURES[k]['label'] for k in {x_key, y_key, self.color_by.currentData()} - {SUBCYCLE_COLORS}
                   if state.measure_values(depth, k) is None and (k != x_key or kind not in ('time', 'index'))]
        if missing:
            self.info.setText(f"{', '.join(missing)} needs a cycle model (choose one in the toolbar).")
            return
        y = np.asarray(state.measure_values(depth, y_key), dtype=float)[indices]
        coloring = self.color_by.currentData()
        mappable = None
        if coloring == SUBCYCLE_COLORS:
            colors = state.colors(depth, state.color_key)[indices]
        else:
            colors, mappable = measure_colors(np.asarray(state.measure_values(depth, coloring), dtype=float)[indices],
                                              coloring)
        three_d = kind.startswith('3d')
        sizes = self.point_sizes(part.durations, scatter=kind == 'scatter' or three_d)
        if kind in ('time', 'index', '3d_time', '3d_index'):
            if kind.endswith('index'):
                t, t_label = indices.astype(float), 'Index'
            else:
                t, t_label = part.starts + part.durations / 2, 'Normalized time'
                if state.time_map is not None:
                    t, t_label = np.asarray(state.time_map.to_physical(t), dtype=float), 'Year'
        if three_d:
            x = np.asarray(state.measure_values(depth, x_key), dtype=float)[indices]
            ax = self.figure.add_subplot(111, projection='3d')
            ax.plot(x, y, t, color='0.75', lw=0.5, zorder=1)
            ax.scatter(xs=x, ys=y, zs=t, c=colors, s=sizes, alpha=0.9, depthshade=False)
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            ax.set_zlabel(t_label)
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
            self._z = np.asarray(t, dtype=float)
        elif kind == 'scatter':
            x = np.asarray(state.measure_values(depth, x_key), dtype=float)[indices]
            ax = self.figure.add_subplot(111)
            ax.scatter(x, y, c=colors, s=sizes, alpha=0.3 if mappable is None else 0.8)
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            ax.set_title(title, fontsize=9)
        else:
            x = t
            ax = self.figure.add_subplot(111)
            plot_y_vs_x(x, y, (None, None), title, t_label, y_label, ax=ax, show=False, colors=colors, size=sizes)
            ax.title.set_fontsize(9)
            ax.xaxis.set_major_locator(MaxNLocator(5))
        if mappable is not None:
            bar = self.figure.colorbar(mappable, ax=ax, shrink=0.8, pad=0.08 if three_d else 0.02)
            bar.set_label(MEASURES[coloring]['label'], fontsize=8)
            bar.ax.tick_params(labelsize=7)
        self.ax = ax
        self._x, self._y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
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
        if self.ax is None:
            return
        positions = {int(i): k for k, i in enumerate(self._indices)}
        moment = positions.get(state.moment_index(depth))
        if moment is not None:
            self._highlights.append(self._ring([moment], s=200, color=MOMENT_COLOR, width=2.0))
        selection = state.selection
        if selection is None or len(selection) != depth:
            return
        if self.join.isChecked():
            points = np.column_stack([self._x, self._y] + ([self._z] if self._z is not None else []))
            self._highlights += draw_links(self.ax, state.highlight_links(selection), positions, points)
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
        index = int(self._indices[k])
        x_key, y_key = self.measures()
        keys = dict.fromkeys((y_key,) if self.kind.currentData() in ('time', 'index') else (x_key, y_key))
        values = ', '.join(f"{MEASURES[key]['label'].lower()} {self.state.measure_values(len(address), key)[index]:.4f}"
                           for key in keys if self.state.measure_values(len(address), key) is not None)
        QToolTip.showText(QCursor.pos(), ' › '.join(self.state.names[d] for d in address) + '\n' + values,
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
