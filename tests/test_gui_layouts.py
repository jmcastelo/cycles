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
