"""The dock panels: arrangements, and opening panels that were closed when they were arranged."""

import pytest

pytestmark = pytest.mark.gui

LAYOUTS = ['tabs', 'side', 'stacked', 'grid', 'below']


def test_all_panels_exist(window):
    assert list(window.docks) == ['inspector', 'date', 'sky', 'measures', 'colorspace', 'permutations',
                                  'compositions', 'skycompare', 'landscape', 'notes', 'events']


@pytest.mark.parametrize('layout', LAYOUTS)
def test_closed_panels_stay_in_the_layout(window, spin, layout):
    """Arranging removes the docks and adds them back: the closed ones too, so that opening them works."""
    from PySide6.QtCore import Qt
    window.reset_layout()
    for name in ('date', 'sky', 'measures', 'colorspace'):
        window.docks[name].toggleViewAction().trigger()
    window.docks['measures'].toggleViewAction().trigger()
    window.arrange_panels(layout)
    spin()
    for dock in window.docks.values():
        assert window.dockWidgetArea(dock) != Qt.DockWidgetArea.NoDockWidgetArea, dock.objectName()
    for name in ('sky', 'colorspace'):
        window.docks[name].toggleViewAction().trigger()
    spin()
    for name in ('sky', 'colorspace'):
        dock = window.docks[name]
        assert dock.isVisible()
        assert window.dockWidgetArea(dock) != Qt.DockWidgetArea.NoDockWidgetArea
        if layout == 'tabs':
            dock.raise_()
            spin()
        geometry = dock.geometry()
        assert geometry.x() >= 0 and geometry.y() >= 0 and geometry.width() >= 50, (name, geometry)
