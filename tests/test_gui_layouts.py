"""Placing the panels around the navigator: moving one, arrangements by kind, corners, named layouts."""

import pytest

pytestmark = pytest.mark.gui


def _area(window, name):
    from cycles.gui.layouts import side_of
    return side_of(window, window.docks[name])


@pytest.mark.parametrize('side', ['left', 'right', 'top', 'bottom'])
def test_a_panel_moves_to_any_side(window, spin, side):
    from cycles.gui.layouts import move_panel
    move_panel(window, 'measures', side)
    spin()
    assert _area(window, 'measures') == side and window.docks['measures'].isVisible()
    move_panel(window, 'colorspace', side)                      # beside the one already there
    spin()
    assert _area(window, 'colorspace') == side and window.docks['measures'].isVisible()


def test_floating_and_in_a_tab(window, spin):
    from cycles.gui.layouts import move_panel
    move_panel(window, 'sky', 'float')
    spin()
    assert window.docks['sky'].isFloating() and _area(window, 'sky') == 'float'
    move_panel(window, 'sky', 'tab', 'notes')
    spin()
    assert not window.docks['sky'].isFloating()
    assert window.docks['notes'] in window.tabifiedDockWidgets(window.docks['sky'])
    # a floating target is docked first
    move_panel(window, 'date', 'float')
    move_panel(window, 'measures', 'tab', 'date')
    spin()
    assert not window.docks['date'].isFloating()
    assert window.docks['date'] in window.tabifiedDockWidgets(window.docks['measures'])


@pytest.mark.parametrize('layout', ['sides', 'around', 'left_below'])
def test_arrangements_put_each_kind_on_its_side(window, spin, layout):
    from cycles.gui.layouts import AROUND, kind_of
    window.docks['permutations'].close()                         # closed panels stay closed, but placed
    spin()
    window.arrange_panels(layout)
    spin()
    sides = AROUND[layout][2]
    for name, dock in window.docks.items():
        side = next(side for side, kinds in sides.items() if kind_of(name) in kinds)
        assert _area(window, name) == side, name
        assert dock.isHidden() == (name == 'permutations'), name
    window.docks['permutations'].toggleViewAction().trigger()   # opening it later puts it on its side
    spin()
    assert window.docks['permutations'].isVisible() and _area(window, 'permutations') == \
        next(side for side, kinds in sides.items() if 'graphs' in kinds)


def test_the_navigator_keeps_its_room(window, spin):
    from cycles.gui.layouts import move_panel
    window.resize(1400, 760)
    for name, side in (('measures', 'top'), ('colorspace', 'bottom'), ('inspector', 'left'), ('sky', 'right')):
        move_panel(window, name, side)
    spin()
    assert window.centralWidget().height() >= 240 and window.centralWidget().width() >= 360


def test_corners(window, spin, tmp_path):
    from PySide6.QtCore import Qt
    from cycles.gui import session
    from cycles.gui.layouts import set_corners
    assert window.corner(Qt.Corner.TopLeftCorner) == Qt.DockWidgetArea.LeftDockWidgetArea   # the default
    window.placement.set_corners('rows')
    assert window.corner(Qt.Corner.BottomRightCorner) == Qt.DockWidgetArea.BottomDockWidgetArea
    assert window.session.modified
    data = session.capture(window)
    assert data['layout']['corners'] == 'rows'
    set_corners(window, 'columns')
    session.apply(window, data)
    assert window.corner_mode == 'rows'
    window.reset_layout()
    assert window.corner_mode == 'columns'
    with pytest.raises(ValueError):
        set_corners(window, 'diagonal')


def test_named_layouts(window, spin):
    from cycles.gui import layouts
    window.arrange_panels('around')
    window.placement.set_corners('rows')
    spin()
    layouts.save_layout(window, '  Sky work ')
    assert 'Sky work' in layouts.saved_layouts()
    window.reset_layout()
    spin()
    assert _area(window, 'inspector') == 'right' and window.corner_mode == 'columns'
    assert layouts.apply_layout(window, 'Sky work')
    spin()
    assert _area(window, 'inspector') == 'left' and _area(window, 'measures') == 'bottom'
    assert window.corner_mode == 'rows'
    menu = window.panels_submenus['layouts']
    window.placement.fill_layouts_menu(menu)
    assert [a.text() for a in menu.actions()][0] == 'Sky work'
    stored = layouts.saved_layouts()
    stored['Old'] = dict(stored['Sky work'], version=-1)
    layouts._store(stored)
    assert not layouts.apply_layout(window, 'Old') and not layouts.apply_layout(window, 'Missing')
    layouts.delete_layout('Sky work')
    assert 'Sky work' not in layouts.saved_layouts()
    with pytest.raises(ValueError):
        layouts.save_layout(window, '   ')


def test_the_menus_of_a_panel(window, spin, monkeypatch):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QTabBar
    import cycles.gui.layouts as layouts
    menu = window.placement.panel_menu('sky')
    labels = [a.text() for a in menu.actions()]
    assert labels[:5] == ['Left of the navigator', 'Right of the navigator', 'Above the navigator',
                          'Below the navigator', 'Floating']
    menu.actions()[0].trigger()
    spin()
    assert _area(window, 'sky') == 'left'
    move = window.panels_submenus['move']
    window.placement.fill_move_menu(move)
    assert len(move.actions()) == len(window.docks)
    # right-click on a tab gives that panel's menu
    window.reset_layout()
    spin()
    bar = next(b for b in window.findChildren(QTabBar) if b.isVisible() and b.count() > 1)
    index = next(i for i in range(bar.count()) if bar.tabText(i) == 'Notes')
    centre = bar.mapToGlobal(bar.tabRect(index).center())
    monkeypatch.setattr(layouts.QCursor, 'pos', staticmethod(lambda: QPoint(centre)))
    assert window.placement.dock_under_tab() == 'notes'
    assert window.createPopupMenu().title() == 'Notes'
