"""Inspector: everything known about the selected subcycle."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QFormLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from cycles.functions.division import CMYK_KEYS, COLOR_KEYS
from cycles.gui.navigator import rgb_to_qcolor
from cycles.gui.state import CycleState, date_text, span_text, subcycle_info


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
            ('composition', 'Composition'),
            ('equal_duration', 'Same duration'),
            ('same_composition', 'Same composition'),
            ('dharma', 'Dharma'),
            ('purity', 'Purity'),
        ]
        for key, label in rows:
            value = QLabel()
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setWordWrap(True)
            self.fields[key] = value
            form.addRow(label + ':', value)
        self.form = form
        layout.addLayout(form)

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
        self.refresh()

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
        for key in ('time_start', 'time_end', 'time_span'):
            self.form.setRowVisible(f[key], time_map is not None)
        if time_map is not None:
            t0, t1 = time_map.to_physical(info['start']), time_map.to_physical(info['end'])
            f['time_start'].setText(f"{date_text(t0)}   ({t0:.2f})")
            f['time_end'].setText(f"{date_text(t1)}   ({t1:.2f})")
            contains = state.date is not None and t0 <= state.date < t1
            f['time_span'].setText(span_text(t1 - t0) + ('   — contains the marked date' if contains else ''))
        f['composition'].setText(', '.join(f"{names[k]} {n}" for k, n in enumerate(info['composition'])))
        f['equal_duration'].setText(
            f"{info['equal_duration']} subcycles at depth {info['depth']}"
            f" ({info['equal_compositions']} composition{'s' if info['equal_compositions'] > 1 else ''})")
        f['same_composition'].setText(f"{info['same_composition']} subcycles (orderings of its ages)")
        f['dharma'].setText(f"{info['dharma']:.6f}")
        f['purity'].setText(f"{info['purity']:.6f}")

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
