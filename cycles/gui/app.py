"""Main window of the cycles GUI. Run with ``cycles-gui`` or ``python -m cycles.gui``."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDockWidget, QFileDialog, QLabel, QMainWindow, QMessageBox, QSpinBox,
    QToolBar, QVBoxLayout, QWidget,
)

from cycles.functions.division import COLOR_KEYS
from cycles.gui.datepanel import DatePanel
from cycles.gui.inspector import Inspector
from cycles.gui.navigator import Breadcrumb, Navigator
from cycles.gui.state import MAX_DEPTH, NAME_SETS, TIME_MAP_LABELS, CycleState


class MainWindow(QMainWindow):
    def __init__(self, state: CycleState | None = None):
        super().__init__()
        self.state = state or CycleState()
        self.setWindowTitle('Cycles')

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)
        self.breadcrumb = Breadcrumb(self.state)
        self.navigator = Navigator(self.state)
        layout.addWidget(self.breadcrumb)
        layout.addWidget(self.navigator, 1)
        self.setCentralWidget(central)

        self.inspector = Inspector(self.state)
        dock = QDockWidget('Subcycle', self)
        dock.setObjectName('inspector')
        dock.setWidget(self.inspector)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable
                         | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        self.date_panel = DatePanel(self.state)
        date_dock = QDockWidget('Date', self)
        date_dock.setObjectName('date')
        date_dock.setWidget(self.date_panel)
        date_dock.setFeatures(dock.features())
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, date_dock)
        self.tabifyDockWidget(dock, date_dock)
        dock.raise_()

        self._build_toolbar()
        self._build_menus()
        self.navigator.hovered.connect(self._show_hovered)
        self.navigator.busy.connect(self._show_busy)
        self.resize(1400, 760)
        self.resizeDocks([dock], [430], Qt.Orientation.Horizontal)
        self.navigator.setFocus()

    def _build_toolbar(self) -> None:
        state = self.state
        bar = QToolBar('View')
        bar.setObjectName('view')
        self.addToolBar(bar)

        bar.addWidget(QLabel(' Time '))
        self.time_box = QComboBox()
        for name in state.time_maps:
            self.time_box.addItem(TIME_MAP_LABELS.get(name, name), name)
        self.time_box.setToolTip('Physical time of the yuga cycle, from the precession of the equinoxes. '
                                 'Dividing precession angle, every boundary is a precession boundary.')
        self.time_box.currentIndexChanged.connect(lambda i: state.set_time_map(self.time_box.itemData(i)))
        bar.addWidget(self.time_box)

        bar.addWidget(QLabel('  Color '))
        self.color_box = QComboBox()
        self.color_box.addItems(COLOR_KEYS)
        self.color_box.setCurrentText(state.color_key)
        self.color_box.currentTextChanged.connect(state.set_color_key)
        bar.addWidget(self.color_box)

        bar.addWidget(QLabel('  Levels '))
        self.rows_box = QSpinBox()
        self.rows_box.setRange(1, 6)
        self.rows_box.setValue(state.rows)
        self.rows_box.setToolTip('Number of levels drawn below the zoomed subcycle')
        self.rows_box.valueChanged.connect(state.set_rows)
        bar.addWidget(self.rows_box)

        bar.addWidget(QLabel('  Widths '))
        self.spacing_box = QComboBox()
        self.spacing_box.addItem('by duration', 'time')
        self.spacing_box.addItem('equal', 'index')
        self.spacing_box.setToolTip('By duration: the horizontal axis is time. Equal: it is the index.')
        self.spacing_box.currentIndexChanged.connect(
            lambda i: state.set_spacing(self.spacing_box.itemData(i)))
        bar.addWidget(self.spacing_box)

        bar.addWidget(QLabel('  Names '))
        self.names_box = QComboBox()
        for label, names in NAME_SETS.items():
            self.names_box.addItem(label, names)
        self.names_box.currentIndexChanged.connect(lambda i: state.set_names(self.names_box.itemData(i)))
        bar.addWidget(self.names_box)

        bar.addSeparator()
        self.equal_box = QCheckBox('Equal durations')
        self.equal_box.setToolTip('Dim the subcycles whose duration differs from the selected one')
        self.equal_box.toggled.connect(state.set_highlight_equal)
        bar.addWidget(self.equal_box)

        state.viewChanged.connect(self._sync_toolbar)

    def _sync_toolbar(self) -> None:
        """Keep the toolbar in step with changes made elsewhere (e.g. from the inspector)."""
        self.color_box.setCurrentText(self.state.color_key)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu('&File')
        save = QAction('&Save view as image…', self)
        save.setShortcut(QKeySequence.StandardKey.Save)
        save.triggered.connect(self.save_view)
        file_menu.addAction(save)
        file_menu.addSeparator()
        quit_action = QAction('&Quit', self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = self.menuBar().addMenu('&View')
        zoom_out = QAction('Zoom &out', self)
        zoom_out.setShortcut(QKeySequence('Ctrl+Up'))
        zoom_out.triggered.connect(self.state.zoom_out)
        view_menu.addAction(zoom_out)
        whole = QAction('&Whole cycle', self)
        whole.setShortcut(QKeySequence('Ctrl+Home'))
        whole.triggered.connect(lambda: self.state.set_focus(()))
        view_menu.addAction(whole)

        help_menu = self.menuBar().addMenu('&Help')
        about = QAction('&Navigation', self)
        about.triggered.connect(self.show_help)
        help_menu.addAction(about)

    def _show_hovered(self, address) -> None:
        if address:
            names = self.state.names
            self.statusBar().showMessage(' › '.join(names[d] for d in address))
        else:
            self.statusBar().clearMessage()

    def _show_busy(self, message: str) -> None:
        if message:
            self.statusBar().showMessage(message)
            self.statusBar().repaint()   # the computation blocks the event loop
        else:
            self.statusBar().clearMessage()

    def save_view(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, 'Save view', 'cycles.png', 'Images (*.png *.jpg *.bmp)')
        if path:
            self.navigator.grab().save(path)

    def show_help(self) -> None:
        QMessageBox.information(self, 'Navigation', (
            'Click a subcycle to select it; double-click to zoom into it; right-click to zoom out.\n\n'
            'Keys in the navigator:\n'
            '  ← →  previous / next subcycle of the same depth\n'
            '  ↑  parent      ↓  first part\n'
            '  Enter  zoom into the selection\n'
            '  Backspace / Esc  zoom out\n\n'
            f'Subcycles are computed down to depth {MAX_DEPTH}; the deepest levels take a few '
            'seconds the first time.'))


def main(argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv if argv is None else argv)
    app.setApplicationName('Cycles')
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
