"""The navigator: the tag band of the markers, dragging the tags, Shift+click, and the window (zoom, pan, map, fits)."""

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


# -- the window: wheel zoom, panning, the overview as a map, the scroll bar, fits

def wheel(navigator, x, notches):
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QApplication
    area = navigator._area()
    pos = QPointF(x, area.center().y())
    event = QWheelEvent(pos, navigator.mapToGlobal(pos), QPoint(0, 0), QPoint(0, 120 * notches),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
                        False)
    QApplication.sendEvent(navigator, event)


def test_the_wheel_zooms_around_the_pointer(window, spin):
    state, navigator = window.state, window.navigator
    state.set_focus(())
    spin()
    area = navigator._area()
    x = area.left() + 0.3 * area.width()
    before = 0.3                                     # the point under the pointer, in the whole cycle
    wheel(navigator, x, 4)
    spin()
    a, b = state.window
    assert b - a == pytest.approx(1.25 ** -4) and a + 0.3 * (b - a) == pytest.approx(before)
    wheel(navigator, x, 40)                         # down to the narrowest: a subcycle of depth 8
    spin()
    a, b = state.window
    assert len(state.focus) >= 7 and state.min_width_at((a + b) / 2) <= b - a < 1e-4   # about a subcycle of depth 8
    wheel(navigator, x, -200)                        # and out to the whole cycle
    spin()
    assert state.window == (0.0, 1.0) and state.focus == ()


def test_the_focus_is_the_smallest_subcycle_holding_the_window(window, spin):
    state = window.state
    focuses = []
    state.focusChanged.connect(focuses.append)
    state.set_window(0.91, 0.93)                    # inside Kali › Satya (0.9 to 0.94)
    assert state.focus == (3, 0)
    state.set_window(0.92, 0.935)                   # still there: no signal
    assert focuses == [(3, 0)]
    state.set_window(0.85, 0.95)                    # across the start of the Kali
    assert state.focus == ()


def test_dragging_pans_and_a_click_still_selects(window, spin):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    state, navigator = window.state, window.navigator
    state.set_window(0.5, 0.6)
    state.select(None)
    spin()
    navigator.repaint()
    area = navigator._area()
    start = QPoint(int(area.center().x()), int(area.top() + 10))
    QTest.mousePress(navigator, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    for k in range(1, 6):
        QTest.mouseMove(navigator, start + QPoint(-20 * k, 0))
    QTest.mouseRelease(navigator, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start + QPoint(-100, 0))
    spin()
    a, b = state.window
    assert a == pytest.approx(0.5 + 100 / area.width() * 0.1) and b - a == pytest.approx(0.1)
    assert state.selection is None                  # a pan does not select
    QTest.mouseClick(navigator, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    spin()
    assert state.selection is not None and len(state.selection) == len(state.focus) + 1


def test_the_overview_is_a_map_of_the_window(window, spin):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    state, navigator = window.state, window.navigator
    state.set_window(0.2, 0.3)
    spin()
    strip = navigator._overview_rect()
    y = int(strip.center().y())
    x = lambda u: int(round(strip.left() + u * strip.width()))
    QTest.mousePress(navigator, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(x(0.25), y))
    for k in range(1, 5):                            # drag the frame
        QTest.mouseMove(navigator, QPoint(x(0.25 + 0.1 * k / 4), y))
    QTest.mouseRelease(navigator, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(x(0.35), y))
    a, b = state.window
    assert a == pytest.approx(0.3, abs=2e-3) and b - a == pytest.approx(0.1)
    QTest.mousePress(navigator, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(x(0.4), y))
    for k in range(1, 5):                            # drag its right edge: zoom
        QTest.mouseMove(navigator, QPoint(x(0.4 + 0.1 * k / 4), y))
    QTest.mouseRelease(navigator, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(x(0.5), y))
    a, b = state.window
    assert a == pytest.approx(0.3, abs=2e-3) and b == pytest.approx(0.5, abs=2e-3)
    QTest.mouseClick(navigator, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(x(0.95), y))
    assert state.focus == (3,) and state.window == pytest.approx((0.9, 1.0))     # a click fits that yuga


def test_the_scroll_bar_and_the_keys(window, spin):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    state, navigator = window.state, window.navigator
    bar = navigator.hscroll
    assert bar.isVisible() and bar.maximum() == 0
    state.set_window(0.0, 0.25)
    assert bar.maximum() > 0 and bar.value() == 0
    bar.setValue(bar.maximum())
    assert state.window == pytest.approx((0.75, 1.0))
    state.set_window(0.4, 0.5)
    assert bar.value() == pytest.approx(0.4 / 0.9 * bar.maximum(), abs=1)
    navigator.setFocus()
    QTest.keyClick(navigator, Qt.Key.Key_Plus)
    a, b = state.window
    assert b - a == pytest.approx(0.1 / 1.25 ** 2) and (a + b) / 2 == pytest.approx(0.45)
    QTest.keyClick(navigator, Qt.Key.Key_Home)
    assert state.window == (0.0, 1.0)


def test_fits_spacing_and_reveal(window, spin):
    state, navigator = window.state, window.navigator
    state.zoom_in((2, 1))                            # double-click: the subcycle fills the rows
    assert state.focus == (2, 1) and state.window == pytest.approx((0.78, 0.84))
    state.zoom_out()
    assert state.focus == (2,) and state.window == pytest.approx((0.7, 0.9))
    state.set_window(0.75, 0.8)
    state.set_spacing('index')                       # the same part of the cycle, with equal widths
    from cycles.gui.state import index_to_time
    assert (index_to_time(state.window[0]), index_to_time(state.window[1])) == pytest.approx((0.75, 0.8))
    spin()
    navigator.repaint()
    assert navigator._window_time() == pytest.approx((0.75, 0.8))
    state.set_spacing('time')
    state.set_window(0.71, 0.73)                     # inside Dvapara › Satya; reveal a subcycle beside it
    focus = state.focus
    state.reveal(focus + (3,))
    a, b = state.window
    assert state.focus == focus and b - a == pytest.approx(0.02)
    from cycles.gui.state import coordinate_extent
    start, end = coordinate_extent(focus + (3,), 'time')
    assert a < end and start < b                     # moved over it


def test_a_session_keeps_the_window(window, spin):
    from cycles.gui import session
    state = window.state
    state.set_window(0.123, 0.1278)
    data = session.capture(window)
    state.set_focus(())
    assert session.apply(window, data) == []
    assert state.window == pytest.approx((0.123, 0.1278))
