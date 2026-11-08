"""
Subcycle dossier: a PDF about the selected subcycle, on a chosen paper size.

Sections (each can be left out):

* Summary: everything the inspector shows (address, dates, ayanamsa and arc,
  composition, durations, its image under σ, dharma and purity, the measures
  by level, its colors), its bookmarks, and the cycle model and session it
  comes from (with the version of the code);
* Navigator: the subcycle among its siblings, with its parts below;
* Sky: the charts at its start, middle and end (needs the ephemeris);
* Panels: the Measures, Color space, Compositions, Permutations, Sky
  comparison and Model landscape graphs as they are set up in the explorer
  (they show the selection);
* Notes: the notes of the session and all its bookmarks.

Text and the navigator are vectors; the Matplotlib graphs are vectors too, or
images at a chosen resolution (lighter for graphs with many points).
"""

import html
import io
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QByteArray, QMarginsF, QPointF, QRectF, QSettings, QSize, QSizeF, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QImage, QPageSize, QPainter, QPdfWriter, QTextDocument
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from cycles.gui.export import LOGICAL_DPI, PAPER_SIZES, light_palette
from cycles.functions.division import MEASURE_COLOR_KEYS
from cycles.gui.state import COLOR_KEYS, CycleState, date_text, span_text

SECTIONS = {
    'summary': ('Summary', True),
    'navigator': ('Navigator', True),
    'sky': ('Sky at its start, middle and end', True),
    'measures': ('Measures panel', True),
    'colorspace': ('Color space panel', True),
    'compositions': ('Compositions panel', True),
    'permutations': ('Permutations panel', False),
    'skycompare': ('Sky comparison panel', False),
    'landscape': ('Model landscape panel', False),
    'events': ('Events panel', False),
    'notes': ('Notes and bookmarks of the session', True),
}
PANELS = {'measures': 'measures_panel', 'colorspace': 'colorspace_panel', 'compositions': 'compositions_panel',
          'permutations': 'permutations_panel', 'skycompare': 'skycompare_panel', 'landscape': 'landscape_panel',
          'events': 'events_panel'}
# Largest height / width of each graph on the page (it is laid out again at that size)
ASPECTS = {'measures': 0.8, 'colorspace': 1.0, 'compositions': 1.0, 'permutations': 0.7, 'skycompare': 1.25,
           'landscape': 0.85, 'events': 0.6}
SETTINGS = 'dossier'
BODY_POINTS = 9.0
HEADER_POINTS = 8.0
HEADING_POINTS = 13.0


@dataclass
class DossierOptions:
    path: Path
    paper: str = 'A4'
    landscape: bool = False
    margin_mm: float = 15.0
    vector: bool = True                    # Matplotlib graphs as vectors, or images at ``dpi``
    dpi: int = 200
    sections: tuple = tuple(key for key, (_, on) in SECTIONS.items() if on)
    extra: dict = field(default_factory=dict)

    def page_mm(self) -> tuple[float, float]:
        width, height = PAPER_SIZES[self.paper]
        return (height, width) if self.landscape else (width, height)


def _points(painter: QPainter, points: float) -> QFont:
    font = QFont(painter.font())
    font.setPointSizeF(points)
    return font


def initials(state: CycleState, address: tuple) -> str:
    return ''.join(state.names[d][0] for d in address)


# -- the summary

def summary_html(window, address: tuple) -> str:
    """The inspector's data about ``address``, its bookmarks, and where it comes from, as HTML."""
    state = window.state
    inspector = window.inspector
    inspector.refresh()
    esc = html.escape
    parts = [f"<h1>{esc(' › '.join(state.names[d] for d in address))}</h1>"]
    rows = []
    for key, value in inspector.fields.items():
        label = inspector.form.labelForField(value)
        if label is None or not inspector.form.isRowVisible(value):
            continue
        rows.append(f"<tr><td class='key'>{esc(label.text())}</td><td>{esc(value.text())}</td></tr>")
    parts.append("<table class='fields' cellspacing=0 cellpadding=1>" + ''.join(rows) + '</table>')

    table = inspector.levels
    headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    body = ''.join('<tr><td>' + str(r + 1) + '</td>' + ''.join(
        f"<td{' align=right' if c else ''}>{esc(table.item(r, c).text() if table.item(r, c) else '')}</td>"
        for c in range(table.columnCount())) + '</tr>' for r in range(table.rowCount()))
    parts.append("<h2>Measures by level</h2><table class='grid' cellspacing=0 cellpadding=2><tr><th>Level</th>"
                 + ''.join(f"<th>{esc(h)}</th>" for h in headers) + '</tr>' + body + '</table>')
    parts.append(f"<p class='note'>{esc(inspector.levels_note.text())}</p>")

    colors = []
    for row, key in enumerate(COLOR_KEYS):
        if key in MEASURE_COLOR_KEYS + ('density', 'gathering') and key != state.color_key:
            continue            # the measures themselves are in the summary
        swatch = inspector.colors.item(row, 0).background().color().name()
        rgb = inspector.colors.item(row, 1).text() if inspector.colors.item(row, 1) else ''
        cmyk = inspector.colors.item(row, 2).text() if inspector.colors.item(row, 2) else ''
        mark = ' (shown)' if key == state.color_key else ''
        colors.append(f"<tr><td bgcolor='{swatch}' width=28>&nbsp;</td><td>{esc(key)}{mark}</td>"
                      f"<td>{esc(rgb)}</td><td>{esc(cmyk)}</td></tr>")
    parts.append("<h2>Colors</h2><table class='grid' cellspacing=0 cellpadding=2><tr><th></th><th>Coloring</th><th>RGB</th><th>CMYK</th></tr>"
                 + ''.join(colors) + '</table>')

    bookmarks = state.bookmarks_of(address)
    if bookmarks:
        parts.append('<h2>Bookmarked</h2>' + ''.join(
            f"<p><b>{esc(b['label'] or 'Bookmark')}</b>{(': ' + esc(b['note'])) if b['note'] else ''}</p>"
            for b in bookmarks))

    model = state.model
    if model is None:
        parts.append('<h2>Time</h2><p>Normalized time (no cycle model).</p>')
    else:
        solution = model.solve()
        anchor = (f"{model.anchor_date} {model.anchor_time} (longitude {model.anchor_longitude:g}°)"
                  if model.anchor_date else f"ayanamsa {model.anchor_ayanamsa:g}°")
        preset = ' (a preset)' if state.presets.get(model.name) == model else ' (modified)' \
            if model.name in state.presets else ''
        parts.append(
            f"<h2>Cycle model: {esc(model.name)}{preset}</h2><table class='fields' cellspacing=0 cellpadding=1>"
            f"<tr><td class='key'>Anchor</td><td>{esc(anchor)}, at the {esc(model.anchor_point)} point</td></tr>"
            f"<tr><td class='key'>Cycle</td><td>{date_text(solution['start'])} to {date_text(solution['end'])}"
            f" ({span_text(solution['years'])}), {solution['turns']:.4g} turns</td></tr>"
            f"<tr><td class='key'>Division</td><td>{esc(model.division)}; precession {esc(model.precession)}"
            + (f" (period {model.period:g} years)" if model.precession == 'constant' else '') + '</td></tr></table>')
    session = getattr(window, 'session', None)
    from cycles.gui.session import code_version
    code = code_version()
    commit = f"version {code['version']}" + (f", commit {code['commit'][:12]}" if code['commit'] else '') + \
        (' with uncommitted changes' if code['modified'] else '')
    parts.append(f"<p class='note'>Session: {esc(session.name() if session else '—')}"
                 f"{' (unsaved changes)' if session and session.modified else ''}. Colors: {esc(state.color_key)}. "
                 f"Code: {esc(commit)}. Made {datetime.now():%d %b %Y %H:%M}.</p>")
    return '\n'.join(parts)


def notes_html(state: CycleState) -> str:
    esc = html.escape
    parts = ['<h1>Notes of the session</h1>']
    parts.append(f"<p style='white-space: pre-wrap'>{esc(state.notes)}</p>" if state.notes.strip()
                 else "<p class='note'>No notes.</p>")
    parts.append('<h2>Bookmarks</h2>')
    if not state.bookmarks:
        parts.append("<p class='note'>No bookmarks.</p>")
    else:
        rows = []
        for b in state.bookmarks:
            where = ' › '.join(state.names[d] for d in b['address'])
            if state.time_map is not None:
                where += f" ({date_text(state.time_map.interval(b['address'])[0])})"
            rows.append(f"<tr><td>{esc(b['label'])}</td><td>{esc(where)}</td><td>{esc(b['note'])}</td></tr>")
        parts.append("<table class='grid' cellspacing=0 cellpadding=2><tr><th>Label</th><th>Subcycle</th><th>Note</th></tr>"
                     + ''.join(rows) + '</table>')
    return '\n'.join(parts)


STYLE = """
h1 { font-size: 15pt; margin-bottom: 4pt; }
h2 { font-size: 11pt; margin-top: 10pt; margin-bottom: 3pt; }
td, th { vertical-align: top; }
td.key { color: #555555; white-space: nowrap; }
table.grid th { background: #eeeeee; text-align: left; }
p.note { color: #555555; }
"""


# -- drawing pages

class DossierWriter:
    """Pages of the dossier on a PDF writer, with a header and a page number."""

    def __init__(self, options: DossierOptions, title: str, footer: str):
        self.options = options
        self.title, self.footer = title, footer
        width_mm, height_mm = options.page_mm()
        self.writer = QPdfWriter(str(options.path))
        self.writer.setPageSize(QPageSize(QSizeF(width_mm, height_mm), QPageSize.Unit.Millimeter))
        self.writer.setPageMargins(QMarginsF(0, 0, 0, 0))
        self.writer.setResolution(round(LOGICAL_DPI))
        self.writer.setTitle(title)
        self.writer.setCreator('Cycles explorer')
        unit = LOGICAL_DPI / 25.4
        self.page = QRectF(0, 0, width_mm * unit, height_mm * unit)
        margin = options.margin_mm * unit
        self.band = 16.0                                     # header and footer, in layout units
        self.content = self.page.adjusted(margin, margin + self.band, -margin, -margin - self.band)
        self.painter = QPainter(self.writer)
        self.painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self.pages = 0
        self._fresh = True                                   # the current page is still empty

    def new_page(self) -> QRectF:
        if self.pages:
            self.writer.newPage()
        self.pages += 1
        self._fresh = False
        painter = self.painter
        painter.fillRect(self.page, QColor('white'))
        painter.setPen(QColor('#666666'))
        painter.setFont(_points(painter, HEADER_POINTS))
        top = QRectF(self.content.left(), self.content.top() - self.band, self.content.width(), self.band - 4)
        painter.drawText(top, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, self.title)
        bottom = QRectF(self.content.left(), self.content.bottom() + 4, self.content.width(), self.band - 4)
        painter.drawText(bottom, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, self.footer)
        painter.drawText(bottom, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop, f"{self.pages}")
        painter.setPen(QColor('black'))
        return QRectF(self.content)

    def heading(self, rect: QRectF, text: str) -> QRectF:
        """Draw a section heading at the top of ``rect``; returns the room left below it."""
        painter = self.painter
        painter.setFont(_points(painter, HEADING_POINTS))
        height = painter.fontMetrics().height() * 1.6
        painter.drawText(QRectF(rect.left(), rect.top(), rect.width(), height),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        return rect.adjusted(0, height, 0, 0)

    def html(self, text: str) -> None:
        """Rich text from the top of a new page, continued on as many pages as it needs."""
        document = QTextDocument()
        document.setDefaultStyleSheet(STYLE)
        font = QFont(self.painter.font())
        font.setPointSizeF(BODY_POINTS)
        document.setDefaultFont(font)
        document.setHtml(text)
        width, height = self.content.width(), self.content.height()
        document.setPageSize(QSizeF(width, height))     # breaks pages between lines
        document.setDocumentMargin(0)
        for k in range(document.pageCount()):
            rect = self.new_page()
            painter = self.painter
            painter.save()
            painter.translate(rect.topLeft() - QPointF(0, k * height))
            document.drawContents(painter, QRectF(0, k * height, width, height))
            painter.restore()

    def panel_figure(self, rect: QRectF, figure, aspect: float, relayout=None) -> None:
        """
        A panel's figure laid out again to fill the width of ``rect`` (and at
        most ``aspect`` times as high), then given back its size on screen.
        """
        previous = figure.get_size_inches().copy()
        width = rect.width() / LOGICAL_DPI
        height = min(rect.height(), rect.width() * aspect) / LOGICAL_DPI
        try:
            figure.set_size_inches(width, height, forward=False)
            if relayout is not None:
                relayout()
            self.figure(rect, figure)
        finally:
            figure.set_size_inches(*previous, forward=False)
            if relayout is not None:
                relayout()
            figure.canvas.draw_idle()

    def figure(self, rect: QRectF, figure) -> None:
        """A Matplotlib figure in ``rect``, keeping its proportions."""
        w_in, h_in = figure.get_size_inches()
        scale = min(rect.width() / w_in, rect.height() / h_in)
        target = QRectF(0, 0, w_in * scale, h_in * scale)
        target.moveCenter(QPointF(rect.center().x(), rect.top() + target.height() / 2))
        buffer = io.BytesIO()
        if self.options.vector:
            figure.savefig(buffer, format='svg', facecolor='white')
            from PySide6.QtSvg import QSvgRenderer
            renderer = QSvgRenderer(QByteArray(buffer.getvalue()))
            renderer.render(self.painter, target)
        else:
            figure.savefig(buffer, format='png', dpi=self.options.dpi, facecolor='white')
            image = QImage.fromData(buffer.getvalue(), 'PNG')
            self.painter.drawImage(target, image)

    def widget(self, rect: QRectF, widget: QWidget) -> None:
        """Paint ``widget`` (sized to ``rect``) as vectors."""
        widget.setPalette(light_palette(False))
        widget.resize(QSize(round(rect.width()), round(rect.height())))
        self.painter.save()
        self.painter.translate(rect.topLeft())
        widget.render(self.painter, QPointF(0, 0).toPoint(), renderFlags=QWidget.RenderFlag.DrawChildren)
        self.painter.restore()

    def finish(self) -> None:
        if not self.pages:
            self.new_page()
        self.painter.end()


def _private_state(state: CycleState, focus: tuple) -> CycleState:
    """A copy of ``state`` zoomed on ``focus``, for drawing without moving the explorer."""
    copy = CycleState(cache=state.cache, presets=state.presets)
    for name in ('model', '_time_map', 'date', 'sky_time', 'follow', 'selection', 'color_key', 'spacing', 'names',
                 'highlight', 'compare_criteria', 'permutation', 'borders', 'labels'):
        setattr(copy, name, getattr(state, name))
    copy.bookmarks = [dict(b) for b in state.bookmarks]
    copy.focus = focus
    copy.rows = max(2, min(state.rows, 4))
    return copy


def write_dossier(window, address: tuple, options: DossierOptions) -> int:
    """Write the dossier of ``address``; returns the number of pages."""
    from matplotlib.figure import Figure
    state = window.state
    names = ' › '.join(state.names[d] for d in address)
    session = getattr(window, 'session', None)
    from cycles import __version__
    footer = f"Dossier of {initials(state, address)}" + (f" · {session.name()}" if session else '') \
        + f" · {datetime.now():%d %b %Y} · Cycles {__version__}"
    out = DossierWriter(options, names, footer)
    sections = set(options.sections)
    try:
        if 'summary' in sections:
            out.html(summary_html(window, address))

        if 'navigator' in sections:
            from cycles.gui.navigator import Navigator
            rect = out.heading(out.new_page(), 'In the cycle')
            focus = address[:-1]
            navigator = Navigator(_private_state(state, focus))
            height = min(rect.height() * 0.5, rect.width() * 0.6)
            out.widget(QRectF(rect.left(), rect.top(), rect.width(), height), navigator)
            if state.time_map is not None:
                t0, t1 = state.time_map.interval(address)
                out.painter.setFont(_points(out.painter, BODY_POINTS))
                out.painter.drawText(QRectF(rect.left(), rect.top() + height + 6, rect.width(), 40),
                                     Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
                                     f"{names}: {date_text(t0)} to {date_text(t1)} ({span_text(t1 - t0)}), "
                                     f"framed in the rows of its depth; its parts are the rows below.")
            navigator.deleteLater()

        tables = getattr(window.sky_panel, 'tables', None)
        if 'sky' in sections and tables and state.time_map is not None:
            from cycles.gui.sky import INNER_BODIES, OUTER_BODIES
            from cycles.plotting.equinoctial_precession import plot_zodiac_with_planets
            import warnings
            rect = out.heading(out.new_page(), 'Sky at its start, middle and end')
            t0, t1 = state.time_map.interval(address)
            bodies = INNER_BODIES + (OUTER_BODIES if window.sky_panel.outer.isChecked() else ())
            wide = rect.width() > rect.height()
            figure = Figure(figsize=(9, 3.4) if wide else (4.2, 11.5))
            for k, (label, year) in enumerate((('Start', t0), ('Middle', (t0 + t1) / 2), ('End', t1))):
                ax = figure.add_subplot(1, 3, k + 1, projection='polar') if wide else \
                    figure.add_subplot(3, 1, k + 1, projection='polar')
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        plot_zodiac_with_planets(year, tables, bodies=bodies, ax=ax, show=False, table=False,
                                                 compact=True, time_scale='UT', epoch_display=(),
                                                 sign_labels='symbol')
                    ax.set_title(f"{label}: {date_text(year)}", fontsize=9, pad=14)
                except ValueError:
                    ax.set_axis_off()
                    ax.set_title(f"{label}: {date_text(year)}\noutside the ephemeris", fontsize=9)
            figure.subplots_adjust(left=0.04, right=0.96, top=0.9 if wide else 0.96, bottom=0.04,
                                   wspace=0.3, hspace=0.3)
            out.figure(rect, figure)

        for key, attribute in PANELS.items():
            if key not in sections:
                continue
            panel = getattr(window, attribute)
            if key == 'landscape':
                panel.finish()
            elif panel._dirty:
                panel.render()
            title = window.docks[key].windowTitle() if key in window.docks else SECTIONS[key][0]
            out.panel_figure(out.heading(out.new_page(), title), panel.figure, ASPECTS[key],
                             panel.fit_charts if key == 'skycompare' else None)

        if 'notes' in sections:
            out.html(notes_html(state))
    finally:
        out.finish()
    return out.pages


# -- the dialog

class DossierDialog(QDialog):
    """Options of the dossier of the selected subcycle, and the file to write."""

    def __init__(self, window, parent=None):
        super().__init__(parent or window)
        self.window_ = window
        self.state = window.state
        self.setWindowTitle('Subcycle dossier')
        layout = QVBoxLayout(self)
        self.subject = QLabel()
        self.subject.setWordWrap(True)
        bold = QFont(self.subject.font())
        bold.setBold(True)
        self.subject.setFont(bold)
        layout.addWidget(self.subject)

        page = QGroupBox('Page')
        form = QFormLayout(page)
        self.paper = QComboBox()
        self.paper.addItems(list(PAPER_SIZES))
        self.orientation = QComboBox()
        self.orientation.addItems(['Portrait', 'Landscape'])
        self.margin = QDoubleSpinBox()
        self.margin.setRange(0, 50)
        self.margin.setSuffix(' mm')
        self.margin.setValue(15)
        form.addRow('Paper', self.paper)
        form.addRow('Orientation', self.orientation)
        form.addRow('Margins', self.margin)
        self.graphs = QComboBox()
        self.graphs.addItem('Vectors (sharp at any zoom)', 'vector')
        self.graphs.addItem('Images (lighter with many points)', 'image')
        self.dpi = QSpinBox()
        self.dpi.setRange(72, 600)
        self.dpi.setSingleStep(50)
        self.dpi.setValue(200)
        self.dpi.setSuffix(' dpi')
        row = QHBoxLayout()
        row.addWidget(self.graphs, 1)
        row.addWidget(self.dpi)
        form.addRow('Graphs', row)
        self.graphs.currentIndexChanged.connect(lambda: self.dpi.setEnabled(self.graphs.currentData() == 'image'))
        layout.addWidget(page)

        contents = QGroupBox('Contents')
        grid = QGridLayout(contents)
        self.sections = {}
        for k, (key, (label, on)) in enumerate(SECTIONS.items()):
            box = QCheckBox(label)
            box.setChecked(on)
            self.sections[key] = box
            grid.addWidget(box, k % 5, k // 5)
        self.sections['sky'].setToolTip('Needs the ephemeris tables (see the Sky panel) and a cycle model')
        self.sections['landscape'].setToolTip('Computes the whole landscape first (a few seconds at depth 2–3)')
        layout.addWidget(contents)

        row = QHBoxLayout()
        self.path = QLineEdit()
        browse = QToolButton()
        browse.setText('…')
        browse.clicked.connect(self.browse)
        row.addWidget(QLabel('File'))
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        layout.addLayout(row)
        self.open_after = QCheckBox('Open it when written')
        self.open_after.setChecked(True)
        layout.addWidget(self.open_after)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.write_button = QPushButton('Write')
        self.write_button.setDefault(True)
        self.write_button.clicked.connect(self.write)
        close = QPushButton('Close')
        close.clicked.connect(self.close)
        buttons.addWidget(self.write_button)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self._load_settings()
        self.state.selectionChanged.connect(self.refresh)
        self.refresh()

    def refresh(self, *_) -> None:
        state = self.state
        address = state.selection
        self.write_button.setEnabled(bool(address))
        sky_possible = bool(getattr(self.window_.sky_panel, 'tables', None)) and state.time_map is not None
        self.sections['sky'].setEnabled(sky_possible)
        if not address:
            self.subject.setText('Select a subcycle first.')
            return
        self.subject.setText('Dossier of ' + ' › '.join(state.names[d] for d in address))
        folder = Path(self.path.text()).parent if self.path.text() else Path(
            QSettings().value(f"{SETTINGS}/folder", str(Path.home())))
        self.path.setText(str(folder / f"dossier-{initials(state, address)}.pdf"))

    def browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, 'Dossier', self.path.text(), 'PDF (*.pdf)')
        if path:
            self.path.setText(path if path.lower().endswith('.pdf') else path + '.pdf')

    def options(self) -> DossierOptions:
        return DossierOptions(
            path=Path(self.path.text()).expanduser(), paper=self.paper.currentText(),
            landscape=self.orientation.currentIndex() == 1, margin_mm=self.margin.value(),
            vector=self.graphs.currentData() == 'vector', dpi=self.dpi.value(),
            sections=tuple(key for key, box in self.sections.items() if box.isChecked() and box.isEnabled()))

    def write(self) -> bool:
        address = self.state.selection
        if not address:
            return False
        options = self.options()
        if not options.sections:
            self.status.setText('Choose something to include.')
            return False
        from PySide6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            options.path.parent.mkdir(parents=True, exist_ok=True)
            pages = write_dossier(self.window_, address, options)
        except (OSError, ValueError) as error:
            self.status.setText(f"<span style='color:#d62728'>Could not write it: {html.escape(str(error))}</span>")
            return False
        finally:
            QApplication.restoreOverrideCursor()
        self._save_settings(options)
        self.status.setText(f"Wrote {pages} page{'s' if pages != 1 else ''} to {html.escape(str(options.path))}")
        if self.open_after.isChecked():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(options.path)))
        return True

    def _load_settings(self) -> None:
        settings = QSettings()
        self.paper.setCurrentText(settings.value(f"{SETTINGS}/paper", 'A4'))
        self.orientation.setCurrentIndex(int(settings.value(f"{SETTINGS}/landscape", 0)))
        self.margin.setValue(float(settings.value(f"{SETTINGS}/margin", 15.0)))
        self.graphs.setCurrentIndex(max(0, self.graphs.findData(settings.value(f"{SETTINGS}/graphs", 'vector'))))
        self.dpi.setValue(int(settings.value(f"{SETTINGS}/dpi", 200)))
        self.dpi.setEnabled(self.graphs.currentData() == 'image')
        chosen = settings.value(f"{SETTINGS}/sections")
        if chosen is not None:
            chosen = [chosen] if isinstance(chosen, str) else list(chosen)
            for key, box in self.sections.items():
                box.setChecked(key in chosen)
        self.open_after.setChecked(settings.value(f"{SETTINGS}/open", 'true') in (True, 'true'))

    def _save_settings(self, options: DossierOptions) -> None:
        settings = QSettings()
        settings.setValue(f"{SETTINGS}/paper", options.paper)
        settings.setValue(f"{SETTINGS}/landscape", int(options.landscape))
        settings.setValue(f"{SETTINGS}/margin", options.margin_mm)
        settings.setValue(f"{SETTINGS}/graphs", 'vector' if options.vector else 'image')
        settings.setValue(f"{SETTINGS}/dpi", options.dpi)
        settings.setValue(f"{SETTINGS}/sections", [k for k, box in self.sections.items() if box.isChecked()])
        settings.setValue(f"{SETTINGS}/folder", str(options.path.parent))
        settings.setValue(f"{SETTINGS}/open", self.open_after.isChecked())
