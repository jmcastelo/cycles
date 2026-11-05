"""Main window of the cycles GUI. Run with ``cycles-gui`` or ``python -m cycles.gui``."""

import sys

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDockWidget, QFileDialog, QLabel, QMainWindow, QMessageBox, QSpinBox,
    QToolBar, QToolButton, QVBoxLayout, QWidget,
)

from cycles.functions.division import COLOR_KEYS
from cycles.gui.colordialog import ColorDialog
from cycles.gui.datepanel import DatePanel
from cycles.gui.inspector import Inspector
from cycles.gui.measures import MeasuresPanel
from cycles.gui.navigator import Breadcrumb, Navigator
from cycles.gui.sky import SkyPanel
from cycles.gui.studies import StudyLauncher
from cycles.gui.modeldialog import CycleModelDialog
from cycles.gui.state import LABEL_MODES, MAX_DEPTH, NAME_SETS, CycleState


# Version of the saved panel layout (increase when the panels change)
LAYOUT_VERSION = 1


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

        self.setDockOptions(QMainWindow.DockOption.AllowNestedDocks | QMainWindow.DockOption.AllowTabbedDocks
                            | QMainWindow.DockOption.AnimatedDocks)
        self.inspector = Inspector(self.state)
        self.inspector.setMinimumWidth(330)
        self.date_panel = DatePanel(self.state)
        self.sky_panel = SkyPanel(self.state)
        self.measures_panel = MeasuresPanel(self.state)
        self.docks = {
            'inspector': self._make_dock('Subcycle', 'inspector', self.inspector),
            'date': self._make_dock('Date', 'date', self.date_panel),
            'sky': self._make_dock('Sky', 'sky', self.sky_panel),
            'measures': self._make_dock('Measures', 'measures', self.measures_panel),
        }
        self.launcher: StudyLauncher | None = None
        self.model_dialog: CycleModelDialog | None = None
        self.color_dialog: ColorDialog | None = None

        self._build_toolbar()
        self._build_menus()
        self.navigator.hovered.connect(self._show_hovered)
        self.navigator.busy.connect(self._show_busy)
        self.resize(1400, 760)
        self.arrange_panels('tabs')
        self._restore_layout()
        self.navigator.setFocus()

    # -- panels

    def _make_dock(self, title: str, name: str, widget: QWidget) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(name)
        dock.setWidget(widget)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable
                         | QDockWidget.DockWidgetFeature.DockWidgetFloatable
                         | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        return dock

    def arrange_panels(self, layout: str) -> None:
        """
        Arrange the open panels (all of them if none is open): ``'tabs'``,
        ``'side'`` (side by side), ``'stacked'``, ``'grid'`` (2 x 2), or
        ``'below'`` (side by side under the navigator).
        """
        docks = [dock for dock in self.docks.values() if dock.isVisible()] or list(self.docks.values())
        area = (Qt.DockWidgetArea.BottomDockWidgetArea if layout == 'below'
                else Qt.DockWidgetArea.RightDockWidgetArea)
        for dock in self.docks.values():
            self.removeDockWidget(dock)
        first = docks[0]
        first.setFloating(False)
        self.addDockWidget(area, first)
        first.show()
        horizontal, vertical = Qt.Orientation.Horizontal, Qt.Orientation.Vertical
        for k, dock in enumerate(docks[1:], 1):
            dock.setFloating(False)
            if layout == 'tabs':
                self.tabifyDockWidget(first, dock)
            elif layout in ('side', 'below'):
                self.splitDockWidget(docks[k - 1], dock, horizontal)
            elif layout == 'stacked':
                self.splitDockWidget(docks[k - 1], dock, vertical)
            elif layout == 'grid':
                # 0 | 1 on top, 2 under 0, 3 under 1
                if k == 1:
                    self.splitDockWidget(first, dock, horizontal)
                else:
                    self.splitDockWidget(docks[k - 2], dock, vertical)
            dock.show()
        first.raise_()
        width, height = self.width(), self.height()
        if layout == 'below':
            self.resizeDocks(docks, [width // len(docks)] * len(docks), horizontal)
            self.resizeDocks([first], [int(height * 0.45)], vertical)
        elif layout == 'side':
            self.resizeDocks(docks, [int(width * 0.6) // len(docks)] * len(docks), horizontal)
        elif layout == 'grid' and len(docks) > 1:
            self.resizeDocks(docks[:2], [int(width * 0.3)] * 2, horizontal)
        else:
            self.resizeDocks([first], [430], horizontal)

    def _restore_layout(self) -> None:
        settings = QSettings()
        geometry, state = settings.value('window/geometry'), settings.value('window/state')
        if geometry is not None:
            self.restoreGeometry(geometry)
        if state is not None:
            self.restoreState(state, LAYOUT_VERSION)

    def reset_layout(self) -> None:
        for dock in self.docks.values():
            dock.show()
        self.resize(1400, 760)
        self.arrange_panels('tabs')
        self.docks['inspector'].raise_()

    def closeEvent(self, event) -> None:
        settings = QSettings()
        settings.setValue('window/geometry', self.saveGeometry())
        settings.setValue('window/state', self.saveState(LAYOUT_VERSION))
        super().closeEvent(event)

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
        color_button = QToolButton()
        color_button.setText('Parameters…')
        color_button.setToolTip('Bases and scales of the colorings and measures')
        color_button.clicked.connect(self.show_color_dialog)
        bar.addWidget(color_button)

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

        bar.addWidget(QLabel('  Labels '))
        self.labels_box = QComboBox()
        for key, label in LABEL_MODES.items():
            self.labels_box.addItem(label, key)
        self.labels_box.setToolTip('Names (rotated in tall cells) and/or dots: 4 for Satya, 3 Treta, 2 Dvapara, '
                                   '1 Kali')
        self.labels_box.setCurrentIndex(self.labels_box.findData(state.labels))
        self.labels_box.currentIndexChanged.connect(lambda i: state.set_labels(self.labels_box.itemData(i)))
        bar.addWidget(self.labels_box)
        self.borders_box = QCheckBox('Borders')
        self.borders_box.setChecked(state.borders)
        self.borders_box.toggled.connect(state.set_borders)
        bar.addWidget(self.borders_box)

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

    def show_color_dialog(self) -> None:
        if self.color_dialog is None:
            self.color_dialog = ColorDialog(self.state, self)
        elif not self.color_dialog.isVisible():
            self.color_dialog.open_from_state()
        self.color_dialog.show()
        self.color_dialog.raise_()
        self.color_dialog.activateWindow()

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

        panels_menu = self.menuBar().addMenu('&Panels')
        for k, dock in enumerate(self.docks.values(), 1):
            action = dock.toggleViewAction()
            action.setShortcut(QKeySequence(f'Alt+{k}'))
            panels_menu.addAction(action)
        panels_menu.addSeparator()
        for label, layout, key in (('Arrange as &tabs', 'tabs', 'Ctrl+Alt+T'),
                                   ('Arrange side by &side', 'side', 'Ctrl+Alt+S'),
                                   ('Arrange s&tacked', 'stacked', 'Ctrl+Alt+V'),
                                   ('Arrange in a &grid', 'grid', 'Ctrl+Alt+G'),
                                   ('Arrange side by side &below the navigator', 'below', 'Ctrl+Alt+B')):
            action = QAction(label, self)
            action.setShortcut(QKeySequence(key))
            action.setToolTip('Arranges the open panels (all of them if none is open)')
            action.triggered.connect(lambda _=False, l=layout: self.arrange_panels(l))
            panels_menu.addAction(action)
        panels_menu.addSeparator()
        reset = QAction('&Reset layout', self)
        reset.triggered.connect(self.reset_layout)
        panels_menu.addAction(reset)
        panels_menu.setToolTipsVisible(True)

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
