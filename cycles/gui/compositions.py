"""
Compositions panel: the compositions (n₀, n₁, n₂, n₃) of the addresses of a
level (how many digits of each age) as the points of a discrete tetrahedron,
one vertex per age: a composition sits at the mean of the vertices of its
digits. Its point is sized by how many subcycles have it (the orderings of
its ages) and colored by its duration.

Compositions of equal duration differ by multiples of (1, 0, -2, 1) (one
Golden and one Iron digit last as long as two Bronze ones), so they lie on
parallel lines, drawn joining them; seen along those lines, each class of
equal duration is a single point. Clicking a composition selects its first
subcycle and highlights all of them everywhere (Same composition).
"""

from math import factorial

import numpy as np
from matplotlib import colormaps
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.colors import LogNorm
from matplotlib.figure import Figure
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QSpinBox, QToolButton, QToolTip, QVBoxLayout, QWidget,
)

from cycles.functions.composition import compositions_grouped_by_duration
from cycles.functions.view import top_view
from cycles.gui.state import (
    MAX_DEPTH, MOMENT_COLOR, SELECTION_COLOR, CycleState, address_of, children_range, tcoord,
)

PICK_RADIUS = 9          # pixels
DRAG_THRESHOLD = 4       # pixels moved between press and release that make it a rotation, not a click
# vertices of a regular tetrahedron, one per age (Satya, Treta, Dvapara, Kali)
VERTICES = np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], dtype=float)
EQUAL_DURATION = VERTICES[0] - 2 * VERTICES[2] + VERTICES[3]       # direction of the classes of equal duration
EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
AGE_DURATIONS = np.array([0.4, 0.3, 0.2, 0.1])
VIEWS = {
    'oblique': ('Oblique', (12.0, 75.0, 0.0)),        # every vertex on the outline, none in front of the others
    'equal': ('Along the lines of equal duration', top_view(EQUAL_DURATION)),
    'satya': ('From the Satya vertex', top_view(VERTICES[0])),
    'kali': ('From the Kali vertex', top_view(VERTICES[3])),
}
COLORS = {'duration': 'Duration', 'coloring': 'Composition coloring', 'count': 'Number of subcycles'}


class CompositionsPanel(QWidget):
    """The compositions of a level in a tetrahedron, with the lines of equal duration."""

    saveRequested = Signal()     # the Save… button

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        self._dirty = True
        self._base = None
        self._data = None
        self._highlights = []
        self._press = None
        self.ax = None

        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.color_by = QComboBox()
        for key, label in COLORS.items():
            self.color_by.addItem(label, key)
        self.color_by.setToolTip('Duration: a color map (log scale). Composition coloring: cmyk_composition, one '
                                 'color per composition. Number: how many subcycles have it.')
        self.depth = QSpinBox()
        self.depth.setRange(0, MAX_DEPTH)
        self.depth.setSpecialValueText('auto')
        self.depth.setToolTip('Auto: the depth of the selection, or the level below the zoom')
        self.inside = QCheckBox('Only inside the zoom')
        self.inside.setChecked(True)
        self.inside.setToolTip('Count only the subcycles inside the zoomed one (the others are hollow)')
        save_button = QToolButton()
        save_button.setText('Save…')
        save_button.setToolTip('Save this graph to a file (page size, resolution, format…)')
        save_button.clicked.connect(self.saveRequested)
        row.addWidget(QLabel('Color'))
        row.addWidget(self.color_by)
        row.addWidget(QLabel('Depth'))
        row.addWidget(self.depth)
        row.addWidget(self.inside)
        row.addStretch(1)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.lines = QCheckBox('Lines of equal duration')
        self.lines.setChecked(True)
        self.labels = QCheckBox('Counts')
        self.labels.setToolTip('Write the number of subcycles of each composition')
        self.view = QComboBox()
        self.view.addItem('Free (drag to rotate)', None)
        for key, (label, _) in VIEWS.items():
            self.view.addItem(label, key)
        self.view.setCurrentIndex(self.view.findData('oblique'))
        row.addWidget(self.lines)
        row.addWidget(self.labels)
        row.addStretch(1)
        row.addWidget(QLabel('View'))
        row.addWidget(self.view)
        row.addWidget(save_button)
        layout.addLayout(row)

        self.figure = Figure(figsize=(5, 5))
        self.figure.subplots_adjust(0, 0, 1, 1)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumSize(260, 260)
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
        self.color_by.currentIndexChanged.connect(self._schedule)
        self.view.currentIndexChanged.connect(self._apply_view)
        self.depth.valueChanged.connect(self._schedule)
        for widget in (self.inside, self.lines, self.labels):
            widget.toggled.connect(self._schedule)
        for signal in (state.selectionChanged, state.focusChanged, state.viewChanged, state.colorParametersChanged,
                       state.skyTimeChanged):
            signal.connect(self._schedule)

    # -- what to show

    def plot_depth(self) -> int:
        state = self.state
        if self.depth.value():
            return self.depth.value()
        if state.selection is not None and len(state.selection) > len(state.focus):
            return len(state.selection)
        return min(MAX_DEPTH, len(state.focus) + 1)

    def scope(self, depth: int) -> tuple:
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
        coloring = self.color_by.currentData()
        base = (depth, scope, coloring, self.lines.isChecked(), self.labels.isChecked(), state.model, state.names,
                state.parameters_of('cmyk_composition') if coloring == 'coloring' else None)
        if base != self._base:
            self._data = self._compute(depth, scope)
            self._draw_base()
            self._base = base
        self._draw_highlights()
        self.canvas.draw_idle()

    def _compute(self, depth: int, scope: tuple) -> dict:
        state = self.state
        level = state.cache.level(depth)
        lcoords = np.asarray(level.lcoords)
        counts_of = np.stack([(lcoords == k).sum(axis=1) for k in range(4)], axis=1)   # composition of each subcycle
        span = children_range(scope, depth)
        classes = compositions_grouped_by_duration(depth)
        compositions = np.array([c for group in classes for c in group], dtype=int)
        class_of = np.concatenate([np.full(len(group), k) for k, group in enumerate(classes)])
        index = {tuple(c): k for k, c in enumerate(compositions)}
        which = np.array([index[tuple(c)] for c in counts_of])            # composition of each subcycle (index)
        inside = np.zeros(len(which), dtype=bool)
        inside[span.start:span.stop] = True
        counts = np.bincount(which[inside], minlength=len(compositions))
        multiplicities = np.array([factorial(depth) // int(np.prod([factorial(int(n)) for n in c]))
                                   for c in compositions])
        durations = np.prod(AGE_DURATIONS ** compositions, axis=1)
        first = np.full(len(compositions), -1)
        for k in range(len(compositions)):
            members = np.flatnonzero(inside & (which == k))
            if len(members):
                first[k] = members[0]
        coloring = np.asarray(state.cache.colors(depth, 'cmyk_composition'))
        colors = np.array([np.clip(coloring[np.flatnonzero(which == k)[0], :3], 0, 1)
                           for k in range(len(compositions))])
        return dict(depth=depth, scope=scope, compositions=compositions, class_of=class_of, classes=classes,
                    points=compositions @ VERTICES / depth, counts=counts, multiplicities=multiplicities,
                    durations=durations, first=first, which=which, colors=colors, inside=span)

    def _draw_base(self) -> None:
        data = self._data
        state = self.state
        camera = (self.ax.elev, self.ax.azim, self.ax.roll) if self.ax is not None else \
            self.__dict__.pop('_saved_camera', None)
        self.figure.clear()
        ax = self.figure.add_subplot(111, projection='3d')
        self.figure.subplots_adjust(0, 0, 1, 1)
        for a, b in EDGES:
            ax.plot(*zip(VERTICES[a], VERTICES[b]), color='0.6', lw=0.7)
        for k, vertex in enumerate(VERTICES):
            ax.text(*(vertex * 1.14), state.names[k], ha='center', va='center', fontsize=9)
        points = data['points']
        if self.lines.isChecked():
            for group in data['classes']:
                if len(group) > 1:
                    line = np.array(group) @ VERTICES / data['depth']
                    ax.plot(line[:, 0], line[:, 1], line[:, 2], color='0.35', lw=0.8, alpha=0.7)
        present = data['counts'] > 0
        largest = data['counts'].max() if present.any() else 1
        sizes = 20 + 380 * data['counts'] / largest
        coloring = self.color_by.currentData()
        if coloring == 'duration':
            norm = LogNorm(data['durations'].min(), data['durations'].max()) \
                if data['durations'].min() < data['durations'].max() else None
            colors = colormaps['viridis'](norm(data['durations']) if norm else np.full(len(points), 0.5))[:, :3]
        elif coloring == 'count':
            colors = colormaps['magma_r'](0.15 + 0.75 * data['counts'] / largest)[:, :3]
        else:
            colors = data['colors']
        ax.scatter(points[present, 0], points[present, 1], points[present, 2], s=sizes[present],
                   c=colors[present], edgecolors='0.2', linewidths=0.5, depthshade=False, alpha=0.95)
        if (~present).any():
            ax.scatter(points[~present, 0], points[~present, 1], points[~present, 2], s=14, facecolors='none',
                       edgecolors='0.6', linewidths=0.6, depthshade=False)
        if self.labels.isChecked():
            for k in np.flatnonzero(present):
                ax.text(*(points[k] + 0.06), str(int(data['counts'][k])), fontsize=7, color='0.15')
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)
        ax.set_zlim(-1, 1)
        ax.set_box_aspect((1, 1, 1), zoom=0.9)
        ax.set_proj_type('ortho')         # parallel lines stay parallel: seen along them, they are points
        ax.set_axis_off()
        view = VIEWS.get(self.view.currentData())
        ax.view_init(*(camera if camera is not None and view is None else view[1] if view else VIEWS['oblique'][1]))
        where = ' › '.join(state.names[d] for d in data['scope']) or 'whole cycle'
        ax.set_title(f"Compositions at depth {data['depth']} ({where})", fontsize=9)
        self.ax = ax
        self._highlights = []
        n = len(points)
        self.info.setText(
            f"{n} compositions of {data['depth']} digits in {len(data['classes'])} classes of equal duration "
            f"({int(present.sum())} present in {where}, {int(data['counts'].sum())} subcycles). Sizes: how many "
            "subcycles have each one. Drag to rotate; click a composition to highlight its subcycles.")

    def camera(self) -> tuple | None:
        """(elevation, azimuth, roll) of the 3D view, or None."""
        ax = self.ax
        if ax is None or not hasattr(ax, 'elev'):
            return getattr(self, '_saved_camera', None)
        return (float(ax.elev), float(ax.azim), float(ax.roll))

    def restore_camera(self, camera) -> None:
        """Turn the 3D view to ``camera`` now, or when it is next drawn."""
        camera = tuple(float(c) for c in camera) if camera else None
        ax = self.ax
        if camera and ax is not None and hasattr(ax, 'elev'):
            ax.view_init(*camera)
            self.canvas.draw_idle()
        else:
            self._saved_camera = camera

    def _apply_view(self, *_) -> None:
        view = VIEWS.get(self.view.currentData())
        if view is not None and self.ax is not None:
            self.ax.view_init(*view[1])
            self.canvas.draw_idle()

    def _draw_highlights(self) -> None:
        for artist in self._highlights:
            artist.remove()
        self._highlights = []
        data = self._data
        if data is None or self.ax is None:
            return
        state = self.state
        points = data['points']
        selection = state.selection
        if selection is not None and len(selection) == data['depth']:
            k = int(data['which'][tcoord(selection)])
            group = np.array(data['classes'][data['class_of'][k]]) @ VERTICES / data['depth']
            if len(group) > 1:
                self._highlights += self.ax.plot(group[:, 0], group[:, 1], group[:, 2], color='black', lw=2.2)
            self._highlights.append(self.ax.scatter(*points[k], s=520, facecolors='none', edgecolors=SELECTION_COLOR,
                                                    linewidths=2.4, depthshade=False))
        if state.follow and state.sky_time is not None:
            index = state.moment_index(data['depth'])
            if index is not None:
                k = int(data['which'][index])
                self._highlights.append(self.ax.scatter(*points[k], s=420, facecolors='none',
                                                        edgecolors=MOMENT_COLOR, linewidths=2.0, depthshade=False))

    # -- interaction

    def _nearest(self, event) -> int | None:
        if self.ax is None or event.inaxes is not self.ax or self._data is None:
            return None
        from mpl_toolkits.mplot3d import proj3d
        points = self._data['points']
        x, y, _ = proj3d.proj_transform(points[:, 0], points[:, 1], points[:, 2], self.ax.get_proj())
        screen = self.ax.transData.transform(np.column_stack([x, y]))
        distances = np.hypot(screen[:, 0] - event.x, screen[:, 1] - event.y)
        k = int(np.argmin(distances))
        return k if distances[k] <= PICK_RADIUS * self.canvas.devicePixelRatioF() else None

    def _pressed(self, event) -> None:
        self._press = (event.x, event.y) if event.button == 1 else None

    def _released(self, event) -> None:
        if self._press is None or event.button != 1:
            return
        moved = np.hypot(event.x - self._press[0], event.y - self._press[1])
        self._press = None
        if moved > DRAG_THRESHOLD:
            if self.view.currentData() is not None:
                self.view.blockSignals(True)
                self.view.setCurrentIndex(0)
                self.view.blockSignals(False)
            return
        k = self._nearest(event)
        if k is not None:
            self.choose(k)

    def choose(self, k: int) -> None:
        """Select the first subcycle (in the zoom) of composition ``k``, and highlight the others like it."""
        data = self._data
        selection = self.state.selection
        if selection is not None and len(selection) == data['depth'] and data['which'][tcoord(selection)] == k:
            pass                                    # already one of them
        elif data['first'][k] >= 0:
            self.state.reveal(address_of(int(data['first'][k]), data['depth']))
        else:
            return
        self.state.set_highlight('composition')

    def composition_text(self, k: int) -> str:
        data = self._data
        state = self.state
        composition = data['compositions'][k]
        parts = ', '.join(f"{state.names[a]} {int(n)}" for a, n in enumerate(composition) if n)
        # in normalized time: the years of a subcycle depend on where it is (the time map need not be linear)
        lasting = f"{data['durations'][k]:.6g} of the cycle"
        group = len(data['classes'][data['class_of'][k]])
        return (f"{parts}\n{int(data['counts'][k])} subcycles here (of {int(data['multiplicities'][k])} orderings)\n"
                f"each lasts {lasting}\n{group} composition{'s' if group > 1 else ''} of this duration")

    def _hovered(self, event) -> None:
        if self._press is not None:
            return
        k = self._nearest(event)
        if k is None:
            QToolTip.hideText()
            return
        QToolTip.showText(QCursor.pos(), self.composition_text(k), self.canvas)
