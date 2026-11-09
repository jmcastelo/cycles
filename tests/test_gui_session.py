"""Research sessions: saving and opening everything the explorer shows, restoring the last one, bookmarks."""

import json

import numpy as np
import pytest

pytestmark = pytest.mark.gui


def _change_everything(window, spin):
    """Move away from the defaults in every part a session keeps."""
    state = window.state
    state.set_model(state.model.replace(anchor_date='3000 BC-01-01', anchor_time='06:00', turns=2.25))
    bases, scales, colors, _ = state.color_parameters
    state.set_color_parameters(bases[:1] + (3,) + bases[2:], scales, colors,     # as the color dialog does
                               ('magma', 'PuOr_r'))
    window.color_box.setCurrentIndex((window.color_box.currentIndex() + 1) % window.color_box.count())
    window.rows_box.setValue(4)
    window.spacing_actions['index'].trigger()
    window.names_actions['Ages'].trigger()
    window.labels_actions['dots'].trigger()
    window.borders_action.trigger()
    window.highlight_box.setCurrentIndex(window.highlight_box.findData('composition'))
    window.criteria_action.setChecked(True)
    state.set_date(-1000.5)
    state.set_sky_time(-2500.25)
    state.set_focus((3, 1))
    state.select((3, 1, 2))
    window.measures_panel.kind.setCurrentIndex(1)
    window.measures_panel.depth.setValue(4)
    window.permutations_panel.preset.setCurrentText('Custom')
    window.permutations_panel.element.setText('2 0 1')
    window.permutations_panel.element.setModified(True)
    window.permutations_panel.element.editingFinished.emit()
    window.skycompare_panel.order.setCurrentIndex(window.skycompare_panel.order.findData('similar'))
    window.landscape_panel.depth.setValue(2)
    window.landscape_panel.turns_to.setValue(4.0)
    window.compositions_panel.view.setCurrentIndex(0)       # Free: the camera is the user's
    window.compositions_panel.restore_camera((20.0, 33.0, 0.0))
    state.set_notes('Testing the sessions.\nSecond line.')
    state.add_bookmark((3, 1, 2), 'here', 'a note')
    state.add_bookmark((0,), 'Satya')
    window.docks['measures'].close()
    spin()


def checked(actions: dict):
    """The key of the checked action of a choice in the View menu."""
    return next(key for key, action in actions.items() if action.isChecked())


def _snapshot(window):
    state = window.state
    return {
        'model': state.model, 'colors': state.color_parameters, 'color_key': state.color_key,
        'rows': state.rows, 'spacing': state.spacing, 'names': state.names, 'labels': state.labels,
        'borders': state.borders, 'highlight': state.highlight, 'criteria': state.compare_criteria,
        'date': state.date, 'sky_time': state.sky_time, 'focus': state.focus, 'selection': state.selection,
        'measures': (window.measures_panel.kind.currentIndex(), window.measures_panel.depth.value()),
        'preset': window.permutations_panel.preset.currentText(), 'permutation': state.permutation,
        'order': window.skycompare_panel.order.currentData(),
        'landscape': (window.landscape_panel.depth.value(), window.landscape_panel.turns_to.value()),
        'camera': window.compositions_panel.camera(), 'notes': state.notes,
        'bookmarks': [dict(b) for b in state.bookmarks],
        'measures_open': not window.docks['measures'].isHidden(),
        'toolbar': (window.rows_box.value(), checked(window.spacing_actions), checked(window.labels_actions),
                    window.borders_action.isChecked(), window.criteria_action.isChecked(),
                    checked(window.names_actions)),
    }


def test_a_session_keeps_everything(window, spin, tmp_path):
    defaults = _snapshot(window)
    _change_everything(window, spin)
    changed = _snapshot(window)
    for key in defaults:
        assert changed[key] != defaults[key], key
    assert window.session.modified and window.isWindowModified()
    path = tmp_path / 'study.cycles.json'
    assert window.session._write(path)
    assert not window.session.modified and window.windowTitle().startswith('study[*]')
    data = json.loads(path.read_text())
    assert data['format'] == 'cycles-session' and data['version'] == 1 and 'commit' in data['code']
    assert data['state']['preset'] is None and data['state']['model']['turns'] == 2.25

    window.session.new()
    spin()
    fresh = _snapshot(window)
    for key in defaults:
        if key not in ('measures_open',):          # New keeps the layout
            assert fresh[key] == defaults[key], key
    assert window.windowTitle().startswith('Untitled session')

    assert window.session.open(path)
    spin()
    restored = _snapshot(window)
    for key in changed:
        assert restored[key] == changed[key], key
    assert not window.session.modified and window.session.recent()[0] == path.resolve()


def _start_again(spin):
    from cycles.gui.app import MainWindow
    again = MainWindow()
    again.resize(1400, 850)
    again.show()
    spin()
    return again


def _answer(monkeypatch, button):
    from PySide6.QtWidgets import QMessageBox
    asked = []

    def question(parent, title, text, *args, **kwargs):
        asked.append(text)
        return button
    monkeypatch.setattr(QMessageBox, 'question', question)
    return asked


def test_the_last_session_comes_back_when_the_explorer_starts(window, spin, tmp_path):
    from cycles.gui.session import autosave_path
    _change_everything(window, spin)
    path = tmp_path / 'kept.cycles.json'
    window.session._write(path)
    saved = _snapshot(window)
    window.close()                                          # nothing unsaved: closes without asking
    assert autosave_path().exists()
    again = _start_again(spin)
    try:
        assert _snapshot(again) == saved
        assert again.session.path == path and not again.session.modified
        assert again.windowTitle().startswith('kept[*]') and not again.isWindowModified()
    finally:
        again.close()
        again.deleteLater()


def test_closing_with_unsaved_changes_asks(window, spin, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from cycles.gui.session import read
    path = tmp_path / 'asked.cycles.json'
    window.session._write(path)
    window.state.set_notes('changed after saving')
    assert window.session.modified
    # Cancel: the window stays open, with its changes
    asked = _answer(monkeypatch, QMessageBox.StandardButton.Cancel)
    window.close()
    spin()
    assert asked and 'asked' in asked[0] and window.isVisible() and window.session.modified
    # Save: the file gets the changes, and the window closes
    _answer(monkeypatch, QMessageBox.StandardButton.Save)
    window.close()
    spin()
    assert not window.isVisible() and read(path)['notes'] == 'changed after saving'


def test_dont_save_reopens_the_session_as_saved(window, spin, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    path = tmp_path / 'discarded.cycles.json'
    window.state.set_notes('kept')
    window.session._write(path)
    window.state.set_notes('thrown away')
    _answer(monkeypatch, QMessageBox.StandardButton.Discard)
    window.close()
    again = _start_again(spin)
    try:
        assert again.state.notes == 'kept' and again.session.path == path and not again.session.modified
    finally:
        _answer(monkeypatch, QMessageBox.StandardButton.Discard)
        again.close()
        again.deleteLater()


def test_dont_save_a_new_session_starts_anew(window, spin, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from cycles.gui.session import autosave_path
    window.state.set_notes('never saved')
    _answer(monkeypatch, QMessageBox.StandardButton.Discard)
    window.close()
    assert not autosave_path().exists()
    again = _start_again(spin)
    try:
        assert again.state.notes == '' and again.session.path is None
    finally:
        again.close()
        again.deleteLater()


def test_after_a_crash_the_unsaved_changes_come_back(window, spin, tmp_path):
    """The session is kept every minute while it has unsaved changes: if the explorer is killed, they are back."""
    path = tmp_path / 'crashed.cycles.json'
    window.session._write(path)
    window.state.set_notes('not saved yet')
    window.session._periodic_save()                         # as the timer does
    again = _start_again(spin)                              # without closing the first window
    try:
        assert again.state.notes == 'not saved yet' and again.session.path == path and again.session.modified
        assert again.isWindowModified()
    finally:
        again.session.modified = False
        again.close()
        again.deleteLater()


def test_bad_files_are_refused_and_change_nothing(window, spin, tmp_path):
    before = _snapshot(window)
    for name, content in (('not-json.json', '{'), ('other.json', json.dumps({'a': 1})),
                          ('newer.json', json.dumps({'format': 'cycles-session', 'version': 99}))):
        path = tmp_path / name
        path.write_text(content)
        assert not window.session.open(path)
        assert 'Cannot open' in window.statusBar().currentMessage()
    assert _snapshot(window) == before and window.session.path is None


def test_parts_that_do_not_fit_are_reported(window, spin, tmp_path):
    from cycles.gui import session
    data = session.capture(window)
    data['state']['selection'] = [3, 7]
    data['ephemeris'] = str(tmp_path / 'nowhere')
    data['state']['rows'] = 3
    problems = session.apply(window, data)
    assert any(p.startswith('selection') for p in problems) and any(p.startswith('ephemeris') for p in problems)
    assert window.state.rows == 3                    # the rest is applied


def test_a_random_sigma_is_kept_as_it_was(window, spin):
    from cycles.gui import session
    panel = window.permutations_panel
    panel.preset.setCurrentText('Random')
    spin()
    panel.render()
    sigma = panel.element.text()
    data = session.capture(window)
    assert data['panels']['permutations_panel']['preset']['text'] == 'Custom'
    panel.preset.setCurrentText('Identity')
    session.apply(window, data)
    assert panel.preset.currentText() == 'Custom' and panel.element.text() == sigma


def test_bookmarks(window, spin):
    state = window.state
    state.set_focus((3,))
    state.select((3, 1, 2))
    spin()
    window.bookmark_selection()                       # Ctrl+B
    spin()
    notes = window.notes_panel
    assert state.bookmarks == [{'address': (3, 1, 2), 'label': '', 'note': ''}]
    assert window.docks['notes'].isVisible() and notes.table.rowCount() == 1
    notes.table.item(0, 0).setText('Kali seed')
    notes.table.item(0, 2).setText('worth a look')
    assert state.bookmarks[0]['label'] == 'Kali seed' and state.bookmarks[0]['note'] == 'worth a look'
    assert 'Kali › Treta › Dvapara' in notes.table.item(0, 1).text()
    assert window.navigator.bookmark_text((3, 1, 2)) == '\n🔖 Kali seed: worth a look'
    state.set_focus(())
    state.select((0,))
    notes.table.selectRow(0)
    notes.go_to_current()
    assert state.selection == (3, 1, 2) and len(state.focus) < 3
    window.navigator.repaint()                         # the flags are drawn
    notes.remove_current()
    assert state.bookmarks == [] and notes.table.rowCount() == 0
    with pytest.raises(ValueError):
        state.add_bookmark((4,))


def test_notes_and_recent_sessions(window, spin, tmp_path):
    window.notes_panel.notes.setPlainText('hello')
    assert window.state.notes == 'hello' and window.session.modified
    for k in range(10):
        window.session._write(tmp_path / f"s{k}.cycles.json")
    recent = window.session.recent()
    assert len(recent) == 8 and recent[0].name == 's9.cycles.json'
    window._fill_recent_menu()
    assert window.recent_menu.actions()[0].text() == 's9.cycles.json'
    (tmp_path / 's8.cycles.json').unlink()
    assert not window.session.open(tmp_path / 's8.cycles.json')
    assert all(p.name != 's8.cycles.json' for p in window.session.recent())


def test_the_study_launcher_passes_the_session(window, spin):
    from pathlib import Path
    from cycles.gui.studies import StudyLauncher
    window.state.set_model(window.state.model.replace(turns=2.25))
    launcher = StudyLauncher(window)
    args = launcher.command(Path('study_of_precession.py'), ['yuga_epochs'])
    assert '--session' in args
    data = json.loads(Path(args[args.index('--session') + 1]).read_text())
    assert data['format'] == 'cycles-session' and data['state']['model']['turns'] == 2.25 and 'layout' not in data
    launcher.with_session.setChecked(False)
    assert '--session' not in launcher.command(Path('study_of_precession.py'), ['yuga_epochs'])
    launcher.close()
