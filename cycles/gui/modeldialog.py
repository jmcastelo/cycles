"""
Cycle model dialog: choose how the yuga cycle sits in history (anchor, scale,
division, precession), see the resulting cycle at once, and keep the
combinations worth comparing as presets.
"""

import html

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QRadioButton, QScrollArea, QSplitter, QVBoxLayout, QWidget,
)

from cycles.functions.cycle_model import (
    ANCHOR_LABELS, BUILTIN_PRESETS, UJJAIN_LONGITUDE, CycleModel, load_user_presets, mean_rate,
    save_user_presets, USER_PRESETS_FILE,
)
from cycles.gui.state import CycleState, datetime_text, span_text

DIVISION_LABELS = {
    'angle': 'Precession angle, at every level',
    'time': 'Time, at every level',
    'hybrid': 'Angle for the yugas, time inside them',
}
PRECESSION_LABELS = {'long_term': 'Long-term model (varying rate)', 'constant': 'Constant rate'}


def _spin(low: float, high: float, decimals: int, suffix: str = '', step: float = 1.0) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(low, high)
    spin.setDecimals(decimals)
    spin.setSingleStep(step)
    spin.setSuffix(suffix)
    spin.setKeyboardTracking(False)
    return spin


class CycleModelDialog(QDialog):
    """Edit the cycle model of a ``CycleState``."""

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        self.setWindowTitle('Cycle model')
        self.resize(1050, 660)
        self._loading = False

        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel('Preset'))
        self.preset = QComboBox()
        self.preset.activated.connect(self._preset_chosen)
        row.addWidget(self.preset, 1)
        layout.addLayout(row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)

        # Anchor
        anchor = QGroupBox('Anchor: the moment that ties the cycle to history')
        grid = QGridLayout(anchor)
        self.by_date = QRadioButton('Date')
        self.by_ayanamsa = QRadioButton('Ayanamsa')
        group = QButtonGroup(self)
        group.addButton(self.by_date)
        group.addButton(self.by_ayanamsa)
        self.date = QLineEdit()
        self.date.setPlaceholderText('3102 BC-02-18')
        self.date.setToolTip('Julian calendar before 1582, e.g. 3102 BC-02-18 or -3101-02-18')
        self.time = QLineEdit()
        self.time.setPlaceholderText('HH:MM')
        self.time.setMaximumWidth(70)
        self.longitude = _spin(-180, 180, 2, '° E', 0.25)
        self.longitude.setToolTip(f'The time is local mean time at this longitude: 0 for UT, '
                                  f'{UJJAIN_LONGITUDE} for Ujjain')
        self.ayanamsa = _spin(-2700, 2700, 4, '°', 1.0)
        self.ayanamsa.setToolTip('Accumulated ayanamsa (Lahiri at J2000: 23.853°), e.g. a position of the '
                                 'vernal point in the sidereal zodiac, minus whole turns')
        self.point = QComboBox()
        for key, label in ANCHOR_LABELS.items():
            self.point.addItem(label, key)
        grid.addWidget(self.by_date, 0, 0)
        grid.addWidget(self.date, 0, 1)
        grid.addWidget(QLabel('at'), 0, 2)
        grid.addWidget(self.time, 0, 3)
        grid.addWidget(self.longitude, 0, 4)
        grid.addWidget(self.by_ayanamsa, 1, 0)
        grid.addWidget(self.ayanamsa, 1, 1)
        grid.addWidget(QLabel('is the'), 2, 0)
        grid.addWidget(self.point, 2, 1, 1, 2)
        form_layout.addWidget(anchor)

        # Scale
        scale = QGroupBox('Scale: the length of the whole cycle')
        grid = QGridLayout(scale)
        self.by_turns = QRadioButton('Precession arc')
        self.by_years = QRadioButton('Years')
        group = QButtonGroup(self)
        group.addButton(self.by_turns)
        group.addButton(self.by_years)
        self.turns = _spin(0.01, 100, 6, ' turns', 0.25)
        self.years = _spin(1, 5_000_000, 1, ' years', 100)
        grid.addWidget(self.by_turns, 0, 0)
        grid.addWidget(self.turns, 0, 1)
        grid.addWidget(self.by_years, 1, 0)
        grid.addWidget(self.years, 1, 1)
        form_layout.addWidget(scale)

        # Division and precession
        other = QGroupBox('Division and precession')
        form = QFormLayout(other)
        self.division = QComboBox()
        for key, label in DIVISION_LABELS.items():
            self.division.addItem(label, key)
        self.division.setToolTip('What the 4:3:2:1 proportions divide')
        self.precession = QComboBox()
        for key, label in PRECESSION_LABELS.items():
            self.precession.addItem(label, key)
        self.period = _spin(1000, 100000, 1, ' years per turn', 10)
        form.addRow('Divide', self.division)
        form.addRow('Precession', self.precession)
        form.addRow('Period', self.period)
        form_layout.addWidget(other)

        # Name and notes
        notes = QGroupBox('Preset')
        form = QFormLayout(notes)
        self.name = QLineEdit()
        self.description = QPlainTextEdit()
        self.description.setMaximumHeight(90)
        form.addRow('Name', self.name)
        form.addRow('Notes', self.description)
        form_layout.addWidget(notes)
        form_layout.addStretch(1)
        splitter.addWidget(form_widget)

        self.summary = QLabel()
        self.summary.setTextFormat(Qt.TextFormat.RichText)
        self.summary.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.summary.setWordWrap(True)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.summary)
        splitter.addWidget(scroll)
        splitter.setSizes([470, 580])
        layout.addWidget(splitter, 1)

        row = QHBoxLayout()
        self.status = QLabel()
        self.status.setWordWrap(True)
        row.addWidget(self.status, 1)
        self.save_button = QPushButton('Save preset')
        self.save_button.setToolTip(f'Save under the name above, in {USER_PRESETS_FILE}')
        self.save_button.clicked.connect(self.save_preset)
        self.delete_button = QPushButton('Delete preset')
        self.delete_button.clicked.connect(self.delete_preset)
        self.apply_button = QPushButton('Apply')
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(self.apply)
        close = QPushButton('Close')
        close.clicked.connect(self.close)
        for button in (self.save_button, self.delete_button, self.apply_button, close):
            row.addWidget(button)
        layout.addLayout(row)

        self.summary_timer = QTimer(self)
        self.summary_timer.setSingleShot(True)
        self.summary_timer.setInterval(150)
        self.summary_timer.timeout.connect(self.update_summary)
        for widget in (self.date, self.time, self.name):
            widget.textChanged.connect(self._changed)
        for widget in (self.longitude, self.ayanamsa, self.turns, self.years, self.period):
            widget.valueChanged.connect(self._changed)
        for widget in (self.by_date, self.by_ayanamsa, self.by_turns, self.by_years):
            widget.toggled.connect(self._changed)
        for widget in (self.point, self.division, self.precession):
            widget.currentIndexChanged.connect(self._changed)
        self.description.textChanged.connect(self._changed)
        state.presetsChanged.connect(self._fill_presets)

        self._fill_presets()
        self.load(state.model or BUILTIN_PRESETS[next(iter(BUILTIN_PRESETS))])

    # -- presets

    def _fill_presets(self) -> None:
        current = self.preset.currentText()
        self.preset.clear()
        user = load_user_presets()
        for name in self.state.presets:
            self.preset.addItem(f"{name}{'' if name in user else '  (built-in)'}", name)
        index = self.preset.findData(current or (self.state.model.name if self.state.model else ''))
        self.preset.setCurrentIndex(max(0, index))

    def _preset_chosen(self, index: int) -> None:
        self.load(self.state.presets[self.preset.itemData(index)])

    def load(self, model: CycleModel) -> None:
        """Show ``model`` in the form."""
        self._loading = True
        by_date = model.anchor_date is not None
        self.by_date.setChecked(by_date)
        self.by_ayanamsa.setChecked(not by_date)
        self.date.setText(model.anchor_date or '')
        self.time.setText(model.anchor_time)
        self.longitude.setValue(model.anchor_longitude)
        anchor_ayanamsa = model.anchor_ayanamsa
        if anchor_ayanamsa is None:
            try:
                anchor_ayanamsa = float(model.ayanamsa(model.anchor_year()))
            except ValueError:
                anchor_ayanamsa = 0.0
        self.ayanamsa.setValue(anchor_ayanamsa)
        self.point.setCurrentIndex(self.point.findData(model.anchor_point))
        by_turns = model.turns is not None
        self.by_turns.setChecked(by_turns)
        self.by_years.setChecked(not by_turns)
        try:
            solution = model.solve()
            self.turns.setValue(solution['turns'])
            self.years.setValue(solution['years'])
        except ValueError:
            self.turns.setValue(model.turns or 2.5)
            self.years.setValue(model.years or 64430.0)
        self.division.setCurrentIndex(self.division.findData(model.division))
        self.precession.setCurrentIndex(self.precession.findData(model.precession))
        self.period.setValue(model.period)
        self.name.setText(model.name)
        self.description.setPlainText(model.description)
        index = self.preset.findData(model.name)
        if index >= 0:
            self.preset.setCurrentIndex(index)
        self._loading = False
        self._changed()

    def model(self) -> CycleModel:
        """The model in the form (``ValueError`` if it is invalid)."""
        by_date = self.by_date.isChecked()
        by_turns = self.by_turns.isChecked()
        return CycleModel(
            name=self.name.text().strip() or 'Custom',
            anchor_date=self.date.text().strip() if by_date else None,
            anchor_time=self.time.text().strip() or '00:00',
            anchor_longitude=self.longitude.value(),
            anchor_ayanamsa=None if by_date else self.ayanamsa.value(),
            anchor_point=self.point.currentData(),
            turns=self.turns.value() if by_turns else None,
            years=None if by_turns else self.years.value(),
            division=self.division.currentData(),
            precession=self.precession.currentData(),
            period=self.period.value(),
            description=self.description.toPlainText().strip(),
        )

    def _changed(self, *_) -> None:
        by_date = self.by_date.isChecked()
        for widget in (self.date, self.time, self.longitude):
            widget.setEnabled(by_date)
        self.ayanamsa.setEnabled(not by_date)
        self.turns.setEnabled(self.by_turns.isChecked())
        self.years.setEnabled(self.by_years.isChecked())
        self.period.setEnabled(self.precession.currentData() == 'constant')
        if not self._loading:
            self.summary_timer.start()

    # -- summary

    def update_summary(self) -> None:
        try:
            model = self.model()
            solution = model.solve()
            boundaries = model.boundaries()
        except (ValueError, KeyError) as error:
            self.summary.setText(f"<p style='color:#d62728'><b>This model cannot be solved:</b><br>"
                                 f"{html.escape(str(error))}</p>")
            self.apply_button.setEnabled(False)
            self.save_button.setEnabled(False)
            return
        self.apply_button.setEnabled(True)
        self.save_button.setEnabled(True)
        # Show the derived scale in the disabled field
        self._loading = True
        (self.years if self.by_turns.isChecked() else self.turns).setValue(
            solution['years'] if self.by_turns.isChecked() else solution['turns'])
        self._loading = False

        total = solution['years']
        rate = solution['turns'] * 1296000 / total
        names = self.state.names
        rows = []
        ayanamsas = [float(model.ayanamsa(t)) for t in boundaries]
        for k in range(4):
            t0, t1 = boundaries[k], boundaries[k + 1]
            arc = (ayanamsas[k + 1] - ayanamsas[k]) / 360
            rows.append(
                f"<tr><td><b>{names[k]}</b></td><td>{datetime_text(t0)}</td>"
                f"<td align=right>{t1 - t0:,.1f}</td><td align=right>{(t1 - t0) / total:.4f}</td>"
                f"<td align=right>{arc:.4f}</td><td align=right>{arc / solution['turns']:.4f}</td>"
                f"<td align=right>{ayanamsas[k]:.3f}°</td><td align=right>{mean_rate(model, t0, t1):.2f}″</td></tr>")
        rows.append(f"<tr><td><b>End</b></td><td>{datetime_text(boundaries[4])}</td><td></td><td></td><td></td>"
                    f"<td></td><td align=right>{ayanamsas[4]:.3f}°</td><td></td></tr>")
        scope = ('Varying rate (Vondrák et al. 2011).' if model.precession == 'long_term'
                 else f"Constant rate: {1296000 / model.period:.3f}″ per year.")
        warnings = []
        if solution['start'] < -68000 or solution['end'] > 72000:
            warnings.append('The cycle reaches beyond the ephemeris tables (about 68,000 BC to AD 72,000): '
                            'the sky chart will not be available there.')
        self.summary.setText(
            f"<p><b>Anchor:</b> {datetime_text(solution['anchor'])} "
            f"({ANCHOR_LABELS[model.anchor_point]}, ayanamsa {float(model.ayanamsa(solution['anchor'])):.3f}°)"
            f"<br><b>Cycle:</b> {datetime_text(solution['start'])} to {datetime_text(solution['end'])}"
            f"<br><b>Length:</b> {span_text(total)}, {solution['turns']:.6f} turns of precession, "
            f"mean rate {rate:.3f}″ per year<br>{scope}</p>"
            "<table cellspacing=0 cellpadding=3>"
            "<tr><th align=left>Yuga</th><th align=left>Starts (UT)</th><th align=right>Years</th>"
            "<th align=right>Of time</th><th align=right>Turns</th><th align=right>Of arc</th>"
            "<th align=right>Ayanamsa at start</th><th align=right>Mean rate</th></tr>"
            + ''.join(rows) + "</table>"
            "<p>The 4:3:2:1 proportions are 0.4, 0.3, 0.2 and 0.1: the <i>of time</i> and <i>of arc</i> "
            "columns show how closely each criterion holds.</p>"
            + ''.join(f"<p style='color:#d62728'>{html.escape(w)}</p>" for w in warnings))

    # -- actions

    def apply(self) -> None:
        try:
            self.state.set_model(self.model())
        except ValueError as error:
            self.status.setText(f"<span style='color:#d62728'>{html.escape(str(error))}</span>")
            return
        self.status.setText(f"Applied: {html.escape(self.state.model.name)}")

    def save_preset(self) -> None:
        try:
            model = self.model()
            model.solve()
        except ValueError as error:
            self.status.setText(f"<span style='color:#d62728'>{html.escape(str(error))}</span>")
            return
        user = load_user_presets()
        replacing = model.name in user or model.name in BUILTIN_PRESETS
        user[model.name] = model
        save_user_presets(user)
        self.state.reload_presets()
        self.preset.setCurrentIndex(max(0, self.preset.findData(model.name)))
        note = ' (it replaces the one with the same name)' if replacing else ''
        self.status.setText(f"Saved “{html.escape(model.name)}”{note} in {USER_PRESETS_FILE.name}.")

    def delete_preset(self) -> None:
        name = self.preset.currentData()
        user = load_user_presets()
        if name not in user:
            self.status.setText('Built-in presets cannot be deleted (a saved preset with the same name '
                                'replaces one).')
            return
        del user[name]
        save_user_presets(user)
        self.state.reload_presets()
        self.status.setText(f"Deleted “{html.escape(name)}”.")
