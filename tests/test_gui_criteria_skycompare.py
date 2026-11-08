"""The two division criteria in the navigator, and the Sky comparison panel."""

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
    window.criteria_action.setChecked(True)
    assert state.compare_criteria
    state.set_focus((3,))
    spin()
    navigator.repaint()
    spin()
    assert navigator._criteria_shown == ['time']        # the default model divides by angle
    text = navigator.criteria_text((3, 2))
    assert text.startswith('\nBy 4:3:2:1 of the years: starts') and 'years)' in text
    window.criteria_action.setChecked(False)
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


# -- sky comparison

def test_concentration():
    from cycles.gui.skycompare import concentration, random_concentration
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
    window.sky_panel.compareRequested.emit()        # the Compare… button of the Sky panel
    spin()
    panel = window.skycompare_panel
    assert window.docks['skycompare'].isVisible() and panel.isVisible()
    panel.render()
    return panel


@pytest.mark.ephemeris
def test_the_class_panel_draws_only_when_visible(window, class_window, spin):
    window.docks['skycompare'].close()
    spin()
    assert not class_window.isVisible()
    window.state.select((3, 1, 2, 1))
    spin()
    assert class_window._dirty and not class_window.render_timer.isActive()
    window.sky_panel.compareRequested.emit()        # Compare… opens it again
    spin()
    assert class_window.isVisible()
    assert class_window.render_timer.isActive()
    class_window.render()
    assert not class_window._dirty
    assert class_window.title().startswith('Sky of Kali › Treta › Dvapara › Treta')


@pytest.mark.ephemeris
@pytest.mark.parametrize('kind, count', [('composition', 24), ('duration', 28), ('children', 4), ('orbit', 3),
                                         ('all', 256)])
def test_class_members(window, class_window, spin, kind, count):
    class_window.kind.setCurrentIndex(class_window.kind.findData(kind))
    indices, depth, _ = class_window.members()
    assert len(indices) == count
    class_window.render()
    assert len(class_window._members) == min(count, class_window.charts.value())
    assert class_window._strip is not None
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
    dialog.path.setText(str(tmp_path / 'skycompare.png'))
    dialog.save()
    out = tmp_path / 'skycompare.png'
    assert out.exists() and out.stat().st_size > 500, dialog.status.text()


def test_sky_distance_and_the_chance_reference():
    from cycles.gui.skycompare import expected_closest, sky_distance
    reference = {'mars': 10.0, 'saturn': 350.0}
    longitudes = {'mars': np.array([10.0, 20.0, 190.0]), 'saturn': np.array([350.0, 0.0, 170.0])}
    assert np.allclose(sky_distance(longitudes, reference, ['mars', 'saturn']), [0.0, 10.0, 180.0])
    rng = np.random.default_rng(2)
    random = sky_distance({'mars': rng.uniform(0, 360, 100_000)}, {'mars': 0.0}, ['mars'])
    assert abs(random.mean() - 90) < 1                        # unrelated skies: 90° on average
    assert abs(expected_closest(random, 9) - 18) < 1          # the smallest of 9 uniform on (0°, 180°)


@pytest.mark.ephemeris
def test_many_positions_at_once_match_one_by_one(ephemeris):
    import cycles.functions.nbody_ephemeris as nbe
    from cycles.gui.sky import ephemeris_parts
    from cycles.plotting.equinoctial_precession import planet_positions, planet_positions_many
    tables = [nbe.load_ephemeris(part) for part in ephemeris_parts(ephemeris)]
    bodies = ('sun', 'mercury', 'mars', 'jupiter', 'neptune')
    years = np.array([-3101.1, -800.5, 0.25, 1000.0, 2026.8, 1e7])     # the last outside every table
    many = planet_positions_many(years, tables, bodies)
    for k, year in enumerate(years[:-1]):
        one = planet_positions(year, tables, bodies)
        for body in bodies:
            for key, value in one[body].items():
                assert np.isclose(many[body][key][k], value, atol=1e-9)
    assert all(np.isnan(many[body]['sidereal'][-1]) for body in bodies)


@pytest.mark.ephemeris
def test_most_similar_first(window, class_window):
    class_window.kind.setCurrentIndex(class_window.kind.findData('all'))
    class_window.order.setCurrentIndex(class_window.order.findData('similar'))
    class_window.render()
    members = class_window._members
    assert members[0][0] == window.state.selection and members[0][2] == 0.0     # the reference first
    distances = [d for _, _, d in members[1:]]
    assert distances == sorted(distances)
    _, _, all_distances, sampled, _ = class_window._strip
    others = np.sort(all_distances[sampled != 3 * 64 + 1 * 16 + 2 * 4 + 0])
    assert np.allclose(distances, others[:len(distances)])
    summary = class_window.summary
    assert summary['n'] == 255 and np.isclose(summary['closest'], others[0])
    assert 0 < summary['chance'] < summary['random_median']
    # only the slow bodies, or all of them
    slow = summary['closest']
    class_window.compared.setCurrentIndex(class_window.compared.findData('all'))
    class_window.render()
    assert class_window.summary['closest'] != slow


@pytest.mark.ephemeris
def test_clicking_the_strip_selects(window, class_window, spin):
    from matplotlib.backend_bases import MouseEvent
    class_window.kind.setCurrentIndex(class_window.kind.findData('all'))
    class_window.render()
    class_window.canvas.draw()
    ax, years, distances, sampled, depth = class_window._strip
    k = int(np.nanargmax(distances))                      # the farthest sky stands apart at the top
    x, y = ax.transData.transform((years[k], distances[k]))
    event = MouseEvent('button_release_event', class_window.canvas, x, y, button=1)
    event.inaxes = ax
    class_window._clicked(event)
    spin()
    from cycles.gui.state import address_of
    assert window.state.selection == address_of(int(sampled[k]), depth)
    assert window.state.sky_time == years[k]


@pytest.mark.ephemeris
def test_the_charts_fill_the_panel_as_it_changes_size(window, class_window, spin):
    dock = window.docks['skycompare']
    dock.setFloating(True)
    layouts = {}
    for size in ((900, 750), (500, 900), (1300, 650)):
        dock.resize(*size)
        spin()
        class_window.fit_charts()
        class_window.canvas.draw()
        renderer = class_window.canvas.get_renderer()
        figure = class_window.figure.bbox
        boxes = [ax.get_tightbbox(renderer) for ax in class_window._axes]
        for box in boxes:                                   # inside the canvas, labels included
            assert box.x0 >= -1 and box.y0 >= -1 and box.x1 <= figure.x1 + 1 and box.y1 <= figure.y1 + 1
        for i, a in enumerate(boxes):                       # and apart from one another
            for b in boxes[i + 1:]:
                assert min(a.x1, b.x1) - max(a.x0, b.x0) <= 1 or min(a.y1, b.y1) - max(a.y0, b.y0) <= 1
        strip = class_window._strip[0].get_window_extent(renderer)
        assert all(box.y0 > strip.y1 for box in boxes)
        layouts[size] = dict(class_window.chart_layout)
    assert layouts[(1300, 650)]['rows'] == 1                # wide: one row
    assert layouts[(500, 900)]['columns'] < layouts[(900, 750)]['columns']
    assert layouts[(900, 750)]['side'] > 60
