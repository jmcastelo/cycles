"""
Color parameters dialog: the bases, scales and tetrahedron colors of the colorings and measures,
within the ranges that keep the colors of each level unique, with a check of
how many colors are different, and how many a display can show apart.
"""

import html

import numpy as np
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QColorDialog, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from cycles.functions.color import (
    DEFAULT_COLOR_MAPS, DIVERGING_MAPS, MAX_TETRAHEDRON_VOLUME, SEQUENTIAL_MAPS, color_parameter_problems,
    tetrahedron_volume,
)
from cycles.functions.division import (
    LEVEL_COLOR_KEYS, DEFAULT_BASES, DEFAULT_SCALES, TETRAHEDRON_COLORS, compute_level, level_colors,
)
from cycles.gui.navigator import rgb_to_qcolor, text_color
from cycles.gui.state import CycleState

# Colorings that are not meant to give every subcycle its own color
SHARED_COLORS = {
    'cmyk_composition': 'one color per composition',
    'lrgb': 'the ink of the innermost age',
    'duration_class': 'one color per class of equal duration',
}
CHECK_MAX_DEPTH = 7


def _map_box(maps: dict) -> QComboBox:
    """A choice of color maps, each shown with its gradient."""
    from matplotlib import colormaps
    box = QComboBox()
    box.setIconSize(QSize(64, 12))
    box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    box.setMinimumContentsLength(9)
    for name, label in maps.items():
        rgb = (colormaps[name](np.linspace(0, 1, 64))[:, :3] * 255).astype(np.uint8)
        strip = np.ascontiguousarray(np.repeat(rgb[None], 12, axis=0))
        image = QImage(strip.data, 64, 12, 64 * 3, QImage.Format.Format_RGB888).copy()
        box.addItem(QIcon(QPixmap.fromImage(image)), label, name)
    return box


def _spin(low: float, high: float, step: float, decimals: int = 3) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(low, high)
    spin.setSingleStep(step)
    spin.setDecimals(decimals)
    spin.setKeyboardTracking(False)
    return spin


def _note(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet('color: palette(placeholder-text)')
    return label


class ColorDialog(QDialog):
    """Edit the bases and scales of a ``CycleState``'s colorings and measures."""

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        self.setWindowTitle('Color parameters')
        self.resize(880, 660)
        layout = QHBoxLayout(self)

        form_box = QGroupBox('Parameters')
        form = QFormLayout(form_box)
        self.color_base = _spin(2, 16, 1, 3)
        form.addRow('Color weight base', self.color_base)
        form.addRow(_note('Weights b⁻¹, b⁻², … of the ages of an address, outer levels first, in every CMYK '
                          'coloring and in dharma. At least 2: then the colors are unique. Larger bases keep '
                          'them unique but make the deep levels nearly identical on screen.'))
        self.purity_base = _spin(0.1, 16, 0.5, 3)
        form.addRow('Purity weight base', self.purity_base)
        form.addRow(_note('Weights of the levels in purity (1: all levels weigh the same).'))
        self.cmyk_scale = _spin(0.01, 1, 0.05, 3)
        form.addRow('cmyk_scaled scale', self.cmyk_scale)
        form.addRow(_note('All inks multiplied by it: (0, 1].'))
        self.black_scale = _spin(0, 1, 0.05, 3)
        form.addRow('cmyk_kscaled black scale', self.black_scale)
        form.addRow(_note('Black multiplied by it: [0, 0.25] or [0.5, 1]. In between, the conversion to RGB is '
                          'not one-to-one and uniqueness is not guaranteed.'))
        self.tetra_step = _spin(0.5, 0.99, 0.05, 3)
        form.addRow('Tetrahedron step', self.tetra_step)
        form.addRow(_note('Fraction of the way to the vertex of each age: [0.5, 1). 0.5 fills a Sierpinski '
                          'tetrahedron; larger steps bring deep levels together.'))
        vertices = QHBoxLayout()
        self.vertex_buttons = []
        for k in range(4):
            button = QPushButton()
            button.setToolTip(f"Color of the vertex of {state.names[k]} (click to choose)")
            button.clicked.connect(lambda _=False, k=k: self.choose_vertex(k))
            vertices.addWidget(button)
            self.vertex_buttons.append(button)
        form.addRow('Tetrahedron colors', vertices)
        self.volume = _note('')
        form.addRow(self.volume)
        maps = QHBoxLayout()
        self.sequential_map = _map_box(SEQUENTIAL_MAPS)
        self.sequential_map.setToolTip('For the measures from 0 to 1: dharma, purity, mixture, tension, roughness')
        self.diverging_map = _map_box(DIVERGING_MAPS)
        self.diverging_map.setToolTip('For the signed measures, 0 in the middle: trend, contrast, balance; and the '
                                      'angular density, 1 in the middle')
        maps.addWidget(self.sequential_map)
        maps.addWidget(self.diverging_map)
        form.addRow('Measure color maps', maps)
        form.addRow(_note('Of the colorings of the measures and the Measures panel: sequential, for the measures '
                          'from 0 to 1; diverging, for the signed ones. Changing them only recolors.'))
        self.problems = QLabel()
        self.problems.setWordWrap(True)
        form.addRow(self.problems)
        buttons = QHBoxLayout()
        defaults = QPushButton('Defaults')
        defaults.clicked.connect(lambda: self.load(DEFAULT_BASES, DEFAULT_SCALES, TETRAHEDRON_COLORS,
                                                   DEFAULT_COLOR_MAPS))
        defaults.setToolTip('The default parameters')
        revert = QPushButton('Revert')
        revert.setToolTip('The parameters there were when this window was opened')
        revert.clicked.connect(lambda: self.load(*self._original))
        close = QPushButton('Close')
        close.setDefault(True)
        close.clicked.connect(self.close)
        buttons.addWidget(defaults)
        buttons.addWidget(revert)
        buttons.addStretch(1)
        buttons.addWidget(close)
        form.addRow(buttons)
        layout.addWidget(form_box, 1)

        check_box = QGroupBox('Check')
        check = QVBoxLayout(check_box)
        row = QHBoxLayout()
        row.addWidget(QLabel('Colors of the subcycles of depth'))
        self.depth = QSpinBox()
        self.depth.setRange(1, CHECK_MAX_DEPTH)
        self.depth.setValue(min(5, CHECK_MAX_DEPTH))
        row.addWidget(self.depth)
        row.addStretch(1)
        check.addLayout(row)
        self.table = QTableWidget(len(LEVEL_COLOR_KEYS), 2)
        self.table.setHorizontalHeaderLabels(['Different', 'Apart on screen'])
        self.table.setVerticalHeaderLabels(list(LEVEL_COLOR_KEYS))
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        check.addWidget(self.table, 1)
        check.addWidget(_note('“Apart on screen”: colors still different when rounded to the 256 levels per '
                              'channel of a display. Colorings marked * are not meant to be unique.'))
        layout.addWidget(check_box, 1)

        self.check_timer = QTimer(self)
        self.check_timer.setSingleShot(True)
        self.check_timer.setInterval(300)
        self.check_timer.timeout.connect(self.update_check)
        # Changes are applied as they are made, after a short pause (dragging a value or a color)
        self.apply_timer = QTimer(self)
        self.apply_timer.setSingleShot(True)
        self.apply_timer.setInterval(150)
        self.apply_timer.timeout.connect(self.apply)
        for spin in (self.color_base, self.purity_base, self.cmyk_scale, self.black_scale, self.tetra_step):
            spin.valueChanged.connect(self._changed)
        for box in (self.sequential_map, self.diverging_map):
            box.currentIndexChanged.connect(self._changed)
        self.depth.valueChanged.connect(self._changed)
        self.open_from_state()

    def open_from_state(self) -> None:
        """Show the parameters in use, and remember them for Revert."""
        self._original = self.state.color_parameters
        self.load(*self._original)

    def _fields(self) -> list:
        """The spinboxes, in the order of ``_values``: bases[1], bases[2], scales[0..2]."""
        return [self.color_base, self.purity_base, self.cmyk_scale, self.black_scale, self.tetra_step]

    def load(self, bases, scales, colors=TETRAHEDRON_COLORS, maps=DEFAULT_COLOR_MAPS) -> None:
        # exact values, kept for the fields left unchanged (2/3 is not 0.667)
        self._values = [bases[1], bases[2], *scales]
        self._colors = np.array(colors, dtype=float)
        self._show_vertices()
        self.color_base.setValue(bases[1])
        self.purity_base.setValue(bases[2])
        self.cmyk_scale.setValue(scales[0])
        self.black_scale.setValue(scales[1])
        self.tetra_step.setValue(scales[2])
        for box, name in zip((self.sequential_map, self.diverging_map), maps):
            box.blockSignals(True)
            box.setCurrentIndex(max(0, box.findData(name)))
            box.blockSignals(False)
        self._changed()

    def parameters(self) -> tuple[list, list, np.ndarray, tuple]:
        """``(bases, scales, tetrahedron colors, color maps)`` as set in the dialog."""
        values = [exact if round(exact, spin.decimals()) == spin.value() else spin.value()
                  for spin, exact in zip(self._fields(), self._values)]
        return ([DEFAULT_BASES[0], values[0], values[1]], values[2:], self._colors.copy(),
                (self.sequential_map.currentData(), self.diverging_map.currentData()))

    # -- tetrahedron vertices

    def _show_vertices(self) -> None:
        for k, button in enumerate(self.vertex_buttons):
            color = rgb_to_qcolor(self._colors[k])
            button.setText(f"{self.state.names[k]}\n{color.name()}")
            button.setStyleSheet(f"background-color: {color.name()}; color: {text_color(color).name()}; "
                                 "padding: 4px;")
        volume = tetrahedron_volume(self._colors)
        self.volume.setText(f"Vertices of the tetrahedron coloring, one per age: they must not lie in one plane. "
                            f"Volume {volume:.4f}, {volume / MAX_TETRAHEDRON_VOLUME:.0%} of the largest in the "
                            f"RGB cube (the default); a flatter tetrahedron crowds the colors.")

    def choose_vertex(self, k: int) -> None:
        """Pick the color of a vertex; the plots follow the picker, and Cancel restores the color."""
        previous = self._colors[k].copy()
        picker = QColorDialog(rgb_to_qcolor(previous), self)
        picker.setWindowTitle(f"Tetrahedron color of {self.state.names[k]}")
        picker.currentColorChanged.connect(
            lambda color: self.set_vertex(k, (color.redF(), color.greenF(), color.blueF())))
        if picker.exec() == QDialog.DialogCode.Accepted:
            color = picker.selectedColor()
            self.set_vertex(k, (color.redF(), color.greenF(), color.blueF()))
        else:
            self.set_vertex(k, previous)

    def set_vertex(self, k: int, rgb) -> None:
        self._colors[k] = np.clip(np.asarray(rgb, dtype=float), 0, 1)
        self._show_vertices()
        self._changed()

    def _changed(self, *_) -> None:
        problems = color_parameter_problems(*self.parameters())
        self.problems.setText('' if not problems else
                              "<span style='color:#d62728'>" + html.escape('; '.join(problems)).capitalize()
                              + '. Not applied.</span>')
        self.check_timer.start()
        if problems:
            self.apply_timer.stop()
        else:
            self.apply_timer.start()

    def update_check(self) -> None:
        bases, scales, vertices, _ = self.parameters()
        depth = self.depth.value()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            colors = level_colors(compute_level(depth, bases, scales, vertices))
        finally:
            QApplication.restoreOverrideCursor()
        count = 4 ** depth
        for row, key in enumerate(LEVEL_COLOR_KEYS):
            rgb = np.clip(colors[key], 0, 1)
            different = len(np.unique(np.round(rgb, 10), axis=0))
            on_screen = len(np.unique(np.round(rgb * 255), axis=0))
            label = f"{key} *" if key in SHARED_COLORS else key
            self.table.setVerticalHeaderItem(row, QTableWidgetItem(label))
            items = [QTableWidgetItem(f"{different} of {count}"), QTableWidgetItem(f"{on_screen} of {count}")]
            if key not in SHARED_COLORS and different < count:
                items[0].setForeground(Qt.GlobalColor.red)
            if key in SHARED_COLORS:
                items[0].setToolTip(SHARED_COLORS[key])
            for col, item in enumerate(items):
                self.table.setItem(row, col, item)

    def apply(self) -> None:
        if color_parameter_problems(*self.parameters()):
            return
        try:
            self.state.set_color_parameters(*self.parameters())
        except ValueError as error:
            self.problems.setText(f"<span style='color:#d62728'>{html.escape(str(error))}</span>")
