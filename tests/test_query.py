"""Queries: conditions on the subcycles (functions.query), and the highlight that shows their matches."""

import numpy as np
import pytest

from cycles.functions.division import compute_level
from cycles.functions.query import QueryError, evaluate, names_in, parse


def run(text, level):
    tree = parse(text)
    values = {'duration': level.durations, 'start': level.starts, 'dharma': level.dharmas,
              'purity': level.purities, 'index': np.arange(len(level.starts)), 'depth': level.lcoords.shape[1],
              'first': level.lcoords[:, 0], 'last': level.lcoords[:, -1]}
    values.update({f"a{k + 1}": level.lcoords[:, k] for k in range(level.lcoords.shape[1])})
    return evaluate(tree, {n: values[n] for n in names_in(tree)}, level.lcoords)


def test_conditions():
    level = compute_level(3)
    assert np.array_equal(run('dharma > 0.5', level), level.dharmas > 0.5)
    assert np.array_equal(run('0.4 < dharma <= 0.7 and not purity == 1', level),
                          (level.dharmas > 0.4) & (level.dharmas <= 0.7) & (level.purities != 1))
    assert np.array_equal(run('a1 == Kali or last == Satya', level),
                          (level.lcoords[:, 0] == 3) | (level.lcoords[:, -1] == 0))
    assert np.array_equal(run('count(Satya) >= 2', level), (level.lcoords == 0).sum(axis=1) >= 2)
    assert np.array_equal(run('abs(dharma - 0.5) < 0.1', level), np.abs(level.dharmas - 0.5) < 0.1)
    assert np.array_equal(run('duration * 1000 > 20', level), level.durations > 0.02)
    assert run('first == Golden', level).sum() == 16                     # the other names of the ages
    assert run('index < 0', level).sum() == 0


@pytest.mark.parametrize('text, problem', [
    ('__import__("os").system("ls")', 'functions'),
    ('dharma.real > 0', 'attribute'),
    ('[dharma][0] > 0', 'subscript'),
    ('dharma if purity else 0', 'ifexp'),
    ('lambda: 0', 'lambda'),
    ('"a" < "b"', 'numbers'),
    ('True', 'numbers'),
    ('dharma >', 'cannot read'),
    ('', 'empty'),
    ('count(Satya, Kali) > 1', 'functions'),
])
def test_what_is_refused(text, problem):
    with pytest.raises(QueryError, match=problem):
        parse(text)


def test_a_number_is_not_a_condition():
    with pytest.raises(QueryError, match='condition'):
        run('dharma + 1', compute_level(2))


# -- in the explorer



@pytest.mark.gui
def test_the_state_evaluates_queries(window):
    state = window.state
    with pytest.raises(QueryError, match='unknown name'):
        state.set_query('karma > 1')
    state.set_query('trend > 0.3   and dharma < 0.5')
    assert state.query == 'trend > 0.3 and dharma < 0.5'                 # spaces tidied
    state.set_highlight('query')
    matches = state.query_matches(4)
    trend, dharma = state.cache.measure(4, 'trend'), state.cache.level(4).dharmas
    assert np.array_equal(matches, (trend > 0.3) & (dharma < 0.5)) and matches.any()
    assert np.array_equal(state.highlighted(4), np.flatnonzero(matches))  # at every depth, without a selection
    state.set_query('a5 == Kali')
    assert not state.query_matches(3).any() and state.query_matches(5).sum() == 4 ** 4   # no fifth digit at 3
    state.set_query('year > 0')
    assert np.all(state.query_matches(2) == (state.time_map.to_physical(state.cache.level(2).starts) > 0))
    model = state.model
    state.set_model(None)
    assert not state.query_matches(2).any() and 'needs a cycle model' in state.query_problem
    state.set_model(model)
    state.set_query('')
    assert state.query_matches(3) is None and state.highlighted(3) is None


@pytest.mark.gui
def test_the_toolbar_and_the_views(window, spin):
    state = window.state
    state.set_focus((3,))
    spin()
    window.query_edit.setText('last == Kali and count(Treta) >= 1')
    window.query_edit.editingFinished.emit()
    spin()
    assert state.highlight == 'query' and window.highlight_box.currentData() == 'query'
    assert 'at depth' in window.query_info.text()
    window.navigator.repaint()                                          # dims every row, not only the selection's
    window.show_panel('measures')
    panel = window.measures_panel
    panel.depth.setValue(3)

    def ringed():
        panel.render()
        return sum(len(a.get_offsets()) for a in panel._highlights if a.get_edgecolor()[0][:3].sum() == 0)

    def matches_in_view():
        return len(set(state.highlighted(3)) & set(panel._indices))

    assert ringed() == matches_in_view() > 0                            # every match in the plot, ringed
    state.set_query('last == Satya')
    spin()
    assert ringed() == matches_in_view() > 0
    window.query_edit.setText('trend >')                                # refused, kept as it was
    window.query_edit.editingFinished.emit()
    spin()
    assert state.query == 'last == Satya' and 'not applied' in window.statusBar().currentMessage()
    window.query_edit.setText('')
    window.query_edit.editingFinished.emit()
    spin()
    assert state.query == '' and state.highlight == 'none'


@pytest.mark.gui
def test_the_query_is_kept_in_sessions(window, spin):
    from cycles.gui import session
    state = window.state
    state.set_query('microcosm > 0.7')
    state.set_highlight('query')
    data = session.capture(window)
    state.set_query('')
    state.set_highlight('none')
    session.apply(window, data)
    spin()
    assert state.query == 'microcosm > 0.7' and state.highlight == 'query'
    assert window.query_edit.text() == 'microcosm > 0.7'
