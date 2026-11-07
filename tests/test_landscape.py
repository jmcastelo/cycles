"""The model landscape: the mismatch over anchor × arc, its period, and moving the model on it."""

import numpy as np
import pytest

from cycles.functions.cycle_analysis import (
    boundary_fractions, mismatch_by_depth, mismatch_grid, precession_rate, time_shares,
)
from cycles.functions.cycle_model import ANCHOR_POINTS, BUILTIN_PRESETS, DEFAULT_PRESET
from cycles.functions.division import proportions

DEFAULT = BUILTIN_PRESETS[DEFAULT_PRESET]


def test_the_grid_measures_agree_with_mismatch_by_depth():
    solution = DEFAULT.solve()
    for depth, row in enumerate(mismatch_by_depth(DEFAULT, 3), 1):
        for measure in ('max', 'rms'):
            value = mismatch_grid(DEFAULT, np.array([solution['anchor']]), np.array([solution['turns']]), depth,
                                  measure)[0, 0]
            assert np.isclose(value, row[measure], rtol=1e-6)
    with pytest.raises(ValueError):
        mismatch_grid(DEFAULT, np.array([0.0]), np.array([2.5]), 1, 'mean')


def _maxima(x, y):
    inner = (y[1:-1] > y[:-2]) & (y[1:-1] >= y[2:])
    return x[1:-1][inner]


def test_the_landscape_repeats_at_half_the_period_of_the_precession_rate():
    """The rate varies about every 41,000 years (the obliquity); the signed share deviations follow it, and
    their size, without the sign, repeats twice per period: about every 20,000 years."""
    years = np.arange(-150_000.0, 150_000.0, 200.0)
    rate = precession_rate(DEFAULT, years)
    rate_period = np.median(np.diff(_maxima(years, rate)))
    assert 36_000 < rate_period < 46_000
    anchors = np.arange(-90_000.0, 90_000.0, 100.0)
    u = boundary_fractions(1) - ANCHOR_POINTS['kali']
    from cycles.plotting.equinoctial_precession import year_from_ayanamsa
    years = year_from_ayanamsa(u[None, :] * 2.5, unit='turns', reference_year=anchors[:, None], model='long_term')
    treta = (time_shares(years) - proportions)[:, 0, 1]
    changes = anchors[1:][np.diff(np.sign(treta)) != 0]
    assert 17_000 < np.median(np.diff(changes)) < 23_000          # half the rate's period
    for turns in (1.0, 2.5, 4.0):                                 # whatever the arc
        mismatch = mismatch_grid(DEFAULT, anchors[::5], np.array([turns]), 1)[:, 0]
        smooth = np.convolve(mismatch, np.ones(9) / 9, mode='same')
        peaks = _maxima(anchors[::5][10:-10], smooth[10:-10])
        assert 17_000 < np.median(np.diff(peaks)) < 23_000


# -- the panel



@pytest.fixture
def panel(window, spin):
    window.show_panel('landscape')
    spin()
    p = window.landscape_panel
    p.resolution.setCurrentIndex(p.resolution.findData('coarse'))
    p.render()
    p.finish()
    p.canvas.draw()
    return p


@pytest.mark.gui
def test_the_panel_fills_the_grid_and_finds_the_best_point(window, panel):
    assert not panel._pending and np.isfinite(panel.grid).any()
    i, j = np.unravel_index(np.nanargmin(np.where(np.isfinite(panel.grid), panel.grid, np.nan)), panel.grid.shape)
    assert panel.best == (panel.anchors[i], panel.turns[j], panel.grid[i, j])
    assert np.isclose(panel.value_at(panel.anchors[i], panel.turns[j]), panel.grid[i, j])
    anchor, turns = panel.model_position()
    assert np.allclose(panel._marker.get_offsets()[0], (anchor, turns))
    assert 'Model: Start of Kali 17 Feb 3102 BC, 2.50 turns: 0.0085' in panel.readout.text()


@pytest.mark.gui
def test_the_grid_is_computed_progressively_from_the_models_arc(window, spin):
    window.show_panel('landscape')
    spin(1)
    p = window.landscape_panel
    p.resolution.setCurrentIndex(p.resolution.findData('coarse'))
    p.render()
    first = p._pending[0]
    assert np.isclose(p.turns[first], p.turns[np.argmin(np.abs(p.turns - 2.5))])
    p._compute_next()
    assert np.isfinite(p.grid[:, first]).any() and len(p._pending) < len(p.turns)
    assert 'Computing the landscape' in p.readout.text()


def _event(panel, name, x, y, dblclick=False, key=None):
    from matplotlib.backend_bases import KeyEvent, MouseEvent
    px, py = panel.ax.transData.transform((x, y))
    if key is not None:
        return KeyEvent(name, panel.canvas, key, px, py)
    event = MouseEvent(name, panel.canvas, px, py, button=1, dblclick=dblclick)
    return event


@pytest.mark.gui
def test_dragging_the_model_moves_the_cycle(window, panel, spin):
    state = window.state
    anchor, turns = panel.model_position()
    before = state.time_map.to_physical(np.array([0.0, 1.0]))
    panel._pressed(_event(panel, 'button_press_event', anchor, turns))
    assert panel._drag is not None
    panel._moved(_event(panel, 'motion_notify_event', 20_000.0, 3.0))
    panel._released(_event(panel, 'button_release_event', 20_000.0, 3.0))
    spin()
    solution = state.model.solve()
    assert abs(solution['anchor'] - 20_000.0) < 0.01 and np.isclose(solution['turns'], 3.0, atol=1e-3)
    assert state.model.name == DEFAULT.name and state.model.anchor_point == 'kali'
    assert not np.allclose(state.time_map.to_physical(np.array([0.0, 1.0])), before)   # every panel follows
    assert window.model_box.currentText().endswith('(modified)')


@pytest.mark.gui
def test_escape_cancels_a_drag_and_a_double_click_moves(window, panel, spin):
    state = window.state
    anchor, turns = panel.model_position()
    panel._pressed(_event(panel, 'button_press_event', anchor, turns))
    panel._moved(_event(panel, 'motion_notify_event', -30_000.0, 1.5))
    panel._key(_event(panel, 'key_press_event', 0, 0, key='escape'))
    assert panel._drag is None and np.allclose(panel._marker.get_offsets()[0], (anchor, turns))
    panel._released(_event(panel, 'button_release_event', -30_000.0, 1.5))
    assert state.model == DEFAULT
    panel._pressed(_event(panel, 'button_press_event', -30_000.0, 1.5, dblclick=True))
    spin()
    assert abs(state.model.solve()['anchor'] + 30_000.0) < 0.01


@pytest.mark.gui
def test_presets_are_named_on_hover(window, panel):
    names = panel.presets_near(panel.model_position())
    assert 'Kali 3102 BC, sunrise at Lanka' in names and DEFAULT_PRESET not in names
    panel._moved(_event(panel, 'motion_notify_event', *panel.model_position()))
    assert 'presets: ' in panel.readout.text()


@pytest.mark.gui
def test_no_landscape_with_a_constant_rate(window, spin):
    window.state.set_model(BUILTIN_PRESETS['Precession period at constant rate'])
    window.show_panel('landscape')
    spin()
    p = window.landscape_panel
    p.render()
    assert p.ax is None and 'constant precession rate' in p.figure.texts[0].get_text()


@pytest.mark.gui
def test_the_landscape_is_saved_complete(window, panel, spin, tmp_path):
    panel.resolution.setCurrentIndex(panel.resolution.findData('medium'))
    panel.render()
    assert panel._pending
    window.save_graph('landscape')
    spin()
    dialog = window.export_dialog
    dialog.format.setCurrentIndex(dialog.format.findData('png'))
    dialog.path.setText(str(tmp_path / 'landscape.png'))
    dialog.save()
    assert (tmp_path / 'landscape.png').stat().st_size > 1000 and not panel._pending
