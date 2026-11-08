"""
Permutations panel: a permutation σ of the digit positions of the addresses
acts on the subcycles of a level (an address ``a`` becomes ``a ∘ σ``, as in
``study_of_permutations``), keeping their durations. Shown as the timelines
of the powers σ⁰, σ¹, … back to the identity, with lines following each
subcycle, or as the permutation matrix of σ or of each of its powers.

σ acts either on the digits below the zoom (the subcycles stay inside it) or
on all the digits (the whole cycle). The depth is chosen, or automatic.
"""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QToolButton, QToolTip, QVBoxLayout, QWidget,
)

from cycles.functions.permutation import (
    cycle_text, cycle_type, cycles, identity, order, parse_permutation, permute_digits, power, sign, tcoords_of,
)
from cycles.gui.state import MAX_DEPTH, MOMENT_COLOR, SELECTION_COLOR, CycleState, address_of, children_range, tcoord

VIEWS = {
    'timeline': 'Powers timeline',
    'matrix': 'Matrix of σ',
    'matrices': 'Matrices of the powers',
}
ACTS_ON = {
    'below': 'the digits below the zoom',
    'all': 'all the digits',
}
PRESETS = ('Cyclic shift', 'Inverse shift', 'Reversal', 'Swap the first two', 'Swap the last two', 'Random',
           'Custom')
LINES = {'auto': 'Lines: auto', 'all': 'Lines: all', 'none': 'Lines: none'}
MATRIX_IMAGE = 1024       # largest matrix drawn as an image (larger: as points)
AUTO_LINES = 1024          # largest number of subcycles whose lines are drawn in auto
ROW_GAP = 1.4              # between the rows of the timeline, in row heights
SUPERSCRIPTS = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')


def preset_permutation(name: str, m: int) -> tuple:
    """The permutation of ``m`` positions of a preset (not Random or Custom)."""
    if m < 2:
        return identity(m)
    if name == 'Cyclic shift':
        return tuple(range(1, m)) + (0,)
    if name == 'Inverse shift':
        return (m - 1,) + tuple(range(m - 1))
    if name == 'Reversal':
        return tuple(range(m - 1, -1, -1))
    if name == 'Swap the first two':
        return (1, 0) + tuple(range(2, m))
    if name == 'Swap the last two':
        return tuple(range(m - 2)) + (m - 1, m - 2)
    return identity(m)


class PermutationsPanel(QWidget):
    """The action of a permutation of the digit positions on the subcycles of a level."""

    saveRequested = Signal()     # the Save… button

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        self._dirty = True
        self._base = None
        self._data = None            # what is drawn: see _compute
        self._axes = []
        self._highlights = []
        self._random: dict[int, tuple] = {}
        self.explorer = None              # the group explorer window, once opened
        self._rng = np.random.default_rng()

        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.view = QComboBox()
        for key, label in VIEWS.items():
            self.view.addItem(label, key)
        self.acts = QComboBox()
        for key, label in ACTS_ON.items():
            self.acts.addItem(label, key)
        self.acts.setToolTip('Below the zoom: σ permutes the digits after those of the zoomed subcycle, so the '
                             'subcycles stay inside it.\nAll: σ permutes every digit, over the whole cycle.')
        self.depth = QSpinBox()
        self.depth.setRange(0, MAX_DEPTH)
        self.depth.setSpecialValueText('auto')
        self.depth.setToolTip('Auto: the depth of the selection, or the level below the zoom')
        save_button = QToolButton()
        save_button.setText('Save…')
        save_button.setToolTip('Save this graph to a file (page size, resolution, format…)')
        save_button.clicked.connect(self.saveRequested)
        row.addWidget(self.view)
        row.addWidget(QLabel('acting on'))
        row.addWidget(self.acts)
        row.addWidget(QLabel('Depth'))
        row.addWidget(self.depth)
        row.addStretch(1)
        row.addWidget(save_button)
        layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel('σ'))
        self.preset = QComboBox()
        self.preset.addItems(PRESETS)
        self.element = QLineEdit()
        self.element.setToolTip('The images of the positions 0, 1, … (like 1 2 0: position 0 takes the digit of '
                                'position 1, …),\nor cycles (like (0 1 2)(3 4)). Position 0 is the first digit '
                                'σ acts on.')
        self.element.setPlaceholderText('1 2 0  or  (0 1 2)')
        self.new_random = QToolButton()
        self.new_random.setText('↻')
        self.new_random.setToolTip('Another random permutation')
        self.lines = QComboBox()
        for key, label in LINES.items():
            self.lines.addItem(label, key)
        self.lines.setToolTip(f"Lines following each subcycle from row to row (auto: up to {AUTO_LINES} "
                              "subcycles)")
        row.addWidget(self.preset)
        row.addWidget(self.element, 1)
        row.addWidget(self.new_random)
        row.addWidget(self.lines)
        group_button = QToolButton()
        group_button.setText('Group…')
        group_button.setToolTip('Every element of the group, with how each one moves the subcycles, in a sortable '
                                'table')
        group_button.clicked.connect(self.show_group)
        row.addWidget(group_button)
        layout.addLayout(row)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.figure = Figure(figsize=(5, 4), layout='constrained')
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumSize(260, 220)
        self.canvas.mpl_connect('button_release_event', self._clicked)
        self.canvas.mpl_connect('motion_notify_event', self._hovered)
        layout.addWidget(self.canvas, 1)
        self.info = QLabel()
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(0)
        self.render_timer.timeout.connect(self.render)
        for widget in (self.view, self.acts, self.lines):
            widget.currentIndexChanged.connect(self._schedule)
        self.depth.valueChanged.connect(self._schedule)
        self.preset.currentIndexChanged.connect(self._preset_changed)
        self.element.editingFinished.connect(self._element_edited)
        self.new_random.clicked.connect(self._another_random)
        for signal in (state.selectionChanged, state.focusChanged, state.viewChanged, state.colorParametersChanged,
                       state.skyTimeChanged):
            signal.connect(self._schedule)
        self._preset_changed()

    # -- what to show

    def plot_depth(self) -> int:
        if self.depth.value():
            return self.depth.value()
        # as in the other panels: the depth of the selection, or the level below the zoom
        state = self.state
        if state.selection is not None and len(state.selection) > len(state.focus):
            return len(state.selection)
        return min(MAX_DEPTH, len(state.focus) + 1)

    def scope(self, depth: int) -> tuple[tuple, int] | None:
        """(prefix kept, first permuted position), or None if no digit is left to permute."""
        if self.acts.currentData() == 'all':
            return (), 0
        focus = self.state.focus
        return (focus, len(focus)) if depth > len(focus) else None

    def permutation(self, m: int) -> tuple:
        """σ on ``m`` positions; ``ValueError`` if the typed one is not a permutation of them."""
        name = self.preset.currentText()
        if name == 'Custom':
            return parse_permutation(self.element.text(), m)
        if name == 'Random':
            if len(self._random.get(m, ())) != m:
                self._random[m] = tuple(int(i) for i in self._rng.permutation(m))
            return self._random[m]
        return preset_permutation(name, m)

    def _preset_changed(self, *_) -> None:
        self.new_random.setVisible(self.preset.currentText() == 'Random')
        self.element.setReadOnly(False)
        self._schedule()

    def _element_edited(self) -> None:
        if self.preset.currentText() != 'Custom' and self.element.isModified():
            self.preset.blockSignals(True)
            self.preset.setCurrentText('Custom')
            self.preset.blockSignals(False)
            self.new_random.setVisible(False)
        self.element.setModified(False)
        self._schedule()

    def load_permutation(self, sigma: tuple) -> None:
        """Show ``sigma`` (as Custom), e.g. chosen in the group explorer."""
        self.preset.blockSignals(True)
        self.preset.setCurrentText('Custom')
        self.preset.blockSignals(False)
        self.new_random.setVisible(False)
        self.element.setText(' '.join(map(str, sigma)))
        self._schedule()

    def show_group(self) -> None:
        from cycles.gui.groupexplorer import GroupExplorer
        if self.explorer is None:
            self.explorer = GroupExplorer(self, self.state, self.window())
        self.explorer.show()
        self.explorer.raise_()
        self.explorer.activateWindow()

    def _another_random(self) -> None:
        self._random.clear()
        self._schedule()

    # -- drawing

    def _schedule(self, *_) -> None:
        self._dirty = True
        self._publish()
        if self.explorer is not None:
            self.explorer.refresh()        # the depth or the scope may have changed with the same σ
        if self.isVisible():
            self.render_timer.start()

    def _publish(self) -> None:
        """Tell the other views which σ acts, and on which positions (even while this panel is hidden)."""
        depth = self.plot_depth()
        scope = self.scope(depth)
        try:
            sigma = self.permutation(depth - scope[1]) if scope is not None else None
        except ValueError:
            sigma = None
        self.state.set_permutation(sigma, scope[1] if scope is not None else 0)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._dirty:
            self.render_timer.start()

    def _message(self, text: str) -> None:
        self.figure.clear()
        self._axes, self._highlights, self._data, self._base = [], [], None, None
        self.figure.text(0.5, 0.5, text, ha='center', va='center', wrap=True, color='#555555')
        self.canvas.draw_idle()

    def render(self) -> None:
        self._dirty = False
        state = self.state
        depth = self.plot_depth()
        scope = self.scope(depth)
        if scope is None:
            self.summary.setText('')
            self.info.setText('')
            self._message('Choose a depth below the zoom,\nor let σ act on all the digits.')
            return
        prefix, first = scope
        m = depth - first
        try:
            sigma = self.permutation(m)
        except ValueError as error:
            self.summary.setText(f"<span style='color:#d62728'>{error}.</span>")
            self._message(f"σ must be a permutation of the {m} positions 0 to {m - 1}.")
            return
        if self.preset.currentText() != 'Custom' and not self.element.hasFocus():
            self.element.setText(' '.join(map(str, sigma)))
        self._show_summary(sigma, first, depth)
        base = (self.view.currentData(), depth, prefix, first, sigma, state.color_key,
                state.parameters_of(state.color_key), state.context_of(state.color_key), state.spacing, state.model,
                state.names,
                self.lines.currentData())
        if base != self._base:
            self._data = self._compute(depth, prefix, first, sigma)
            self._draw_base()
            self._base = base
        self._draw_highlights()
        self.canvas.draw_idle()

    def _show_summary(self, sigma: tuple, first: int, depth: int) -> None:
        m = len(sigma)
        o = order(sigma)
        fixed = 4 ** len(cycles(sigma))
        orbits = sum(4 ** len(cycles(power(sigma, r))) for r in range(o)) // o      # Burnside
        positions = f"digit {first + 1}" if m == 1 else f"digits {first + 1}–{depth}"
        self.summary.setText(
            f"σ = {cycle_text(sigma)} on the {positions} of the addresses (position 0 = digit {first + 1}): "
            f"order {o}, {'even' if sign(sigma) > 0 else 'odd'}, cycle type {'+'.join(map(str, cycle_type(sigma)))}. "
            f"It fixes {fixed} of the {4 ** m} subcycles; ⟨σ⟩ moves them in {orbits} orbits.")

    def _compute(self, depth: int, prefix: tuple, first: int, sigma: tuple) -> dict:
        """Positions of the subcycles in each power, and the geometry of the slots."""
        state = self.state
        if not state.cache.has(depth):
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                state.cache.level(depth)
            finally:
                QApplication.restoreOverrideCursor()
        level = state.cache.level(depth)
        span = children_range(prefix, depth)
        indices = np.arange(span.start, span.stop)
        lcoords = level.lcoords[indices]
        o = order(sigma)
        slots = np.empty((o + 1, len(indices)), dtype=np.int64)     # slot of subcycle k in row r
        current = lcoords
        for r in range(o + 1):
            slots[r] = tcoords_of(current) - span.start
            current = permute_digits(current, sigma, first)
        if state.spacing == 'time':
            starts = level.starts[indices]
            edges = np.append(starts, starts[-1] + level.durations[indices[-1]])
            if state.time_map is not None:
                edges = np.asarray(state.time_map.to_physical(edges), dtype=float)
                xlabel = 'Year'
            else:
                xlabel = 'Normalized time'
        else:
            edges = np.arange(len(indices) + 1, dtype=float) + span.start
            xlabel = 'Index'
        colors = np.clip(np.asarray(state.colors(depth, state.color_key))[indices][:, :3], 0, 1)
        return dict(depth=depth, prefix=prefix, first=first, sigma=sigma, order=o, indices=indices,
                    slots=slots, edges=edges, centers=(edges[:-1] + edges[1:]) / 2, colors=colors, xlabel=xlabel,
                    occupants=None)

    def _title(self) -> str:
        data = self._data
        where = ' › '.join(self.state.names[d] for d in data['prefix']) or 'whole cycle'
        return f"σ = {cycle_text(data['sigma'])}, depth {data['depth']} ({where})"

    def _draw_base(self) -> None:
        data = self._data
        self.figure.clear()
        self._highlights = []
        view = self.view.currentData()
        n = len(data['indices'])
        if view == 'timeline':
            ax = self.figure.add_subplot(111)
            o = data['order']
            for r in range(o + 1):
                row = np.empty_like(data['colors'])
                row[data['slots'][r]] = data['colors']
                y = r * (1 + ROW_GAP)
                ax.pcolormesh(data['edges'], [y, y + 1], row[None, :, :], shading='flat', rasterized=n > 4096)
            lines = self.lines.currentData()
            if lines == 'all' or (lines == 'auto' and n <= AUTO_LINES):
                centers = data['centers']
                segments = [np.column_stack([centers[data['slots'][r]], np.full(n, r * (1 + ROW_GAP) + 1),
                                             centers[data['slots'][r + 1]], np.full(n, (r + 1) * (1 + ROW_GAP))])
                            .reshape(n, 2, 2) for r in range(o)]
                if segments:
                    ax.add_collection(LineCollection(np.concatenate(segments), colors='k',
                                                     linewidths=0.3 if n > 256 else 0.6, alpha=0.6))
            ax.set_xlim(data['edges'][0], data['edges'][-1])
            ax.set_ylim((o + 1) * (1 + ROW_GAP) - ROW_GAP, 0)
            ax.set_yticks([r * (1 + ROW_GAP) + 0.5 for r in range(o + 1)],
                          [f"σ{str(r).translate(SUPERSCRIPTS)}" for r in range(o + 1)])
            ax.tick_params(axis='y', length=0)
            for side in ('left', 'right', 'top'):
                ax.spines[side].set_visible(False)
            ax.set_xlabel(data['xlabel'])
            ax.set_title(self._title(), fontsize=9)
            self._axes = [ax]
        else:
            powers = [1] if view == 'matrix' else list(range(1, data['order'] + 1))
            columns = int(np.ceil(np.sqrt(len(powers))))
            rows = int(np.ceil(len(powers) / columns))
            self._axes = []
            for k, r in enumerate(powers):
                ax = self.figure.add_subplot(rows, columns, k + 1)
                if n <= MATRIX_IMAGE:
                    # exact: one pixel of the image per entry, the ones in the color of their subcycle
                    image = np.full((n, n, 3), 255, dtype=np.uint8)
                    image[data['slots'][r], np.arange(n)] = np.round(data['colors'] * 255).astype(np.uint8)
                    ax.imshow(image, interpolation='nearest', extent=(-0.5, n - 0.5, n - 0.5, -0.5))
                else:
                    ax.scatter(np.arange(n), data['slots'][r], s=0.5, c=data['colors'], marker=',',
                               linewidths=0, rasterized=True)
                ax.set_xlim(-0.5, n - 0.5)
                ax.set_ylim(n - 0.5, -0.5)
                ax.set_aspect('equal')
                ax.set_title(f"σ{str(r).translate(SUPERSCRIPTS)} = {cycle_text(power(data['sigma'], r))}"
                             if len(powers) > 1 else self._title(), fontsize=8 if len(powers) > 1 else 9)
                if len(powers) == 1:
                    ax.set_xlabel('Subcycle (time order)')
                    ax.set_ylabel('Its place under σ')
                else:
                    ax.set_xticks([])
                    ax.set_yticks([])
                ax._permutation_power = r
                self._axes.append(ax)
        what = 'Click a subcycle to select it.'
        self.info.setText(f"{n} subcycles of depth {data['depth']}. {what}")

    def _draw_highlights(self) -> None:
        for artist in self._highlights:
            artist.remove()
        self._highlights = []
        data = self._data
        if data is None:
            return
        state = self.state
        marks = []
        if state.follow and state.sky_time is not None:
            marks.append((state.moment_index(data['depth']), MOMENT_COLOR))
        selection = state.selection
        if selection is not None and len(selection) == data['depth']:
            marks.append((tcoord(selection), SELECTION_COLOR))
        n = len(data['indices'])
        for index, color in marks:
            if index is None or not data['indices'][0] <= index <= data['indices'][-1]:
                continue
            k = int(index - data['indices'][0])
            path = data['slots'][:, k]
            if self.view.currentData() == 'timeline':
                ax = self._axes[0]
                xs, ys = [], []
                for r, slot in enumerate(path):
                    x = data['centers'][slot]
                    xs += [x, x]
                    ys += [r * (1 + ROW_GAP), r * (1 + ROW_GAP) + 1]
                self._highlights += ax.plot(xs, ys, color=color, linewidth=2, solid_capstyle='butt')
                self._highlights.append(ax.scatter(data['centers'][path], [r * (1 + ROW_GAP) + 0.5
                                                                           for r in range(len(path))],
                                                   s=40, facecolors='white', edgecolors=color, linewidths=1.5,
                                                   zorder=5))
            else:
                for ax in self._axes:
                    r = ax._permutation_power
                    self._highlights.append(ax.scatter([k], [data['slots'][r][k]], s=120 if n <= 256 else 60,
                                                       facecolors='none', edgecolors=color, linewidths=1.8,
                                                       zorder=5))
        if selection is not None and len(selection) == data['depth'] \
                and data['indices'][0] <= tcoord(selection) <= data['indices'][-1]:
            k = tcoord(selection) - data['indices'][0]
            orbit = len(set(int(s) for s in data['slots'][:-1, k]))
            names = ' › '.join(state.names[d] for d in selection)
            self.info.setText(f"{n} subcycles of depth {data['depth']}. Selected: {names}, which ⟨σ⟩ moves through "
                              f"{orbit} subcycle{'s' if orbit != 1 else ''}.")

    # -- interaction

    def _subcycle_at(self, event) -> int | None:
        """Index (in the level) of the subcycle under the mouse, or None."""
        data = self._data
        if data is None or event.inaxes is None or event.inaxes not in self._axes or event.xdata is None:
            return None
        n = len(data['indices'])
        if self.view.currentData() == 'timeline':
            y = event.ydata
            r = int(y // (1 + ROW_GAP))
            if not 0 <= r <= data['order'] or y - r * (1 + ROW_GAP) > 1:
                return None
            slot = int(np.searchsorted(data['edges'], event.xdata, side='right')) - 1
            if not 0 <= slot < n:
                return None
            if data['occupants'] is None:
                data['occupants'] = np.argsort(data['slots'], axis=1)      # subcycle in each slot, per row
            return int(data['indices'][data['occupants'][r][slot]])
        k = int(round(event.xdata))
        return int(data['indices'][k]) if 0 <= k < n else None

    def _clicked(self, event) -> None:
        if event.button != 1:
            return
        index = self._subcycle_at(event)
        if index is not None:
            self.state.reveal(address_of(index, self._data['depth']))

    def _hovered(self, event) -> None:
        index = self._subcycle_at(event)
        if index is None:
            QToolTip.hideText()
            return
        address = address_of(index, self._data['depth'])
        QToolTip.showText(QCursor.pos(), ' › '.join(self.state.names[d] for d in address), self.canvas)
