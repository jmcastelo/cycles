"""
Where the panels go around the navigator, with the Qt Advanced Docking System (QtAds): the dock manager, the
ready-made arrangements (as tabs, side by side, stacked, in a grid, below the navigator, or each kind of panel on
its side), and named layouts (QtAds perspectives).

The navigator is the central widget of the dock manager. The panels can be dragged anywhere, with drop targets
showing where they will go: beside or around another panel, into its tabs, or floating; and pinned to a side bar
of the window (auto-hide), from where they slide out when their tab is pointed at.
"""

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QInputDialog, QMenu, QWidget

import PySide6QtAds as ads

# Kinds of panels, for the arrangements around the navigator
KINDS = {
    'text': ('inspector', 'date', 'notes'),
    'sky': ('sky', 'skycompare', 'events'),
    'graphs': ('measures', 'colorspace', 'permutations', 'compositions', 'landscape'),
}
SIDES = {'left': ads.LeftDockWidgetArea, 'right': ads.RightDockWidgetArea, 'bottom': ads.BottomDockWidgetArea}
# Arrangements: side -> kinds of panels there (a group of tabs per side)
AROUND = {
    'sides': ('Left and right (information | sky and graphs)', 'Ctrl+Alt+L',
              {'left': ('text',), 'right': ('sky', 'graphs')}),
    'around': ('Around the navigator (information | sky | graphs below)', 'Ctrl+Alt+A',
               {'left': ('text',), 'right': ('sky',), 'bottom': ('graphs',)}),
    'left_below': ('Left and below (information and sky | graphs)', 'Ctrl+Alt+D',
                   {'left': ('text', 'sky'), 'bottom': ('graphs',)}),
}
ARRANGEMENTS = ('tabs', 'side', 'stacked', 'grid', 'below') + tuple(AROUND)
PERSPECTIVES_GROUP = 'panels/perspectives'
PANEL_SHARE = 0.34          # of the window's width for the panels beside the navigator (as tabs)


def configure() -> None:
    """The QtAds options, set before the dock manager is made."""
    M = ads.CDockManager
    for flag in (M.eConfigFlag.OpaqueSplitterResize, M.eConfigFlag.FocusHighlighting,
                 M.eConfigFlag.DockAreaHasTabsMenuButton, M.eConfigFlag.DockAreaHasUndockButton,
                 M.eConfigFlag.AllTabsHaveCloseButton, M.eConfigFlag.MiddleMouseButtonClosesTab):
        M.setConfigFlag(flag, True)
    # side bars: each group of panels has a pin button; a pinned panel slides out when its tab is pointed at
    M.setAutoHideConfigFlags(M.eAutoHideFlag.DefaultAutoHideConfig | M.eAutoHideFlag.AutoHideShowOnMouseOver)


def _mix(a, b, share: float) -> str:
    """The color ``share`` of the way from ``b`` to ``a`` (QColors), as #rrggbb."""
    from PySide6.QtGui import QColor
    return QColor(*(round(share * x + (1 - share) * y) for x, y in
                    zip((a.red(), a.green(), a.blue()), (b.red(), b.green(), b.blue())))).name()


def tab_style(palette) -> str:
    """
    The colors of the tab titles, from the application's ``palette``: QtAds' own style sheet leaves the inactive
    ones nearly invisible in dark themes. Inactive: the window text blended a quarter towards the background;
    active: the window text; focused: the highlighted text, as QtAds has it.
    """
    from PySide6.QtGui import QPalette
    text, window = palette.color(QPalette.ColorRole.WindowText), palette.color(QPalette.ColorRole.Window)
    inactive = _mix(text, window, 0.75)
    return f"""
ads--CDockWidgetTab QLabel {{ color: {inactive}; }}
ads--CDockWidgetTab[activeTab="true"] QLabel {{ color: {text.name()}; }}
ads--CDockWidgetTab[focused="true"] QLabel {{ color: palette(highlighted-text); }}
ads--CAutoHideTab {{ color: {inactive}; }}
ads--CAutoHideTab:hover {{ color: palette(highlight); }}
"""


def apply_tab_style(manager) -> None:
    """Add ``tab_style`` (for the current palette) to QtAds' style sheet."""
    from PySide6.QtWidgets import QApplication
    if not hasattr(manager, '_base_style'):
        manager._base_style = manager.styleSheet()
    manager.setStyleSheet(manager._base_style + tab_style(QApplication.palette()))


class _PaletteWatcher(QWidget):
    """Follows the application's palette (a change between light and dark) to recolor the tab titles."""

    def __init__(self, manager):
        super().__init__(manager)
        self.manager = manager
        self.hide()

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.PaletteChange:
            apply_tab_style(self.manager)
            for dock in self.manager.dockWidgets():
                action = getattr(dock, '_attach_action', None)
                if action is not None:
                    action.setIcon(attach_icon())
        super().changeEvent(event)


def make_manager(window, central: QWidget):
    """The dock manager of ``window``, with ``central`` (the navigator) as its central widget."""
    configure()
    manager = ads.CDockManager(window)
    apply_tab_style(manager)
    manager._palette_watcher = _PaletteWatcher(manager)
    dock = ads.CDockWidget(manager, 'Navigator')
    dock.setObjectName('navigator')
    dock.setWidget(central)
    dock.setFeature(ads.CDockWidget.DockWidgetFeature.NoTab, True)
    manager.setCentralWidget(dock)
    return manager


def central_area(window):
    """The dock area of the navigator (looked up each time: restoring a layout makes the areas anew)."""
    return window.dock_manager.centralWidget().dockAreaWidget()


def make_dock(manager, title: str, name: str, widget: QWidget):
    dock = ads.CDockWidget(manager, title)
    dock.setObjectName(name)
    # the text panels scroll when their group is short (a form is not squeezed); the others resize with their
    # dock, so that their plots refit
    mode = ads.CDockWidget.eInsertMode
    dock.setWidget(widget, mode.ForceScrollArea if name in KINDS['text'] else mode.ForceNoScrollArea)
    return dock


def kind_of(name: str) -> str:
    return next((kind for kind, names in KINDS.items() if name in names), 'graphs')


def _clear(window) -> None:
    for dock in window.docks.values():
        if dock.isAutoHide():
            dock.setAutoHide(False)
        window.dock_manager.removeDockWidget(dock)


def _give_navigator(window, width: float, height: float = 0.62) -> None:
    """
    Give the navigator ``width`` of the window's width and ``height`` of its height, in each splitter that holds
    it (up from its area); the panels beside it share the rest evenly.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QSplitter
    widget = central_area(window)
    splitter = widget.parentWidget()
    while isinstance(splitter, QSplitter):
        horizontal = splitter.orientation() == Qt.Orientation.Horizontal
        total = sum(splitter.sizes()) or (window.width() if horizontal else window.height())
        index, count = splitter.indexOf(widget), splitter.count()
        if count > 1:
            own = int(total * (width if horizontal else height))
            rest = (total - own) // (count - 1)
            splitter.setSizes([own if k == index else rest for k in range(count)])
        widget, splitter = splitter, splitter.parentWidget()


def arrange(window, layout: str) -> None:
    """
    Arrange the open panels (all of them if none is open): ``'tabs'``, ``'side'`` (side by side), ``'stacked'``,
    ``'grid'`` (2 × 2 and on), ``'below'`` (side by side under the navigator), or each kind of panel on its side of
    the navigator (a key of ``AROUND``). The closed panels are placed too, in the same arrangement, and stay
    closed: opening one later puts it where the arrangement continues.
    """
    if layout not in ARRANGEMENTS:
        raise ValueError(f"unknown arrangement {layout!r}")
    manager, docks = window.dock_manager, window.docks
    open_names = [name for name, dock in docks.items() if not dock.isClosed()] or list(docks)
    _clear(window)
    if layout in AROUND:
        for side, kinds in AROUND[layout][2].items():
            members = sorted((n for n in docks if kind_of(n) in kinds), key=lambda n: n not in open_names)
            if not members:
                continue
            area = manager.addDockWidget(SIDES[side], docks[members[0]])
            for name in members[1:]:
                manager.addDockWidgetTabToArea(docks[name], area)
    else:
        order = open_names + [n for n in docks if n not in open_names]
        first = docks[order[0]]
        side = ads.BottomDockWidgetArea if layout == 'below' else ads.RightDockWidgetArea
        areas = [manager.addDockWidget(side, first)]
        for k, name in enumerate(order[1:], 1):
            dock = docks[name]
            if layout == 'tabs':
                manager.addDockWidgetTabToArea(dock, areas[0])
            elif layout in ('side', 'below'):
                areas.append(manager.addDockWidget(ads.RightDockWidgetArea, dock, areas[-1]))
            elif layout == 'stacked':
                areas.append(manager.addDockWidget(ads.BottomDockWidgetArea, dock, areas[-1]))
            elif layout == 'grid':
                # 0 | 1 on top, 2 under 0, 3 under 1, and so on down the two columns
                where = ads.RightDockWidgetArea if k == 1 else ads.BottomDockWidgetArea
                areas.append(manager.addDockWidget(where, dock, areas[0] if k == 1 else areas[k - 2]))
    if layout in AROUND:
        _give_navigator(window, 0.42, 0.6)
    elif layout == 'below':
        _give_navigator(window, 1.0, 0.55)
    else:
        _give_navigator(window, 0.4 if layout in ('side', 'grid') else 1 - PANEL_SHARE)
    for name, dock in docks.items():
        dock.toggleView(name in open_names)
    shown = [docks[n] for n in open_names]
    for dock in reversed(shown):              # the first open panel of each group of tabs in front
        dock.setAsCurrentTab()


def show_panel(window, name: str) -> None:
    """Open the panel ``name`` (it goes back where it was) and bring it to the front."""
    dock = window.docks[name]
    dock.toggleView(True)
    if dock.isAutoHide():
        dock.autoHideDockContainer().collapseView(False)
    else:
        dock.setAsCurrentTab()
    dock.raise_()


def float_panel(window, name: str, size: tuple[int, int] | None = None) -> None:
    """Open the panel ``name`` in a window of its own (floating), of ``size`` (width, height) if given."""
    dock = window.docks[name]
    dock.toggleView(True)
    if not dock.isFloating():
        dock.setFloating()
    container = dock.floatingDockContainer()
    if container is not None and size is not None:
        container.resize(*size)


def is_floating(dock) -> bool:
    """Whether a panel is in a floating window, alone or with others (QtAds' isFloating is only for alone)."""
    return dock.isFloating() or dock.isInFloatingContainer()


def attach_panel(window, name: str) -> None:
    """
    Put a floating panel back in the window: in the tabs of a docked panel of its kind (``KINDS``), or else
    beside the navigator, on the right. It stays open and in front.
    """
    dock = window.docks[name]
    if not is_floating(dock):
        return
    manager = window.dock_manager
    partner = next((window.docks[n] for n in KINDS[kind_of(name)]
                    if n != name and not is_floating(window.docks[n]) and not window.docks[n].isAutoHide()
                    and window.docks[n].dockAreaWidget() is not None and not window.docks[n].isClosed()), None)
    if partner is not None:
        manager.addDockWidgetTabToArea(dock, partner.dockAreaWidget())
    else:
        manager.addDockWidget(ads.RightDockWidgetArea, dock)
    dock.toggleView(True)
    dock.setAsCurrentTab()
    update_attach_buttons(window)


def attach_window(window, name: str) -> None:
    """Put back every panel of the floating window that holds the panel ``name`` (each with its kind)."""
    container = window.docks[name].dockContainer()
    together = [n for n, d in window.docks.items() if is_floating(d) and d.dockContainer() is container]
    for n in together:
        attach_panel(window, n)
    if name in together:
        window.docks[name].setAsCurrentTab()


def attach_all(window) -> int:
    """Attach every floating panel (``attach_panel``); how many there were."""
    floating = [name for name, dock in window.docks.items() if is_floating(dock)]
    for name in floating:
        attach_panel(window, name)
    return len(floating)


def palette_is_dark(palette=None) -> bool:
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QApplication
    palette = palette or QApplication.palette()
    return palette.color(QPalette.ColorRole.Window).lightness() < 128


def attach_icon():
    """The icon of QtAds' detach (undock) button, for Attach too: its dark variant on a dark palette."""
    from PySide6.QtGui import QIcon
    return QIcon(f":/ads/images/detach-button{'_dark' if palette_is_dark() else ''}.svg")


def add_attach_buttons(window) -> None:
    """An Attach button in the title bar of each panel, shown while it floats."""
    from PySide6.QtGui import QAction
    for name, dock in window.docks.items():
        action = QAction(attach_icon(), 'Attach', dock)
        action.setToolTip('Attach: put the panels of this floating window back in the main window, each with its '
                          'kind')
        action.triggered.connect(lambda _=False, name=name: attach_window(window, name))
        action.setVisible(False)
        dock.setTitleBarActions([action])
        dock._attach_action = action
        dock.topLevelChanged.connect(lambda *_: _update_later(window))
        dock.visibilityChanged.connect(lambda *_: _update_later(window))     # a tab to the front shows the buttons
    manager = window.dock_manager
    for signal in (manager.floatingWidgetCreated, manager.dockAreasAdded, manager.dockAreasRemoved,
                   manager.stateRestored, manager.perspectiveOpened):
        signal.connect(lambda *_: _update_later(window))


def _update_later(window) -> None:
    """
    Update the Attach buttons once QtAds has finished moving the panels: it says that a floating window was made
    before the panels are in it (and a hidden action is also disabled, so its button would stay greyed out).
    """
    from PySide6.QtCore import QTimer
    QTimer.singleShot(0, lambda: update_attach_buttons(window))


def update_attach_buttons(window) -> None:
    """Show the Attach button of the floating panels only (QtAds does not always say when a panel docks)."""
    from PySide6.QtWidgets import QToolButton
    actions = {}
    for dock in window.docks.values():
        action = getattr(dock, '_attach_action', None)
        if action is not None:
            action.setVisible(is_floating(dock))
            actions[id(action)] = action
    # QtAds shows a hidden title bar action as a disabled button: hide the buttons themselves while docked
    holders = [window.dock_manager] + list(window.dock_manager.floatingWidgets())
    for holder in holders:
        for button in holder.findChildren(QToolButton):
            action = button.defaultAction()
            if action is not None and id(action) in actions:
                button.setVisible(action.isVisible())


def pin_to_side(window, name: str, side: str = 'left') -> None:
    """Put the panel ``name`` in a side bar of the window (auto-hide): it slides out when its tab is pointed at."""
    bars = {'left': ads.SideBarLeft, 'right': ads.SideBarRight, 'bottom': ads.SideBarBottom, 'top': ads.SideBarTop}
    dock = window.docks[name]
    dock.toggleView(True)
    window.dock_manager.addAutoHideDockWidget(bars[side], dock)


# -- named layouts: QtAds perspectives, kept in the settings

def _settings_group():
    settings = QSettings()
    settings.beginGroup(PERSPECTIVES_GROUP)
    return settings


def load_layouts(window) -> None:
    settings = _settings_group()
    window.dock_manager.loadPerspectives(settings)
    settings.endGroup()


def _store_layouts(window) -> None:
    settings = _settings_group()
    settings.remove('')
    window.dock_manager.savePerspectives(settings)
    settings.endGroup()


def saved_layouts(window) -> list[str]:
    return sorted(window.dock_manager.perspectiveNames(), key=str.lower)


def save_layout(window, name: str) -> None:
    name = name.strip()
    if not name:
        raise ValueError('a layout needs a name')
    window.dock_manager.addPerspective(name)
    _store_layouts(window)


def apply_layout(window, name: str) -> bool:
    """Arrange the panels as the layout ``name``; False if there is none of that name."""
    if name not in window.dock_manager.perspectiveNames():
        return False
    window.dock_manager.openPerspective(name)
    return True


def delete_layout(window, name: str) -> None:
    window.dock_manager.removePerspective(name)
    _store_layouts(window)


def fill_layouts_menu(window, menu: QMenu) -> None:
    menu.clear()
    names = saved_layouts(window)
    for name in names:
        menu.addAction(name).triggered.connect(lambda _=False, name=name: _apply(window, name))
    if names:
        menu.addSeparator()
    menu.addAction('Save layout as…').triggered.connect(lambda: _save_as(window))
    if names:
        delete = menu.addMenu('Delete')
        for name in names:
            delete.addAction(name).triggered.connect(lambda _=False, name=name: delete_layout(window, name))


def _apply(window, name: str) -> None:
    if apply_layout(window, name):
        window.statusBar().showMessage(f"Layout “{name}”", 4000)
        window.session.mark_modified()


def _save_as(window) -> None:
    name, ok = QInputDialog.getText(window, 'Save layout', 'Name of the layout:')
    if ok and name.strip():
        save_layout(window, name)
        window.statusBar().showMessage(f"Saved the layout “{name.strip()}”", 4000)
