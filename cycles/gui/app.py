"""Main window of the cycles GUI. Run with ``cycles-gui`` or ``python -m cycles.gui``."""

import sys

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDockWidget, QLabel, QLineEdit, QMainWindow, QMessageBox, QSpinBox,
    QToolBar, QToolButton, QVBoxLayout, QWidget,
)

from cycles.functions.division import (
    COLOR_DESCRIPTIONS, COLOR_KEYS, LEVEL_COLOR_KEYS, MEASURE_COLOR_KEYS, MODEL_COLOR_KEYS, SKY_COLOR_KEYS,
)
from cycles.gui.colordialog import ColorDialog
from cycles.gui.colorspace import ColorSpacePanel
from cycles.gui.compositions import CompositionsPanel
from cycles.gui.skycompare import SkyComparisonPanel
from cycles.gui.landscape import LandscapePanel
from cycles.gui.notes import NotesPanel
from cycles.gui.eventspanel import EventsPanel
from cycles.gui.layouts import AROUND, PanelPlacement, set_corners
from cycles.gui.session import SessionManager
from cycles.gui.permutations import PermutationsPanel
from cycles.gui.datepanel import DatePanel
from cycles.gui.export import LOGICAL_DPI, ExportDialog, GraphSource, save_figure, save_widget
from cycles.gui.inspector import Inspector
from cycles.gui.measures import MeasuresPanel
from cycles.gui.navigator import Breadcrumb, Navigator
from cycles.gui.sky import SkyPanel
from cycles.gui.studies import StudyLauncher
from cycles.gui.modeldialog import CycleModelDialog
from cycles.gui.state import HIGHLIGHTS, LABEL_MODES, MAX_DEPTH, NAME_SETS, CycleState, datetime_text


# Version of the saved panel layout (increase when the panels change)
QUERY_HELP = (
    'A condition on the subcycles, for the highlight "Matching the query" (Enter applies it):\n'
    '  the measures: dharma, purity, mixture, tension, trend, roughness, contrast, balance, microcosm,\n'
    '    complexity, density (with a model), gathering (with a model and the ephemeris);\n'
    '  duration, start (fractions of the cycle), year, years (with a model), index, depth;\n'
    '  a1, a2, … (the age of each level), first, last; the ages Satya, Treta, Dvapara, Kali;\n'
    '  and, or, not, < <= > >= == !=, + - * /, count(age), abs(x).\n'
    'Examples: trend > 0.3 and dharma < 0.5   |   last == Kali and count(Satya) >= 2   |   year > 0')
LAYOUT_VERSION = 8


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
        central.setMinimumSize(360, 240)      # panels around it never squeeze the navigator away
        self.setCentralWidget(central)

        self.setDockOptions(QMainWindow.DockOption.AllowNestedDocks | QMainWindow.DockOption.AllowTabbedDocks
                            | QMainWindow.DockOption.AnimatedDocks
                            | QMainWindow.DockOption.GroupedDragging)     # a group of tabs moves as a whole
        self.corner_mode = 'columns'
        self.inspector = Inspector(self.state)
        self.inspector.setMinimumWidth(330)
        self.date_panel = DatePanel(self.state)
        self.sky_panel = SkyPanel(self.state)
        self.measures_panel = MeasuresPanel(self.state)
        self.colorspace_panel = ColorSpacePanel(self.state)
        self.permutations_panel = PermutationsPanel(self.state)
        self.compositions_panel = CompositionsPanel(self.state)
        self.skycompare_panel = SkyComparisonPanel(self.sky_panel, self.state)
        self.landscape_panel = LandscapePanel(self.state)
        self.notes_panel = NotesPanel(self.state)
        self.events_panel = EventsPanel(self.sky_panel, self.state)
        self.docks = {
            'inspector': self._make_dock('Subcycle', 'inspector', self.inspector),
            'date': self._make_dock('Date', 'date', self.date_panel),
            'sky': self._make_dock('Sky', 'sky', self.sky_panel),
            'measures': self._make_dock('Measures', 'measures', self.measures_panel),
            'colorspace': self._make_dock('Color space', 'colorspace', self.colorspace_panel),
            'permutations': self._make_dock('Permutations', 'permutations', self.permutations_panel),
            'compositions': self._make_dock('Compositions', 'compositions', self.compositions_panel),
            'skycompare': self._make_dock('Sky comparison', 'skycompare', self.skycompare_panel),
            'landscape': self._make_dock('Model landscape', 'landscape', self.landscape_panel),
            'notes': self._make_dock('Notes', 'notes', self.notes_panel),
            'events': self._make_dock('Events', 'events', self.events_panel),
        }
        self.launcher: StudyLauncher | None = None
        self.model_dialog: CycleModelDialog | None = None
        self.color_dialog: ColorDialog | None = None
        self.export_dialog: ExportDialog | None = None
        for key, panel in (('sky', self.sky_panel), ('measures', self.measures_panel),
                           ('colorspace', self.colorspace_panel), ('permutations', self.permutations_panel),
                           ('compositions', self.compositions_panel), ('skycompare', self.skycompare_panel),
                           ('landscape', self.landscape_panel), ('events', self.events_panel)):
            panel.saveRequested.connect(lambda key=key: self.save_graph(key))
        self.sky_panel.compareRequested.connect(lambda: self.show_panel('skycompare'))

        set_corners(self, QSettings().value('panels/corners', 'columns'))
        self.placement = PanelPlacement(self)
        self._build_toolbar()
        self._build_menus()
        self.navigator.hovered.connect(self._show_hovered)
        self.navigator.busy.connect(self._show_busy)
        self.state.busy.connect(self._show_busy)
        self.resize(1400, 760)
        self.arrange_panels('tabs')
        self._restore_layout()
        self.session = SessionManager(self)
        self._fill_recent_menu()
        self.session.restore_last()
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

    def show_panel(self, name: str) -> None:
        """Open a panel (it stays where the arrangement put it) and bring it to the front."""
        dock = self.docks[name]
        dock.show()
        dock.raise_()

    def arrange_panels(self, layout: str) -> None:
        """
        Arrange the open panels (all of them if none is open): ``'tabs'``,
        ``'side'`` (side by side), ``'stacked'``, ``'grid'`` (2 x 2), or
        ``'below'`` (side by side under the navigator); or each kind of panel
        on its side of the navigator (a key of ``layouts.AROUND``).
        """
        if layout in AROUND:
            from cycles.gui.layouts import arrange_around
            arrange_around(self, layout)
            return
        docks = [dock for dock in self.docks.values() if dock.isVisible()] or list(self.docks.values())
        # The closed panels are placed too, after the open ones and kept closed, so that they stay in the
        # layout: opening one later puts it where the arrangement continues (a removed dock widget that is
        # shown again is not in any dock area, and appears nowhere)
        closed = [dock for dock in self.docks.values() if dock not in docks]
        area = (Qt.DockWidgetArea.BottomDockWidgetArea if layout == 'below'
                else Qt.DockWidgetArea.RightDockWidgetArea)
        for dock in self.docks.values():
            self.removeDockWidget(dock)
        first = docks[0]
        first.setFloating(False)
        self.addDockWidget(area, first)
        first.show()
        horizontal, vertical = Qt.Orientation.Horizontal, Qt.Orientation.Vertical
        order = docks + closed
        for k, dock in enumerate(order[1:], 1):
            dock.setFloating(False)
            if layout == 'tabs':
                self.tabifyDockWidget(first, dock)
            elif layout in ('side', 'below'):
                self.splitDockWidget(order[k - 1], dock, horizontal)
            elif layout == 'stacked':
                self.splitDockWidget(order[k - 1], dock, vertical)
            elif layout == 'grid':
                # 0 | 1 on top, 2 under 0, 3 under 1
                if k == 1:
                    self.splitDockWidget(first, dock, horizontal)
                else:
                    self.splitDockWidget(order[k - 2], dock, vertical)
            dock.setVisible(dock in docks)
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
        set_corners(self, 'columns')
        QSettings().setValue('panels/corners', 'columns')
        for dock in self.docks.values():
            dock.show()
        self.resize(1400, 760)
        self.arrange_panels('tabs')
        self.docks['inspector'].raise_()

    def closeEvent(self, event) -> None:
        if not self.session.confirm_close():          # unsaved changes: save, don't save, or cancel
            event.ignore()
            return
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
        landscape_button = QToolButton()
        landscape_button.setText('Landscape')
        landscape_button.setToolTip('Open the Model landscape panel: how well the two division criteria agree '
                                    'for every anchor and arc,\nwith the model as a point to move')
        landscape_button.clicked.connect(lambda: self.show_panel('landscape'))
        bar.addWidget(landscape_button)
        self._fill_model_box()
        state.modelChanged.connect(self._fill_model_box)
        state.presetsChanged.connect(self._fill_model_box)

        bar.addSeparator()
        bar.addWidget(QLabel(' Color '))
        self.color_box = QComboBox()
        # in groups: of the address, of a measure, of the cycle model
        for group in (LEVEL_COLOR_KEYS, MEASURE_COLOR_KEYS, MODEL_COLOR_KEYS, SKY_COLOR_KEYS):
            if self.color_box.count():
                self.color_box.insertSeparator(self.color_box.count())
            for key in group:
                self.color_box.addItem(key)
                self.color_box.setItemData(self.color_box.count() - 1, COLOR_DESCRIPTIONS[key],
                                           Qt.ItemDataRole.ToolTipRole)
        self.color_box.setMaxVisibleItems(len(COLOR_KEYS) + 3)
        self.color_box.setCurrentText(state.color_key)
        self.color_box.currentTextChanged.connect(state.set_color_key)
        bar.addWidget(self.color_box)
        color_button = QToolButton()
        color_button.setText('Parameters…')
        color_button.setToolTip('Bases and scales of the colorings and measures')
        color_button.clicked.connect(self.show_color_dialog)
        bar.addWidget(color_button)

        bar.addSeparator()
        bar.addWidget(QLabel(' Levels '))
        self.rows_box = QSpinBox()
        self.rows_box.setRange(1, MAX_DEPTH)
        self.rows_box.setValue(state.rows)
        self.rows_box.setToolTip('Number of levels drawn below the zoomed subcycle')
        self.rows_box.valueChanged.connect(state.set_rows)
        bar.addWidget(self.rows_box)

        bar.addSeparator()
        bar.addWidget(QLabel(' Highlight '))
        self.highlight_box = QComboBox()
        for key, label in HIGHLIGHTS.items():
            self.highlight_box.addItem(label, key)
        self.highlight_box.setToolTip(
            'Around the selection, keep bright (and ring in the plots) the subcycles of its depth with the same '
            'duration,\nthe same composition (the orderings of its ages, a class inside the equal durations), or '
            'its orbit under the powers\nof the σ of the Permutations panel (its image under σ outlined in purple); '
            'or, at every depth, those matching the query;\ndim the others.')
        self.highlight_box.currentIndexChanged.connect(lambda i: state.set_highlight(self.highlight_box.itemData(i)))
        bar.addWidget(self.highlight_box)
        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText('query, e.g. trend > 0.3 and dharma < 0.5')
        self.query_edit.setClearButtonEnabled(True)
        self.query_edit.setMinimumWidth(260)
        self.query_edit.setToolTip(QUERY_HELP)
        self.query_edit.editingFinished.connect(self._apply_query)
        bar.addWidget(self.query_edit)
        self.query_info = QLabel()
        bar.addWidget(self.query_info)
        for signal in (state.viewChanged, state.selectionChanged, state.focusChanged, state.colorParametersChanged):
            signal.connect(self._show_query)

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

    def _apply_query(self) -> None:
        """Use the typed query (and its highlight); a query that cannot be read is shown in red, not applied."""
        from cycles.functions.query import QueryError
        state, text = self.state, self.query_edit.text()
        try:
            state.set_query(text)
        except QueryError as error:
            self.query_edit.setStyleSheet('color: #d62728;')
            self.query_edit.setToolTip(f"{error}\n\n{QUERY_HELP}")
            self.statusBar().showMessage(f"Query not applied: {error}", 10000)
            return
        self.query_edit.setStyleSheet('')
        self.query_edit.setToolTip(QUERY_HELP)
        if state.query and state.highlight != 'query':
            state.set_highlight('query')
        elif not state.query and state.highlight == 'query':
            state.set_highlight('none')
        self._show_query()

    def _show_query(self, *_) -> None:
        """How many subcycles match the query, at the depth of the selection or of the deepest row shown."""
        state = self.state
        if self.query_edit.text().strip() != state.query and not self.query_edit.hasFocus():
            self.query_edit.setText(state.query)            # set elsewhere (a session)
        if state.highlight != 'query' or not state.query:
            self.query_info.setText('')
            return
        depth = len(state.selection) if state.selection else max(state.visible_depths(), default=1)
        matches = state.query_matches(depth)
        text = f" {int(matches.sum()):,} of {matches.size:,} at depth {depth} "
        if state.query_problem:
            text += f"({state.query_problem}) "
        self.query_info.setText(text)

    def _sync_toolbar(self) -> None:
        """Keep the toolbar in step with changes made elsewhere (the inspector, a session...)."""
        state = self.state
        self.color_box.setCurrentText(state.color_key)
        self.highlight_box.setCurrentIndex(self.highlight_box.findData(state.highlight))
        self.rows_box.setValue(state.rows)
        self.spacing_actions[state.spacing].setChecked(True)
        names = next((label for label, names in NAME_SETS.items() if tuple(names) == tuple(state.names)), None)
        if names is not None:
            self.names_actions[names].setChecked(True)
        self.labels_actions[state.labels].setChecked(True)
        self.borders_action.setChecked(state.borders)
        self.criteria_action.setChecked(state.compare_criteria)
        self.sky_panel.follow.setChecked(state.follow)

    def _build_view_options(self, menu) -> None:
        """How the navigator draws the cycle: widths, names, labels, borders, the comparison of the criteria."""
        state = self.state
        menu.setToolTipsVisible(True)

        def choices(title: str, options: dict, setter, tip: str = '') -> dict:
            submenu = menu.addMenu(title)
            submenu.setToolTipsVisible(True)
            if tip:
                submenu.menuAction().setToolTip(tip)
            group = QActionGroup(self)
            actions = {}
            for key, (label, value) in options.items():
                action = QAction(label, self, checkable=True)
                if tip:
                    action.setToolTip(tip)
                action.toggled.connect(lambda on, value=value: setter(value) if on else None)
                group.addAction(action)
                submenu.addAction(action)
                actions[key] = action
            return actions

        self.spacing_actions = choices('&Widths', {'time': ('By &duration', 'time'), 'index': ('&Equal', 'index')},
                                       state.set_spacing, 'By duration: the horizontal axis is time. Equal: it is '
                                                          'the index.')
        self.names_actions = choices('&Names', {label: (f"&{label}", names) for label, names in NAME_SETS.items()},
                                     state.set_names)
        self.labels_actions = choices('&Labels', {key: (f"&{label}", key) for key, label in LABEL_MODES.items()},
                                      state.set_labels, 'Names (rotated in tall cells) and/or dots: 4 for Satya, '
                                                        '3 Treta, 2 Dvapara, 1 Kali')
        self.borders_action = QAction('&Borders', self, checkable=True)
        self.borders_action.setShortcut(QKeySequence('Ctrl+Shift+B'))
        self.borders_action.setToolTip('A border round every cell')
        self.borders_action.toggled.connect(state.set_borders)
        menu.addAction(self.borders_action)
        self.criteria_action = QAction('Compare the division &criteria', self, checkable=True)
        self.criteria_action.setShortcut(QKeySequence('Ctrl+Shift+C'))
        self.criteria_action.setToolTip(
            'Compare the two criteria for dividing the cycle, 4:3:2:1 of the precession arc and 4:3:2:1 of the '
            'years:\nwhere the one that is not the model\'s division puts the boundaries (dashed), with the gap '
            'shaded.\nThe tooltip of a subcycle gives the dates. Needs a cycle model.')
        self.criteria_action.toggled.connect(state.set_compare_criteria)
        menu.addAction(self.criteria_action)
        self._sync_toolbar()

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu('&File')
        for label, shortcut, slot in (('&New session', QKeySequence.StandardKey.New, lambda: self.session.new()),
                                      ('&Open session…', QKeySequence.StandardKey.Open, lambda: self.session.open()),
                                      (None, None, None),
                                      ('&Save session', QKeySequence.StandardKey.Save, lambda: self.session.save()),
                                      ('Save session &as…', QKeySequence.StandardKey.SaveAs,
                                       lambda: self.session.save_as())):
            if label is None:
                self.recent_menu = file_menu.addMenu('Open &recent')
                self.recent_menu.aboutToShow.connect(self._fill_recent_menu)
                continue
            action = QAction(label, self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(slot)
            file_menu.addAction(action)
        file_menu.addSeparator()
        save = QAction('Save &graph…', self)
        save.setShortcut(QKeySequence('Ctrl+E'))
        save.setToolTip('Save the navigator or a panel\'s graph to a file')
        save.triggered.connect(lambda: self.save_graph())
        file_menu.addAction(save)
        dossier = QAction('Subcycle &dossier…', self)
        dossier.setShortcut(QKeySequence('Ctrl+D'))
        dossier.setToolTip('Write a PDF about the selected subcycle')
        dossier.triggered.connect(self.show_dossier)
        file_menu.addAction(dossier)
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
        view_menu.addSeparator()
        self._build_view_options(view_menu)
        view_menu.addSeparator()
        bookmark = QAction('&Bookmark the selection', self)
        bookmark.setShortcut(QKeySequence('Ctrl+B'))
        bookmark.triggered.connect(self.bookmark_selection)
        view_menu.addAction(bookmark)

        panels_menu = self.menuBar().addMenu('&Panels')
        for k, dock in enumerate(self.docks.values(), 1):
            action = dock.toggleViewAction()
            if k <= 10:
                action.setShortcut(QKeySequence(f'Alt+{k % 10}'))  # the tenth: Alt+0
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
        around = panels_menu.addMenu('Arrange &around the navigator')
        around.setToolTipsVisible(True)
        for layout, (label, key, _) in AROUND.items():
            action = QAction(label, self)
            action.setShortcut(QKeySequence(key))
            action.setToolTip('Each kind of panel on its side, in tabs (closed panels stay closed)')
            action.triggered.connect(lambda _=False, l=layout: self.arrange_panels(l))
            around.addAction(action)
        panels_menu.addSeparator()
        move = panels_menu.addMenu('&Move a panel')
        move.aboutToShow.connect(lambda: self.placement.fill_move_menu(move))
        corners = panels_menu.addMenu('&Corners')
        corners.aboutToShow.connect(lambda: self.placement.fill_corners_menu(corners))
        layouts = panels_menu.addMenu('&Layouts')
        layouts.aboutToShow.connect(lambda: self.placement.fill_layouts_menu(layouts))
        self.panels_submenus = {'around': around, 'move': move, 'corners': corners, 'layouts': layouts}
        panels_menu.addSeparator()
        reset = QAction('&Reset layout', self)
        reset.triggered.connect(self.reset_layout)
        panels_menu.addAction(reset)
        panels_menu.setToolTipsVisible(True)

        help_menu = self.menuBar().addMenu('&Help')
        about = QAction('&Navigation', self)
        about.triggered.connect(self.show_help)
        help_menu.addAction(about)
        version = QAction('&About', self)
        version.triggered.connect(self.show_about)
        help_menu.addAction(version)

    def _fill_recent_menu(self) -> None:
        menu = self.recent_menu
        menu.clear()
        recent = self.session.recent() if hasattr(self, 'session') else []
        for path in recent:
            action = menu.addAction(path.name)
            action.setToolTip(str(path))
            action.triggered.connect(lambda _=False, path=path: self.session.open(path))
        if recent:
            menu.addSeparator()
            menu.addAction('Clear the list').triggered.connect(lambda: self.session.clear_recent())
        else:
            menu.addAction('No recent sessions').setEnabled(False)
        menu.setToolTipsVisible(True)

    def createPopupMenu(self):
        """Right-click on a panel's tab: where to put it; elsewhere, the panels to show or hide."""
        name = self.placement.dock_under_tab()
        if name is not None:
            return self.placement.panel_menu(name)
        return super().createPopupMenu()

    def show_dossier(self) -> None:
        from cycles.gui.dossier import DossierDialog
        if getattr(self, 'dossier_dialog', None) is None:
            self.dossier_dialog = DossierDialog(self)
        self.dossier_dialog.refresh()
        self.dossier_dialog.show()
        self.dossier_dialog.raise_()
        self.dossier_dialog.activateWindow()

    def bookmark_selection(self) -> None:
        """Bookmark the selection, showing the Notes panel to name it."""
        if not self.state.selection:
            self.statusBar().showMessage('Select a subcycle to bookmark it', 5000)
            return
        self.show_panel('notes')
        self.notes_panel.add_selection()

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

    # -- saving graphs

    def graph_sources(self) -> list[GraphSource]:
        state = self.state

        def navigator_title() -> str:
            path = ' › '.join(state.names[d] for d in state.focus) or 'The whole cycle'
            return f"{path} · {state.color_key}"

        def sky_title() -> str:
            return f"Sky at {datetime_text(state.sky_time)}" if state.sky_time is not None else 'Sky'

        def figure_source(key, label, panel, title, relayout=None) -> GraphSource:
            def save(options):
                if panel._dirty:                  # hidden panels draw only when asked
                    panel.render()
                save_figure(panel.figure, options, relayout)
            return GraphSource(key, label, lambda: tuple(panel.figure.get_size_inches()), title, save)

        navigator = self.navigator
        return [
            GraphSource('navigator', 'Subcycles (navigator)',
                        lambda: (navigator.width() / LOGICAL_DPI, navigator.height() / LOGICAL_DPI),
                        navigator_title,
                        lambda options: save_widget(lambda: Navigator(state), options),
                        formats=('png', 'jpg', 'pdf', 'svg')),
            figure_source('sky', 'Sky chart', self.sky_panel, sky_title, self.sky_panel.fit_chart),
            figure_source('measures', 'Measures', self.measures_panel,
                          lambda: self.measures_panel.graph_name()),
            figure_source('colorspace', 'Color space', self.colorspace_panel,
                          lambda: f"{self.colorspace_panel.plot.currentText()} · {state.color_key}"),
            figure_source('permutations', 'Permutations', self.permutations_panel,
                          lambda: f"{self.permutations_panel.view.currentText()} · {state.color_key}"),
            figure_source('compositions', 'Compositions', self.compositions_panel,
                          lambda: f"Compositions at depth {self.compositions_panel.plot_depth()}"),
            figure_source('skycompare', 'Sky comparison', self.skycompare_panel, self.skycompare_panel.title,
                          self.skycompare_panel.fit_charts),
            figure_source('landscape', 'Model landscape', self.landscape_panel, self.landscape_panel.title,
                          self.landscape_panel.finish),
            figure_source('events', 'Events', self.events_panel, self.events_panel.title),
        ]

    def save_graph(self, key: str | None = None) -> None:
        """Open the dialog to save a graph: ``key``, or the panel being used, or the navigator."""
        if key is None:
            focus = QApplication.focusWidget()
            key = next((name for name, dock in self.docks.items()
                        if focus is not None and dock.isAncestorOf(focus) and name in
                        ('sky', 'measures', 'colorspace', 'permutations', 'compositions', 'skycompare',
                                                       'landscape', 'events')),
                       'navigator')
        if self.export_dialog is None:
            self.export_dialog = ExportDialog(self.graph_sources(), key, self)
        else:
            self.export_dialog.select(key)
        self.export_dialog.show()
        self.export_dialog.raise_()
        self.export_dialog.activateWindow()

    def show_help(self) -> None:
        QMessageBox.information(self, 'Navigation', (
            'Click a subcycle to select it; double-click to zoom into it; right-click to zoom out.\n\n'
            'Keys in the navigator:\n'
            '  ← →  previous / next subcycle of the same depth\n'
            '  ↑  parent      ↓  first part\n'
            '  Enter  zoom into the selection\n'
            '  Backspace / Esc  zoom out\n\n'
            f'Subcycles are computed down to depth {MAX_DEPTH} ({4 ** MAX_DEPTH:,} subcycles, under a '
            'second the first time).'))


    def show_about(self) -> None:
        from cycles import __version__
        from cycles.gui.session import code_version
        code = code_version()
        commit = (f"<br>Code: commit {code['commit'][:12]}" + (' (with uncommitted changes)' if code['modified'] else '')
                  if code['commit'] else '')
        QMessageBox.about(self, 'About the Cycles explorer', (
            f"<b>Cycles explorer {__version__}</b><br>"
            "Mathematical analysis of cycles divided fractally into four ages (4:3:2:1), placed in history "
            f"through the precession of the equinoxes.{commit}<br><br>"
            "Versions follow MAJOR.MINOR.PATCH; what each one added is in CHANGELOG.md, and the documentation "
            "(docs/es) states the version it describes."))


def main(argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv if argv is None else argv)
    app.setOrganizationName('cycles')
    app.setApplicationName('cycles-gui')
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
