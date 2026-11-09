"""The Dynamics panel: the series of a level as a dynamical system (return map, DFA, spectrum, recurrences, changes)."""

import numpy as np
import pytest

pytestmark = pytest.mark.gui


@pytest.fixture
def panel(window, spin):
    state = window.state
    state.set_focus(())
    state.select((3, 1, 2, 0, 1))                  # depth 5: 1024 subcycles
    window.show_panel('dynamics')
    spin()
    return window.dynamics_panel


def choose(box, key):
    box.setCurrentIndex(box.findData(key))


def test_every_plot_in_both_readings(window, panel):
    state = window.state
    for reading in ('index', 'time'):
        choose(panel.reading, reading)
        for plot in ('return', 'fluctuations', 'spectrum', 'recurrence', 'changes'):
            choose(panel.plot, plot)
            panel.render()
            assert panel.ax is not None and panel.ax.get_title().startswith(panel.plot.currentText()), (reading, plot)
    choose(panel.reading, 'index')
    choose(panel.plot, 'return')
    panel.render()
    dharma = state.cache.measure(5, 'dharma')
    assert np.allclose(panel._points[0], dharma[:-1]) and np.allclose(panel._points[1], dharma[1:])
    assert 'roughness log₄ b = 0.500' in panel.info.text() and 'backwards it turns around 0.6250' in panel.info.text()
    assert len(panel._highlights) == 1                          # the selection ringed
    assert panel.delay.isVisible()
    choose(panel.plot, 'spectrum')
    panel.render()
    assert not panel.delay.isVisible()


def test_the_durations_and_the_surrogates(window, panel):
    choose(panel.series_box, 'duration')
    choose(panel.plot, 'fluctuations')
    choose(panel.surrogate, 'shuffled')
    panel.render()
    lines = panel.ax.get_lines()
    assert len(lines) == 2 and 'H = 0.934' in panel.info.text()
    alphas = [float(line.get_label().split('α = ')[1]) for line in lines]
    assert alphas[0] > alphas[1] + 0.2                          # the order carries the memory
    choose(panel.surrogate, 'digits')                           # the durations depend only on the composition
    panel.render()
    s = panel.series()
    assert np.allclose(s['surrogate'], s['values'], rtol=1e-12)
    choose(panel.plot, 'return')
    panel.render()
    assert panel.ax.get_xscale() == 'log'


def test_inside_the_zoom_and_in_years(window, panel):
    state = window.state
    state.set_focus((3,))
    choose(panel.reading, 'time')
    choose(panel.plot, 'changes')
    panel.render()
    s = panel._series
    assert np.array_equal(s['indices'], np.arange(768, 1024))           # the subcycles of depth 5 inside Kali
    years = state.time_map.to_physical(np.array([0.9, 1.0]))
    assert years[0] <= s['x'].min() and s['x'].max() <= years[1]        # in years, inside the zoom
    assert len(s['cuts']) == 7 and 'change points' in panel.info.text()
    assert len(panel._highlights) >= 1                                  # the selection, as a band


def test_clicking_selects_a_subcycle(window, panel, spin):
    from matplotlib.backend_bases import MouseEvent
    choose(panel.plot, 'changes')
    panel.render()
    panel.canvas.draw()
    s = panel._series
    x, y = panel.ax.transData.transform((s['x'][100], s['values'][100]))
    event = MouseEvent('button_release_event', panel.canvas, x, y, button=1)
    panel._clicked(event)
    spin()
    from cycles.gui.state import address_of
    assert window.state.selection == address_of(100, 5)


def test_a_measure_of_the_model_without_a_model(window, panel):
    choose(panel.series_box, 'density')
    panel.render()
    assert panel.ax is not None
    window.state.set_model(None)
    panel.render()
    assert panel.ax is None and 'needs a cycle model' in panel.info.text()


def test_the_session_keeps_the_panel(window, panel):
    from cycles.gui import session
    choose(panel.plot, 'recurrence')
    choose(panel.series_box, 'trend')
    choose(panel.surrogate, 'phase')
    data = session.capture(window)
    choose(panel.plot, 'return')
    choose(panel.series_box, 'dharma')
    choose(panel.surrogate, 'none')
    session.apply(window, data)
    assert (panel.plot.currentData(), panel.series_key(), panel.surrogate.currentData()) == \
        ('recurrence', 'trend', 'phase')
