"""
Color space panel: the colors of the subcycles of a level as points (and/or
the path joining them in time order) in 3D, in RGB or in CMY ink coordinates.

Linked like the other panels: the selected subcycle is ringed, and with "Equal
durations" on so are those with its duration; clicking a point (without
dragging) selects that subcycle, and dragging rotates the view. The plot
follows the coloring and the live color parameters.
"""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QSpinBox, QToolTip, QToolButton, QVBoxLayout, QWidget,
)

from cycles.functions.division import CMYK_KEYS
from cycles.functions.view import bottom_view, camera_view_angles, top_view
from cycles.gui.links import draw_links
from cycles.gui.state import MOMENT_COLOR, CycleState, address_of, children_range, tcoord
from cycles.plotting.color import draw_color_path_3d, draw_colors_3d, draw_rgb_cube, setup_color_axes_3d

MAX_PLOT_DEPTH = 7
PICK_RADIUS = 8          # pixels
DRAG_THRESHOLD = 4       # pixels moved between press and release that make it a rotation, not a click
PLOTS = {'points': 'Points', 'path': 'Path in time order', 'both': 'Points and path'}
SPACES = {'rgb': 'RGB', 'cmy': 'CMY inks'}
VIEWS = {
    'gray': ('Gray axis vertical', camera_view_angles((1, 1, 1), angle=0.4, height=-0.35)),
    'white': ('Down the gray axis, from white', top_view((1, 1, 1))),
    'black': ('Up the gray axis, from black', bottom_view((1, 1, 1))),
    'rg': ('Red–green face', top_view((0, 0, 1))),
    'gb': ('Green–blue face', top_view((1, 0, 0))),
    'br': ('Blue–red face', top_view((0, 1, 0))),
}
TETRAHEDRON_EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))


class ColorSpacePanel(QWidget):
    """Colors of the subcycles of one level in a 3D color space."""

    saveRequested = Signal()     # the Save… button

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        self._base = None
        self._coords = np.empty((0, 3))
        self._indices = np.array([], dtype=int)
        self._depth = 1
        self._highlights = []
        self._press = None
        self._dirty = True
        self.ax = None

        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.plot = QComboBox()
        for key, label in PLOTS.items():
            self.plot.addItem(label, key)
        self.space = QComboBox()
        for key, label in SPACES.items():
            self.space.addItem(label, key)
        self.space.setToolTip('RGB: the colors as shown. CMY inks: the cyan, magenta and yellow of a CMYK coloring '
                              '(black is left out).')
        self.depth = QSpinBox()
        self.depth.setRange(0, MAX_PLOT_DEPTH)
        self.depth.setSpecialValueText('auto')
        self.depth.setToolTip('Auto: the depth of the selection, or the level below the zoom')
        for widget, label in ((self.plot, None), (self.space, 'in'), (self.depth, 'Depth')):
            if label:
                row.addWidget(QLabel(label))
            row.addWidget(widget)
        row.addStretch(1)
        save_button = QToolButton()
        save_button.setText('Save…')
        save_button.setToolTip('Save this graph to a file (page size, resolution, format…)')
        save_button.clicked.connect(self.saveRequested)
        row.addWidget(save_button)
        layout.addLayout(row)

        row = QHBoxLayout()
        self.inside = QCheckBox('Only inside the zoom')
        self.inside.setChecked(True)
        self.sized = QCheckBox('Size by duration')
        self.cube = QCheckBox('Cube')
        self.cube.setChecked(True)
        self.cube.setToolTip('Edges of the RGB cube, with its corners named')
        self.tetrahedron = QCheckBox('Tetrahedron')
        self.tetrahedron.setChecked(True)
        self.tetrahedron.setToolTip('Vertices and edges of the tetrahedron coloring (when it is shown)')
        self.join = QCheckBox('Join')
        self.join.setChecked(True)
        self.join.setToolTip('Join the highlighted subcycles: the steps of the ⟨σ⟩ orbit of the selection, with arrows, or the swaps of neighbouring digits between the orderings of its ages (Same composition)')
        self.view = QComboBox()
        self.view.addItem('Free (drag to rotate)', None)
        for key, (label, _) in VIEWS.items():
            self.view.addItem(label, key)
        self.view.setCurrentIndex(self.view.findData('gray'))
        for widget in (self.inside, self.sized, self.cube, self.tetrahedron, self.join):
            row.addWidget(widget)
        row.addStretch(1)
        row.addWidget(QLabel('View'))
        row.addWidget(self.view)
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
        for widget in (self.plot, self.space, self.view):
            widget.currentIndexChanged.connect(self._schedule)
        self.view.currentIndexChanged.connect(self._apply_view)
        self.depth.valueChanged.connect(self._schedule)
        for widget in (self.inside, self.sized, self.cube, self.tetrahedron, self.join):
            widget.toggled.connect(self._schedule)
        for signal in (state.selectionChanged, state.focusChanged, state.viewChanged, state.colorParametersChanged,
                       state.skyTimeChanged, state.permutationChanged):
            signal.connect(self._schedule)

    # -- what to plot

    def plot_depth(self) -> int:
        state = self.state
        if self.depth.value():
            return self.depth.value()
        if state.selection is not None and len(state.selection) > len(state.focus):
            return min(MAX_PLOT_DEPTH, len(state.selection))
        return min(MAX_PLOT_DEPTH, len(state.focus) + 1)

    def scope(self, depth: int) -> tuple:
        focus = self.state.focus
        return focus[:min(len(focus), depth - 1)] if self.inside.isChecked() else ()

    def space_key(self) -> str:
        """The space actually used: CMY only for the CMYK colorings."""
        return 'cmy' if self.space.currentData() == 'cmy' and self.state.color_key in CMYK_KEYS else 'rgb'

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
        key = state.color_key
        self.space.setEnabled(key in CMYK_KEYS)
        base = (self.plot.currentData(), self.space_key(), depth, scope, key, state.parameters_of(key),
                state.context_of(key),
                self.sized.isChecked(), self.cube.isChecked(), self.tetrahedron.isChecked())
        if base != self._base:
            self._draw_base(depth, scope)
            self._base = base
        self._draw_highlights()
        self.canvas.draw_idle()

    def _draw_base(self, depth: int, scope: tuple) -> None:
        state = self.state
        camera = (self.ax.elev, self.ax.azim, self.ax.roll) if self.ax is not None else \
            self.__dict__.pop('_saved_camera', None)
        level = state.cache.level(depth)
        span = children_range(scope, depth)
        indices = np.arange(span.start, span.stop)
        rgbs = state.colors(depth, state.color_key)[indices]
        cmy = self.space_key() == 'cmy'
        coords = level.cmyk(state.color_key)[indices, :3] if cmy else rgbs

        self.figure.clear()
        ax = self.figure.add_subplot(111, projection='3d')
        self.figure.subplots_adjust(0, 0, 1, 1)
        if self.cube.isChecked():
            draw_rgb_cube(ax, labels=not cmy)
        if self.tetrahedron.isChecked() and state.color_key == 'tetrahedron':
            vertices = state.cache.vertices
            for a, b in TETRAHEDRON_EDGES:
                ax.plot(*zip(vertices[a], vertices[b]), color='0.45', lw=0.6, ls='--')
            draw_colors_3d(ax, vertices, vertices, sizes=60, alpha=1.0)
        kind = self.plot.currentData()
        if kind in ('path', 'both') and len(coords) > 1:
            draw_color_path_3d(ax, coords, rgbs, lw=0.8 if len(coords) < 1000 else 0.4)
        if kind in ('points', 'both'):
            if self.sized.isChecked():
                sizes = 120 * level.durations[indices] / level.durations[indices].max()
            else:
                sizes = 18 if len(coords) <= 256 else 8 if len(coords) <= 1024 else 3
            draw_colors_3d(ax, coords, rgbs, sizes=sizes, alpha=0.9)
        # the whole unit cube in view, whatever is drawn
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_zlim(0, 1)
        if cmy:
            ax.text(1.08, 0, 0, 'C', color='#00a6d6')
            ax.text(0, 1.08, 0, 'M', color='#d6008f')
            ax.text(0, 0, 1.08, 'Y', color='#b8a000')
        setup_color_axes_3d(ax)
        ax.set_box_aspect((1, 1, 1), zoom=0.85)     # room for the corner labels
        view = VIEWS.get(self.view.currentData())
        ax.view_init(*(camera if camera is not None and view is None else view[1] if view else (30, -60, 0)))
        self.ax = ax
        self._coords, self._indices, self._depth = np.asarray(coords, dtype=float), indices, depth
        self._highlights = []
        where = ' › '.join(state.names[d] for d in scope) or 'whole cycle'
        self.info.setText(f"{len(indices)} subcycles of depth {depth} ({where}), {state.color_key} in "
                          f"{'CMY inks' if cmy else 'RGB'}. Drag to rotate; click a point to select it.")

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
        state = self.state
        for artist in self._highlights:
            artist.remove()
        self._highlights = []
        if self.ax is None:
            return
        positions = {int(i): k for k, i in enumerate(self._indices)}
        moment = positions.get(state.moment_index(self._depth))
        if moment is not None:
            c = self._coords[moment]
            self._highlights.append(self.ax.scatter([c[0]], [c[1]], [c[2]], s=170, facecolors='none',
                                                    edgecolors=MOMENT_COLOR, linewidths=2.0, depthshade=False))
        selection = state.selection
        if selection is None or len(selection) != self._depth:
            return
        if self.join.isChecked():
            self._highlights += draw_links(self.ax, state.highlight_links(selection), positions, self._coords)
        bright = state.highlight_indices(selection)
        if bright is not None:
            equal = [positions[int(i)] for i in bright if int(i) in positions]
            if equal:
                c = self._coords[equal]
                self._highlights.append(self.ax.scatter(c[:, 0], c[:, 1], c[:, 2], s=70, facecolors='none',
                                                        edgecolors='black', linewidths=0.8, depthshade=False))
        k = positions.get(tcoord(selection))
        if k is not None:
            c = self._coords[k]
            self._highlights.append(self.ax.scatter([c[0]], [c[1]], [c[2]], s=220, facecolors='none',
                                                    edgecolors='#1f77b4', linewidths=2.5, depthshade=False))

    # -- interaction

    def _nearest(self, event) -> int | None:
        """Position (in the plotted arrays) of the point nearest the mouse, within ``PICK_RADIUS``."""
        if self.ax is None or event.inaxes is not self.ax or not len(self._coords):
            return None
        from mpl_toolkits.mplot3d import proj3d
        x, y, _ = proj3d.proj_transform(self._coords[:, 0], self._coords[:, 1], self._coords[:, 2],
                                        self.ax.get_proj())
        points = self.ax.transData.transform(np.column_stack([x, y]))
        distances = np.hypot(points[:, 0] - event.x, points[:, 1] - event.y)
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
            # the user rotated the view: it is now a free view
            if self.view.currentData() is not None:
                self.view.blockSignals(True)
                self.view.setCurrentIndex(0)
                self.view.blockSignals(False)
            return
        k = self._nearest(event)
        if k is not None:
            self.state.reveal(address_of(int(self._indices[k]), self._depth))

    def _hovered(self, event) -> None:
        if self._press is not None:
            return
        k = self._nearest(event)
        if k is None:
            QToolTip.hideText()
            return
        address = address_of(int(self._indices[k]), self._depth)
        r, g, b = np.clip(self.state.colors(self._depth, self.state.color_key)[self._indices[k]], 0, 1)
        QToolTip.showText(QCursor.pos(), ' › '.join(self.state.names[d] for d in address)
                          + f"\n#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}", self.canvas)
