"""Main window of the cycles GUI. Run with ``cycles-gui`` or ``python -m cycles.gui``."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDockWidget, QFileDialog, QLabel, QMainWindow, QMessageBox, QSpinBox,
    QToolBar, QToolButton, QVBoxLayout, QWidget,
)

from cycles.functions.division import COLOR_KEYS
from cycles.gui.datepanel import DatePanel
from cycles.gui.inspector import Inspector
from cycles.gui.measures import MeasuresPanel
from cycles.gui.navigator import Breadcrumb, Navigator
from cycles.gui.sky import SkyPanel
from cycles.gui.studies import StudyLauncher
from cycles.gui.modeldialog import CycleModelDialog
from cycles.gui.state import MAX_DEPTH, NAME_SETS, CycleState


class MainWindow(QMainWindow):
    # Special entries of the cycle box
    CURRENT, NORMALIZED = '\x00current', '\x00normalized'
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

        self.sky_panel = SkyPanel(self.state)
        sky_dock = QDockWidget('Sky', self)
        sky_dock.setObjectName('sky')
        sky_dock.setWidget(self.sky_panel)
        sky_dock.setFeatures(dock.features())
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, sky_dock)
        self.tabifyDockWidget(date_dock, sky_dock)

        self.measures_panel = MeasuresPanel(self.state)
        measures_dock = QDockWidget('Measures', self)
        measures_dock.setObjectName('measures')
        measures_dock.setWidget(self.measures_panel)
        measures_dock.setFeatures(dock.features())
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, measures_dock)
        self.tabifyDockWidget(sky_dock, measures_dock)
        dock.raise_()
        self.docks = {'inspector': dock, 'date': date_dock, 'sky': sky_dock, 'measures': measures_dock}
        self.launcher: StudyLauncher | None = None
        self.model_dialog: CycleModelDialog | None = None

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

        bar.addWidget(QLabel(' Cycle '))
        self.model_box = QComboBox()
        self.model_box.setToolTip('How the yuga cycle sits in history (a preset), or normalized time')
        self.model_box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.model_box.activated.connect(self._model_chosen)
        bar.addWidget(self.model_box)
        model_button = QToolButton()
        model_button.setText('Model…')
        model_button.setToolTip('Edit the cycle model: anchor, length, division, precession; save presets')
        model_button.clicked.connect(self.show_model_dialog)
        bar.addWidget(model_button)
        self._fill_model_box()
        state.modelChanged.connect(self._fill_model_box)
        state.presetsChanged.connect(self._fill_model_box)

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

    def _fill_model_box(self, *_) -> None:
        """Presets, the current model if it is not one of them, and normalized time."""
        state = self.state
        box = self.model_box
        box.blockSignals(True)
        box.clear()
        for name in state.presets:
            box.addItem(name, name)
        if state.model is not None and state.presets.get(state.model.name) != state.model:
            box.insertItem(0, f"{state.model.name} (modified)", self.CURRENT)
        box.addItem('Normalized time (0 to 1)', self.NORMALIZED)
        if state.model is None:
            box.setCurrentIndex(box.findData(self.NORMALIZED))
        elif state.presets.get(state.model.name) == state.model:
            box.setCurrentIndex(box.findData(state.model.name))
        else:
            box.setCurrentIndex(box.findData(self.CURRENT))
        box.blockSignals(False)

    def _model_chosen(self, index: int) -> None:
        key = self.model_box.itemData(index)
        if key == self.CURRENT:
            return
        try:
            self.state.set_model(None if key == self.NORMALIZED else self.state.presets[key])
        except ValueError as error:
            self.statusBar().showMessage(f"Cannot use this cycle model: {error}", 10000)
            self._fill_model_box()

    def show_model_dialog(self) -> None:
        if self.model_dialog is None:
            self.model_dialog = CycleModelDialog(self.state, self)
        elif self.state.model is not None:
            self.model_dialog.load(self.state.model)
        self.model_dialog.show()
        self.model_dialog.raise_()
        self.model_dialog.activateWindow()

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
        studies = QAction('S&tudies…', self)
        studies.setShortcut(QKeySequence('Ctrl+T'))
        studies.triggered.connect(self.show_studies)
        file_menu.addAction(studies)
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

    def show_studies(self) -> None:
        if self.launcher is None:
            self.launcher = StudyLauncher(self)
        self.launcher.show()
        self.launcher.raise_()
        self.launcher.activateWindow()

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
    app.setOrganizationName('cycles')
    app.setApplicationName('cycles-gui')
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
