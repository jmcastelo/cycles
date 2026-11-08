"""The Measures panel with any two measures, colored by a measure, and the inspector's line of measures."""

import numpy as np
import pytest

pytestmark = pytest.mark.gui


@pytest.fixture
def panel(window, spin):
    state = window.state
    state.set_focus((3,))
    state.select((3, 1, 2))
    window.show_panel('measures')
    spin()
    return window.measures_panel


def choose(box, key):
    box.setCurrentIndex(box.findData(key))


def test_any_two_measures(window, panel):
    state = window.state
    assert panel.measures() == ('dharma', 'purity') and panel.kind.currentData() == 'scatter'
    choose(panel.x_measure, 'tension')
    choose(panel.y_measure, 'trend')
    panel.render()
    indices = np.arange(48, 64)                                  # depth 3 inside Kali
    assert np.array_equal(panel._indices, indices)
    assert np.allclose(panel._x, state.cache.measure(3, 'tension')[indices])
    assert np.allclose(panel._y, state.cache.measure(3, 'trend')[indices])
    assert panel.ax.get_xlabel() == 'Tension' and panel.graph_name() == 'Trend vs Tension'
    choose(panel.kind, 'time')
    panel.render()
    assert np.allclose(panel._y, state.cache.measure(3, 'trend')[indices]) and panel.x_measure.isHidden()
    choose(panel.kind, '3d_index')
    panel.render()
    assert panel._z is not None and np.allclose(panel._z, indices)


def test_colored_by_a_measure(window, panel):
    choose(panel.color_by, 'contrast')
    panel.render()
    assert len(panel.figure.axes) == 2                           # the plot and its color bar
    assert panel.figure.axes[1].get_ylabel() == 'Contrast'
    choose(panel.color_by, 'subcycle')
    panel.render()
    assert len(panel.figure.axes) == 1


def test_the_angular_density_needs_a_model(window, panel):
    state = window.state
    choose(panel.y_measure, 'density')
    panel.render()
    density = state.measure_values(3, 'density')
    assert density is not None and np.allclose(panel._y, density[48:64])
    model = state.model
    state.set_model(None)
    panel.render()
    assert panel.ax is None and 'needs a cycle model' in panel.info.text()
    assert 'angular density' not in window.inspector.fields['measures'].text()
    state.set_model(model)
    panel.render()
    assert panel.ax is not None


def test_the_inspector_line(window, panel):
    text = window.inspector.fields['measures'].text()
    for word in ('mixture', 'tension', 'trend', 'roughness', 'contrast', 'balance', 'angular density'):
        assert word in text
    trend = window.state.cache.measure(3, 'trend')[3 * 16 + 1 * 4 + 2]
    assert f"trend {trend:+.4f}".replace('-', '−') in text


def test_kept_in_sessions(window, panel):
    from cycles.gui import session
    choose(panel.x_measure, 'roughness')
    choose(panel.color_by, 'balance')
    data = session.capture(window)
    choose(panel.x_measure, 'dharma')
    choose(panel.color_by, 'subcycle')
    session.apply(window, data)
    assert panel.x_measure.currentData() == 'roughness' and panel.color_by.currentData() == 'balance'
