"""
Where the panels go around the navigator: moving one panel to a side (or
floating, or into a tab with another), arrangements that place the kinds of
panels on different sides, which docks own the corners of the window, and
named layouts to switch between.

The window's docks can be on any of its four sides; these are the shortcuts
to put them there without dragging (dragging still works: a panel, or a whole
group of tabs, dropped on an edge of the window or on another panel).
"""

import base64
import json

from PySide6.QtCore import QByteArray, QObject, QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QCursor
from PySide6.QtWidgets import QDockWidget, QInputDialog, QMenu, QTabBar

AREAS = {
    'left': (Qt.DockWidgetArea.LeftDockWidgetArea, 'Left of the navigator'),
    'right': (Qt.DockWidgetArea.RightDockWidgetArea, 'Right of the navigator'),
    'top': (Qt.DockWidgetArea.TopDockWidgetArea, 'Above the navigator'),
    'bottom': (Qt.DockWidgetArea.BottomDockWidgetArea, 'Below the navigator'),
}
# Kinds of panels, for the arrangements around the navigator
KINDS = {
    'text': ('inspector', 'date', 'notes'),
    'sky': ('sky', 'skycompare'),
    'graphs': ('measures', 'colorspace', 'permutations', 'compositions', 'landscape'),
}
# Arrangements: side -> kinds of panels there (a group of tabs per side)
AROUND = {
    'sides': ('Left and right (information | sky and graphs)', 'Ctrl+Alt+L',
              {'left': ('text',), 'right': ('sky', 'graphs')}),
    'around': ('Around the navigator (information | sky | graphs below)', 'Ctrl+Alt+A',
               {'left': ('text',), 'right': ('sky',), 'bottom': ('graphs',)}),
    'left_below': ('Left and below (information and sky | graphs)', 'Ctrl+Alt+D',
                   {'left': ('text', 'sky'), 'bottom': ('graphs',)}),
}
CORNERS = {
    'columns': 'Side columns full height',
    'rows': 'Top and bottom rows full width',
}
LAYOUTS_KEY = 'panels/layouts'
CORNERS_KEY = 'panels/corners'


def kind_of(name: str) -> str:
    return next((kind for kind, names in KINDS.items() if name in names), 'graphs')


def set_corners(window, mode: str) -> None:
    """Which docks take the corners of the window: the side columns, or the top and bottom rows."""
    if mode not in CORNERS:
        raise ValueError(f"corners must be one of {list(CORNERS)}")
    C, A = Qt.Corner, Qt.DockWidgetArea
    if mode == 'columns':
        corners = ((C.TopLeftCorner, A.LeftDockWidgetArea), (C.BottomLeftCorner, A.LeftDockWidgetArea),
                   (C.TopRightCorner, A.RightDockWidgetArea), (C.BottomRightCorner, A.RightDockWidgetArea))
    else:
        corners = ((C.TopLeftCorner, A.TopDockWidgetArea), (C.TopRightCorner, A.TopDockWidgetArea),
                   (C.BottomLeftCorner, A.BottomDockWidgetArea), (C.BottomRightCorner, A.BottomDockWidgetArea))
    for corner, area in corners:
        window.setCorner(corner, area)
    window.corner_mode = mode


def side_of(window, dock: QDockWidget) -> str | None:
    """'left', 'right', 'top', 'bottom', 'float', or None (not placed)."""
    if dock.isFloating():
        return 'float'
    area = window.dockWidgetArea(dock)
    return next((key for key, (value, _) in AREAS.items() if value == area), None)


def move_panel(window, name: str, where: str, other: str | None = None) -> None:
    """
    Put the panel ``name`` on a side of the navigator (``'left'``, ``'right'``,
    ``'top'``, ``'bottom'``, beside the panels already there), floating
    (``'float'``), or in a tab with the panel ``other`` (``'tab'``); it is
    opened and brought to the front.
    """
    dock = window.docks[name]
    if where == 'tab':
        target = window.docks[other]
        if target is dock:
            return
        if target.isFloating() or side_of(window, target) is None:
            move_panel(window, other, 'right')
        target.show()
        dock.setFloating(False)
        window.tabifyDockWidget(target, dock)
    elif where == 'float':
        dock.show()
        dock.setFloating(True)
        geometry = window.geometry()
        width, height = max(dock.width(), 420), max(dock.height(), 360)
        dock.resize(width, height)
        dock.move(geometry.center().x() - width // 2, geometry.center().y() - height // 2)
    elif where in AREAS:
        area = AREAS[where][0]
        dock.setFloating(False)
        window.removeDockWidget(dock)
        orientation = (Qt.Orientation.Horizontal if where in ('top', 'bottom') else Qt.Orientation.Vertical)
        window.addDockWidget(area, dock, orientation)
    else:
        raise ValueError(f"unknown place {where!r}")
    dock.show()
    dock.raise_()


def arrange_around(window, layout: str) -> None:
    """
    Put each kind of panel on its side of the navigator (``AROUND``), a group
    of tabs per side; closed panels are placed too, and stay closed.
    """
    sides = AROUND[layout][2]
    docks = window.docks
    open_names = [name for name, dock in docks.items() if dock.isVisible()] or list(docks)
    groups = {}
    for side, kinds in sides.items():
        members = [name for name in docks if kind_of(name) in kinds]
        # the open ones first, so that a group starts with a panel that is shown
        groups[side] = sorted(members, key=lambda name: name not in open_names)
    for dock in docks.values():
        dock.setFloating(False)
        window.removeDockWidget(dock)
    for side, members in groups.items():
        if not members:
            continue
        area = AREAS[side][0]
        first = docks[members[0]]
        window.addDockWidget(area, first)
        first.show()
        for name in members[1:]:
            window.tabifyDockWidget(first, docks[name])
        for name in members:
            docks[name].setVisible(name in open_names)
        shown = [name for name in members if name in open_names]
        if shown:
            docks[shown[0]].raise_()
    width, height = window.width(), window.height()
    sized = {side: [docks[n] for n in members if n in open_names] for side, members in groups.items()}
    for side, size in (('left', int(width * 0.24)), ('right', int(width * 0.34))):
        if sized.get(side):
            window.resizeDocks([sized[side][0]], [size], Qt.Orientation.Horizontal)
    if sized.get('bottom'):
        window.resizeDocks([sized['bottom'][0]], [int(height * 0.4)], Qt.Orientation.Vertical)


# -- named layouts

def _encode(data: QByteArray) -> str:
    return base64.b64encode(bytes(data)).decode('ascii')


def saved_layouts() -> dict:
    try:
        layouts = json.loads(QSettings().value(LAYOUTS_KEY, '{}') or '{}')
    except (TypeError, ValueError):
        return {}
    return layouts if isinstance(layouts, dict) else {}


def _store(layouts: dict) -> None:
    QSettings().setValue(LAYOUTS_KEY, json.dumps(layouts))


def save_layout(window, name: str) -> None:
    from cycles.gui.app import LAYOUT_VERSION
    name = name.strip()
    if not name:
        raise ValueError('a layout needs a name')
    layouts = saved_layouts()
    layouts[name] = {'version': LAYOUT_VERSION, 'state': _encode(window.saveState(LAYOUT_VERSION)),
                     'corners': getattr(window, 'corner_mode', 'columns')}
    _store(layouts)


def apply_layout(window, name: str) -> bool:
    """Arrange the panels as the layout ``name``; False if it is missing or made for other panels."""
    from cycles.gui.app import LAYOUT_VERSION
    layout = saved_layouts().get(name)
    if layout is None or layout.get('version') != LAYOUT_VERSION:
        return False
    set_corners(window, layout.get('corners', 'columns'))
    return window.restoreState(QByteArray(base64.b64decode(layout['state'])), LAYOUT_VERSION)


def delete_layout(name: str) -> None:
    layouts = saved_layouts()
    layouts.pop(name, None)
    _store(layouts)


# -- menus

class PanelPlacement(QObject):
    """The menus that place the panels: Panels → Move, Corners, Layouts, and the context menu of a panel."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        for name, dock in window.docks.items():
            dock.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            dock.customContextMenuRequested.connect(lambda pos, name=name: self._title_menu(name, pos))

    def panel_menu(self, name: str, parent=None) -> QMenu:
        """Move ``name``: to a side, floating, or into a tab with another panel."""
        window = self.window
        menu = QMenu(window.docks[name].windowTitle(), parent or window)
        current = side_of(window, window.docks[name])
        for key, (_, label) in AREAS.items():
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(current == key and window.docks[name].isVisible())
            action.triggered.connect(lambda _=False, key=key: move_panel(window, name, key))
        action = menu.addAction('Floating')
        action.setCheckable(True)
        action.setChecked(current == 'float')
        action.triggered.connect(lambda: move_panel(window, name, 'float'))
        tabs = menu.addMenu('In a tab with')
        for other, dock in window.docks.items():
            if other != name:
                tabs.addAction(dock.windowTitle()).triggered.connect(
                    lambda _=False, other=other: move_panel(window, name, 'tab', other))
        return menu

    def _title_menu(self, name: str, pos) -> None:
        dock = self.window.docks[name]
        widget = dock.widget()
        if widget is not None and widget.geometry().contains(pos):
            return                                   # inside the panel, not on its title bar
        self.panel_menu(name).exec(dock.mapToGlobal(pos))

    def dock_under_tab(self):
        """The panel whose tab is under the pointer, if any (tabs belong to the main window)."""
        window = self.window
        titles = {dock.windowTitle().replace('&', ''): name for name, dock in window.docks.items()}
        for bar in window.findChildren(QTabBar):
            if not bar.isVisible():
                continue
            index = bar.tabAt(bar.mapFromGlobal(QCursor.pos()))
            if index >= 0:
                return titles.get(bar.tabText(index).replace('&', ''))
        return None

    def fill_move_menu(self, menu: QMenu) -> None:
        menu.clear()
        for name in self.window.docks:
            menu.addMenu(self.panel_menu(name, menu))

    def fill_corners_menu(self, menu: QMenu) -> None:
        menu.clear()
        group = QActionGroup(menu)
        for key, label in CORNERS.items():
            action = QAction(label, menu)
            action.setCheckable(True)
            action.setChecked(getattr(self.window, 'corner_mode', 'columns') == key)
            action.triggered.connect(lambda _=False, key=key: self.set_corners(key))
            group.addAction(action)
            menu.addAction(action)

    def set_corners(self, mode: str) -> None:
        set_corners(self.window, mode)
        QSettings().setValue(CORNERS_KEY, mode)
        self.window.session.mark_modified()

    def fill_layouts_menu(self, menu: QMenu) -> None:
        menu.clear()
        layouts = saved_layouts()
        for name in sorted(layouts, key=str.lower):
            menu.addAction(name).triggered.connect(lambda _=False, name=name: self.apply(name))
        if layouts:
            menu.addSeparator()
        menu.addAction('Save layout as…').triggered.connect(self.save_as)
        if layouts:
            delete = menu.addMenu('Delete')
            for name in sorted(layouts, key=str.lower):
                delete.addAction(name).triggered.connect(lambda _=False, name=name: delete_layout(name))

    def apply(self, name: str) -> None:
        if apply_layout(self.window, name):
            self.window.statusBar().showMessage(f"Layout “{name}”", 4000)
            self.window.session.mark_modified()
        else:
            self.window.statusBar().showMessage(f"The layout “{name}” was made for other panels", 8000)

    def save_as(self) -> None:
        name, ok = QInputDialog.getText(self.window, 'Save layout', 'Name of the layout:')
        if ok and name.strip():
            save_layout(self.window, name)
            self.window.statusBar().showMessage(f"Saved the layout “{name.strip()}”", 4000)
