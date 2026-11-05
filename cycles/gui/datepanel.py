"""Date panel: mark a date and list the subcycles that contain it, at every depth."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from cycles.gui.state import MAX_DEPTH, CycleState, current_year, date_text, parse_year, span_text, time_text


class DatePanel(QWidget):
    """Go to a date; the table lists the subcycle containing it at each depth (click to select)."""

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText('2026-11-05,  3102 BC-02-18  or  -3101.5')
        self.entry.setToolTip('A date (Julian calendar before 1582, Gregorian after) or a decimal year '
                              '(astronomical numbering: 0 = 1 BC)')
        self.entry.returnPressed.connect(self.go)
        self.go_button = QPushButton('Go')
        self.go_button.clicked.connect(self.go)
        self.now_button = QPushButton('Now')
        self.now_button.clicked.connect(self.go_now)
        row.addWidget(self.entry, 1)
        row.addWidget(self.go_button)
        row.addWidget(self.now_button)
        layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel('Select the subcycle of depth'))
        self.depth = QSpinBox()
        self.depth.setRange(1, MAX_DEPTH)
        self.depth.setValue(4)
        row.addWidget(self.depth)
        row.addStretch(1)
        layout.addLayout(row)

        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        self.table = QTableWidget(MAX_DEPTH, 4)
        self.table.setHorizontalHeaderLabels(['Subcycle', 'From', 'To', 'Lasts'])
        self.table.setVerticalHeaderLabels([f"d{d}" for d in range(1, MAX_DEPTH + 1)])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideLeft)
        for col in (1, 2, 3):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellClicked.connect(self._row_clicked)
        layout.addWidget(self.table, 1)

        self._addresses: list[tuple | None] = []
        state.dateChanged.connect(self.refresh)
        state.viewChanged.connect(self.refresh)
        state.selectionChanged.connect(self._mark_selection)
        self.refresh()

    def go(self) -> None:
        text = self.entry.text()
        if not text.strip():
            return
        try:
            year = parse_year(text)
        except ValueError as error:
            self.message.setText(f"<span style='color:#d62728'>{error}</span>")
            return
        self.state.go_to_date(year, self.depth.value())

    def go_now(self) -> None:
        self.entry.clear()
        self.state.go_to_date(current_year(), self.depth.value())

    def refresh(self, *_) -> None:
        state = self.state
        time_map = state.time_map
        self._addresses = []
        self.table.clearContents()
        enabled = time_map is not None
        for widget in (self.entry, self.go_button, self.now_button, self.depth, self.table):
            widget.setEnabled(enabled)
        if not enabled:
            self.message.setText('Choose a time map in years to use dates.')
            return
        if state.date is None:
            self.message.setText('No date marked.')
            return
        text = f"Marked: <b>{date_text(state.date)}</b> ({state.date:.3f})"
        if state.date_position() is None:
            self.message.setText(f"{text}<br>Outside the cycle, which goes from {date_text(time_map.start)} "
                                 f"to {date_text(time_map.end)}.")
            return
        self.message.setText(text)
        for depth in range(1, MAX_DEPTH + 1):
            address = state.subcycle_of_date(depth)
            self._addresses.append(address)
            t0, t1 = time_map.interval(address)
            items = [' › '.join(state.names[d] for d in address),
                     time_text(t0, t1 - t0), time_text(t1, t1 - t0), span_text(t1 - t0)]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setToolTip(f"{items[0]}\n{date_text(t0)} to {date_text(t1)}")
                self.table.setItem(depth - 1, col, item)
        self._mark_selection(state.selection)

    def _mark_selection(self, selection) -> None:
        self.table.clearSelection()
        if selection in self._addresses:
            self.table.selectRow(self._addresses.index(selection))

    def _row_clicked(self, row: int, _column: int) -> None:
        if row < len(self._addresses) and self._addresses[row] is not None:
            self.state.reveal(self._addresses[row])
