"""The Events panel: planetary events against the boundaries, the significance test, the navigator layer."""

import numpy as np
import pytest

pytestmark = [pytest.mark.gui, pytest.mark.ephemeris]


@pytest.fixture
def panel(window, spin, ephemeris):
    window.show_panel('events')
    spin()
    p = window.events_panel
    p.rotations.setValue(1000)
    return p


def choose(panel, key):
    panel.kind.setCurrentIndex(panel.kind.findData(key))


def test_the_test_of_the_great_conjunctions(window, panel):
    from cycles.functions.cycle_analysis import boundary_fractions
    from cycles.functions.events import first_of_series, tdb_years
    from cycles.functions.significance import proximity_test
    choose(panel, 'great')
    panel.depth.setValue(2)
    panel.render()
    r = panel.result
    assert r['count'] == 17 and 0 < r['p'] <= 1 and r['rotations'] == 1000
    # the same as computing it directly
    state = window.state
    boundaries = tdb_years(state.time_map.to_physical(boundary_fractions(2)))
    start, end = tdb_years([state.time_map.start, state.time_map.end])
    data = next(iter(panel._catalogs.values()))
    direct = proximity_test(boundaries, data['times'][first_of_series(data)], start, end, 1000)
    assert np.isclose(direct['observed'], r['observed']) and np.isclose(direct['p'], r['p'])
    assert 'over the whole cycle' in panel.heading.text()
    from cycles.gui.eventspanel import MAX_ROWS
    assert panel.table.rowCount() == MAX_ROWS and panel.table.item(0, 1).text().startswith('conjunction')
    assert f"first {MAX_ROWS}" in panel.note.text()


def test_trigon_changes_and_the_planets_at_aries(window, panel):
    choose(panel, 'trigon_tropical')
    panel.depth.setValue(1)
    panel.render()
    assert panel.result['count'] == 5
    assert all(panel.table.item(r, 1).text().startswith('trigon change to') for r in range(panel.table.rowCount()))
    choose(panel, 'aries_sidereal')
    panel.render()
    r = panel.result
    assert r['unit'] == '°' and r['p'] < 0.05            # the gathering at the start of Kali (the anchor)
    assert panel.table.rowCount() == 5 and 'mean angle' in panel.table.item(3, 2).text()


def test_inside_the_zoom(window, panel, spin):
    state = window.state
    state.set_focus((3,))
    spin()
    choose(panel, 'great')
    panel.inside.setChecked(True)
    panel.depth.setValue(2)
    panel.render()
    assert panel.result['count'] == 5 and 'inside the zoom' in panel.heading.text()
    lo, hi = state.time_map.interval((3,))
    assert all(lo <= y <= hi for y in panel._rows)
    panel.depth.setValue(1)                               # not below the zoom
    panel.render()
    assert panel.result is None and 'below the zoom' in panel.heading.text()


def test_clicking_an_event_and_the_navigator_layer(window, panel, spin):
    state = window.state
    choose(panel, 'neptune_pluto')
    panel.depth.setValue(3)
    panel.render()
    years, label = state.event_marks
    assert label == 'Neptune–Pluto conjunctions' and len(years) > 100
    panel.go_to(0)
    spin()
    year = panel._rows[0]
    assert state.sky_time == year and len(state.selection) == 3
    t0, t1 = state.time_map.interval(state.selection)
    assert t0 <= year <= t1
    window.navigator.repaint()
    assert window.navigator._events_shown >= 1
    panel.show_marks.setChecked(False)
    assert state.event_marks is None
    choose(panel, 'aries_tropical')
    panel.show_marks.setChecked(True)
    panel.render()
    assert state.event_marks is None                      # no events to show for the planets at 0° Aries


def test_the_panel_is_kept_in_sessions(window, panel):
    from cycles.gui import session
    choose(panel, 'uranus_neptune')
    panel.depth.setValue(4)
    data = session.capture(window)
    assert data['panels']['events_panel']['kind']['data'] == 'uranus_neptune'
    choose(panel, 'great')
    session.apply(window, data)
    assert panel.kind.currentData() == 'uranus_neptune' and panel.depth.value() == 4


def test_without_the_ephemeris(window, panel):
    tables = window.sky_panel.tables
    window.sky_panel.tables = None
    try:
        panel.render()
        assert panel.result is None and 'ephemeris' in panel.heading.text()
    finally:
        window.sky_panel.tables = tables


def test_the_map_over_the_models(window, panel, spin):
    state = window.state
    choose(panel, 'great')
    panel.view.setCurrentIndex(panel.view.findData('models'))
    panel.depth.setValue(1)
    panel.render()
    r = panel.result
    scan = r['map']
    assert scan['ratio'].shape == (len(r['anchors']), len(r['turns'])) and scan['valid'].sum() > 100
    assert 0 < scan['p_global'] <= 1 and 0 <= r['own_rank'] <= 1
    assert 'global p' in panel.heading.text() and panel.table.rowCount() == 20
    ratios = [float(panel.table.item(k, 2).text()) for k in range(20)]
    assert ratios == sorted(ratios)
    # a row places the cycle there
    anchor, turns = panel._map_rows[0]
    panel.go_to(0)
    spin()
    solution = state.model.solve()
    assert abs(solution['anchor'] - anchor) < 0.01 and np.isclose(solution['turns'], turns)
    choose(panel, 'aries_sidereal')
    panel.render()
    assert panel.result is None and 'this model only' in panel.heading.text()
