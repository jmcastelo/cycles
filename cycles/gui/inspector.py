"""Inspector: everything known about the selected subcycle."""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QFormLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from cycles.functions.division import CMYK_KEYS, COLOR_KEYS
from cycles.gui.navigator import rgb_to_qcolor
from cycles.functions.permutation import cycle_text
from cycles.gui.state import CycleState, date_text, measure_breakdown, span_text, subcycle_info, tcoord


def _hex(rgb) -> str:
    return rgb_to_qcolor(rgb).name()


class Inspector(QWidget):
    """Properties of the selected subcycle, and its color in every variant."""

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        layout = QVBoxLayout(self)

        self.title = QLabel()
        title_font = QFont(self.font())
        title_font.setBold(True)
        title_font.setPointSizeF(title_font.pointSizeF() * 1.2)
        self.title.setFont(title_font)
        self.title.setWordWrap(True)
        layout.addWidget(self.title)

        self.fields = {}
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        rows = [
            ('address', 'Address'),
            ('index', 'Index'),
            ('start', 'Start'),
            ('duration', 'Duration'),
            ('end', 'End'),
            ('time_start', 'Starts'),
            ('time_end', 'Ends'),
            ('time_span', 'Lasts'),
            ('ayanamsa', 'Ayanamsa'),
            ('arc', 'Arc'),
            ('rate', 'Mean rate'),
            ('composition', 'Composition'),
            ('equal_duration', 'Same duration'),
            ('same_composition', 'Same composition'),
            ('permutation', 'Under σ'),
            ('dharma', 'Dharma'),
            ('purity', 'Purity'),
            ('measures', 'More measures'),
        ]
        for key, label in rows:
            value = QLabel()
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setWordWrap(True)
            self.fields[key] = value
            form.addRow(label + ':', value)
        self.form = form
        layout.addLayout(form)

        # how each level adds to dharma, and the shares of the ages that give purity
        self.levels_title = QLabel('Measures by level:')
        layout.addWidget(self.levels_title)
        self.levels = QTableWidget(0, 5)
        self.levels.setHorizontalHeaderLabels(['Age', 'Weight', 'Virtue', 'Dharma +', 'Purity weight'])
        for col, tip in enumerate(['The age of the digit of this level',
                                   'Its weight in dharma (color weight base), the weights adding up to 1',
                                   'Value of the age: Satya 1, Treta 3/4, Dvapara 1/2, Kali 1/4',
                                   'What this level adds to dharma: weight × virtue',
                                   'Its weight in purity (purity weight base), adding up to 1']):
            self.levels.horizontalHeaderItem(col).setToolTip(tip)
        self.levels.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.levels.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.levels.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.levels.verticalHeader().setDefaultSectionSize(self.levels.fontMetrics().height() + 4)
        layout.addWidget(self.levels)
        self.levels_note = QLabel()
        self.levels_note.setWordWrap(True)
        layout.addWidget(self.levels_note)

        layout.addWidget(QLabel('Colors (double-click to use):'))
        self.colors = QTableWidget(len(COLOR_KEYS), 3)
        self.colors.setHorizontalHeaderLabels(['', 'RGB', 'CMYK'])
        self.colors.setVerticalHeaderLabels(list(COLOR_KEYS))
        self.colors.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.colors.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        header = self.colors.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 28)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.colors.cellDoubleClicked.connect(lambda row, _: state.set_color_key(COLOR_KEYS[row]))
        layout.addWidget(self.colors, 1)

        self.hint = QLabel('Click a subcycle to inspect it.\n\n'
                           'Double-click zooms in, right-click zooms out.\n'
                           'Keys: ← → previous/next, ↑ parent, ↓ first part,\n'
                           'Enter zoom in, Backspace zoom out.')
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        state.selectionChanged.connect(self.refresh)
        state.viewChanged.connect(self.refresh)
        state.dateChanged.connect(self.refresh)
        state.colorParametersChanged.connect(self.refresh)   # it shows every coloring
        state.permutationChanged.connect(self.refresh)
        self.refresh()

    def _permutation_text(self, address: tuple) -> str:
        """The image of ``address`` under the σ of the Permutations panel, and the size of its orbit."""
        state = self.state
        if state.permutation is None:
            return '—'
        sigma, first = state.permutation
        orbit = state.permutation_orbit(address)
        if orbit is None:
            return (f"σ = {cycle_text(sigma)} of the Permutations panel acts on subcycles of depth "
                    f"{first + len(sigma)}" + (f" inside {' › '.join(state.names[d] for d in address[:first])}"
                                                if first else ''))
        if len(orbit) == 1:
            return f"fixed by σ = {cycle_text(sigma)}"
        image = ' › '.join(state.names[d] for d in orbit[1])
        return f"σ = {cycle_text(sigma)} takes it to {image}; its orbit has {len(orbit)} subcycles"

    def _measures_text(self, address: tuple) -> str:
        """The measures other than dharma and purity (measure.MEASURES), on one line."""
        from cycles.functions.measure import MEASURES
        state, index = self.state, tcoord(address)
        parts = []
        for key, m in MEASURES.items():
            if key in ('dharma', 'purity'):
                continue
            values = state.measure_values(len(address), key)
            if values is not None:
                signed = m['range'] is not None and m['range'][0] < 0 or key == 'balance'
                parts.append(f"{m['label'].lower()} {values[index]:{'+' if signed else ''}.4f}".replace('-', '−'))
        return ' · '.join(parts)

    def _show_levels(self, address: tuple) -> None:
        """The per-level table of dharma and the age shares of purity, and their range over the orderings."""
        state = self.state
        names = state.names
        bases = state.color_parameters[0]
        b = measure_breakdown(state.cache.level(len(address)), address, bases)
        self.levels.setRowCount(len(address))
        self.levels.setVerticalHeaderLabels([str(k + 1) for k in range(len(address))])
        for k, digit in enumerate(address):
            cells = [names[digit], f"{b['dharma_weights'][k]:.4f}", f"{b['virtues'][k]:g}",
                     f"{b['dharma_parts'][k]:.4f}", f"{b['purity_weights'][k]:.4f}"]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.levels.setItem(k, col, item)
        rows = min(len(address), 8)
        self.levels.setFixedHeight(self.levels.horizontalHeader().sizeHint().height()
                                   + rows * self.levels.verticalHeader().defaultSectionSize() + 4)
        shares = b['shares']
        top, bottom = int(np.argmax(shares)), int(np.argmin(shares))
        lo_d, hi_d = b['dharma_range']
        lo_p, hi_p = b['purity_range']
        n = b['orderings']
        if n == 1:
            orderings = 'Its ages have a single ordering.'
        else:
            dharma = 'the same dharma' if hi_d - lo_d < 1e-12 else f"dharma from {lo_d:.4f} to {hi_d:.4f}"
            purity = 'the same purity' if hi_p - lo_p < 1e-12 else f"purity from {lo_p:.4f} to {hi_p:.4f}"
            orderings = (f"Its {n} orderings (same composition) have {dharma} and {purity}: outer levels weigh "
                         f"more (bases {bases[1]:g} and {bases[2]:g}); a base of 1 would weigh all levels alike.")
        self.levels_note.setText(
            f"Dharma = the sum of the column Dharma + = {b['dharma']:.4f}. Shares of the ages for purity: "
            + ', '.join(f"{names[a]} {shares[a]:.4f}" for a in range(4))
            + f"; purity = {names[top]} − {names[bottom]} = {b['purity']:.4f}. " + orderings)

    def refresh(self, *_) -> None:
        state = self.state
        address = state.selection
        self.hint.setVisible(address is None)
        for widget in (self.title, self.colors, *self.fields.values()):
            widget.setEnabled(address is not None)
        if address is None:
            self.title.setText('No selection')
            for value in self.fields.values():
                value.setText('—')
            for row in range(self.colors.rowCount()):
                for col in range(3):
                    self.colors.setItem(row, col, QTableWidgetItem(''))
            self.levels.setRowCount(0)
            self.levels_note.setText('')
            return

        info = subcycle_info(state.cache, address)
        names = state.names
        self.title.setText(' › '.join(names[d] for d in address))
        f = self.fields
        f['address'].setText(f"{' '.join(map(str, address))}   (depth {info['depth']})")
        f['index'].setText(f"{info['index']} of {info['count']}")
        f['start'].setText(f"{info['start']:.12g}")
        f['duration'].setText(f"{info['duration']:.12g}   (1/{1 / info['duration']:.6g} of the cycle)")
        f['end'].setText(f"{info['end']:.12g}")
        time_map = state.time_map
        for key in ('time_start', 'time_end', 'time_span', 'ayanamsa', 'arc', 'rate'):
            self.form.setRowVisible(f[key], time_map is not None)
        if time_map is not None:
            t0, t1 = time_map.to_physical(info['start']), time_map.to_physical(info['end'])
            f['time_start'].setText(f"{date_text(t0)}   ({t0:.2f})")
            f['time_end'].setText(f"{date_text(t1)}   ({t1:.2f})")
            contains = state.date is not None and t0 <= state.date < t1
            f['time_span'].setText(span_text(t1 - t0) + ('   — contains the marked date' if contains else ''))
            model = state.model
            a0, a1 = float(model.ayanamsa(t0)), float(model.ayanamsa(t1))
            cycle_start = float(model.ayanamsa(time_map.start))
            f['ayanamsa'].setText(f"{a0:.4f}° to {a1:.4f}°")
            f['arc'].setText(f"{a1 - a0:.4f}°, from {a0 - cycle_start:.4f}° to {a1 - cycle_start:.4f}° "
                             f"after the start of the cycle")
            f['rate'].setText(f"{(a1 - a0) * 3600 / (t1 - t0):.3f}″ per year" if t1 > t0 else '—')
        f['composition'].setText(', '.join(f"{names[k]} {n}" for k, n in enumerate(info['composition'])))
        f['equal_duration'].setText(
            f"{info['equal_duration']} subcycles at depth {info['depth']}"
            f" ({info['equal_compositions']} composition{'s' if info['equal_compositions'] > 1 else ''})")
        f['same_composition'].setText(f"{info['same_composition']} subcycles (orderings of its ages); "
                                      f"it is number {info['composition_rank']} in time order")
        f['permutation'].setText(self._permutation_text(address))
        f['dharma'].setText(f"{info['dharma']:.6f}")
        f['purity'].setText(f"{info['purity']:.6f}")
        f['measures'].setText(self._measures_text(address))
        self._show_levels(address)

        bold = QFont(self.colors.font())
        bold.setBold(True)
        for row, key in enumerate(COLOR_KEYS):
            rgb = info['rgb'][key]
            swatch = QTableWidgetItem('')
            swatch.setBackground(rgb_to_qcolor(rgb))
            self.colors.setItem(row, 0, swatch)
            items = [QTableWidgetItem(_hex(rgb)),
                     QTableWidgetItem(' '.join(f"{c:.3f}" for c in info['cmyk'][key]) if key in CMYK_KEYS else '')]
            for col, item in enumerate(items, 1):
                if key == state.color_key:
                    item.setFont(bold)
                self.colors.setItem(row, col, item)
