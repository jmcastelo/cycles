"""
Research sessions: everything the explorer shows, kept in a JSON file.

A session holds the cycle model (in full, so that later changes to a preset
do not change it), the color parameters and the display options, the zoom,
the selection, the marked date and the sky moment, the settings of every
panel (with the camera of the 3D views), the window layout, the notes and the
bookmarks, and, for reproducibility, the version of the code (its git
commit) and the ephemeris folder used.

The last session is restored when the explorer starts: it is saved
automatically when the window closes (and every minute while there are
unsaved changes) to ``<settings folder>/<application>-last-session.json``,
with the file it came from, so nothing is lost and nothing is asked on
quitting.
"""

import base64
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QByteArray, QCoreApplication, QObject, QSettings, QTimer
from PySide6.QtWidgets import (
    QAbstractButton, QAbstractSpinBox, QComboBox, QDoubleSpinBox, QFileDialog, QLineEdit, QMessageBox, QSpinBox,
)

from cycles.functions.color import DEFAULT_COLOR_MAPS
from cycles.functions.cycle_model import CycleModel
from cycles.gui.state import NAME_SETS

SESSION_FORMAT = 'cycles-session'
SESSION_VERSION = 1
SUFFIX = '.cycles.json'
FILE_FILTER = f"Cycles sessions (*{SUFFIX});;JSON files (*.json);;All files (*)"
RECENT_KEY = 'sessions/recent'
RECENT_COUNT = 8
AUTOSAVE_SECONDS = 60

# The controls of each panel kept in a session, in the order they are restored (a preset before the text it
# fills, the kind of a plot before its view...)
PANEL_WIDGETS = {
    'date_panel': ('depth',),
    'sky_panel': ('outer', 'follow', 'step', 'step_unit', 'delay'),
    'skycompare_panel': ('kind', 'moment', 'inside', 'order', 'compared', 'charts'),
    'measures_panel': ('kind', 'x_measure', 'y_measure', 'color_by', 'depth', 'inside', 'sized', 'join', 'view'),
    'colorspace_panel': ('plot', 'space', 'depth', 'inside', 'sized', 'cube', 'tetrahedron', 'join', 'view'),
    'permutations_panel': ('view', 'acts', 'depth', 'lines', 'preset', 'element'),
    'compositions_panel': ('depth', 'inside', 'color_by', 'lines', 'labels', 'view'),
    'landscape_panel': ('depth', 'measure', 'resolution', 'anchor_from', 'anchor_to', 'turns_from', 'turns_to'),
    'events_panel': ('kind', 'view', 'depth', 'inside', 'rotations', 'show_marks'),
    'dynamics_panel': ('plot', 'series_box', 'reading', 'surrogate', 'depth', 'inside', 'delay'),
}
CAMERA_PANELS = ('measures_panel', 'colorspace_panel', 'compositions_panel')


def autosave_path() -> Path:
    """Where the last session is kept between runs (next to the settings)."""
    name = QCoreApplication.applicationName() or 'cycles-gui'
    return Path(QSettings().fileName()).parent / f"{name}-last-session.json"


def code_version() -> dict:
    """The version of the program, its git commit and whether it had uncommitted changes (None outside a repository)."""
    from cycles import __version__
    root = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True,
                                timeout=3).stdout.strip()
        dirty = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=root,
                               capture_output=True, text=True, timeout=3).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return {'version': __version__, 'commit': None, 'modified': None}
    return {'version': __version__, 'commit': commit or None, 'modified': bool(dirty) if commit else None}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


# -- widgets

def widget_value(widget):
    if isinstance(widget, QComboBox):
        data = widget.currentData()
        return {'data': data if isinstance(data, (str, int, float, bool)) else None, 'text': widget.currentText()}
    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
        return widget.value()
    if isinstance(widget, QAbstractButton):
        return widget.isChecked()
    if isinstance(widget, QLineEdit):
        return widget.text()
    raise TypeError(f"cannot keep a {type(widget).__name__}")


def set_widget_value(widget, value) -> None:
    """Set a control as a user would (so that its panel reacts); values that do not fit are ignored."""
    if isinstance(widget, QComboBox):
        index = -1
        if isinstance(value, dict):
            if value.get('data') is not None:
                index = widget.findData(value['data'])
            if index < 0:
                index = widget.findText(value.get('text', ''))
        if index >= 0:
            widget.setCurrentIndex(index)
    elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            widget.setValue(int(round(value)) if isinstance(widget, QSpinBox) else float(value))
    elif isinstance(widget, QAbstractButton):
        if isinstance(value, bool):
            widget.setChecked(value)
    elif isinstance(widget, QLineEdit):
        if isinstance(value, str) and widget.text() != value:
            widget.setText(value)
            widget.setModified(True)
            widget.editingFinished.emit()


def _bytes(data: QByteArray) -> str:
    return base64.b64encode(bytes(data)).decode('ascii')


def _from_bytes(text: str) -> QByteArray:
    return QByteArray(base64.b64decode(text.encode('ascii')))


def _address(value) -> tuple | None:
    if value is None:
        return None
    address = tuple(int(d) for d in value)
    if any(d not in (0, 1, 2, 3) for d in address):
        raise ValueError(f"not an address: {value}")
    return address


# -- capturing and applying

def capture(window, layout: bool = True) -> dict:
    """Everything the window shows, as a JSON-ready dict."""
    from cycles.gui.app import LAYOUT_VERSION
    state = window.state
    model = state.model
    bases, scales, colors, maps = state.color_parameters
    names = next((key for key, value in NAME_SETS.items() if tuple(value) == tuple(state.names)),
                 list(state.names))
    panels = {}
    for panel_name, widget_names in PANEL_WIDGETS.items():
        panel = getattr(window, panel_name)
        values = {name: widget_value(getattr(panel, name)) for name in widget_names}
        if panel_name == 'permutations_panel':
            if values['preset']['text'] == 'Random':
                # a new random σ is drawn every time: keep the one shown
                values['preset'] = {'data': None, 'text': 'Custom'}
            elif values['preset']['text'] != 'Custom':
                del values['element']          # the preset gives σ
        panels[panel_name] = values
    ephemeris = getattr(window.sky_panel, 'ephemeris_path', None)
    data = {
        'format': SESSION_FORMAT,
        'version': SESSION_VERSION,
        'saved': now(),
        'code': code_version(),
        'state': {
            'model': model.to_dict() if model is not None else None,
            'preset': model.name if model is not None and state.presets.get(model.name) == model else None,
            'color_parameters': {'bases': list(bases), 'scales': list(scales), 'colors': [list(c) for c in colors],
                                 'maps': {'sequential': maps[0], 'diverging': maps[1]}},
            'color_key': state.color_key,
            'spacing': state.spacing,
            'names': names,
            'labels': state.labels,
            'borders': state.borders,
            'highlight': state.highlight,
            'query': state.query,
            'compare_criteria': state.compare_criteria,
            'date': state.date,
            'sky_time': state.sky_time,
            'focus': list(state.focus),
            'window': list(state.window),
            'row_height': window.navigator.row_height,
            'follow_zoom': window.navigator.follow_zoom,
            'rows_offset': window.navigator.scroll_offset(),
            'selection': list(state.selection) if state.selection is not None else None,
        },
        'panels': panels,
        'cameras': {name: getattr(window, name).camera() for name in CAMERA_PANELS},
        'notes': state.notes,
        'bookmarks': [{'address': list(b['address']), 'label': b['label'], 'note': b['note']}
                      for b in state.bookmarks],
        'ephemeris': str(ephemeris) if ephemeris else None,
    }
    if layout:
        data['layout'] = {'version': LAYOUT_VERSION, 'geometry': _bytes(window.saveGeometry()),
                          'state': _bytes(window.saveState(LAYOUT_VERSION)),                  # the toolbar
                          'docks': _bytes(window.dock_manager.saveState(LAYOUT_VERSION))}     # the panels
    return data


def apply(window, data: dict, layout: bool = True) -> list[str]:
    """
    Show the session ``data`` in ``window``. Raises ``ValueError`` if it is not
    a session this version can read; returns the problems with parts of it
    (which are left as they were).
    """
    from cycles.gui.app import LAYOUT_VERSION
    if not isinstance(data, dict) or data.get('format') != SESSION_FORMAT:
        raise ValueError('not a cycles session file')
    if int(data.get('version', 0)) > SESSION_VERSION:
        raise ValueError(f"the session was saved by a newer version (format {data['version']}); "
                         f"this one reads up to {SESSION_VERSION}")
    state = window.state
    problems = []

    def attempt(what, action):
        try:
            action()
        except (ValueError, TypeError, KeyError, IndexError) as error:
            problems.append(f"{what}: {error}")

    saved = data.get('state', {})
    if 'model' in saved:
        attempt('cycle model', lambda: state.set_model(
            CycleModel.from_dict(saved['model']) if saved['model'] is not None else None))
    if 'color_parameters' in saved:
        c = saved['color_parameters']
        maps = c.get('maps') or {}
        attempt('color parameters', lambda: state.set_color_parameters(
            c['bases'], c['scales'], c['colors'],
            (maps.get('sequential', DEFAULT_COLOR_MAPS[0]), maps.get('diverging', DEFAULT_COLOR_MAPS[1]))))
    if 'names' in saved:
        names = saved['names']
        attempt('names', lambda: state.set_names(tuple(NAME_SETS[names] if isinstance(names, str) else names)))
    if saved.get('query'):
        attempt('query', lambda: state.set_query(saved['query']))
    for key in ('color_key', 'spacing', 'labels', 'borders', 'highlight', 'compare_criteria'):
        if key in saved:
            attempt(key.replace('_', ' '), lambda key=key: getattr(state, f"set_{key}")(saved[key]))
    if 'date' in saved:
        attempt('marked date', lambda: state.set_date(saved['date']))
    if 'sky_time' in saved:
        attempt('sky moment', lambda: state.set_sky_time(saved['sky_time']))

    ephemeris = data.get('ephemeris')
    current = getattr(window.sky_panel, 'ephemeris_path', None)
    if ephemeris and (current is None or Path(ephemeris) != Path(current)):
        if Path(ephemeris).is_dir():
            attempt('ephemeris', lambda: window.sky_panel.load_ephemeris(ephemeris))
        else:
            problems.append(f"ephemeris: {ephemeris} is not on this computer; kept {current or 'none'}")

    for panel_name, values in data.get('panels', {}).items():
        panel = getattr(window, panel_name, None)
        if panel is None or panel_name not in PANEL_WIDGETS:
            continue
        for name in PANEL_WIDGETS[panel_name]:
            if name in values:
                attempt(f"{panel_name.replace('_panel', '')} {name}",
                        lambda panel=panel, name=name: set_widget_value(getattr(panel, name), values[name]))

    if 'focus' in saved:
        attempt('zoom', lambda: state.set_focus(_address(saved['focus']) or (), animate=False))
    if 'row_height' in saved or 'follow_zoom' in saved:             # the rows of the navigator
        def rows():
            navigator = window.navigator
            height = saved.get('row_height')
            navigator.row_height = None if height is None else min(max(float(height), 10.0), 300.0)
            navigator.follow_zoom = bool(saved.get('follow_zoom', True))
            navigator._offset = float(saved.get('rows_offset', 0.0))
            navigator._sync_vscroll()
            navigator.update()
            navigator.rowsChanged.emit()
        attempt('rows', rows)
    if isinstance(saved.get('window'), list) and len(saved['window']) == 2:     # the window in view (older sessions: the zoom)
        attempt('zoom', lambda: state.set_window(*(float(x) for x in saved['window'])))
    if 'selection' in saved:
        attempt('selection', lambda: state.select(_address(saved['selection'])))
    if 'notes' in data:
        attempt('notes', lambda: state.set_notes(str(data['notes'])))
    if 'bookmarks' in data:
        attempt('bookmarks', lambda: state.set_bookmarks(data['bookmarks']))

    saved_layout = data.get('layout')
    if layout and saved_layout:
        if saved_layout.get('version') == LAYOUT_VERSION and saved_layout.get('docks'):
            window.restoreGeometry(_from_bytes(saved_layout['geometry']))
            window.restoreState(_from_bytes(saved_layout['state']), LAYOUT_VERSION)
            if not window.dock_manager.restoreState(_from_bytes(saved_layout['docks']), LAYOUT_VERSION):
                problems.append('layout: could not be restored')
        else:
            problems.append('layout: saved for another set of panels; kept the current one')
    for name, camera in data.get('cameras', {}).items():
        if name in CAMERA_PANELS:              # also no camera (a panel never drawn): forget the one there is
            attempt(f"camera of {name.replace('_panel', '')}", lambda name=name, camera=camera:
                    getattr(window, name).restore_camera(camera))
    window._sync_toolbar()
    return problems


def read(path) -> dict:
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def write(data: dict, path) -> None:
    """Write atomically (a half-written session never replaces a good one)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.part')
    with open(temporary, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    temporary.replace(path)


class SessionManager(QObject):
    """The session of a main window: its file, unsaved changes, recent files and the automatic save."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.path: Path | None = None
        self.created: str | None = None
        self.modified = False
        self._applying = False
        self.defaults = capture(window, layout=False)       # for New session
        self._watch()
        self.timer = QTimer(self)
        self.timer.setInterval(AUTOSAVE_SECONDS * 1000)
        self.timer.timeout.connect(self._periodic_save)
        self.timer.start()
        self.update_title()

    # -- unsaved changes

    def _watch(self) -> None:
        state = self.window.state
        for signal in (state.focusChanged, state.selectionChanged, state.viewChanged, state.modelChanged,
                       state.colorParametersChanged, state.dateChanged, state.skyTimeChanged,
                       state.permutationChanged, state.bookmarksChanged, state.notesChanged,
                       self.window.navigator.rowsChanged):
            signal.connect(self.mark_modified)
        for panel_name, widget_names in PANEL_WIDGETS.items():
            panel = getattr(self.window, panel_name)
            for name in widget_names:
                widget = getattr(panel, name)
                if isinstance(widget, QComboBox):
                    widget.currentIndexChanged.connect(self.mark_modified)
                elif isinstance(widget, QAbstractSpinBox):
                    widget.valueChanged.connect(self.mark_modified)
                elif isinstance(widget, QAbstractButton):
                    widget.toggled.connect(self.mark_modified)
                elif isinstance(widget, QLineEdit):
                    widget.editingFinished.connect(self.mark_modified)
        manager = self.window.dock_manager                # a panel moved, opened, closed, floated or pinned
        for signal in (manager.dockAreasAdded, manager.dockAreasRemoved, manager.floatingWidgetCreated,
                       manager.autoHideWidgetCreated, manager.perspectiveOpened):
            signal.connect(self.mark_modified)
        for dock in self.window.docks.values():
            dock.viewToggled.connect(self.mark_modified)
            dock.topLevelChanged.connect(self.mark_modified)

    def mark_modified(self, *_) -> None:
        if not self._applying and not self.modified:
            self.modified = True
            self.update_title()

    def name(self) -> str:
        if self.path is None:
            return 'Untitled session'
        name = self.path.name
        return name[:-len(SUFFIX)] if name.endswith(SUFFIX) else self.path.stem

    def update_title(self) -> None:
        from cycles import __version__
        self.window.setWindowTitle(f"{self.name()}[*] — Cycles explorer {__version__}")
        self.window.setWindowModified(self.modified)

    # -- applying

    def _apply(self, data: dict, layout: bool = True) -> list[str]:
        self._applying = True
        try:
            return apply(self.window, data, layout)
        finally:
            self._applying = False

    def _report(self, problems: list[str], what: str) -> None:
        if problems:
            self.window.statusBar().showMessage(f"{what}, except: " + '; '.join(problems), 15000)
        else:
            self.window.statusBar().showMessage(what, 5000)

    def capture(self) -> dict:
        data = capture(self.window)
        data['created'] = self.created or data['saved']
        return data

    # -- files

    def new(self) -> None:
        """Back to the default state (the layout stays as it is)."""
        self._apply(self.defaults, layout=False)
        self.window.state.set_bookmarks([])
        self.window.state.set_notes('')
        self.path, self.created, self.modified = None, None, False
        self.update_title()
        self.window.statusBar().showMessage('New session', 5000)

    def open(self, path=None) -> bool:
        if path is None:
            start = str(self.path.parent if self.path else Path.home())
            path, _ = QFileDialog.getOpenFileName(self.window, 'Open session', start, FILE_FILTER)
            if not path:
                return False
        path = Path(path)
        try:
            data = read(path)
            problems = self._apply(data)
        except (OSError, ValueError) as error:          # json errors are ValueErrors
            self.window.statusBar().showMessage(f"Cannot open {path.name}: {error}", 15000)
            self._forget_recent(path)
            return False
        self.path, self.created, self.modified = path, data.get('created'), False
        self._add_recent(path)
        self.update_title()
        self._report(problems, f"Opened {path.name}")
        return True

    def save(self) -> bool:
        if self.path is None:
            return self.save_as()
        return self._write(self.path)

    def save_as(self) -> bool:
        start = str((self.path or Path.home() / f"session{SUFFIX}"))
        path, _ = QFileDialog.getSaveFileName(self.window, 'Save session', start, FILE_FILTER)
        if not path:
            return False
        path = Path(path)
        if not path.name.endswith('.json'):
            path = path.with_name(path.name + SUFFIX)
        return self._write(path)

    def _write(self, path: Path) -> bool:
        data = self.capture()
        try:
            write(data, path)
        except OSError as error:
            self.window.statusBar().showMessage(f"Cannot save {path}: {error}", 15000)
            return False
        self.path, self.created, self.modified = path, data['created'], False
        self._add_recent(path)
        self.update_title()
        self.window.statusBar().showMessage(f"Saved {path.name}", 5000)
        return True

    # -- recent files

    def recent(self) -> list[Path]:
        values = QSettings().value(RECENT_KEY) or []
        if isinstance(values, str):
            values = [values]
        return [Path(v) for v in values]

    def _set_recent(self, paths: list[Path]) -> None:
        QSettings().setValue(RECENT_KEY, [str(p) for p in paths[:RECENT_COUNT]])

    def _add_recent(self, path: Path) -> None:
        path = path.resolve()
        self._set_recent([path] + [p for p in self.recent() if p != path])

    def _forget_recent(self, path: Path) -> None:
        self._set_recent([p for p in self.recent() if p != path.resolve()])

    def clear_recent(self) -> None:
        self._set_recent([])

    # -- closing

    def confirm_close(self) -> bool:
        """
        Whether the window may close. With unsaved changes, ask: Save (to the session's file, or a new one;
        cancelling that dialog cancels the closing), Don't save (the next run then reopens the session as it
        was last saved, or a new one if it never was), or Cancel. Then keep what the next run will reopen.
        """
        if not self.modified:
            self.autosave()
            return True
        answer = QMessageBox.question(
            self.window, 'Unsaved changes',
            f"The session “{self.name()}” has changes that are not saved.\nSave them before closing?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Save)
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            if not self.save():
                return False
            self.autosave()
            return True
        self.forget_changes()
        return True

    def forget_changes(self) -> None:
        """The changes are not kept: the next run reopens the session's file as saved, or starts anew."""
        path = autosave_path()
        try:
            if self.path is not None and self.path.exists():
                data = read(self.path)
                data['session_path'] = str(self.path)
                data['session_modified'] = False
                write(data, path)
            else:
                path.unlink(missing_ok=True)
        except (OSError, ValueError):
            path.unlink(missing_ok=True)

    # -- between runs

    def autosave(self) -> None:
        """Keep the session (with its file and unsaved changes) for the next run."""
        data = self.capture()
        data['session_path'] = str(self.path) if self.path else None
        data['session_modified'] = self.modified
        try:
            write(data, autosave_path())
        except OSError:
            pass

    def _periodic_save(self) -> None:
        if self.modified:
            self.autosave()

    def restore_last(self) -> bool:
        """Show the session of the last run, if there is one."""
        path = autosave_path()
        if not path.exists():
            return False
        try:
            data = read(path)
            problems = self._apply(data)
        except (OSError, ValueError) as error:
            self.window.statusBar().showMessage(f"Could not restore the last session: {error}", 15000)
            return False
        session_path = data.get('session_path')
        self.path = Path(session_path) if session_path else None
        self.created = data.get('created')
        self.modified = bool(data.get('session_modified'))
        self.update_title()
        self._report(problems, 'Restored the last session')
        return True
