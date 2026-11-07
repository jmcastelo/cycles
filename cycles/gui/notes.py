"""
Notes panel: the notes of the session (free text) and the bookmarked
subcycles, each with a label and a note. Bookmarks are flagged in the
navigator (green corner, and a tick on the overview strip); double-click one
to go to it.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPlainTextEdit, QPushButton, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from cycles.gui.state import CycleState, date_text

COLUMNS = ('Label', 'Subcycle', 'Note')


class NotesPanel(QWidget):
    """The session's notes and bookmarks."""

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        self._filling = False
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Vertical)

        top = QWidget()
        column = QVBoxLayout(top)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(QLabel('Notes of the session'))
        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText('What this session is about, what you found…')
        self.notes.textChanged.connect(lambda: self.state.set_notes(self.notes.toPlainText()))
        column.addWidget(self.notes)
        splitter.addWidget(top)

        bottom = QWidget()
        column = QVBoxLayout(bottom)
        column.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        row.addWidget(QLabel('Bookmarks'))
        row.addStretch(1)
        self.add_button = QPushButton('Bookmark the selection')
        self.add_button.setToolTip('Add the selected subcycle to the bookmarks (Ctrl+B)')
        self.add_button.clicked.connect(self.add_selection)
        self.go_button = QPushButton('Go to')
        self.go_button.setToolTip('Select the bookmarked subcycle, zooming so that it is in view (or double-click)')
        self.go_button.clicked.connect(self.go_to_current)
        self.remove_button = QPushButton('Remove')
        self.remove_button.clicked.connect(self.remove_current)
        for button in (self.add_button, self.go_button, self.remove_button):
            row.addWidget(button)
        column.addLayout(row)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                                   | QAbstractItemView.EditTrigger.EditKeyPressed
                                   | QAbstractItemView.EditTrigger.AnyKeyPressed)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.table.itemChanged.connect(self._edited)
        self.table.cellDoubleClicked.connect(lambda row, col: self.go_to(row) if col == 1 else None)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        column.addWidget(self.table)
        hint = QLabel('Double-click a label or a note to edit it, a subcycle to go to it.')
        hint.setStyleSheet('color: palette(placeholder-text)')
        column.addWidget(hint)
        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        state.notesChanged.connect(self._show_notes)
        state.bookmarksChanged.connect(self.refresh)
        state.selectionChanged.connect(self._update_buttons)
        state.modelChanged.connect(self.refresh)      # the dates
        state.viewChanged.connect(self.refresh)       # the names
        self.refresh()

    def _show_notes(self) -> None:
        if self.notes.toPlainText() != self.state.notes:
            self.notes.blockSignals(True)
            self.notes.setPlainText(self.state.notes)
            self.notes.blockSignals(False)

    def subcycle_text(self, address: tuple) -> str:
        state = self.state
        text = ' › '.join(state.names[d] for d in address)
        if state.time_map is not None:
            t0, _ = state.time_map.interval(address)
            text += f"  ({date_text(t0)})"
        return text

    def refresh(self, *_) -> None:
        self._filling = True
        current = self.table.currentRow()
        self.table.setRowCount(len(self.state.bookmarks))
        for row, bookmark in enumerate(self.state.bookmarks):
            label = QTableWidgetItem(bookmark['label'])
            label.setToolTip('Double-click to edit')
            where = QTableWidgetItem(self.subcycle_text(bookmark['address']))
            where.setFlags(where.flags() & ~Qt.ItemFlag.ItemIsEditable)
            where.setToolTip('Double-click to go to it')
            note = QTableWidgetItem(bookmark['note'])
            for col, item in enumerate((label, where, note)):
                self.table.setItem(row, col, item)
        if 0 <= current < self.table.rowCount():
            self.table.selectRow(current)
        self._filling = False
        self._update_buttons()

    def _edited(self, item: QTableWidgetItem) -> None:
        if self._filling or item.column() == 1:
            return
        key = 'label' if item.column() == 0 else 'note'
        self.state.update_bookmark(item.row(), **{key: item.text()})

    def _update_buttons(self, *_) -> None:
        self.add_button.setEnabled(bool(self.state.selection))
        has_row = self.table.currentRow() >= 0 and self.table.rowCount() > 0
        self.go_button.setEnabled(has_row)
        self.remove_button.setEnabled(has_row)

    def add_selection(self) -> None:
        """Bookmark the selection and start editing its label."""
        if not self.state.selection:
            return
        row = self.state.add_bookmark(self.state.selection)
        self.table.selectRow(row)
        self.table.setCurrentCell(row, 0)
        self.table.editItem(self.table.item(row, 0))

    def go_to(self, row: int) -> None:
        if 0 <= row < len(self.state.bookmarks):
            self.state.reveal(self.state.bookmarks[row]['address'])

    def go_to_current(self) -> None:
        self.go_to(self.table.currentRow())

    def remove_current(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.state.bookmarks):
            self.state.remove_bookmark(row)
