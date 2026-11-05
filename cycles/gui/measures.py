"""
Measures panel: dharma and purity of the subcycles of one level, linked with
the navigator. The selected subcycle is ringed; with "Equal durations" on,
so are those with its duration. Clicking a point selects that subcycle.
"""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from PySide6.QtCore import QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QSpinBox, QToolTip, QVBoxLayout, QWidget

from cycles.gui.state import MAX_DEPTH, CycleState, address_of, children_range, equal_duration_indices, tcoord
from cycles.plotting.generic import plot_y_vs_x
from cycles.plotting.measure import plot_purity_and_dharma

# Plot kinds: label -> (y measure, x axis); x is 'dharma', 'index' or 'time'
KINDS = {
    'Purity vs dharma': ('purity', 'dharma'),
    'Dharma vs time': ('dharma', 'time'),
    'Purity vs time': ('purity', 'time'),
    'Dharma vs index': ('dharma', 'index'),
    'Purity vs index': ('purity', 'index'),
}
PICK_RADIUS = 10    # pixels


class MeasuresPanel(QWidget):
    """Dharma and purity plots of the level of the selection (or a chosen depth)."""

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        self._base = None            # what the drawn plot shows, to redraw only when it changes
        self._x = self._y = None
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
        layout.addLayout(row)

        self.figure = Figure(figsize=(5, 4), layout='constrained')
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumSize(260, 220)
        self.canvas.mpl_connect('button_press_event', self._clicked)
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
                       state.colorParametersChanged):
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
        measures = {y_name, x_name} & {'dharma', 'purity'}
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

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        sizes = self.point_sizes(part.durations, scatter=x_name == 'dharma')
        if x_name == 'dharma':
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
            plot_y_vs_x(x, y, (None, None), title, xlabel, y_name.capitalize(), ax=ax, show=False,
                        colors=colors, size=sizes)
            ax.title.set_fontsize(9)
            ax.xaxis.set_major_locator(MaxNLocator(5))
        self.ax = ax
        self._x, self._y, self._indices = np.asarray(x, dtype=float), np.asarray(y, dtype=float), indices
        self._highlights = []
        self.info.setText(f"{len(indices)} subcycles. Click a point to select it.")

    def _draw_highlights(self, depth: int) -> None:
        state = self.state
        for artist in self._highlights:
            artist.remove()
        self._highlights = []
        selection = state.selection
        if selection is None or len(selection) != depth:
            return
        positions = {int(i): k for k, i in enumerate(self._indices)}
        if state.highlight_equal:
            equal = [positions[int(i)] for i in equal_duration_indices(state.cache.level(depth), tcoord(selection))
                     if int(i) in positions]
            if equal:
                self._highlights.append(self.ax.scatter(self._x[equal], self._y[equal], s=90, facecolors='none',
                                                        edgecolors='black', linewidths=0.8, zorder=3))
        k = positions.get(tcoord(selection))
        if k is not None:
            self._highlights.append(self.ax.scatter([self._x[k]], [self._y[k]], s=260, facecolors='none',
                                                    edgecolors='#1f77b4', linewidths=2.5, zorder=4))

    # -- interaction

    def _nearest(self, event) -> int | None:
        """Position in the plotted arrays of the point nearest the mouse (within ``PICK_RADIUS``)."""
        if self._x is None or event.inaxes is not getattr(self, 'ax', None) or not len(self._x):
            return None
        points = self.ax.transData.transform(np.column_stack([self._x, self._y]))
        distances = np.hypot(points[:, 0] - event.x, points[:, 1] - event.y)
        k = int(np.argmin(distances))
        return k if distances[k] <= PICK_RADIUS * self.canvas.devicePixelRatioF() else None

    def _address(self, k: int) -> tuple:
        return address_of(int(self._indices[k]), self.plot_depth())

    def _clicked(self, event) -> None:
        k = self._nearest(event)
        if k is not None and event.button == 1:
            self.state.reveal(self._address(k))

    def _hovered(self, event) -> None:
        k = self._nearest(event)
        if k is None:
            QToolTip.hideText()
            return
        address = self._address(k)
        QToolTip.showText(QCursor.pos(), ' › '.join(self.state.names[d] for d in address)
                          + f"\ndharma {self.state.cache.level(len(address)).dharmas[self._indices[k]]:.4f}, "
                          f"purity {self.state.cache.level(len(address)).purities[self._indices[k]]:.4f}",
                          self.canvas)
