"""
The cycle navigator: an overview strip of the whole cycle, with the zoomed
part framed, and below it the subdivisions of the zoomed subcycle, one row per
depth, each subcycle drawn in its color and labelled with its name and/or a
column of dots (4, 3, 2, 1 for Satya, Treta, Dvapara, Kali).

Mouse: click selects, double-click zooms in, right-click zooms out; a click on
the overview zooms to that yuga; Shift+click sets the moment of the sky chart.
The tags of the marked date and of the sky moment, in a band under the
rows (above the time axis), can be dragged along the rows (Escape cancels a
drag).
Keys: Left/Right previous/next subcycle, Up parent, Down first part,
Enter zoom into the selection, Backspace/Escape zoom out.
"""

from typing import NamedTuple

import numpy as np
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QSizePolicy, QToolButton, QToolTip, QWidget

from cycles.gui.state import (
    BOOKMARK_COLOR, DATE_COLOR, EVENT_COLOR, MAX_DEPTH, MOMENT_COLOR, SELECTION_COLOR, PERMUTATION_COLOR, CycleState, address_of, children_range, current_year,
    date_text, span_text, tcoord, time_text,
)

LABEL_WIDTH = 44     # left margin, for the depth of each row
AXIS_HEIGHT = 24     # bottom margin, for the time axis
OVERVIEW_HEIGHT = 22  # strip of the whole cycle, at the top
TAG_GAP = 3          # around the band of the marker tags, between the rows and the time axis
ROWS_TOP_GAP = 6     # between the overview and the first row
DENSE_CELL = 2.0     # rows with more subcycles than one per this many pixels are drawn as a strip of pixels
ROW_GAP = 2          # between rows
# the two criteria for dividing the cycle, when the navigator compares them
CRITERIA_COLORS = {'angle': '#8c564b', 'time': '#17becf'}
SELECTION_WIDTH = 2.0      # border of the selected subcycle (and of those that contain the sky moment, with Follow)
PARENT_WIDTH = 1.0         # border of its parents
CURSOR_WIDTH = 1.5         # the lines of the marked date and the sky moment
ZOOM_COLOR = '#404040'     # the frame of the zoomed part on the overview strip
HALO = QColor(255, 255, 255, 210)    # the light edge under borders and cursors, to stand out over any color


class Row(NamedTuple):
    """Where a row of the navigator is drawn: its depth, top and height, the indices of its subcycles in their
    level (start to stop), their left edges and widths (pixels), and whether it is dense (drawn as pixels)."""
    depth: int
    top: float
    height: float
    start: int
    stop: int
    lefts: np.ndarray
    widths: np.ndarray
    dense: bool


def stroke(painter: QPainter, color: QColor, width: float, draw) -> None:
    """Draw (``draw()``) a line or border in ``color`` over a light edge a pixel wider on each side."""
    painter.setPen(QPen(HALO, width + 2))
    draw()
    painter.setPen(QPen(color, width))
    draw()

CRITERIA_NAMES = {'angle': '4:3:2:1 of the precession arc', 'time': '4:3:2:1 of the years'}
CRITERIA_MIN_CELL = 3.0    # mean cell width (px) of the rows where they are compared (finer: zoom in)
CRITERIA_TICK_CELL = 8.0   # ... and where the other boundaries are also drawn as dashed lines
MAX_DOT = 5.0        # diameter of the dots (px): proportional to the cell width, within these
MIN_DOT = 1.5


def rgb_to_qcolor(rgb) -> QColor:
    return QColor.fromRgbF(*(min(1.0, max(0.0, float(c))) for c in rgb))


def text_color(color: QColor) -> QColor:
    """Black or white, whichever reads better on ``color``."""
    luminance = 0.2126 * color.redF() + 0.7152 * color.greenF() + 0.0722 * color.blueF()
    return QColor('black') if luminance > 0.5 else QColor('white')


class Navigator(QWidget):
    """Rows of subcycles below the focus of a ``CycleState``."""

    hovered = Signal(object)   # address under the mouse, or None
    busy = Signal(str)         # message while computing levels ('' when done)

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        self._cells: list[tuple[QRectF, tuple]] = []
        self._tags: dict[str, QRectF] = {}     # 'date' and 'sky': where their tags are drawn
        self._drag: tuple[str, float] | None = None   # marker being dragged, and its year before the drag
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        state.focusChanged.connect(self._changed)
        state.selectionChanged.connect(self.update)
        state.bookmarksChanged.connect(self.update)
        state.eventsChanged.connect(self.update)
        state.viewChanged.connect(self._changed)
        state.dateChanged.connect(self.update)
        state.skyTimeChanged.connect(self.update)
        state.permutationChanged.connect(lambda: self.update() if state.highlight == 'orbit' else None)
        state.colorParametersChanged.connect(
            lambda affected: self._changed() if state.color_key in affected else None)

    def sizeHint(self) -> QSize:
        return QSize(900, 420)

    def _changed(self, *_) -> None:
        """Compute the levels the new view needs (with a wait cursor if slow), then repaint."""
        depths = [d for d in [len(self.state.focus), *self.state.visible_depths()]
                  if d and not self.state.cache.has(d)]
        if depths:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                for depth in depths:
                    self.busy.emit(f"Computing the {4 ** depth} subcycles of depth {depth}…")
                    self.state.cache.level(depth)
            finally:
                self.busy.emit('')
                QApplication.restoreOverrideCursor()
        self.update()

    # -- geometry

    def _rows(self) -> list[int]:
        """Depth of each row: the levels below the zoom."""
        return list(self.state.visible_depths())

    def _overview_rect(self) -> QRectF:
        return QRectF(LABEL_WIDTH, 4, self.width() - LABEL_WIDTH - 8, OVERVIEW_HEIGHT)

    def _tag_height(self) -> float:
        return self.fontMetrics().height() + 2

    def _band_lines(self) -> int:
        """Lines of the tag band: one per marker tag shown (date, sky), as many as the key of the criteria needs."""
        state = self.state
        tags = int(state.date is not None) + int(state.sky_time is not None)
        key = 0
        if state.compare_criteria and state.model is not None:
            key = 2 if state.model.division == 'hybrid' else 1
        return max(1, tags, key)

    def _tag_band(self) -> QRectF:
        """Band between the rows and the time axis, with a line for each marker tag (date, then sky)."""
        height = self._band_lines() * (self._tag_height() + 2)
        bottom = self.height() - AXIS_HEIGHT - TAG_GAP
        return QRectF(LABEL_WIDTH, bottom - height, self.width() - LABEL_WIDTH - 8, height)

    def _layout(self) -> list[tuple[QRectF, tuple, int, int]]:
        """
        Cells to draw one by one: (rectangle, address, depth, index), for the rows whose subcycles are wide
        enough. The geometry of every row is kept in ``self._geometry`` (``Row``); the dense rows (more subcycles
        than about one per ``DENSE_CELL`` pixels) are drawn as a strip of pixels instead.
        """
        state = self.state
        rows = self._rows()
        top = self._overview_rect().bottom() + ROWS_TOP_GAP
        area = QRectF(LABEL_WIDTH, top, self.width() - LABEL_WIDTH - 8, self._tag_band().top() - TAG_GAP - top)
        row_height = area.height() / len(rows)
        focus = state.focus
        if focus:
            level = state.cache.level(len(focus))
            f_start = level.starts[tcoord(focus)]
            f_duration = level.durations[tcoord(focus)]
        else:
            f_start, f_duration = 0.0, 1.0

        cells, self._geometry = [], []
        for r, depth in enumerate(rows):
            top = area.top() + r * row_height
            indices = children_range(focus, depth)
            n = len(indices)
            if state.spacing == 'time' and depth:
                level = state.cache.level(depth)
                lefts = (level.starts[indices.start:indices.stop] - f_start) / f_duration
                widths = level.durations[indices.start:indices.stop] / f_duration
            else:
                lefts = np.arange(n) / n
                widths = np.full(n, 1 / n)
            row = Row(depth, top, row_height - ROW_GAP, indices.start, indices.stop,
                      area.left() + lefts * area.width(), widths * area.width(),
                      n * DENSE_CELL > area.width())
            self._geometry.append(row)
            if not row.dense:
                for k, index in enumerate(indices):
                    rect = QRectF(row.lefts[k], top, row.widths[k], row.height)
                    cells.append((rect, address_of(index, depth), depth, index))
        return cells

    def _row(self, depth: int):
        """The geometry (``Row``) of the row of ``depth``, or None if it is not drawn."""
        return next((row for row in getattr(self, '_geometry', []) if row.depth == depth), None)

    def rect_of(self, address: tuple) -> QRectF | None:
        """Where the subcycle ``address`` is drawn (also in a dense row), or None if it is not in view."""
        row = self._row(len(address))
        if row is None:
            return None
        k = tcoord(address) - row.start
        if not 0 <= k < row.stop - row.start:
            return None
        return QRectF(row.lefts[k], row.top, row.widths[k], row.height)

    def _index_at(self, row, x: float) -> int | None:
        """Index (in its level) of the subcycle of ``row`` at the horizontal position ``x``."""
        rights = row.lefts + row.widths
        if not len(rights) or x < row.lefts[0] or x > rights[-1]:
            return None
        return row.start + int(min(np.searchsorted(rights, x, side='right'), len(rights) - 1))

    def _x_of(self, row, u: float) -> float | None:
        """Horizontal position of the normalized time ``u`` in ``row`` (also with equal widths)."""
        level = self.state.cache.level(row.depth)
        starts = level.starts[row.start:row.stop]
        durations = level.durations[row.start:row.stop]
        k = int(np.searchsorted(starts, u, side='right')) - 1
        if k < 0 or u > starts[-1] + durations[-1] + 1e-12:
            return None
        k = min(k, len(starts) - 1)
        return float(row.lefts[k] + (u - starts[k]) / durations[k] * row.widths[k])

    def cell_at(self, pos: QPointF) -> tuple | None:
        for rect, address in self._cells:
            if rect.contains(pos):
                return address
        for row in getattr(self, '_geometry', []):
            if row.dense and row.top <= pos.y() <= row.top + row.height:
                index = self._index_at(row, pos.x())
                return None if index is None else address_of(index, row.depth)
        return None

    def _draw_dense_row(self, painter: QPainter, row, colors: np.ndarray, mask, dim: QColor) -> None:
        """
        A row of subcycles narrower than a pixel or two, as a strip of pixels: each pixel takes the mean color of
        the subcycles under it, weighted by how much of the pixel each covers. With a highlight, a pixel with
        any bright subcycle shows those (so that no match is lost), and the others are dimmed as the cells are.
        """
        ratio = self.devicePixelRatioF()
        lefts, widths = row.lefts, row.widths
        left, right = float(lefts[0]), float(lefts[-1] + widths[-1])
        pixels = max(1, int(round((right - left) * ratio)))
        edges = left + (right - left) * np.arange(pixels + 1) / pixels
        k = np.minimum(np.searchsorted(lefts + widths, edges, side='right'), len(lefts) - 1)
        covered = np.clip(edges - lefts[k], 0.0, widths[k])

        def integral(values):                   # of values (n, c) over each pixel, as the cells cover it
            cumulative = np.vstack([np.zeros((1, values.shape[1])), np.cumsum(values * widths[:, None], axis=0)])
            at_edges = cumulative[k] + values[k] * covered[:, None]
            return at_edges[1:] - at_edges[:-1]

        rgb = np.clip(np.asarray(colors, dtype=float)[row.start:row.stop], 0, 1)
        pixel = np.diff(edges)[:, None]
        mean = integral(rgb) / pixel
        if mask is not None:
            bright = mask[row.start:row.stop].astype(float)[:, None]
            weight = integral(bright)
            base = np.array([dim.redF(), dim.greenF(), dim.blueF()])
            dimmed = mean * (1 - dim.alphaF()) + base * dim.alphaF()
            with np.errstate(invalid='ignore', divide='ignore'):
                lit = integral(rgb * bright) / weight
            mean = np.where(weight > 1e-12, lit, dimmed)
        data = np.ascontiguousarray((np.clip(mean, 0, 1) * 255 + 0.5).astype(np.uint8)[None])
        image = QImage(data.data, pixels, 1, pixels * 3, QImage.Format.Format_RGB888).copy()
        painter.drawImage(QRectF(left, row.top, right - left, row.height), image)

    # -- painting

    def paintEvent(self, event) -> None:
        state = self.state
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        palette = self.palette()
        painter.fillRect(self.rect(), palette.base())
        cells = self._layout()
        self._cells = [(rect, address) for rect, address, _, _ in cells]

        selection = state.selection
        bright = {}           # depth -> mask of the subcycles kept bright (the highlight), where there is one

        def bright_at(depth: int):
            if depth not in bright:
                indices = state.highlighted(depth)
                if indices is None:
                    bright[depth] = None
                else:
                    mask = np.zeros(4 ** depth, dtype=bool)
                    mask[indices] = True
                    bright[depth] = mask
            return bright[depth]

        font = QFont(self.font())
        metrics = painter.fontMetrics()
        dim = QColor(palette.base().color())
        dim.setAlphaF(0.75)
        border = QPen(QColor(0, 0, 0, 45), 0)    # hairline

        for rect, address, depth, index in cells:
            color = rgb_to_qcolor(state.colors(depth, state.color_key)[index])
            painter.fillRect(rect, color)
            if state.borders and rect.width() >= 3:
                painter.setPen(border)
                painter.drawRect(rect)
            mask = bright_at(depth)
            if mask is not None and not mask[index]:
                painter.fillRect(rect, dim)
                continue
            self._draw_label(painter, metrics, rect, address[-1], text_color(color))
        for row in self._geometry:
            if row.dense:
                self._draw_dense_row(painter, row, state.colors(row.depth, state.color_key), bright_at(row.depth),
                                     dim)

        self._draw_criteria(painter, cells)
        self._draw_overview(painter, metrics)

        # Selection and its ancestors
        if selection:
            for depth in range(1, len(selection) + 1):
                rect = self.rect_of(selection[:depth])
                if rect is not None:
                    width = SELECTION_WIDTH if depth == len(selection) else PARENT_WIDTH
                    inner = self._border_rect(rect, width)
                    stroke(painter, QColor(SELECTION_COLOR), width, lambda r=inner: painter.drawRect(r))
            # its image under the σ of the Permutations panel, with the orbit highlighted
            orbit = state.permutation_orbit(selection) if state.highlight == 'orbit' else None
            if orbit and len(orbit) > 1:
                rect = self.rect_of(orbit[1])
                if rect is not None:
                    painter.setPen(QPen(QColor(PERMUTATION_COLOR), 2, Qt.PenStyle.DashLine))
                    painter.drawRect(self._border_rect(rect, 2))

        # The subcycles that contain the sky moment (Follow)
        if state.follow and state.sky_time is not None:
            for depth in self._rows():
                index = state.moment_index(depth)
                rect = None if index is None else self.rect_of(address_of(index, depth))
                if rect is not None:
                    inner = self._border_rect(rect, SELECTION_WIDTH + 1)
                    stroke(painter, QColor(MOMENT_COLOR), SELECTION_WIDTH, lambda r=inner: painter.drawRect(r))

        self._draw_bookmarks(painter, cells)

        # Depth of each row, and the extent of the zoomed subcycle
        painter.setPen(palette.text().color())
        painter.setFont(font)
        for row in self._geometry:
            painter.drawText(QRectF(0, row.top, LABEL_WIDTH - 6, row.height),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"d{row.depth}")
        self._draw_axis(painter, cells)
        self._draw_markers(painter, cells)
        self._draw_events(painter, cells)           # after the tags, to keep its label clear of them
        self._draw_criteria_key(painter)
        painter.end()

    @staticmethod
    def _border_rect(rect: QRectF, width: float) -> QRectF:
        """The rectangle to stroke a border of ``width`` inside ``rect`` (a narrow subcycle gets at least a line)."""
        inset = width / 2 + 1
        if rect.width() <= 2 * inset + 1:
            return QRectF(rect.center().x() - 0.5, rect.top() + inset, 1.0, rect.height() - 2 * inset)
        return rect.adjusted(inset, inset, -inset, -inset)

    # -- bookmarks

    def _draw_bookmarks(self, painter: QPainter, cells) -> None:
        """A flag in the corner of each bookmarked subcycle in view, and a tick on the overview strip."""
        state = self.state
        if not state.bookmarks:
            return
        marked = {b['address'] for b in state.bookmarks}
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = QColor(BOOKMARK_COLOR)
        painter.setPen(QPen(color.darker(170), 1))
        painter.setBrush(color)
        for address in marked:
            rect = self.rect_of(address)
            if rect is not None and rect.width() >= 4:
                size = min(12.0, rect.width(), rect.height() / 2)
                painter.drawPolygon(QPolygonF([rect.topLeft(), rect.topLeft() + QPointF(size, 0),
                                               rect.topLeft() + QPointF(0, size)]))
        strip = self._overview_rect()
        painter.setPen(QPen(color, 2))
        for address in marked:
            level = state.cache.level(len(address))
            x = strip.left() + float(level.starts[tcoord(address)]) * strip.width()
            painter.drawLine(QPointF(x, strip.top()), QPointF(x, strip.top() + strip.height() * 0.35))
        painter.restore()

    def _draw_events(self, painter: QPainter, cells) -> None:
        """
        The planetary events of the Events panel: a short tick just under the last row at each event in the
        zoomed span (at most one per pixel; dense events read as a band), and their name and number at an end
        of the tag band that no tag covers.
        """
        state = self.state
        if state.event_marks is None or state.time_map is None or not cells:
            return
        years, label = state.event_marks
        start, end = self._focus_extent()
        u = np.asarray(state.time_map.to_normalized(years[(years >= state.time_map.start)
                                                          & (years <= state.time_map.end)]), dtype=float)
        u = u[(u >= start) & (u <= end)]
        row = self._geometry[-1]                # the deepest row
        band = self._tag_band()
        color = QColor(EVENT_COLOR)
        tick = QColor(color)
        span_pixels = max(1.0, float(row.widths.sum()))
        if len(u) > span_pixels / 4:            # crowded: a translucent band that shows the density
            tick.setAlphaF(0.35)
        painter.save()
        painter.setPen(QPen(tick, 1.5))
        bottom = row.top + row.height
        level = state.cache.level(row.depth)
        starts = level.starts[row.start:row.stop]
        durations = level.durations[row.start:row.stop]
        k = np.clip(np.searchsorted(starts, u, side='right') - 1, 0, len(starts) - 1)
        xs = row.lefts[k] + (u - starts[k]) / durations[k] * row.widths[k]
        for x in np.unique(np.round(xs)):
            painter.drawLine(QPointF(x, bottom - 3), QPointF(x, bottom + TAG_GAP + 3))
        if label:
            font = QFont(painter.font())
            font.setPointSizeF(font.pointSizeF() * 0.85)
            painter.setFont(font)
            text = f"{label}: {len(u)} in view"
            width = painter.fontMetrics().horizontalAdvance(text) + 6
            height = painter.fontMetrics().height()
            top = band.bottom() - height
            tags = list(getattr(self, '_tags', {}).values())
            for left in (band.right() - width, band.left()):
                place = QRectF(left, top, width, height)
                if not any(place.intersects(tag) for tag in tags):
                    painter.setPen(color)
                    painter.drawText(place, Qt.AlignmentFlag.AlignCenter, text)
                    break
        painter.restore()
        self._events_shown = len(u)

    def bookmark_text(self, address: tuple) -> str:
        lines = []
        for bookmark in self.state.bookmarks_of(address):
            label = bookmark['label'] or 'Bookmark'
            lines.append(f"\n🔖 {label}" + (f": {bookmark['note']}" if bookmark['note'] else ''))
        return ''.join(lines)

    # -- the other division criterion

    def _draw_criteria(self, painter: QPainter, cells) -> None:
        """
        Where the criteria that are not the model's own division put the
        boundaries of each row: a dashed tick, and the gap to the cell's own
        boundary shaded.
        """
        state = self.state
        self._criteria_shown = []
        if not state.compare_criteria or state.time_map is None:
            return
        rows: dict[int, list] = {}
        for rect, _, depth, index in cells:
            rows.setdefault(depth, []).append((rect, index))
        shown = set()
        for depth, row in rows.items():
            criteria = state.criteria_boundaries(depth)
            level = state.cache.level(depth)
            indices = np.array([index for _, index in row])
            lefts = np.array([rect.left() for rect, _ in row])
            widths = np.array([rect.width() for rect, _ in row])
            top, height = row[0][0].top(), row[0][0].height()
            mean_width = widths.mean()
            if mean_width < CRITERIA_MIN_CELL:
                continue                        # the gaps span several cells: noise at this scale
            starts, durations = level.starts[indices], level.durations[indices]
            own_u = np.append(starts, starts[-1] + durations[-1])
            own_x = np.append(lefts, lefts[-1] + widths[-1])
            boundaries = np.arange(indices[0], indices[-1] + 2)
            for name, data in criteria.items():
                u = data['normalized'][boundaries]
                if np.abs(u - own_u).max() < 1e-9:
                    continue                    # the model's own division
                k = np.clip(np.searchsorted(starts, u, side='right') - 1, 0, len(indices) - 1)
                x = np.clip(lefts[k] + (u - starts[k]) / durations[k] * widths[k], own_x[0], own_x[-1])
                color = QColor(CRITERIA_COLORS[name])
                fill = QColor(color)
                fill.setAlphaF(0.4)
                pen = QPen(color, 1, Qt.PenStyle.DashLine)
                ticks = mean_width >= CRITERIA_TICK_CELL
                painter.setPen(pen)
                for x0, x1 in zip(own_x, x):
                    if abs(x1 - x0) >= 0.5:
                        painter.fillRect(QRectF(min(x0, x1), top, abs(x1 - x0), height), fill)
                        if ticks:
                            painter.drawLine(QPointF(x1, top), QPointF(x1, top + height))
                shown.add(name)
        self._criteria_shown = sorted(shown)

    def _draw_criteria_key(self, painter: QPainter) -> None:
        """Key of the criteria drawn, at the right of the tag band."""
        shown = getattr(self, '_criteria_shown', [])
        if not shown:
            return
        band = self._tag_band()
        height = self._tag_height()
        metrics = painter.fontMetrics()
        texts = [f"boundaries by {CRITERIA_NAMES[name]}" for name in shown]
        width = max(metrics.horizontalAdvance(text) for text in texts) + 16
        key = QRectF(band.right() - width, band.top(), width, band.height())
        if any(key.intersects(tag) for tag in self._tags.values()):
            key.moveLeft(band.left())           # the tags are at the right: the key goes left
        for line, (name, text) in enumerate(zip(shown, texts)):
            y = band.top() + line * (height + 2)
            x = key.left() + 16
            color = QColor(CRITERIA_COLORS[name])
            fill = QColor(color)
            fill.setAlphaF(0.4)
            painter.fillRect(QRectF(x - 16, y + 3, 10, height - 6), fill)
            painter.setPen(QPen(color, 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(x - 6, y + 2), QPointF(x - 6, y + height - 2))
            painter.setPen(color.darker(130))
            painter.drawText(QPointF(x, y + metrics.ascent()), text)

    def criteria_text(self, address: tuple) -> str:
        """Where the other criteria would start ``address``, for its tooltip."""
        state = self.state
        criteria = state.criteria_boundaries(len(address)) if state.compare_criteria else None
        if not criteria:
            return ''
        t0 = state.time_map.interval(address)[0]
        lines = []
        for name, data in criteria.items():
            year = float(data['years'][tcoord(address)])
            if abs(year - t0) > 1e-6:
                lines.append(f"By {CRITERIA_NAMES[name]}: starts {date_text(year)} ({year - t0:+.1f} years)")
        return '\n' + '\n'.join(lines) if lines else ''

    # -- labels

    @staticmethod
    def _dot_size(rect: QRectF) -> float:
        """Diameter of the dots of a cell: proportional to its width, up to ``MAX_DOT``, and room for four."""
        return min(MAX_DOT, rect.width() * 0.4, rect.height() / 7.0)

    def _draw_dots(self, painter: QPainter, center: QPointF, count: int, size: float, color: QColor) -> None:
        """A vertical column of ``count`` dots of diameter ``size`` centred on ``center``."""
        pitch = size * 1.7
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        y0 = center.y() - pitch * (count - 1) / 2
        for k in range(count):
            painter.drawEllipse(QPointF(center.x(), y0 + k * pitch), size / 2, size / 2)
        painter.restore()

    def _draw_label(self, painter: QPainter, metrics, rect: QRectF, digit: int, color: QColor) -> None:
        """
        Label a cell of the age ``digit``: its name, horizontal if it fits, else
        rotated if the cell is tall, else its initial; and/or its dots.
        """
        mode = self.state.labels
        if mode == 'none':
            return
        name = self.state.names[digit]
        dots = 4 - digit
        dot_size = self._dot_size(rect)
        show_dots = mode in ('dots', 'both') and dot_size >= MIN_DOT
        dots_width = dot_size * 1.6 if show_dots else 0.0
        if mode in ('names', 'both'):
            height = metrics.height()
            for text in (name, name[0]):
                width = metrics.horizontalAdvance(text)
                gap = 4 if show_dots else 0
                if width + dots_width + gap + 6 <= rect.width() and height <= rect.height():
                    left = rect.center().x() - (width + dots_width + gap) / 2
                    if show_dots:
                        self._draw_dots(painter, QPointF(left + dot_size / 2, rect.center().y()), dots, dot_size,
                                        color)
                    painter.setPen(color)
                    painter.drawText(QRectF(left + dots_width + gap, rect.top(), width + 2, rect.height()),
                                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
                    return
                if text == name and rect.height() > rect.width() and not show_dots \
                        and width + 6 <= rect.height() and height <= rect.width():
                    # tall, narrow cell: the name reads upwards
                    painter.save()
                    painter.translate(rect.center())
                    painter.rotate(-90)
                    painter.setPen(color)
                    painter.drawText(QRectF(-rect.height() / 2, -rect.width() / 2, rect.height(), rect.width()),
                                     Qt.AlignmentFlag.AlignCenter, text)
                    painter.restore()
                    return
        if show_dots:
            self._draw_dots(painter, rect.center(), dots, dot_size, color)

    # -- overview

    def _draw_overview(self, painter: QPainter, metrics) -> None:
        """The whole cycle's four yugas, with the zoomed part framed and the markers."""
        state = self.state
        strip = self._overview_rect()
        level = state.cache.level(1)
        colors = state.colors(1, state.color_key)
        for k in range(4):
            rect = QRectF(strip.left() + level.starts[k] * strip.width(), strip.top(),
                          level.durations[k] * strip.width(), strip.height())
            color = rgb_to_qcolor(colors[k])
            painter.fillRect(rect, color)
            name = state.names[k]
            for text in (name, name[0]):
                if metrics.horizontalAdvance(text) + 6 <= rect.width():
                    painter.setPen(text_color(color))
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
                    break
        painter.setPen(self.palette().text().color())
        painter.drawText(QRectF(0, strip.top(), LABEL_WIDTH - 6, strip.height()),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, 'cycle')
        # the zoomed part: dim the rest and frame it
        start, end = self._focus_extent()
        if state.focus:
            x0 = strip.left() + start * strip.width()
            x1 = max(strip.left() + end * strip.width(), x0 + 3)
            shade = QColor(self.palette().base().color())
            shade.setAlphaF(0.6)
            painter.fillRect(QRectF(strip.left(), strip.top(), x0 - strip.left(), strip.height()), shade)
            painter.fillRect(QRectF(x1, strip.top(), strip.right() - x1, strip.height()), shade)
            frame = QRectF(x0 - 1, strip.top() + 1, x1 - x0 + 2, strip.height() - 2)
            stroke(painter, QColor(ZOOM_COLOR), PARENT_WIDTH, lambda: painter.drawRect(frame))
        for year, color in ((state.date, QColor(DATE_COLOR)), (state.sky_time, QColor(MOMENT_COLOR))):
            u = state.position(year)
            if u is not None:
                x = strip.left() + u * strip.width()
                stroke(painter, color, CURSOR_WIDTH,
                       lambda x=x: painter.drawLine(QPointF(x, strip.top()), QPointF(x, strip.bottom())))

    def _overview_yuga(self, pos: QPointF) -> int | None:
        strip = self._overview_rect()
        if not strip.contains(pos):
            return None
        u = (pos.x() - strip.left()) / strip.width()
        level = self.state.cache.level(1)
        return int(min(3, max(0, sum(1 for start in level.starts[1:] if u >= start))))

    def _time_label(self, u: float, span: float) -> str:
        """Label of the normalized time ``u``, in the units of the current time map."""
        time_map = self.state.time_map
        if time_map is None:
            return f"{u:.10g}"
        return time_text(time_map.to_physical(min(1.0, u)), span)

    def _draw_axis(self, painter: QPainter, cells) -> None:
        """Ticks at the boundaries of the first row below the zoom, labelled in the current time units."""
        state = self.state
        rows = self._rows()
        if not rows:
            return
        depth = rows[0]
        children = [(rect, address) for rect, address, d, _ in cells if d == depth]
        level = state.cache.level(depth)
        start, end = self._focus_extent()
        time_map = state.time_map
        span = (time_map.to_physical(end) - time_map.to_physical(start)) if time_map else 0.0
        bottom = self._tag_band().bottom() + TAG_GAP
        metrics = painter.fontMetrics()
        ticks = [(rect.left(), float(level.starts[tcoord(address)])) for rect, address in children]
        ticks.append((children[-1][0].right(), end))
        painter.setPen(self.palette().text().color())
        last_right = -1e9
        for k, (x, u) in enumerate(ticks):
            painter.drawLine(QPointF(x, bottom), QPointF(x, bottom + 4))
            text = self._time_label(u, span)
            width = metrics.horizontalAdvance(text)
            left = x if k == 0 else (x - width if k == len(ticks) - 1 else x - width / 2)
            left = min(max(left, LABEL_WIDTH), self.width() - 8 - width)
            if left > last_right + 8:
                painter.drawText(QPointF(left, bottom + 6 + metrics.ascent()), text)
                last_right = left + width

    def _draw_markers(self, painter: QPainter, cells) -> None:
        """The marked date (red) and the moment of the sky chart (orange), solid lines with a light edge."""
        state = self.state
        self._tags = {}
        dragged = self._drag[0] if self._drag else None
        date_label = None
        if state.date is not None:
            date_label = ('now' if abs(state.date - current_year()) < 1 / 365.25 and dragged != 'date'
                          else date_text(state.date))
        self._draw_marker(painter, cells, 'date', state.date, QColor(DATE_COLOR), date_label, 0)
        if state.sky_time is not None:
            self._draw_marker(painter, cells, 'sky', state.sky_time, QColor(MOMENT_COLOR),
                              date_text(state.sky_time) if dragged == 'sky' else 'sky', int(state.date is not None))

    def _draw_marker(self, painter: QPainter, cells, kind: str, year, color: QColor, label, line: int) -> None:
        """
        Line at ``year`` through every row (also with equal widths), with its tag on line ``line``
        of the tag band under the rows, joined to the line in the last row.
        """
        state = self.state
        u = state.position(year)
        if u is None:
            return
        start, end = self._focus_extent()
        if not start <= u <= end:
            return
        last = None                             # (depth, x, bottom) in the deepest row
        for row in self._geometry:
            x = self._x_of(row, u)
            if x is None:
                continue
            stroke(painter, color, CURSOR_WIDTH,
                   lambda x=x, r=row: painter.drawLine(QPointF(x, r.top), QPointF(x, r.top + r.height)))
            if last is None or row.depth > last[0]:
                last = (row.depth, x, row.top + row.height)
        if last is not None and label:
            _, x, rows_bottom = last
            metrics = painter.fontMetrics()
            band = self._tag_band()
            height = self._tag_height()
            y = band.top() + line * (height + 2)
            # the line goes on down from the last row to the tag
            stroke(painter, color, CURSOR_WIDTH,
                   lambda: painter.drawLine(QPointF(x, rows_bottom), QPointF(x, y + height / 2)))
            width = metrics.horizontalAdvance(label) + 8
            left = x if x + width < self.width() - 8 else x - width
            tag = QRectF(left, y, width, height)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(tag, 3, 3)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            painter.setPen(QColor('white'))
            painter.drawText(tag, Qt.AlignmentFlag.AlignCenter, label)
            self._tags[kind] = tag

    def _focus_extent(self) -> tuple[float, float]:
        focus = self.state.focus
        if not focus:
            return 0.0, 1.0
        level = self.state.cache.level(len(focus))
        i = tcoord(focus)
        return float(level.starts[i]), float(min(1.0, level.starts[i] + level.durations[i]))

    # -- interaction

    def _tag_at(self, pos: QPointF) -> str | None:
        return next((kind for kind, rect in self._tags.items() if rect.adjusted(-2, -2, 2, 2).contains(pos)), None)

    def _year_at_x(self, x: float) -> float | None:
        """Year at ``x`` along the first row (where the tags are joined to their lines)."""
        rows = self._rows()
        first = [rect for rect, address in self._cells if len(address) == rows[0]] if rows else []
        if not first:
            return None
        x = min(max(x, first[0].left()), first[-1].right() - 1e-6)
        return self.moment_at(QPointF(x, first[0].center().y()))

    def _move_marker(self, kind: str, year: float | None) -> None:
        if year is None:
            return
        if kind == 'date':
            self.state.set_date(year)
        else:
            self.state.set_sky_time(year)

    def mousePressEvent(self, event) -> None:
        self.setFocus()
        tag = self._tag_at(event.position()) if event.button() == Qt.MouseButton.LeftButton else None
        if tag is not None:
            self._drag = (tag, self.state.date if tag == 'date' else self.state.sky_time)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.update()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self.state.zoom_out()
        elif event.button() == Qt.MouseButton.LeftButton and \
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            year = self.moment_at(event.position())
            if year is not None:
                self.state.set_sky_time(year)
        elif event.button() == Qt.MouseButton.LeftButton:
            yuga = self._overview_yuga(event.position())
            if yuga is not None:
                self.state.set_focus((yuga,))
                return
            address = self.cell_at(event.position())
            if address is not None:
                self.state.select(address)

    def moment_at(self, pos: QPointF) -> float | None:
        """Year at the horizontal position of ``pos`` in the rows (also with equal widths)."""
        time_map = self.state.time_map
        if time_map is None:
            return None
        geometry = getattr(self, '_geometry', [])
        if not geometry:
            return None
        # the row under the mouse, or else the deepest one
        row = next((r for r in geometry if r.top <= pos.y() <= r.top + r.height), geometry[-1])
        i = self._index_at(row, pos.x())
        if i is None:
            return None
        k = i - row.start
        level = self.state.cache.level(row.depth)
        fraction = (pos.x() - row.lefts[k]) / row.widths[k] if row.widths[k] > 0 else 0.0
        u = float(level.starts[i] + fraction * level.durations[i])
        return time_map.to_physical(min(1.0, max(0.0, u)))

    def mouseReleaseEvent(self, event) -> None:
        if self._drag is not None and event.button() == Qt.MouseButton.LeftButton:
            self._end_drag()
        else:
            super().mouseReleaseEvent(event)

    def _end_drag(self, cancel: bool = False) -> None:
        kind, before = self._drag
        self._drag = None
        if cancel:
            self._move_marker(kind, before)
        self.unsetCursor()
        self.update()

    def mouseDoubleClickEvent(self, event) -> None:
        if self._tag_at(event.position()) is not None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            address = self.cell_at(event.position())
            if address:
                self.state.zoom_in(address)

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        if self._drag is not None:
            self._move_marker(self._drag[0], self._year_at_x(pos.x()))
            return
        if self._tag_at(pos) is not None:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.unsetCursor()
        self.hovered.emit(self.cell_at(pos))

    def leaveEvent(self, event) -> None:
        self.hovered.emit(None)

    def event(self, event) -> bool:
        if event.type() == event.Type.ToolTip:
            tag = self._tag_at(QPointF(event.pos()))
            if tag is not None:
                year = self.state.date if tag == 'date' else self.state.sky_time
                what = 'Marked date' if tag == 'date' else 'Moment of the sky chart'
                QToolTip.showText(event.globalPos(), f"{what}: {date_text(year)}\nDrag to move it", self)
                return True
            yuga = self._overview_yuga(QPointF(event.pos()))
            if yuga is not None:
                QToolTip.showText(event.globalPos(), f"{self.state.names[yuga]}: click to zoom here", self)
                return True
            address = self.cell_at(QPointF(event.pos()))
            if address:
                text = ' › '.join(self.state.names[d] for d in address)
                time_map = self.state.time_map
                if time_map is not None:
                    t0, t1 = time_map.interval(address)
                    text += f"\n{time_text(t0, t1 - t0)} to {time_text(t1, t1 - t0)} ({span_text(t1 - t0)})"
                    text += self.criteria_text(address)
                text += self.bookmark_text(address)
                QToolTip.showText(event.globalPos(), text, self)
            else:
                QToolTip.hideText()
            return True
        return super().event(event)

    def keyPressEvent(self, event) -> None:
        state = self.state
        key = event.key()
        selection = state.selection
        if key == Qt.Key.Key_Escape and self._drag is not None:
            self._end_drag(cancel=True)
        elif key in (Qt.Key.Key_Backspace, Qt.Key.Key_Escape):
            state.zoom_out()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and selection:
            state.zoom_in(selection)
        elif selection is None and key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Down):
            self._select(state.focus + (0,))
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            step = -1 if key == Qt.Key.Key_Left else 1
            index = tcoord(selection) + step
            if 0 <= index < 4 ** len(selection):
                self._select(address_of(index, len(selection)))
        elif key == Qt.Key.Key_Up and selection:
            self._select(selection[:-1])
        elif key == Qt.Key.Key_Down and selection and len(selection) < MAX_DEPTH:
            self._select(selection + (0,))
        else:
            super().keyPressEvent(event)

    def _select(self, address: tuple) -> None:
        self.state.reveal(address)


class Breadcrumb(QWidget):
    """Path of the zoomed subcycle; each step zooms out to it."""

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 2, 4, 2)
        self._layout.setSpacing(2)
        state.focusChanged.connect(self.rebuild)
        state.viewChanged.connect(self.rebuild)
        self.rebuild()

    def rebuild(self, *_) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
        focus = self.state.focus
        steps = [((), 'Whole cycle')] + [(focus[:k + 1], self.state.names[d]) for k, d in enumerate(focus)]
        for k, (address, name) in enumerate(steps):
            if k:
                self._layout.addWidget(QLabel('›'))
            button = QToolButton()
            button.setText(name)
            button.setAutoRaise(True)
            if k == len(steps) - 1:   # where we are
                font = button.font()
                font.setBold(True)
                button.setFont(font)
            button.clicked.connect(lambda _=False, a=address: self.state.set_focus(a))
            self._layout.addWidget(button)
        self._layout.addStretch(1)
