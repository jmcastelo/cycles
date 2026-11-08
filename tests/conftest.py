"""
Shared fixtures. The GUI tests run offscreen, each with a new main window and
settings kept in a temporary folder (the user's own settings are not touched).
"""

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('MPLBACKEND', 'Agg')

import pytest  # noqa: E402


@pytest.fixture(scope='session')
def qapp(tmp_path_factory):
    pytest.importorskip('PySide6')
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                      str(tmp_path_factory.mktemp('settings')))
    app = QApplication.instance() or QApplication([])
    app.setOrganizationName('cycles-tests')
    app.setApplicationName('cycles-gui-tests')
    yield app


@pytest.fixture
def spin(qapp):
    """Process pending events (redraws coalesced by timers, signals): ``spin()`` or ``spin(n)``."""
    def process(n: int = 30) -> None:
        for _ in range(n):
            qapp.processEvents()
    return process


@pytest.fixture
def window(qapp, spin, monkeypatch):
    """
    A main window with default settings; questions (e.g. replace a file?) are
    answered yes, and no session of an earlier window is restored. The model
    landscape does not fill in by itself, nor does the Events panel draw by itself (offscreen,
    the panels of hidden tabs count as visible): its tests compute it.
    """
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QMessageBox
    import cycles.gui.landscape as landscape
    from cycles.gui.session import autosave_path
    QSettings().clear()
    autosave_path().unlink(missing_ok=True)            # each window starts without a last session
    monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(landscape, 'FIRST_BATCH_DELAY', 24 * 3600 * 1000)
    import cycles.gui.eventspanel as eventspanel
    monkeypatch.setattr(eventspanel, 'AUTO_RENDER', False)
    from cycles.gui.app import MainWindow
    w = MainWindow()
    w.resize(1400, 850)
    w.show()
    spin()
    yield w
    w.close()
    w.deleteLater()
    spin(5)


@pytest.fixture(scope='session')
def ephemeris():
    """The ephemeris tables, or skip."""
    pytest.importorskip('PySide6')
    from cycles.gui.sky import find_ephemeris
    path = find_ephemeris()
    if path is None:
        pytest.skip('no ephemeris tables')
    return path
