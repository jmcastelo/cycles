"""The Permutations panel and the group explorer."""

import time

import numpy as np
import pytest
from symmetrymath import SymmetricGroup

from cycles.functions.conversion import lcoords_to_tcoord
from cycles.functions.permutation import permute_digits, tcoords_of

pytestmark = pytest.mark.gui


@pytest.fixture
def panel(window, spin):
    window.docks['permutations'].raise_()
    spin()
    return window.permutations_panel


def test_rows_are_those_of_the_study(window, panel, spin):
    panel.acts.setCurrentIndex(panel.acts.findData('all'))
    panel.depth.setValue(3)
    spin()
    data = panel._data
    assert data['sigma'] == (1, 2, 0) and data['order'] == 3 and data['slots'].shape == (4, 64)
    group = SymmetricGroup(3)
    addresses = [tuple(lc) for lc in window.state.cache.level(3).lcoords]
    for r in range(4):
        expected = []
        for a in addresses:
            for _ in range(r):
                a = group.operation(a, (1, 2, 0))
            expected.append(lcoords_to_tcoord(np.array(a)))
        assert (data['slots'][r] == expected).all()


def test_clicking_a_cell_selects_its_subcycle(window, panel, spin):
    from matplotlib.backend_bases import MouseEvent
    from cycles.gui.permutations import ROW_GAP
    panel.acts.setCurrentIndex(panel.acts.findData('all'))
    panel.depth.setValue(3)
    spin()
    data = panel._data
    x, y = panel._axes[0].transData.transform((data['centers'][10], 1 + ROW_GAP + 0.5))
    panel._clicked(MouseEvent('button_release_event', panel.canvas, x, y, button=1))
    spin()
    occupant = int(np.flatnonzero(data['slots'][1] == 10)[0])
    assert lcoords_to_tcoord(np.array(window.state.selection)) == occupant


def test_below_the_zoom_the_subcycles_stay_inside(window, panel, spin):
    window.state.set_focus((3,))
    panel.depth.setValue(4)
    spin()
    data = panel._data
    assert data['first'] == 1 and data['prefix'] == (3,) and len(data['sigma']) == 3
    assert data['slots'].min() == 0 and data['slots'].max() == 63


def test_auto_depth_follows_the_selection(window, panel, spin):
    state = window.state
    state.set_focus((3,))
    state.select((3, 1))
    spin()
    assert panel._data['depth'] == 2 and panel._data['sigma'] == (0,)      # one digit: only the identity
    state.select((3, 1, 2, 0))
    spin()
    assert panel._data['depth'] == 4 and len(panel._data['sigma']) == 3


def test_presets_and_typed_permutations(panel, spin):
    panel.depth.setValue(3)
    spin()
    for name, expected in (('Reversal', (2, 1, 0)), ('Swap the first two', (1, 0, 2)),
                           ('Swap the last two', (0, 2, 1)), ('Inverse shift', (2, 0, 1))):
        panel.preset.setCurrentText(name)
        spin()
        assert panel._data['sigma'] == expected and panel.element.text() == ' '.join(map(str, expected))
    panel.preset.setCurrentText('Custom')
    panel.element.setText('(0 2)')
    panel.element.editingFinished.emit()
    spin()
    assert panel._data['sigma'] == (2, 1, 0)
    panel.element.setText('0 0 1')
    panel.element.editingFinished.emit()
    spin()
    assert panel._data is None and 'permutation' in panel.summary.text()


@pytest.mark.parametrize('view', ['matrix', 'matrices'])
def test_matrix_views(panel, spin, view):
    panel.depth.setValue(3)
    panel.view.setCurrentIndex(panel.view.findData(view))
    spin()
    assert len(panel._axes) == (1 if view == 'matrix' else panel._data['order'])


def test_the_panel_publishes_sigma_even_when_hidden(window, spin):
    state = window.state
    window.docks['inspector'].raise_()
    state.set_focus((3,))
    state.select((3, 1, 2, 0))
    spin()
    assert state.permutation == ((1, 2, 0), 1)
    assert state.permutation_orbit((3, 1, 2, 0)) == [(3, 1, 2, 0), (3, 2, 0, 1), (3, 0, 1, 2)]
    assert 'takes it to Kali › Dvapara › Satya › Treta' in window.inspector.fields['permutation'].text()


# -- the group explorer

def finish(explorer, qapp, limit=120):
    start = time.time()
    while explorer._work is not None and time.time() - start < limit:
        qapp.processEvents()


@pytest.fixture
def explorer(window, panel, spin, qapp):
    window.state.set_focus((3,))
    panel.depth.setValue(4)                 # S_3 on the 64 subcycles of depth 4 in Kali
    spin()
    panel.show_group()
    finish(panel.explorer, qapp)
    spin()
    return panel.explorer


def row_of(model, sigma):
    return int(np.flatnonzero(np.all(model.perms == np.array(sigma), axis=1))[0])


def test_explorer_columns(window, explorer):
    model = explorer.model
    values = model.values
    assert model.rowCount() == 6
    identity = row_of(model, (0, 1, 2))
    assert values['fixed'][identity] == 64 and values['moved'][identity] == 0
    assert values['correlation'][identity] == 1 and values['color'][identity] == 0
    sigma = (1, 2, 0)
    i = row_of(model, sigma)
    level = window.state.cache.level(4)
    slots = tcoords_of(permute_digits(level.lcoords[192:256], sigma, 1)) - 192
    assert np.isclose(values['moved'][i], np.mean(slots != np.arange(64)))
    assert np.isclose(values['correlation'][i], np.corrcoef(np.arange(64), slots)[0, 1])
    assert values['orbits'][i] == 24 and values['fixed'][i] == 4
    assert 'C(6, 3) = 20' in explorer.note.text()


def test_explorer_rows_load_into_the_panel(window, panel, explorer, spin):
    model = explorer.model
    target = next(r for r in range(model.rowCount()) if tuple(model.perms[model.rows[r]]) == (2, 1, 0))
    explorer._clicked(model.index(target, 0))
    spin()
    assert window.state.permutation == ((2, 1, 0), 1)
    assert panel.preset.currentText() == 'Custom' and panel.element.text() == '2 1 0'
    selected = explorer.table.selectionModel().selectedRows()
    assert tuple(model.perms[model.rows[selected[0].row()]]) == (2, 1, 0)


def test_explorer_sorts_and_filters(explorer, spin):
    from PySide6.QtCore import Qt
    from cycles.gui.groupexplorer import COLUMNS
    model = explorer.model
    column = [key for key, *_ in COLUMNS].index('correlation')
    model.sort(column, Qt.SortOrder.DescendingOrder)
    values = [model.values['correlation'][i] for i in model.rows]
    assert values == sorted(values, reverse=True) and values[0] == 1
    explorer.type_filter.setCurrentIndex(explorer.type_filter.findData('2+1'))
    spin()
    assert model.rowCount() == 3
    explorer.parity_filter.setCurrentIndex(explorer.parity_filter.findData(1))
    spin()
    assert model.rowCount() == 0
    explorer.type_filter.setCurrentIndex(0)
    spin()
    assert model.rowCount() == 3


def test_explorer_follows_the_panel_depth(panel, explorer, spin, qapp):
    panel.depth.setValue(6)                 # S_5 below the zoom
    spin()
    assert explorer.model.rowCount() == 120
    finish(explorer, qapp)
    assert not np.isnan(explorer.model.values['purity']).any()
