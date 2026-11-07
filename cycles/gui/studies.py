"""
Study launcher: the studies of the sandbox scripts, run as separate processes
(as on the command line), with their output in a log.

The list comes from the runner itself (``runner.py --catalog``). Studies run
in their own process, which keeps their figure windows, sounds and errors away
from the GUI.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSplitter, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

SANDBOX_DIR = Path(__file__).resolve().parents[2] / 'sandbox'


def study_catalog(sandbox: Path = SANDBOX_DIR) -> dict:
    """
    The studies of the sandbox scripts, from ``sandbox/runner.py --catalog``
    (run in its own process, which imports the scripts without running them):
    ``{script stem: {"doc": ..., "studies": [[name, default, summary], ...]}}``,
    with ``{"error": ...}`` for a script that cannot be imported.
    """
    environment = dict(os.environ, MPLBACKEND='Agg')
    result = subprocess.run([sys.executable, str(sandbox / 'runner.py'), '--catalog'], cwd=sandbox.parent,
                            capture_output=True, text=True, env=environment, timeout=120)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"exit code {result.returncode}")
    return json.loads(result.stdout)


class StudyLauncher(QDialog):
    """Window listing the sandbox studies; check some and run them."""

    def __init__(self, parent=None, sandbox: Path = SANDBOX_DIR):
        super().__init__(parent)
        self.setWindowTitle('Studies')
        self.sandbox = sandbox
        self.process: QProcess | None = None
        self.resize(1000, 640)

        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Study', 'Description'])
        self.tree.setColumnWidth(0, 230)
        self.tree.itemChanged.connect(self._update_run_button)
        self.tree.itemDoubleClicked.connect(self._run_item)
        left_layout.addWidget(self.tree, 1)
        left_layout.addWidget(QLabel('Checked studies run in order, one script at a time; '
                                     'double-click a study to run only it. '
                                     'Initially, each script’s default studies are checked.'))
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        options = QHBoxLayout()
        self.save = QCheckBox('Save figures')
        self.save.setToolTip('--save: write the figures to sandbox/plots and sounds to sandbox/sounds')
        self.show_figures = QCheckBox('Show figures')
        self.show_figures.setChecked(True)
        self.show_figures.setToolTip('Off: --no-show (no windows or sounds; for saving in batch)')
        self.with_session = QCheckBox("With the explorer's session")
        self.with_session.setToolTip('Run the studies with the cycle model and the color parameters shown in '
                                     'the explorer\n(saved for them as a session file; --session)')
        self.with_session.setChecked(True)
        options.addWidget(self.save)
        options.addWidget(self.show_figures)
        options.addWidget(self.with_session)
        options.addStretch(1)
        right_layout.addLayout(options)
        buttons = QHBoxLayout()
        self.run_button = QPushButton('Run checked')
        self.run_button.clicked.connect(self.run_checked)
        self.stop_button = QPushButton('Stop')
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.setEnabled(False)
        plots_button = QPushButton('Open plots folder')
        plots_button.clicked.connect(self.open_plots)
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.stop_button)
        buttons.addStretch(1)
        buttons.addWidget(plots_button)
        right_layout.addLayout(buttons)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont('monospace'))
        self.log.setMaximumBlockCount(20000)
        right_layout.addWidget(self.log, 1)
        splitter.addWidget(right)
        splitter.setSizes([520, 480])
        layout.addWidget(splitter, 1)

        self.queue: list[tuple[Path, list[str]]] = []
        self.populate()

    # -- the list

    def populate(self) -> None:
        self.tree.clear()
        if not self.sandbox.is_dir():
            self.log.setPlainText(f"No sandbox folder at {self.sandbox}: the studies are only available "
                                  "in the source tree (pip install -e).")
            self.run_button.setEnabled(False)
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            catalog = study_catalog(self.sandbox)
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            self.log.setPlainText(f"Cannot list the studies:\n{error}")
            self.run_button.setEnabled(False)
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.tree.blockSignals(True)
        for stem, entry in catalog.items():
            script = self.sandbox / f"{stem}.py"
            parent = QTreeWidgetItem([stem.removeprefix('study_of_').replace('_', ' '),
                                      entry.get('doc') or entry.get('error', '')])
            parent.setData(0, Qt.ItemDataRole.UserRole, str(script))
            parent.setFlags(parent.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
            if 'error' in entry:
                parent.setDisabled(True)
                self._append(f"{script.name} cannot be loaded: {entry['error']}\n")
            for name, default, doc in entry.get('studies', []):
                item = QTreeWidgetItem([name, doc])
                item.setData(0, Qt.ItemDataRole.UserRole, name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Checked if default else Qt.CheckState.Unchecked)
                item.setToolTip(1, doc)
                parent.addChild(item)
            self.tree.addTopLevelItem(parent)
        self.tree.expandAll()
        self.tree.blockSignals(False)
        self._update_run_button()

    def checked(self) -> list[tuple[Path, list[str]]]:
        """Checked studies, grouped by script."""
        runs = []
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            names = [parent.child(k).data(0, Qt.ItemDataRole.UserRole) for k in range(parent.childCount())
                     if parent.child(k).checkState(0) == Qt.CheckState.Checked]
            if names:
                runs.append((Path(parent.data(0, Qt.ItemDataRole.UserRole)), names))
        return runs

    def _update_run_button(self, *_) -> None:
        self.run_button.setEnabled(self.process is None and bool(self.checked()))

    # -- running

    def _run_item(self, item: QTreeWidgetItem, _column: int) -> None:
        parent = item.parent()
        if parent is None or self.process is not None:
            return
        self.queue = [(Path(parent.data(0, Qt.ItemDataRole.UserRole)), [item.data(0, Qt.ItemDataRole.UserRole)])]
        self._next()

    def run_checked(self) -> None:
        if self.process is None:
            self.queue = self.checked()
            self._next()

    def command(self, script: Path, names: list[str]) -> list[str]:
        """Arguments for the Python interpreter that runs ``names`` of ``script``."""
        args = [str(script), *names]
        if self.save.isChecked():
            args.append('--save')
        if not self.show_figures.isChecked():
            args.append('--no-show')
        session = self.session_file()
        if session is not None:
            args += ['--session', str(session)]
        return args

    def session_file(self) -> Path | None:
        """The explorer's session, written for the studies (None if not wanted or not available)."""
        window = self.parent()
        if not self.with_session.isChecked() or not hasattr(window, 'session'):
            return None
        from cycles.gui.session import autosave_path, capture, write
        path = autosave_path().with_name(autosave_path().name.replace('last-session', 'study-session'))
        try:
            write(capture(window, layout=False), path)
        except OSError:
            return None
        return path

    def _next(self) -> None:
        if not self.queue:
            self._finished_all()
            return
        script, names = self.queue.pop(0)
        args = self.command(script, names)
        process = QProcess(self)
        process.setWorkingDirectory(str(self.sandbox.parent))
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert('PYTHONUNBUFFERED', '1')
        process.setProcessEnvironment(environment)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(lambda: self._append(bytes(process.readAll()).decode(errors='replace')))
        process.finished.connect(self._process_finished)
        process.errorOccurred.connect(self._process_error)
        self.process = process
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self._append(f"\n$ python {' '.join(os.path.relpath(a, self.sandbox.parent) if a.endswith('.py') else a for a in args)}\n")
        process.start(sys.executable, args)

    def _append(self, text: str) -> None:
        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(text)
        self.log.moveCursor(QTextCursor.MoveOperation.End)

    def _process_finished(self, code: int, status) -> None:
        if status == QProcess.ExitStatus.CrashExit:
            self._append("[stopped]\n")
            self.queue = []
        elif code:
            self._append(f"[exit code {code}]\n")
        self.process = None
        self._next()

    def _process_error(self, error) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._append(f"[could not start {sys.executable}]\n")
            self.process = None
            self.queue = []
            self._finished_all()

    def _finished_all(self) -> None:
        self.stop_button.setEnabled(False)
        self._update_run_button()

    def stop(self) -> None:
        self.queue = []
        if self.process is not None:
            self.process.kill()

    def open_plots(self) -> None:
        folder = self.sandbox / 'plots'
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def closeEvent(self, event) -> None:
        self.stop()
        if self.process is not None:
            self.process.waitForFinished(2000)
        super().closeEvent(event)
