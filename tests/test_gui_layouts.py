"""The panels around the navigator, with QtAds: arrangements, floating, side bars, named layouts, sessions."""

import pytest

pytestmark = pytest.mark.gui


def _rect(window, widget):
    from PySide6.QtCore import QRect
    return QRect(widget.mapTo(window, widget.rect().topLeft()), widget.size())


def _area_side(window, name: str) -> str:
    """Which side of the navigator the panel ``name`` is on: left, right, below, or above."""
    from cycles.gui.layouts import central_area
    navigator = _rect(window, central_area(window))
    area = _rect(window, window.docks[name].dockAreaWidget())
    if area.top() > navigator.bottom():
        return 'below'
    if area.bottom() < navigator.top():
        return 'above'
    return 'left' if area.right() < navigator.left() else 'right'


def test_the_navigator_is_the_central_widget(window):
    central = window.dock_manager.centralWidget()
    assert central.isCentralWidget() and central.widget().isAncestorOf(window.navigator)
    assert len(window.docks) == 11 and all(not d.isCentralWidget() for d in window.docks.values())


@pytest.mark.parametrize('layout, sides', [
    ('sides', {'inspector': 'left', 'sky': 'right', 'measures': 'right'}),
    ('around', {'notes': 'left', 'events': 'right', 'landscape': 'below'}),
    ('left_below', {'date': 'left', 'sky': 'left', 'colorspace': 'below'}),
])
def test_each_kind_of_panel_on_its_side(window, spin, layout, sides):
    from cycles.gui.layouts import KINDS
    window.docks['permutations'].toggleView(False)             # closed panels stay closed, but placed
    window.arrange_panels(layout)
    spin()
    for name, side in sides.items():
        assert _area_side(window, name) == side, (name, layout)
    # the panels of a kind share their group of tabs
    for members in KINDS.values():
        areas = {window.docks[n].dockAreaWidget() for n in members}
        assert len(areas) == 1
    assert window.docks['permutations'].isClosed()
    window.show_panel('permutations')                           # opening it later puts it with its kind
    spin()
    assert window.docks['permutations'].dockAreaWidget() is window.docks['measures'].dockAreaWidget()
    assert window.navigator.width() > 400 and window.navigator.height() > 250


def test_floating_and_side_bars(window, spin):
    from cycles.gui.layouts import float_panel, pin_to_side
    float_panel(window, 'sky', (640, 520))
    spin()
    dock = window.docks['sky']
    assert dock.isFloating() and dock.floatingDockContainer().width() == 640
    pin_to_side(window, 'notes', 'left')                        # auto-hide: slides out from the left side bar
    spin()
    assert window.docks['notes'].isAutoHide()
    window.show_panel('notes')
    spin()
    assert window.docks['notes'].widget().isVisible()
    window.reset_layout()                                       # everything back in tabs, docked
    spin()
    assert not window.docks['notes'].isAutoHide() and not window.docks['sky'].isFloating()
    assert all(not d.isClosed() for d in window.docks.values())


def test_named_layouts(window, spin):
    from cycles.gui.layouts import apply_layout, delete_layout, fill_layouts_menu, load_layouts, saved_layouts
    from cycles.gui.layouts import save_layout
    window.arrange_panels('around')
    spin()
    save_layout(window, 'Around')
    window.arrange_panels('tabs')
    spin()
    assert 'Around' in saved_layouts(window)
    assert apply_layout(window, 'Around')
    spin()
    assert _area_side(window, 'landscape') == 'below' and _area_side(window, 'inspector') == 'left'
    assert not apply_layout(window, 'No such layout')
    # kept in the settings, for later runs
    window.dock_manager.removePerspective('Around')
    load_layouts(window)
    assert 'Around' in saved_layouts(window)
    menu = window.panels_submenus['layouts']
    fill_layouts_menu(window, menu)
    assert [a.text() for a in menu.actions()][0] == 'Around'
    delete_layout(window, 'Around')
    assert 'Around' not in saved_layouts(window)


def test_a_session_keeps_the_arrangement(window, spin):
    from cycles.gui import session
    window.arrange_panels('around')
    window.docks['events'].toggleView(False)
    spin()
    data = session.capture(window)
    assert data['layout']['docks']
    window.reset_layout()
    spin()
    assert session.apply(window, data) == []
    spin()
    assert _area_side(window, 'landscape') == 'below' and window.docks['events'].isClosed()


def test_moving_a_panel_marks_the_session_modified(window, spin):
    window.session.modified = False
    window.arrange_panels('below')
    spin()
    assert window.session.modified


def test_the_panels_menu(window):
    from PySide6.QtWidgets import QMenu
    menu = next(m for m in window.findChildren(QMenu) if m.title() == '&Panels')
    texts = [a.text() for a in menu.actions()]
    assert texts[:11] == [d.windowTitle() for d in window.docks.values()]   # show or hide each panel
    assert 'Arrange &around the navigator' in texts and '&Layouts' in texts and '&Reset layout' in texts
    assert not any('Move' in t or 'Corners' in t for t in texts)          # dragging does that now


def test_floating_panels_attach_again(window, spin):
    from cycles.gui.layouts import float_panel
    window.arrange_panels('around')
    spin()
    float_panel(window, 'sky', (600, 500))
    float_panel(window, 'measures', (600, 500))
    spin()
    sky = window.docks['sky']
    assert sky.isFloating() and sky._attach_action.isVisible()          # the button, only while it floats
    assert not window.docks['events']._attach_action.isVisible()
    sky._attach_action.trigger()                                        # back with the panels of its kind
    spin()
    assert not sky.isFloating() and not sky._attach_action.isVisible() and not sky.isClosed()
    assert sky.dockAreaWidget() is window.docks['events'].dockAreaWidget()
    window.attach_floating()                                            # Panels → Attach floating panels
    spin()
    assert not window.docks['measures'].isFloating()
    assert window.docks['measures'].dockAreaWidget() is window.docks['landscape'].dockAreaWidget()
    assert not window.dock_manager.floatingWidgets() or not any(c.isVisible()
                                                                    for c in window.dock_manager.floatingWidgets())
    window.attach_floating()
    assert 'No floating panels' in window.statusBar().currentMessage()


def test_a_floating_group_attaches_again(window, spin):
    """The undock button floats a whole group: QtAds' isFloating is then False for its panels."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QToolButton
    window.arrange_panels('around')
    spin()
    window.docks['sky'].dockAreaWidget().setFloating()           # Sky, Sky comparison, Events, in one window
    spin()
    container = window.dock_manager.floatingWidgets()[0]
    button = next(b for b in container.findChildren(QToolButton)
                  if b.defaultAction() is window.docks['sky']._attach_action)
    assert button.isVisible() and button.isEnabled()
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)          # the whole window comes back
    spin()
    names = ('sky', 'skycompare', 'events')
    assert not any(window.docks[n].isInFloatingContainer() for n in names)
    assert len({window.docks[n].dockAreaWidget() for n in names}) == 1
    assert not any(window.docks[n]._attach_action.isVisible() for n in names)
    window.docks['measures'].dockAreaWidget().setFloating()      # and the menu, for a floating group
    spin()
    window.attach_floating()
    spin()
    assert not any(window.docks[n].isInFloatingContainer() for n in ('measures', 'colorspace', 'landscape'))
    assert window.statusBar().currentMessage() == 'Attached 5 floating panels'


def test_inactive_tab_titles_are_readable_in_a_dark_palette(window):
    from PySide6.QtGui import QColor, QPalette
    from cycles.gui.layouts import tab_style
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor('#202326'))
    palette.setColor(QPalette.ColorRole.WindowText, QColor('#fcfcfc'))
    style = tab_style(palette)
    inactive = QColor(style.split('ads--CDockWidgetTab QLabel { color: ')[1].split(';')[0])
    assert inactive.lightness() > 170                     # light on the dark background, dimmer than the active
    assert inactive.lightness() < QColor('#fcfcfc').lightness()
    applied = window.dock_manager.styleSheet()                # the explorer's own palette, appended to QtAds' sheet
    assert applied.rstrip().endswith(tab_style(window.palette()).rstrip())


def test_the_attach_button_shows_only_on_floating_windows(window, spin):
    from PySide6.QtWidgets import QToolButton
    from cycles.gui.layouts import attach_icon

    def attach_buttons(holder):
        actions = {id(d._attach_action) for d in window.docks.values()}
        return [b for b in holder.findChildren(QToolButton)
                if b.defaultAction() is not None and id(b.defaultAction()) in actions and b.isVisible()]

    window.arrange_panels('around')
    spin()
    window.show_panel('date')                                   # another tab of a docked group to the front
    window.show_panel('events')
    spin()
    assert attach_buttons(window.dock_manager) == []            # docked: no Attach button, not even greyed out
    window.docks['sky'].dockAreaWidget().setFloating()
    spin()
    window.show_panel('skycompare')                             # another tab of the floating group
    spin()
    container = window.dock_manager.floatingWidgets()[0]
    shown = attach_buttons(container)
    assert len(shown) == 1 and shown[0].isEnabled() and not shown[0].icon().isNull()
    assert window.docks['sky']._attach_action.icon().cacheKey() is not None and not attach_icon().isNull()
