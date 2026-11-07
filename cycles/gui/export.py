"""
Saving the graphs of the GUI (the navigator and the Matplotlib panels) to a
file: on a paper format (A5 … A1, Letter, Legal, Tabloid) or a custom size,
with margins, an optional title, a resolution for the raster formats, and a
white or transparent background.

The Matplotlib graphs are saved from the panel's own figure, resized for the
page and laid out again, so that they keep everything shown on screen (the
view angles of the 3D plots, the selection and the moment). The navigator is
painted at the size of the page by a copy of it with a light palette, as
vectors in PDF and SVG.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QMarginsF, QPoint, QRect, QRectF, QSettings, QSize, QSizeF, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QImage, QPageSize, QPainter, QPalette, QPdfWriter
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

# Paper formats, portrait (width, height) in millimetres
PAPER_SIZES = {
    'A5': (148.0, 210.0),
    'A4': (210.0, 297.0),
    'A3': (297.0, 420.0),
    'A2': (420.0, 594.0),
    'A1': (594.0, 841.0),
    'Letter': (215.9, 279.4),
    'Legal': (215.9, 355.6),
    'Tabloid': (279.4, 431.8),
}
SCREEN = 'As on screen'
CUSTOM = 'Custom'
UNITS = {'mm': 25.4, 'cm': 2.54, 'in': 1.0}         # per inch
FORMATS = {
    'png': 'PNG image',
    'jpg': 'JPEG image',
    'pdf': 'PDF document',
    'svg': 'SVG drawing',
    'eps': 'EPS (PostScript)',
}
VECTOR_FORMATS = {'pdf', 'svg', 'eps'}
OPAQUE_FORMATS = {'jpg', 'eps'}                    # no transparent background
WIDGET_FORMATS = ('png', 'jpg', 'pdf', 'svg')
LOGICAL_DPI = 96.0      # layout units of the navigator per inch: as on a screen at 100 %
TITLE_POINTS = 14.0
MIN_CONTENT_INCHES = 0.5


@dataclass(frozen=True)
class ExportOptions:
    path: Path
    width: float            # page, in inches (margins and title included)
    height: float
    dpi: int
    margin: float           # inches
    title: str
    transparent: bool

    @property
    def format(self) -> str:
        return self.path.suffix.lower().lstrip('.')

    def title_height(self) -> float:
        return 2.2 * TITLE_POINTS / 72 if self.title else 0.0

    def content_size(self) -> tuple[float, float]:
        """Inches left for the graph, inside the margins and under the title."""
        return (self.width - 2 * self.margin,
                self.height - 2 * self.margin - self.title_height())


@dataclass
class GraphSource:
    """A graph that can be saved: a Matplotlib figure or a painted widget."""
    key: str
    label: str
    screen_size: Callable[[], tuple[float, float]]      # inches, as shown now
    suggested_title: Callable[[], str]
    save: Callable[[ExportOptions], None]
    formats: tuple = tuple(FORMATS)


# -- saving

def save_figure(figure, options: ExportOptions, relayout: Callable[[], None] | None = None) -> None:
    """
    Save a Matplotlib ``figure`` resized to the content area of the page, laid
    out again by ``relayout`` (if the figure does not do it itself), with the
    margins and the title around it; then give it back its size.
    """
    from matplotlib.transforms import Bbox

    width, height = options.content_size()
    previous = figure.get_size_inches().copy()
    title = None
    try:
        figure.set_size_inches(width, height, forward=False)
        if relayout is not None:
            relayout()
        if options.title:
            # above the figure, in the band the saved area adds over it
            title = figure.text(0.5, 1 + options.title_height() / 2 / height, options.title,
                                ha='center', va='center', fontsize=TITLE_POINTS)
        area = Bbox.from_bounds(-options.margin, -options.margin, options.width, options.height)
        figure.savefig(options.path, format=options.format, dpi=options.dpi, bbox_inches=area,
                       transparent=options.transparent,
                       facecolor='none' if options.transparent else 'white')
    finally:
        if title is not None:
            title.remove()
        figure.set_size_inches(*previous, forward=False)
        if relayout is not None:
            relayout()
        figure.canvas.draw_idle()


def light_palette(transparent: bool) -> QPalette:
    """A light palette for printing, whatever the theme of the screen."""
    palette = QApplication.style().standardPalette()
    if transparent:
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
    else:
        palette.setColor(QPalette.ColorRole.Base, QColor('white'))
    palette.setColor(QPalette.ColorRole.Text, QColor('black'))
    return palette


def save_widget(make_widget: Callable[[], QWidget], options: ExportOptions) -> None:
    """
    Paint a widget made by ``make_widget`` at the content size of the page:
    as an image at the resolution of ``options``, or as vectors in PDF and SVG.
    """
    fmt = options.format
    if fmt not in WIDGET_FORMATS:
        raise ValueError(f"this graph cannot be saved as {fmt.upper()}")
    width, height = options.content_size()
    widget = make_widget()
    widget.setPalette(light_palette(options.transparent))
    widget.resize(QSize(round(width * LOGICAL_DPI), round(height * LOGICAL_DPI)))
    page = QRectF(0, 0, options.width * LOGICAL_DPI, options.height * LOGICAL_DPI)
    offset = QPoint(round(options.margin * LOGICAL_DPI),
                    round((options.margin + options.title_height()) * LOGICAL_DPI))

    def paint(painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        if not options.transparent:
            painter.fillRect(page, QColor('white'))
        if options.title:
            font = QFont(widget.font())
            font.setPointSizeF(TITLE_POINTS)
            painter.setFont(font)
            painter.setPen(QColor('black'))
            band = QRectF(0, options.margin * LOGICAL_DPI, page.width(), options.title_height() * LOGICAL_DPI)
            painter.drawText(band, Qt.AlignmentFlag.AlignCenter, options.title)
        widget.render(painter, offset, renderFlags=QWidget.RenderFlag.DrawChildren)

    try:
        if fmt == 'pdf':
            writer = QPdfWriter(str(options.path))
            writer.setPageSize(QPageSize(QSizeF(options.width * 25.4, options.height * 25.4),
                                         QPageSize.Unit.Millimeter))
            writer.setPageMargins(QMarginsF(0, 0, 0, 0))
            writer.setResolution(round(LOGICAL_DPI))
            if options.title:
                writer.setTitle(options.title)
            painter = QPainter(writer)
            paint(painter)
            painter.end()
        elif fmt == 'svg':
            from PySide6.QtSvg import QSvgGenerator
            generator = QSvgGenerator()
            generator.setFileName(str(options.path))
            size = QSize(round(page.width()), round(page.height()))
            generator.setSize(size)
            generator.setViewBox(QRect(QPoint(0, 0), size))
            generator.setResolution(round(LOGICAL_DPI))
            if options.title:
                generator.setTitle(options.title)
            painter = QPainter(generator)
            paint(painter)
            painter.end()
        else:
            scale = options.dpi / LOGICAL_DPI
            image = QImage(round(options.width * options.dpi), round(options.height * options.dpi),
                           QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            painter.scale(scale, scale)
            paint(painter)
            painter.end()
            if fmt == 'jpg':
                image = image.convertToFormat(QImage.Format.Format_RGB32)
            dots_per_metre = round(options.dpi / 0.0254)
            image.setDotsPerMeterX(dots_per_metre)
            image.setDotsPerMeterY(dots_per_metre)
            if not image.save(str(options.path), None, 95 if fmt == 'jpg' else -1):
                raise OSError(f"cannot write {options.path}")
    finally:
        widget.deleteLater()


# -- dialog

class ExportDialog(QDialog):
    """Choose a graph, a page and a file, and save the graph."""

    def __init__(self, sources: list[GraphSource], current: str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Save graph')
        self.sources = {source.key: source for source in sources}
        settings = QSettings()
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.graph = QComboBox()
        for source in sources:
            self.graph.addItem(source.label, source.key)
        form.addRow('Graph', self.graph)

        self.paper = QComboBox()
        self.paper.addItems([SCREEN, *PAPER_SIZES, CUSTOM])
        self.orientation = QComboBox()
        self.orientation.addItems(['Landscape', 'Portrait'])
        row = QHBoxLayout()
        row.addWidget(self.paper, 1)
        row.addWidget(self.orientation)
        form.addRow('Page', row)

        self.unit = QComboBox()
        self.unit.addItems(list(UNITS))
        self.width = self._length_spin()
        self.height = self._length_spin()
        row = QHBoxLayout()
        row.addWidget(self.width, 1)
        row.addWidget(QLabel('×'))
        row.addWidget(self.height, 1)
        row.addWidget(self.unit)
        form.addRow('Size', row)
        self.margin = self._length_spin(0.0)
        form.addRow('Margins', self.margin)

        self.title_box = QCheckBox()
        self.title = QLineEdit()
        row = QHBoxLayout()
        row.addWidget(self.title_box)
        row.addWidget(self.title, 1)
        form.addRow('Title', row)

        self.format = QComboBox()
        self.dpi = QSpinBox()
        self.dpi.setRange(36, 2400)
        self.dpi.setSingleStep(50)
        self.dpi.setSuffix(' dpi')
        self.dpi.setToolTip('Resolution of PNG and JPEG files (PDF, SVG and EPS are vectors)')
        row = QHBoxLayout()
        row.addWidget(self.format, 1)
        row.addWidget(self.dpi)
        form.addRow('Format', row)
        self.pixels = QLabel()
        self.pixels.setStyleSheet('color: palette(placeholder-text)')
        form.addRow('', self.pixels)

        self.background = QComboBox()
        self.background.addItems(['White', 'Transparent'])
        form.addRow('Background', self.background)

        self.path = QLineEdit()
        browse = QPushButton('Browse…')
        browse.clicked.connect(self.browse)
        row = QHBoxLayout()
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        form.addRow('File', row)
        self.open_after = QCheckBox('Open the file after saving it')
        form.addRow('', self.open_after)

        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save = QPushButton('Save')
        save.setDefault(True)
        save.clicked.connect(self.save)
        close = QPushButton('Close')
        close.clicked.connect(self.close)
        buttons.addWidget(save)
        buttons.addWidget(close)
        layout.addLayout(buttons)

        # remembered choices
        self._inches = (float(settings.value('export/width', 297 / 25.4)),
                        float(settings.value('export/height', 210 / 25.4)))
        self.unit.setCurrentText(str(settings.value('export/unit', 'mm')))
        self._unit = self.unit.currentText()
        self.paper.setCurrentText(str(settings.value('export/paper', 'A4')))
        self.orientation.setCurrentText(str(settings.value('export/orientation', 'Landscape')))
        self.margin.setValue(float(settings.value('export/margin', 10 / 25.4)) * UNITS[self._unit])
        self.dpi.setValue(int(settings.value('export/dpi', 300)))
        self.background.setCurrentText(str(settings.value('export/background', 'White')))
        self.open_after.setChecked(settings.value('export/open', 'false') == 'true')
        self._folder = Path(str(settings.value('export/folder', Path.home())))
        self._format = str(settings.value('export/format', 'png'))

        self.graph.currentIndexChanged.connect(self._graph_changed)
        self.paper.currentIndexChanged.connect(self._page_changed)
        self.orientation.currentIndexChanged.connect(self._page_changed)
        self.unit.currentIndexChanged.connect(self._unit_changed)
        for spin in (self.width, self.height):
            spin.valueChanged.connect(self._size_edited)
        self.margin.valueChanged.connect(self._update_info)
        self.title_box.toggled.connect(self.title.setEnabled)
        self.title_box.toggled.connect(self._update_info)
        self.format.currentIndexChanged.connect(self._format_changed)
        self.dpi.valueChanged.connect(self._update_info)
        self.background.currentIndexChanged.connect(self._update_info)
        self.title.setEnabled(False)
        self._unit_changed()            # decimals of the unit

        index = self.graph.findData(current) if current in self.sources else 0
        self.graph.setCurrentIndex(max(0, index))
        self._graph_changed()
        self._page_changed()

    @staticmethod
    def _length_spin(value: float | None = None) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 5000.0)
        spin.setDecimals(1)
        spin.setKeyboardTracking(False)
        if value is not None:
            spin.setValue(value)
        return spin

    def source(self) -> GraphSource:
        return self.sources[self.graph.currentData()]

    def select(self, key: str) -> None:
        index = self.graph.findData(key)
        if index >= 0:
            self.graph.setCurrentIndex(index)

    # -- reactions

    def _graph_changed(self, *_) -> None:
        source = self.source()
        self.title.setText(source.suggested_title())
        fmt = self.format.currentData() or self._format
        self.format.blockSignals(True)
        self.format.clear()
        for key in source.formats:
            self.format.addItem(f"{FORMATS[key]} (.{key})", key)
        self.format.setCurrentIndex(max(0, self.format.findData(fmt)))
        self.format.blockSignals(False)
        stem = Path(self.path.text()).stem
        folder = Path(self.path.text()).parent if self.path.text() else self._folder
        if not self.path.text() or stem in self.sources:          # the default name of a graph
            self.path.setText(str(folder / f"{source.key}.{self.format.currentData()}"))
        self._format_changed()
        if self.paper.currentText() == SCREEN:
            self._page_changed()

    def _page_changed(self, *_) -> None:
        paper = self.paper.currentText()
        if paper == SCREEN:
            self._inches = self.source().screen_size()
        elif paper in PAPER_SIZES:
            short, long = sorted(PAPER_SIZES[paper])
            landscape = self.orientation.currentText() == 'Landscape'
            self._inches = ((long, short) if landscape else (short, long))
            self._inches = (self._inches[0] / 25.4, self._inches[1] / 25.4)
        self.orientation.setEnabled(paper in PAPER_SIZES)
        self._show_size()

    def _show_size(self) -> None:
        factor = UNITS[self.unit.currentText()]
        for spin, inches in zip((self.width, self.height), self._inches):
            spin.blockSignals(True)
            spin.setValue(inches * factor)
            spin.blockSignals(False)
        self._update_info()

    def _size_edited(self, *_) -> None:
        factor = UNITS[self.unit.currentText()]
        self._inches = (self.width.value() / factor, self.height.value() / factor)
        self.paper.blockSignals(True)
        self.paper.setCurrentText(CUSTOM)
        self.paper.blockSignals(False)
        self.orientation.setEnabled(False)
        self._update_info()

    def _unit_changed(self, *_) -> None:
        unit = self.unit.currentText()
        decimals = {'mm': 1, 'cm': 2, 'in': 2}[unit]
        margin = self.margin.value() / UNITS[self._unit]
        for spin in (self.width, self.height, self.margin):
            spin.setDecimals(decimals)
        self.margin.blockSignals(True)
        self.margin.setValue(margin * UNITS[unit])
        self.margin.blockSignals(False)
        self._unit = unit
        self._show_size()

    def _format_changed(self, *_) -> None:
        fmt = self.format.currentData()
        if fmt is None:
            return
        text = self.path.text()
        if text:
            self.path.setText(str(Path(text).with_suffix('.' + fmt)))
        self.dpi.setEnabled(fmt not in VECTOR_FORMATS)
        self.background.setEnabled(fmt not in OPAQUE_FORMATS)
        self._update_info()

    def options(self) -> ExportOptions:
        fmt = self.format.currentData()
        return ExportOptions(
            path=Path(self.path.text()).expanduser(),
            width=self._inches[0], height=self._inches[1], dpi=self.dpi.value(),
            margin=self.margin.value() / UNITS[self.unit.currentText()],
            title=self.title.text().strip() if self.title_box.isChecked() else '',
            transparent=self.background.currentText() == 'Transparent' and fmt not in OPAQUE_FORMATS)

    def _update_info(self, *_) -> None:
        options = self.options()
        unit = self.unit.currentText()
        factor = UNITS[unit]
        width, height = options.content_size()
        graph = f"graph {width * factor:.4g} × {height * factor:.4g} {unit}"
        if self.format.currentData() in VECTOR_FORMATS:
            self.pixels.setText(f"Vectors; {graph}")
        else:
            pixels = (round(options.width * options.dpi), round(options.height * options.dpi))
            self.pixels.setText(f"{pixels[0]} × {pixels[1]} pixels; {graph}")

    # -- actions

    def browse(self) -> None:
        fmt = self.format.currentData()
        filters = ';;'.join(f"{FORMATS[key]} (*.{key})" for key in self.source().formats)
        path, chosen = QFileDialog.getSaveFileName(self, 'Save graph as', self.path.text(), filters,
                                                   f"{FORMATS[fmt]} (*.{fmt})")
        if not path:
            return
        suffix = Path(path).suffix.lower().lstrip('.')
        if suffix == 'jpeg':
            suffix = 'jpg'
        if suffix not in self.source().formats:
            suffix = chosen.rsplit('*.', 1)[-1].rstrip(')') if chosen else fmt
            path = str(Path(path).with_suffix('.' + suffix))
        self.path.setText(path)
        self.format.setCurrentIndex(self.format.findData(suffix))

    def save(self) -> None:
        options = self.options()
        width, height = options.content_size()
        if min(width, height) < MIN_CONTENT_INCHES:
            self._report('The margins and the title leave too little room for the graph.', error=True)
            return
        if not options.path.name or options.path.suffix.lower().lstrip('.') not in self.source().formats:
            self._report('Choose a file name with one of the extensions of the formats.', error=True)
            return
        if not options.path.parent.is_dir():
            self._report(f"There is no folder {options.path.parent}.", error=True)
            return
        if options.path.exists():
            answer = QMessageBox.question(self, 'Save graph', f"{options.path.name} exists. Replace it?")
            if answer != QMessageBox.StandardButton.Yes:
                return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.source().save(options)
        except Exception as error:          # whatever the writers raise, report it here
            QApplication.restoreOverrideCursor()
            self._report(f"Cannot save {options.path.name}: {error}", error=True)
            return
        QApplication.restoreOverrideCursor()
        self._remember(options)
        self._report(f"Saved {options.path}")
        if self.open_after.isChecked():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(options.path)))

    def _report(self, text: str, error: bool = False) -> None:
        self.status.setText(f"<span style='color:#d62728'>{text}</span>" if error else text)

    def _remember(self, options: ExportOptions) -> None:
        settings = QSettings()
        for key, value in (('width', options.width), ('height', options.height),
                           ('unit', self.unit.currentText()), ('paper', self.paper.currentText()),
                           ('orientation', self.orientation.currentText()), ('margin', options.margin),
                           ('dpi', options.dpi), ('background', self.background.currentText()),
                           ('open', 'true' if self.open_after.isChecked() else 'false'),
                           ('folder', str(options.path.parent)), ('format', options.format)):
            settings.setValue(f"export/{key}", value)
