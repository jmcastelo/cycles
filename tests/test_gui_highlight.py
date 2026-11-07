"""What the views highlight around the selection, and the sky moment with Follow."""

import numpy as np
import pytest

from cycles.functions.duration import count_digits

pytestmark = pytest.mark.gui


@pytest.fixture
def selected(window, spin):
    state = window.state
    state.set_focus((3,))
    state.select((3, 1, 2, 0))
    spin()
    return state


def test_highlight_classes_are_nested(window, selected, spin):
    state = selected
    counts = {}
    for mode in ('duration', 'composition', 'orbit'):
        window.highlight_box.setCurrentIndex(window.highlight_box.findData(mode))
        spin()
        assert state.highlight == mode
        counts[mode] = set(int(i) for i in state.highlight_indices(state.selection))
    assert counts['orbit'] <= counts['composition'] <= counts['duration']
    level = state.cache.level(4)
    for i in counts['composition']:
        assert (count_digits(level.lcoords[i]) == count_digits(np.array((3, 1, 2, 0)))).all()
    assert len(counts['composition']) == 24 and len(counts['orbit']) == 3


def test_the_toolbar_follows_the_state(window, selected, spin):
    selected.set_highlight('composition')
    spin()
    assert window.highlight_box.currentData() == 'composition'
    selected.set_highlight('none')
    spin()
    assert window.highlight_box.currentData() == 'none'
    assert selected.highlight_indices(selected.selection) is None


def test_the_measures_plot_rings_the_highlighted_class(window, selected, spin):
    window.docks['measures'].raise_()
    spin()
    panel = window.measures_panel
    selected.set_highlight('none')
    spin()
    plain = len(panel._highlights)
    selected.set_highlight('composition')
    spin()
    assert len(panel._highlights) == plain + 1


def test_follow_rings_the_moment(window, selected, spin):
    state = selected
    window.docks['measures'].raise_()
    state.set_sky_time(float(np.mean(state.time_map.interval((3, 2, 1)))))
    spin()
    panel = window.measures_panel
    state.set_follow(True)
    spin()
    following = len(panel._highlights)
    state.set_follow(False)
    spin()
    assert len(panel._highlights) == following - 1
    state.set_follow(True)
    spin()
    assert state.moment_index(3) is not None


def test_inspector_shows_the_place_among_the_orderings(window, selected):
    text = window.inspector.fields['same_composition'].text()
    assert text.startswith('24 subcycles') and 'number 22 in time order' in text
