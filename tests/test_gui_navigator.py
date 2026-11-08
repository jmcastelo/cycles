"""The navigator: the tag band of the markers, dragging the tags, and Shift+click."""

import pytest

pytestmark = pytest.mark.gui


@pytest.fixture
def navigator(window, spin):
    window.state.set_focus((3,))
    window.state.set_date(2026.8)
    spin()
    window.navigator.repaint()
    spin()
    return window.navigator


def drag(navigator, spin, kind, dx, cancel=False):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    start = navigator._tags[kind].center().toPoint()
    QTest.mousePress(navigator, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    for k in range(1, 6):
        QTest.mouseMove(navigator, start + QPoint(dx * k // 5, 0))
    spin()
    if cancel:
        QTest.keyClick(navigator, Qt.Key.Key_Escape)
    QTest.mouseRelease(navigator, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start + QPoint(dx, 0))
    spin()


def test_tags_are_in_their_band_between_the_rows_and_the_axis(window, navigator, spin):
    from cycles.gui.navigator import AXIS_HEIGHT, ROWS_TOP_GAP
    band = navigator._tag_band()
    rows_top = min(rect.top() for rect, _ in navigator._cells)
    rows_bottom = max(rect.bottom() for rect, _ in navigator._cells)
    # the rows start just under the overview; the tags are under the rows, above the time axis
    assert rows_top == navigator._overview_rect().bottom() + ROWS_TOP_GAP
    assert band.top() >= rows_bottom and band.bottom() <= navigator.height() - AXIS_HEIGHT
    assert set(navigator._tags) == {'date', 'sky'}
    for rect in navigator._tags.values():
        assert band.top() - 0.5 <= rect.top() and rect.bottom() <= band.bottom() + 0.5
    assert navigator._tags['date'].top() < navigator._tags['sky'].top()     # one line each
    # with only one tag the band is a single line, and the rows grow into the space
    lines = navigator._band_lines()
    window.state.set_date(None)
    spin()
    navigator.repaint()
    assert navigator._band_lines() == lines - 1 == 1 and set(navigator._tags) == {'sky'}
    assert max(rect.bottom() for rect, _ in navigator._cells) > rows_bottom


def test_dragging_the_tags_moves_the_markers(window, navigator, spin):
    state = window.state
    selection, focus = state.selection, state.focus
    date = state.date
    drag(navigator, spin, 'date', -300)
    assert state.date < date
    sky = state.sky_time
    drag(navigator, spin, 'sky', 100)
    assert state.sky_time > sky
    assert state.selection == selection and state.focus == focus


def test_escape_cancels_a_drag(window, navigator, spin):
    state = window.state
    before = state.sky_time
    drag(navigator, spin, 'sky', 150, cancel=True)
    assert state.sky_time == before
    assert state.focus == (3,)


def test_a_drag_stops_at_the_end_of_the_zoom(window, navigator, spin):
    state = window.state
    drag(navigator, spin, 'sky', 5000)
    # just inside the last subcycle (minutes before the end), so that it stays in the zoom
    assert 0 <= state.time_map.interval((3,))[1] - state.sky_time < 1 / 8766


def test_shift_click_sets_the_moment_and_keeps_the_selection(window, navigator, spin):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    state = window.state
    state.select((3, 1))
    spin()
    rect = next(r for r, a in navigator._cells if a == (3, 2, 0))
    QTest.mouseClick(navigator, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier,
                     rect.center().toPoint())
    spin()
    assert state.subcycle_at(state.sky_time, 3) == (3, 2, 0)
    assert state.selection == (3, 1)


# -- many levels: the rows of subcycles narrower than a pixel or two are drawn as strips of pixels

def test_all_the_levels_down_to_the_deepest(window, spin):
    import numpy as np
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtTest import QTest
    from cycles.gui.state import MAX_DEPTH, address_of, tcoord
    state, navigator = window.state, window.navigator
    window.resize(1400, 1000)
    state.set_focus(())
    window.rows_box.setValue(MAX_DEPTH)                   # the toolbar allows every level
    spin()
    navigator.repaint()
    rows = navigator._geometry
    assert [r.depth for r in rows] == list(range(1, MAX_DEPTH + 1))
    dense = [r.depth for r in rows if r.dense]
    assert dense and dense[-1] == MAX_DEPTH and len(navigator._cells) < 2000      # not 349,524 cells
    # a click in a dense row selects the subcycle under the pointer
    row = rows[-1]
    x = float(row.lefts[0] + 0.37 * (row.lefts[-1] + row.widths[-1] - row.lefts[0]))
    pos = QPointF(x, row.top + row.height / 2)
    QTest.mouseClick(navigator, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos.toPoint())
    spin()
    selection = state.selection
    assert len(selection) == MAX_DEPTH
    rect = navigator.rect_of(selection)
    assert rect.left() <= round(x) + 1 and rect.right() >= round(x) - 1
    # a single match of a query is not lost among the dimmed subcycles of its pixel
    index = 4 ** MAX_DEPTH // 3
    state.set_query(f"index == {index}")
    state.set_highlight('query')
    state.select(None)
    spin()
    image = navigator.grab().toImage()
    rect = navigator.rect_of(address_of(index, MAX_DEPTH))
    color = image.pixelColor(int(rect.center().x()), int(row.top + row.height / 2))
    expected = np.clip(state.colors(MAX_DEPTH, state.color_key)[index], 0, 1) * 255
    assert np.allclose([color.red(), color.green(), color.blue()], expected, atol=3)
    assert tcoord(address_of(index, MAX_DEPTH)) == index
