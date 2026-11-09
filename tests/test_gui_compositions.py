"""The Compositions panel (the tetrahedron of compositions) and the inspector's measures by level."""

from math import comb

import numpy as np
import pytest

pytestmark = pytest.mark.gui


@pytest.fixture
def panel(window, spin):
    window.show_panel('compositions')
    window.state.set_focus((3,))
    window.state.select((3, 1, 2, 0))
    spin()
    return window.compositions_panel


def test_points_are_the_compositions(panel):
    data = panel._data
    assert data['depth'] == 4
    assert len(data['compositions']) == comb(4 + 3, 3)
    assert (data['compositions'].sum(axis=1) == 4).all()
    # inside Kali: the 64 subcycles of depth 4 below it
    assert data['counts'].sum() == 64
    # a composition sits at the mean of the vertices of its digits
    from cycles.gui.compositions import VERTICES
    k = int(np.flatnonzero((data['compositions'] == [4, 0, 0, 0]).all(axis=1))[0])
    assert np.allclose(data['points'][k], VERTICES[0])


def test_equal_duration_classes_lie_on_lines(panel):
    from cycles.gui.compositions import EQUAL_DURATION, VERTICES
    data = panel._data
    for group in data['classes']:
        durations = np.prod(np.array([0.4, 0.3, 0.2, 0.1]) ** np.array(group), axis=1)
        assert np.ptp(durations) < 1e-15
        points = np.array(group) @ VERTICES / data['depth']
        for a, b in zip(points, points[1:]):
            assert np.allclose(np.cross(b - a, EQUAL_DURATION), 0)


def test_looking_along_the_lines_shows_one_point_per_duration(panel, spin):
    from mpl_toolkits.mplot3d import proj3d
    panel.view.setCurrentIndex(panel.view.findData('equal'))
    spin()
    data = panel._data
    points = data['points']
    x, y, _ = proj3d.proj_transform(points[:, 0], points[:, 1], points[:, 2], panel.ax.get_proj())
    screen = np.round(panel.ax.transData.transform(np.column_stack([x, y])), 1)
    assert len(np.unique(screen, axis=0)) == len(data['classes'])


def test_clicking_a_composition_selects_and_highlights_its_subcycles(window, panel, spin):
    data = panel._data
    k = int(np.flatnonzero((data['compositions'] == [0, 0, 2, 2]).all(axis=1))[0])
    panel.choose(k)
    spin()
    state = window.state
    assert sorted(state.selection) == [2, 2, 3, 3] and state.selection[0] == 3
    assert state.highlight == 'composition'
    assert len(state.highlight_indices(state.selection)) == 6


def test_the_tooltip_describes_the_composition(window, panel):
    data = panel._data
    k = int(np.flatnonzero((data['compositions'] == [1, 1, 1, 1]).all(axis=1))[0])
    text = panel.composition_text(k)
    assert '6 subcycles here (of 24 orderings)' in text
    assert f"{0.4 * 0.3 * 0.2 * 0.1:.6g} of the cycle" in text


# -- the inspector's measures by level

def test_breakdown_gives_back_the_measures(window):
    from cycles.gui.state import measure_breakdown
    state = window.state
    for bases in ((4, 2, 2), (4, 3, 1), (4, 2.5, 5)):
        state.set_color_parameters(bases, state.color_parameters[1])
        level = state.cache.level(4)
        for i in range(0, 256, 11):
            b = measure_breakdown(level, tuple(level.lcoords[i]), bases)
            assert np.isclose(b['dharma'], level.dharmas[i]) and np.isclose(b['purity'], level.purities[i])
            assert np.isclose(b['dharma_weights'].sum(), 1) and np.isclose(b['shares'].sum(), 1)


def test_equal_weights_make_the_measures_depend_only_on_the_composition(window):
    """With base 1 (refused for the colors, which would repeat) dharma and purity ignore the order."""
    from cycles.functions.division import compute_level
    from cycles.gui.state import measure_breakdown
    level = compute_level(4, [4, 1, 1])
    b = measure_breakdown(level, (3, 1, 1, 0), (4, 1, 1))
    assert b['dharma_range'][0] == pytest.approx(b['dharma_range'][1])
    assert b['purity_range'][0] == pytest.approx(b['purity_range'][1])


def test_the_inspector_shows_the_levels(window, panel, spin):
    inspector = window.inspector
    assert inspector.levels.rowCount() == 4
    assert [inspector.levels.item(k, 0).text() for k in range(4)] == ['Kali', 'Treta', 'Dvapara', 'Satya']
    total = sum(float(inspector.levels.item(k, 3).text()) for k in range(4))
    assert total == pytest.approx(window.state.cache.level(4).dharmas[(3 * 64 + 1 * 16 + 2 * 4)], abs=5e-4)
    note = inspector.levels_note.text()
    assert 'Its 24 orderings' in note and 'the same purity' in note       # four different ages: purity is fixed
    window.state.select(None) if False else None
