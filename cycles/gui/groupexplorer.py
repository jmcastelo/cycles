"""
Group explorer: every element of the symmetric group S_m acting on the digit
positions where the Permutations panel's σ acts, in a sortable table.

The structural columns (cycle type, order, parity, fixed subcycles, orbits of
⟨σ⟩) follow from the cycles of each element. The others are means over the
subcycles of the panel's span, computed for many elements at once and filled
in progressively: a permutation σ takes the subcycle with tail digits ``a`` to
the slot ``Σ_j a_j 4^(m-1-σ⁻¹(j))``, so the slots of a whole block of elements
are one matrix product.
"""

import itertools
from math import comb

import numpy as np
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableView, QVBoxLayout,
)

from cycles.functions.permutation import cycle_text, cycle_type, cycles, order, power, sign
from cycles.functions.division import MODEL_COLOR_KEYS
from cycles.gui.state import CycleState, children_range

COLUMNS = [
    # key, header, tooltip
    ('sigma', 'σ', 'In cycle notation; position 0 is the first digit σ acts on'),
    ('oneline', 'One-line', 'The images of the positions 0, 1, …'),
    ('type', 'Cycle type', 'Lengths of the cycles of σ'),
    ('order', 'Order', 'Least power of σ that is the identity'),
    ('sign', 'Parity', 'Even or odd'),
    ('fixed', 'Fixed', 'Subcycles that σ leaves in place (4 to the number of cycles)'),
    ('orbits', 'Orbits', 'Orbits of ⟨σ⟩ on the subcycles (Burnside: the mean of the fixed subcycles of the powers)'),
    ('moved', 'Moved %', 'Share of the subcycles that σ moves to another place'),
    ('shift', 'Mean shift %', 'Mean distance in time between a subcycle and its image, in % of the span'),
    ('correlation', 'Time order', 'Correlation between the order of the subcycles and the order of their images '
                                  '(1: kept, -1: reversed)'),
    ('color', 'Color change', 'Mean RGB distance between a subcycle and its image in the current coloring '
                              '(0: σ keeps the coloring; 1: black to white)'),
    ('dharma', 'Δ dharma', 'Mean change of dharma between a subcycle and its image'),
    ('purity', 'Δ purity', 'Mean change of purity between a subcycle and its image'),
]
NUMERIC = ['order', 'fixed', 'orbits', 'moved', 'shift', 'correlation', 'color', 'dharma', 'purity']
HEAVY = ['moved', 'shift', 'correlation', 'color', 'dharma', 'purity']
BLOCK_ENTRIES = 2_000_000       # subcycles × elements per block (memory and time of one step)


class GroupModel(QAbstractTableModel):
    """The elements of S_m and their columns, with sorting and a filter by cycle type and parity."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.perms = np.zeros((0, 0), dtype=np.int64)
        self.values: dict[str, np.ndarray] = {}
        self.types: list[str] = []
        self.rows = np.zeros(0, dtype=np.int64)     # the elements shown, in the order shown
        self._sort = (None, Qt.SortOrder.AscendingOrder)
        self._filter = (None, None)

    def reset(self, perms: np.ndarray, values: dict, types: list[str]) -> None:
        self.beginResetModel()
        self.perms, self.values, self.types = perms, values, types
        self._arrange()
        self.endResetModel()

    def update_columns(self) -> None:
        """New values of the heavy columns: keep the arrangement unless sorted by one of them."""
        if self._sort[0] in HEAVY:
            self.layoutAboutToBeChanged.emit()
            self._arrange()
            self.layoutChanged.emit()
        else:
            first = [k for k, (key, *_) in enumerate(COLUMNS) if key in HEAVY]
            self.dataChanged.emit(self.index(0, first[0]), self.index(self.rowCount() - 1, first[-1]))

    def set_filter(self, cycle_type: str | None, parity: int | None) -> None:
        self.beginResetModel()
        self._filter = (cycle_type, parity)
        self._arrange()
        self.endResetModel()

    def _arrange(self) -> None:
        rows = np.arange(len(self.perms))
        cycle_type_wanted, parity = self._filter
        if cycle_type_wanted is not None:
            rows = rows[np.array([self.types[i] == cycle_type_wanted for i in rows], dtype=bool)]
        if parity is not None and len(rows):
            rows = rows[self.values['sign'][rows] == parity]
        key, sort_order = self._sort
        if key in NUMERIC or key == 'sign':
            column = self.values[key][rows]
            missing = np.isnan(column)
            ranked = np.argsort(np.where(missing, np.inf, column) if sort_order == Qt.SortOrder.AscendingOrder
                                else np.where(missing, np.inf, -column), kind='stable')
            rows = rows[ranked]
        elif key in ('sigma', 'oneline'):
            # the elements are listed in the lexicographic order of their one-line notation
            if sort_order == Qt.SortOrder.DescendingOrder:
                rows = rows[::-1]
        elif key == 'type':
            rows = np.array(sorted(rows, key=lambda i: tuple(-int(n) for n in self.types[i].split('+')),
                                   reverse=sort_order == Qt.SortOrder.DescendingOrder), dtype=np.int64)
        self.rows = rows

    # -- Qt model

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return COLUMNS[section][1]
            if role == Qt.ItemDataRole.ToolTipRole:
                return COLUMNS[section][2]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        i = int(self.rows[index.row()])
        key = COLUMNS[index.column()][0]
        if role == Qt.ItemDataRole.TextAlignmentRole and key in NUMERIC:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        sigma = tuple(int(x) for x in self.perms[i])
        if key == 'sigma':
            return cycle_text(sigma)
        if key == 'oneline':
            return ' '.join(map(str, sigma))
        if key == 'type':
            return self.types[i]
        if key == 'sign':
            return 'even' if self.values['sign'][i] > 0 else 'odd'
        value = self.values[key][i]
        if np.isnan(value):
            return '…'
        if key in ('order', 'fixed', 'orbits'):
            return f"{int(value)}"
        if key in ('moved', 'shift'):
            return f"{100 * value:.2f}"
        if key == 'correlation':
            return f"{value:+.4f}"
        return f"{value:.4f}"

    def sort(self, column, order=Qt.SortOrder.AscendingOrder) -> None:
        self.layoutAboutToBeChanged.emit()
        self._sort = (COLUMNS[column][0], order)
        self._arrange()
        self.layoutChanged.emit()


class GroupExplorer(QDialog):
    """Every element of the group where the Permutations panel's σ acts; clicking one loads it into the panel."""

    def __init__(self, panel, state: CycleState, parent=None):
        super().__init__(parent)
        self.panel = panel
        self.state = state
        self.setWindowTitle('Group explorer')
        self.resize(980, 620)
        self._context = None
        self._work = None
        layout = QVBoxLayout(self)
        self.heading = QLabel()
        self.heading.setWordWrap(True)
        layout.addWidget(self.heading)

        row = QHBoxLayout()
        row.addWidget(QLabel('Cycle type'))
        self.type_filter = QComboBox()
        row.addWidget(self.type_filter)
        row.addWidget(QLabel('Parity'))
        self.parity_filter = QComboBox()
        self.parity_filter.addItem('both', None)
        self.parity_filter.addItem('even', 1)
        self.parity_filter.addItem('odd', -1)
        row.addWidget(self.parity_filter)
        row.addStretch(1)
        self.progress = QLabel()
        row.addWidget(self.progress)
        self.stop_button = QPushButton('Stop')
        self.stop_button.clicked.connect(self.stop)
        row.addWidget(self.stop_button)
        layout.addLayout(row)

        self.model = GroupModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(self.table.fontMetrics().height() + 6)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.clicked.connect(self._clicked)
        self.table.activated.connect(self._clicked)
        layout.addWidget(self.table, 1)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setStyleSheet('color: palette(placeholder-text)')
        layout.addWidget(self.note)

        self.timer = QTimer(self)
        self.timer.setInterval(0)
        self.timer.timeout.connect(self._step)
        self.type_filter.currentIndexChanged.connect(self._filter_changed)
        self.parity_filter.currentIndexChanged.connect(self._filter_changed)
        for signal in (state.focusChanged, state.selectionChanged, state.viewChanged, state.colorParametersChanged,
                       state.permutationChanged):
            signal.connect(self.refresh)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def closeEvent(self, event) -> None:
        self.stop()
        super().closeEvent(event)

    # -- context

    def context(self):
        """(depth, prefix, first) where the panel's σ acts, or None."""
        depth = self.panel.plot_depth()
        scope = self.panel.scope(depth)
        if scope is None:
            return None
        prefix, first = scope
        return depth, prefix, first

    def refresh(self, *_) -> None:
        if not self.isVisible():
            return
        state = self.state
        context = self.context()
        key = (context, state.color_key, state.parameters_of(state.color_key), state.measure_parameters_of('dharma'),
               state.measure_parameters_of('purity'), state.model if state.color_key in MODEL_COLOR_KEYS else None)
        if key != self._context:
            self._context = key
            self._rebuild(context)
        self._select_current()

    def _rebuild(self, context) -> None:
        self.stop()
        state = self.state
        if context is None:
            self.heading.setText('The Permutations panel has no digits to permute: choose a depth below the zoom, '
                                 'or let σ act on all the digits.')
            self.model.reset(np.zeros((0, 0), dtype=np.int64), {}, [])
            self.note.setText('')
            return
        depth, prefix, first = context
        m = depth - first
        perms = np.array(list(itertools.permutations(range(m))), dtype=np.int64).reshape(-1, m)
        cycle_counts = np.array([len(cycles(tuple(p))) for p in perms])
        orders = np.array([order(tuple(p)) for p in perms])
        orbits = np.array([sum(4 ** len(cycles(power(tuple(p), r))) for r in range(o)) // o
                           for p, o in zip(perms, orders)])
        values = {'order': orders.astype(float), 'sign': np.array([sign(tuple(p)) for p in perms], dtype=float),
                  'fixed': (4.0 ** cycle_counts), 'orbits': orbits.astype(float)}
        for key in HEAVY:
            values[key] = np.full(len(perms), np.nan)
        types = ['+'.join(map(str, cycle_type(tuple(p)))) for p in perms]
        self.model.reset(perms, values, types)
        self.type_filter.blockSignals(True)
        self.type_filter.clear()
        self.type_filter.addItem('all', None)
        for name in sorted(set(types), key=lambda t: tuple(-int(n) for n in t.split('+'))):
            self.type_filter.addItem(name, name)
        self.type_filter.blockSignals(False)
        self.parity_filter.setCurrentIndex(0)

        where = ' › '.join(state.names[d] for d in prefix) or 'the whole cycle'
        n = 4 ** m
        self.heading.setText(
            f"<b>S<sub>{m}</sub></b>: the {len(perms)} permutations of the digits {first + 1}–{depth} of the "
            f"{n} subcycles of depth {depth} in {where}, as in the Permutations panel. Click a row to load it "
            "into the panel; click a header to sort.")
        mean_fixed = values['fixed'].mean()
        self.note.setText(
            f"Burnside: the mean of the fixed subcycles over the group is {mean_fixed:g}, the number of "
            f"compositions of {m} digits among 4 ages, C({m + 3}, 3) = {comb(m + 3, 3)}: the orbits of the whole "
            f"group are the composition classes. Means over the {n} subcycles; the colors in "
            f"{state.color_key}.")

        # what the heavy columns need
        level = state.cache.level(depth)
        span = children_range(prefix, depth)
        indices = np.arange(span.start, span.stop)
        starts = level.starts[indices]
        length = float(starts[-1] + level.durations[indices[-1]] - starts[0])
        weights = 4 ** np.arange(m - 1, -1, -1, dtype=np.int64)
        self._work = dict(
            tails=np.asarray(level.lcoords[indices][:, first:], dtype=np.int64),
            inverse_weights=weights[np.argsort(perms, axis=1)],     # w[σ⁻¹(j)] for each element
            starts=starts / length,
            colors=np.clip(np.asarray(state.colors(depth, state.color_key))[indices][:, :3], 0, 1),
            dharmas=np.asarray(level.dharmas[indices], dtype=float),
            purities=np.asarray(level.purities[indices], dtype=float),
            block=max(1, BLOCK_ENTRIES // n), next=0, total=len(perms))
        self.stop_button.setEnabled(True)
        self.timer.start()

    # -- the heavy columns, block by block

    def _step(self) -> None:
        work = self._work
        if work is None:
            self.timer.stop()
            return
        a, b = work['next'], min(work['total'], work['next'] + work['block'])
        tails = work['tails']
        n = len(tails)
        k = np.arange(n)
        slots = tails @ work['inverse_weights'][a:b].T            # n × block: the slot of each subcycle
        values = self.model.values
        values['moved'][a:b] = (slots != k[:, None]).mean(axis=0)
        values['shift'][a:b] = np.abs(work['starts'][slots] - work['starts'][:, None]).mean(axis=0)
        variance = (n * n - 1) / 12.0
        values['correlation'][a:b] = ((slots * k[:, None]).mean(axis=0) - ((n - 1) / 2) ** 2) / variance \
            if n > 1 else 1.0
        colors = work['colors']
        values['color'][a:b] = np.sqrt(((colors[slots] - colors[:, None, :]) ** 2).sum(axis=2)).mean(axis=0) \
            / np.sqrt(3)
        values['dharma'][a:b] = np.abs(work['dharmas'][slots] - work['dharmas'][:, None]).mean(axis=0)
        values['purity'][a:b] = np.abs(work['purities'][slots] - work['purities'][:, None]).mean(axis=0)
        work['next'] = b
        self.model.update_columns()
        if b >= work['total']:
            self.progress.setText(f"{work['total']} elements")
            self.stop()
        else:
            self.progress.setText(f"Computing: {b} of {work['total']} elements…")

    def stop(self) -> None:
        self.timer.stop()
        if self._work is not None and self._work['next'] < self._work['total']:
            self.progress.setText(f"Stopped at {self._work['next']} of {self._work['total']} elements")
            self._context = None        # computed again when shown or changed
        self._work = None
        self.stop_button.setEnabled(False)

    # -- interaction

    def _filter_changed(self, *_) -> None:
        self.model.set_filter(self.type_filter.currentData(), self.parity_filter.currentData())
        self._select_current()

    def _clicked(self, index) -> None:
        if index.isValid():
            sigma = tuple(int(x) for x in self.model.perms[int(self.model.rows[index.row()])])
            self.panel.load_permutation(sigma)

    def _select_current(self) -> None:
        """Select the row of the panel's σ."""
        permutation = self.state.permutation
        if permutation is None or not len(self.model.perms) or len(permutation[0]) != self.model.perms.shape[1]:
            return
        matches = np.flatnonzero(np.all(self.model.perms == np.array(permutation[0]), axis=1))
        if not len(matches):
            return
        rows = np.flatnonzero(self.model.rows == matches[0])
        if len(rows):
            index = self.model.index(int(rows[0]), 0)
            self.table.selectionModel().select(index, self.table.selectionModel().SelectionFlag.ClearAndSelect
                                               | self.table.selectionModel().SelectionFlag.Rows)
            self.table.scrollTo(index)
