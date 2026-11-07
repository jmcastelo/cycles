"""The two division criteria in the navigator, and the sky of a class of subcycles."""

import numpy as np
import pytest

pytestmark = pytest.mark.gui


# -- the criteria

@pytest.mark.parametrize('division, own', [('angle', 'angle'), ('time', 'time')])
def test_one_criterion_is_the_models_own_division(window, division, own):
    state = window.state
    state.set_model(state.model.replace(division=division))
    for depth in (1, 2, 3):
        criteria = state.criteria_boundaries(depth)
        cells = np.append(state.cache.level(depth).starts, 1.0)
        assert np.allclose(criteria[own]['normalized'], cells, atol=1e-12)
        other = 'time' if own == 'angle' else 'angle'
        assert np.abs(criteria[other]['normalized'] - cells).max() > 1e-4
        # both cover the same span of years
        assert np.isclose(criteria['angle']['years'][0], criteria['time']['years'][0])
        assert np.isclose(criteria['angle']['years'][-1], criteria['time']['years'][-1])


def test_the_years_criterion_divides_the_years_4_3_2_1(window):
    from cycles.functions.cycle_analysis import time_shares
    state = window.state
    years = state.criteria_boundaries(2)['time']['years']
    assert np.allclose(time_shares(years), [0.4, 0.3, 0.2, 0.1])


def test_the_navigator_draws_the_other_criterion(window, spin):
    state = window.state
    navigator = window.navigator
    window.criteria_box.setChecked(True)
    assert state.compare_criteria
    state.set_focus((3,))
    spin()
    navigator.repaint()
    spin()
    assert navigator._criteria_shown == ['time']        # the default model divides by angle
    text = navigator.criteria_text((3, 2))
    assert text.startswith('\nBy 4:3:2:1 of the years: starts') and 'years)' in text
    window.criteria_box.setChecked(False)
    spin()
    navigator.repaint()
    assert navigator._criteria_shown == [] and navigator.criteria_text((3, 2)) == ''


def test_no_criteria_without_a_cycle_model(window, spin):
    state = window.state
    state.set_model(None)
    state.set_compare_criteria(True)
    spin()
    window.navigator.repaint()
    assert state.criteria_boundaries(2) is None and window.navigator._criteria_shown == []


# -- the sky of a class

def test_concentration():
    from cycles.gui.skyclass import concentration, random_concentration
    mean, r = concentration([10, 10, 10])
    assert np.isclose(mean, 10) and np.isclose(r, 1)
    assert np.isclose(concentration([0, 90, 180, 270])[1], 0, atol=1e-12)
    mean, _ = concentration([350, 10])
    assert np.isclose(mean % 360, 0, atol=1e-9) or np.isclose(mean, 360)
    rng = np.random.default_rng(1)
    simulated = np.mean([concentration(rng.uniform(0, 360, 50))[1] for _ in range(2000)])
    assert abs(simulated - random_concentration(50)) < 0.01


@pytest.mark.ephemeris
def test_planet_positions_match_the_chart(ephemeris):
    import cycles.functions.nbody_ephemeris as nbe
    from cycles.gui.sky import ephemeris_parts
    from cycles.plotting.equinoctial_precession import _tdb_year, planet_positions, plot_zodiac_with_planets
    tables = [nbe.load_ephemeris(part) for part in ephemeris_parts(ephemeris)]
    _, _, chart = plot_zodiac_with_planets(1000.0, tables, show=False, table=False, time_scale='UT')
    direct = planet_positions(_tdb_year(1000.0, 'UT'), tables)
    for body, values in direct.items():
        assert np.isclose(values['sidereal'], chart[body]['sidereal'])


@pytest.fixture
def class_window(window, spin, ephemeris):
    state = window.state
    state.set_focus((3,))
    state.select((3, 1, 2, 0))
    spin()
    window.sky_panel.classRequested.emit()          # the Class… button of the Sky panel
    spin()
    panel = window.skyclass_panel
    assert window.docks['skyclass'].isVisible() and panel.isVisible()
    panel.render()
    return panel


@pytest.mark.ephemeris
def test_the_class_panel_draws_only_when_visible(window, class_window, spin):
    window.docks['skyclass'].close()
    spin()
    assert not class_window.isVisible()
    window.state.select((3, 1, 2, 1))
    spin()
    assert class_window._dirty and not class_window.render_timer.isActive()
    window.sky_panel.classRequested.emit()          # Class… opens it again
    spin()
    assert class_window.isVisible()
    assert class_window.render_timer.isActive()
    class_window.render()
    assert not class_window._dirty
    assert 'Kali › Treta › Dvapara › Treta' in class_window.title()


@pytest.mark.ephemeris
@pytest.mark.parametrize('kind, count', [('composition', 24), ('duration', 28), ('children', 4), ('orbit', 3)])
def test_class_members(window, class_window, spin, kind, count):
    class_window.kind.setCurrentIndex(class_window.kind.findData(kind))
    indices, depth, _ = class_window.members()
    assert len(indices) == count
    class_window.render()
    assert len(class_window._members) == min(count, class_window.charts.value())
    assert class_window.table.rowCount() == 6


@pytest.mark.ephemeris
def test_clicking_a_chart_selects_and_moves_the_sky(window, class_window, spin):
    from matplotlib.backend_bases import MouseEvent
    ax = class_window._axes[0]
    address, year = ax._class_member
    x, y = ax.transAxes.transform((0.5, 0.5))
    event = MouseEvent('button_release_event', class_window.canvas, x, y, button=1)
    event.inaxes = ax
    class_window._clicked(event)
    spin()
    assert window.state.selection == address and window.state.sky_time == year


@pytest.mark.ephemeris
def test_only_inside_the_zoom(window, class_window):
    class_window.kind.setCurrentIndex(class_window.kind.findData('duration'))
    everywhere = len(class_window.members()[0])
    class_window.inside.setChecked(True)
    inside = class_window.members()[0]
    assert len(inside) < everywhere and (inside // 64 == 3).all()


@pytest.mark.ephemeris
def test_the_class_panel_saves_with_the_other_graphs(window, class_window, spin, tmp_path):
    class_window.saveRequested.emit()               # its Save… button
    spin()
    dialog = window.export_dialog
    assert dialog.isVisible()
    dialog.format.setCurrentIndex(dialog.format.findData('png'))
    dialog.path.setText(str(tmp_path / 'skyclass.png'))
    dialog.save()
    out = tmp_path / 'skyclass.png'
    assert out.exists() and out.stat().st_size > 500, dialog.status.text()
