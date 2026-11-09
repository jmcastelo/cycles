"""
Dynamics panel: the durations or a measure of the subcycles of one level, as a time series (chapter 16 of the
docs, ``functions.dynamics``), read in the order of the subcycles or sampled evenly in years. Five plots: the
return map x(n + τ) against x(n), the fluctuation function of DFA, the power spectrum, the recurrence plot, and
the series with its change points. A surrogate (shuffled, phase-randomized, or with the digits of the addresses
in another order) can be drawn behind, for comparison. The selected subcycle is marked; clicking selects one.
"""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QSpinBox, QToolButton, QVBoxLayout, QWidget

from cycles.functions import dynamics as dy
from cycles.functions.measure import MEASURES
from cycles.gui.state import MAX_DEPTH, SELECTION_COLOR, CycleState, address_of, children_range, tcoord

PLOTS = {
    'return': 'Return map',
    'fluctuations': 'Fluctuations (DFA)',
    'spectrum': 'Spectrum',
    'recurrence': 'Recurrence plot',
    'changes': 'Series and change points',
}
READINGS = {'index': 'In the order of the subcycles', 'time': 'In time (evenly in years)'}
SURROGATES = {'none': 'No surrogate', 'shuffled': 'Shuffled surrogate', 'phase': 'Phase-randomized surrogate',
              'digits': 'Digits permuted (null)'}
DURATION = 'duration'
MIN_POINTS = 64             # fewer: no estimates
MAX_RECURRENCE = 2048       # points of a recurrence plot (more are thinned out evenly)
MAX_SAMPLES = 2 ** 16       # samples in time
CHANGE_POINTS = 7
SURROGATE_COLOR = '0.65'
LEVEL_COLORS = ('#d62728', '#ff7f0e', '#2ca02c', '#1f77b4', '#9467bd', '#8c564b', '#7f7f7f', '#bcbd22', '#17becf')
PICK_RADIUS = 8             # pixels


class DynamicsPanel(QWidget):
    """The series of one level of the selection (or a chosen depth) as a dynamical system."""

    saveRequested = Signal()     # the Save… button

    def __init__(self, state: CycleState, parent=None):
        super().__init__(parent)
        self.state = state
        self._base = None
        self._dirty = True
        self.ax = None
        self._series = None          # what is drawn: a dict (see series())
        self._points = None          # the points of the return map, and the position of each
        self._highlights = []

        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.plot = self._combo(PLOTS, 'return')
        self.series_box = QComboBox()
        self.series_box.addItem('Duration', DURATION)
        for key, m in MEASURES.items():
            self.series_box.addItem(m['label'], key)
            self.series_box.setItemData(self.series_box.count() - 1, m['description'], 3)    # Qt.ToolTipRole
        self.series_box.setCurrentIndex(self.series_box.findData('dharma'))
        self.series_box.currentIndexChanged.connect(self._schedule)
        self.reading = self._combo(READINGS, 'index')
        self.reading.setToolTip('In the order of the subcycles every subcycle counts the same; in time each one '
                                'counts as long as it lasts (in years of the cycle model, or normalized time)')
        self.surrogate = self._combo(SURROGATES, 'none')
        self.surrogate.setToolTip('A series drawn behind for comparison: the same values in a random order, the same '
                                  'spectrum with random phases, or the subcycles with their digits in another order '
                                  '(the same compositions and durations)')
        for widget in (self.plot, self.series_box, self.reading, self.surrogate):
            row.addWidget(widget)
        row.addStretch(1)
        layout.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel('Depth'))
        self.depth = QSpinBox()
        self.depth.setRange(0, MAX_DEPTH)
        self.depth.setSpecialValueText('auto')
        self.depth.setToolTip('Auto: the depth of the selection, or the level below the zoom')
        self.depth.valueChanged.connect(self._schedule)
        row.addWidget(self.depth)
        self.inside = QCheckBox('Only inside the zoom')
        self.inside.setChecked(True)
        self.inside.toggled.connect(self._schedule)
        row.addWidget(self.inside)
        self.delay_label = QLabel('Delay')
        row.addWidget(self.delay_label)
        self.delay = QSpinBox()
        self.delay.setRange(1, 4096)
        self.delay.setToolTip('τ: the return map plots x(n + τ) against x(n)')
        self.delay.valueChanged.connect(self._schedule)
        row.addWidget(self.delay)
        row.addStretch(1)
        save_button = QToolButton()
        save_button.setText('Save…')
        save_button.setToolTip('Save this graph to a file (page size, resolution, format…)')
        save_button.clicked.connect(self.saveRequested)
        row.addWidget(save_button)
        layout.addLayout(row)

        self.figure = Figure(figsize=(5, 4), layout='constrained')
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumSize(260, 220)
        self.canvas.mpl_connect('button_release_event', self._clicked)
        layout.addWidget(self.canvas, 1)
        self.info = QLabel()
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(0)
        self.render_timer.timeout.connect(self.render)
        for signal in (state.selectionChanged, state.focusChanged, state.viewChanged, state.modelChanged,
                       state.colorParametersChanged):
            signal.connect(self._schedule)

    def _combo(self, items: dict, current: str) -> QComboBox:
        box = QComboBox()
        for key, label in items.items():
            box.addItem(label, key)
        box.setCurrentIndex(box.findData(current))
        box.currentIndexChanged.connect(self._schedule)
        return box

    # -- what to plot

    def series_key(self) -> str:
        return self.series_box.currentData()

    def series_label(self) -> str:
        key = self.series_key()
        return 'Duration' if key == DURATION else MEASURES[key]['label']

    def graph_name(self) -> str:
        """Short name of what is plotted (for file names)."""
        return f"{self.plot.currentText()} · {self.series_label()} ({self.reading.currentData()})"

    def plot_depth(self) -> int:
        state = self.state
        if self.depth.value():
            return self.depth.value()
        if state.selection is not None and len(state.selection) > len(state.focus):
            return len(state.selection)
        return min(MAX_DEPTH, len(state.focus) + 1)

    def scope(self, depth: int) -> tuple:
        """The subcycle whose subcycles at ``depth`` make the series: the zoom (or its ancestor above ``depth``)."""
        focus = self.state.focus
        return focus[:min(len(focus), depth - 1)] if self.inside.isChecked() else ()

    def series(self) -> dict | None:
        """
        The series drawn: ``values`` (as read), ``surrogate`` (or None), ``indices`` (the subcycles of the level
        in the scope), ``subcycle`` (the subcycle of each value: its position among ``indices``), ``x`` (index or
        year of each value), ``depth`` and ``scope``; None if the measure cannot be computed now.
        """
        state = self.state
        depth = self.plot_depth()
        scope = self.scope(depth)
        span = children_range(scope, depth)
        indices = np.arange(span.start, span.stop)
        level = state.cache.level(depth)
        key = self.series_key()
        if key == DURATION:
            values = level.durations[indices]
        else:
            all_values = state.measure_values(depth, key)
            if all_values is None:
                return None
            values = np.asarray(all_values, dtype=float)[indices]
        kind = self.surrogate.currentData()
        if kind == 'digits':
            # the digits below the scope in another order: the subcycles stay inside it
            base = dy.digit_permuted(values, level.lcoords[indices][:, len(scope):])
        else:
            base = None
        if self.reading.currentData() == 'time':
            starts = level.starts[indices]
            start = starts[0]
            end = starts[-1] + level.durations[indices[-1]]
            samples = int(min(MAX_SAMPLES, max(1024, 16 * len(indices))))
            read, moments = dy.time_samples(starts, values, samples, state.time_map, moments=True, span=(start, end))
            subcycle = np.clip(np.searchsorted(starts, moments, side='right') - 1, 0, len(indices) - 1)
            x = (np.asarray(state.time_map.to_physical(moments), dtype=float) if state.time_map is not None
                 else moments)
            if base is not None:
                base = base[subcycle]
        else:
            read, subcycle, x = values, np.arange(len(indices)), indices.astype(float)
        surrogate = (base if kind == 'digits' else dy.shuffled(read) if kind == 'shuffled'
                     else dy.phase_randomized(read) if kind == 'phase' else None)
        return {'values': np.asarray(read, dtype=float), 'surrogate': surrogate, 'indices': indices,
                'subcycle': subcycle, 'x': x, 'depth': depth, 'scope': scope}

    # -- drawing

    def _schedule(self, *_) -> None:
        self._dirty = True
        if self.isVisible():
            self.render_timer.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._dirty:
            self.render_timer.start()

    def render(self) -> None:
        self._dirty = False
        state = self.state
        depth = self.plot_depth()
        key = self.series_key()
        plot = self.plot.currentData()
        self.delay_label.setVisible(plot == 'return')
        self.delay.setVisible(plot == 'return')
        context = () if key == DURATION else (state.parameters_of(key), state.context_of(key))
        base = (plot, key, self.reading.currentData(), self.surrogate.currentData(), depth, self.scope(depth),
                self.delay.value(), state.model, state.names, context, state.cache.bases)
        if base != self._base:
            self._draw_base()
            self._base = base
        self._draw_highlights()
        self.canvas.draw_idle()

    def _title(self, s: dict) -> str:
        where = ' › '.join(self.state.names[d] for d in s['scope']) or 'whole cycle'
        reading = 'in time' if self.reading.currentData() == 'time' else 'index order'
        return f"{self.plot.currentText()}: {self.series_label().lower()}, depth {s['depth']} ({where}, {reading})"

    def _draw_base(self) -> None:
        self.figure.clear()
        self.ax = None
        self._highlights = []
        self._points = None
        key = self.series_key()
        if key != DURATION and not self.state.can_color(key):
            self._series = None
            self.info.setText(f"{MEASURES[key]['label']} {self.state.missing_for(key)} (a cycle model is chosen in "
                              f"the toolbar, the ephemeris in the Sky panel).")
            return
        s = self._series = self.series()
        x = s['values']
        ax = self.ax = self.figure.add_subplot(111)
        plot = self.plot.currentData()
        too_few = len(x) < MIN_POINTS and plot in ('fluctuations', 'spectrum')
        if too_few:
            self.info.setText(f"{len(x)} values: too few for this plot (at least {MIN_POINTS}); choose a deeper level.")
            return
        getattr(self, f"_draw_{plot}")(ax, s)
        ax.set_title(self._title(s), fontsize=9)
        self.info.setText(self._summary(s))

    def _draw_return(self, ax, s: dict) -> None:
        x, tau = s['values'], self.delay.value()
        if len(x) <= tau:
            ax.text(0.5, 0.5, 'The delay is longer than the series', ha='center', transform=ax.transAxes)
            return
        if s['surrogate'] is not None:
            y = s['surrogate']
            ax.plot(y[:-tau], y[tau:], '.', ms=2, color=SURROGATE_COLOR, label=self.surrogate.currentText())
        sizes = 10 if len(x) <= 4096 else 2
        if self.reading.currentData() == 'index':
            colors = self.state.colors(s['depth'], self.state.color_key)[s['indices']][:-tau]
            ax.scatter(x[:-tau], x[tau:], s=sizes, c=colors, zorder=3)
        else:
            ax.plot(x[:-tau], x[tau:], '.', ms=2, color='#1f77b4', zorder=3)
        if np.all(x > 0) and x.max() / x.min() > 100:
            ax.set_xscale('log')
            ax.set_yscale('log')
        ax.set_xlabel(f"{self.series_label()} x(n)")
        ax.set_ylabel(f"x(n + {tau})")
        self._points = (x[:-tau], x[tau:])
        if s['surrogate'] is not None:
            ax.legend(fontsize=7, loc='best')

    def _draw_fluctuations(self, ax, s: dict) -> None:
        scales = dy.scales_between(len(s['values']), 8 if len(s['values']) < 4096 else 16)
        for values, color, label in ((s['values'], '#1f77b4', self.series_label()),
                                     (s['surrogate'], SURROGATE_COLOR, self.surrogate.currentText())):
            if values is None:
                continue
            f = dy.dfa(values, scales)
            alpha = dy.fit_exponent(scales, f)
            ax.loglog(scales, f, 'o-', ms=3, color=color, label=f"{label}: α = {alpha:.3f}")
        ax.set_xlabel('window (values)')
        ax.set_ylabel('fluctuation F(s)')
        ax.legend(fontsize=7)

    def _draw_spectrum(self, ax, s: dict) -> None:
        for values, color, label, raw in ((s['values'], '#1f77b4', self.series_label(), True),
                                          (s['surrogate'], SURROGATE_COLOR, self.surrogate.currentText(), False)):
            if values is None:
                continue
            f, p = dy.power_spectrum(values)
            ok = p > 0
            if raw:
                ax.loglog(f[ok], p[ok], lw=0.3, color='#aec7e8')
            fb, pb = dy.binned_spectrum(f[ok], p[ok], 30)
            beta = -dy.fit_exponent(fb, pb)
            ax.loglog(fb, pb, 'o-', ms=3, color=color, label=f"{label}: β = {beta:.3f}")
        unit = 'value' if self.reading.currentData() == 'time' else 'subcycle'
        ax.set_xlabel(f"frequency (cycles per {unit})")
        ax.set_ylabel('power')
        ax.legend(fontsize=7)

    def _thinned(self, s: dict) -> np.ndarray:
        """Positions of the values shown in a recurrence plot: all, or evenly thinned out to ``MAX_RECURRENCE``."""
        n = len(s['values'])
        return np.arange(n) if n <= MAX_RECURRENCE else np.linspace(0, n - 1, MAX_RECURRENCE).astype(int)

    def _draw_recurrence(self, ax, s: dict) -> None:
        shown = self._thinned(s)
        x = s['values'][shown]
        radius = 0.05 * np.ptp(x) if np.ptp(x) > 0 else 1e-12
        matrix = dy.recurrence_matrix(x, radius)
        extent = (s['x'][shown[0]], s['x'][shown[-1]], s['x'][shown[0]], s['x'][shown[-1]])
        ax.imshow(matrix, cmap='Greys', origin='lower', interpolation='nearest', extent=extent, aspect='auto')
        unit = 'Year' if self.reading.currentData() == 'time' and self.state.time_map is not None else \
            'Normalized time' if self.reading.currentData() == 'time' else 'Index'
        ax.set_xlabel(unit)
        ax.set_ylabel(unit)
        q = dy.rqa(matrix)
        s['rqa'] = q
        if s['surrogate'] is not None:
            q0 = dy.rqa(dy.recurrence_matrix(s['surrogate'][shown], radius))
            s['rqa_surrogate'] = q0

    def _draw_changes(self, ax, s: dict) -> None:
        x, t = s['values'], s['x']
        if s['surrogate'] is not None:
            ax.plot(t, s['surrogate'], lw=0.5, color=SURROGATE_COLOR, label=self.surrogate.currentText())
        ax.plot(t, x, lw=0.7, color='#1f77b4', label=self.series_label())
        cuts = dy.change_points(x, CHANGE_POINTS)
        depth, scope = s['depth'], s['scope']
        local = s['subcycle'][cuts]
        on_boundary = (np.ones(len(cuts), dtype=bool) if self.reading.currentData() == 'index'
                       else local != s['subcycle'][np.maximum(cuts - 1, 0)])
        levels = dy.boundary_levels(local, depth - len(scope)) + len(scope) if depth > len(scope) else \
            np.full(len(cuts), depth)
        s['cuts'] = [(int(c), int(level) if ok else None) for c, level, ok in zip(cuts, levels, on_boundary)]
        drawn = set()
        for c, level in s['cuts']:
            label = f"level {level}" if level is not None else 'inside a subcycle'
            color = LEVEL_COLORS[(level - 1) % len(LEVEL_COLORS)] if level is not None else '0.3'
            ax.axvline(t[c], color=color, lw=1.2, ls='--', label=None if label in drawn else label)
            drawn.add(label)
        unit = ('Year' if self.state.time_map is not None else 'Normalized time') \
            if self.reading.currentData() == 'time' else 'Index'
        ax.set_xlabel(unit)
        ax.set_ylabel(self.series_label())
        ax.legend(fontsize=7, loc='best')

    def _summary(self, s: dict) -> str:
        """The numbers of the series: estimates, and what is known exactly."""
        x = s['values']
        index = self.reading.currentData() == 'index'
        parts = [f"{len(x)} {'subcycles' if index else 'samples'}"]
        if len(x) >= 4 * MIN_POINTS and np.ptp(x) > 0:
            scales = dy.scales_between(len(x), 8 if len(x) < 4096 else 16)
            lags = dy.scales_between(len(x), 4)
            parts.append(f"DFA α {dy.fit_exponent(scales, dy.dfa(x, scales)):.3f}")
            parts.append(f"roughness (q = 1) {dy.fit_exponent(lags, dy.structure_functions(x, lags, [1])[0]):.3f}")
            parts.append(f"Higuchi dimension {dy.higuchi_dimension(x, min(256, len(x) // 8)):.3f}")
            if index:
                h, c = dy.statistical_complexity(x, 5 if len(x) >= 2000 else 4)
                parts.append(f"permutation entropy {h:.3f}, complexity {c:.3f}")
        elif np.ptp(x) == 0:
            parts.append('constant')
        if 'rqa' in s:
            q = s['rqa']
            text = f"recurrence rate {q['rate']:.3f}, determinism {q['determinism']:.3f}"
            if 'rqa_surrogate' in s:
                text += f" (surrogate {s['rqa_surrogate']['determinism']:.3f})"
            parts.append(text)
        if 'cuts' in s:
            levels = [str(level) if level is not None else '–' for _, level in s['cuts']]
            parts.append(f"change points on the boundaries of levels {', '.join(levels)}")
        exact = self._exact(s)
        text = '; '.join(parts) + '.'
        return text + (f" Exact: {exact}." if exact else '') + ' Click to select a subcycle.'

    def _exact(self, s: dict) -> str:
        """What is known exactly about this series (in the index order)."""
        if self.reading.currentData() != 'index':
            return ''
        key = self.series_key()
        known = []
        if key == DURATION:
            known.append(f"H = {dy.exact_duration_hurst([2])[0]:.3f}, β = {2 * dy.exact_duration_hurst([2])[0] - 1:.3f}")
        elif key == 'dharma':
            r = dy.exact_dharma_roughness(self.state.cache.bases[1])
            known.append(f"roughness log₄ b = {r['roughness']:.3f}, graph dimension {r['graph_dimension']:.3f}")
        symmetry = dy.reversal_symmetry(s['values']) if len(s['values']) > 1 else None
        if symmetry is not None:
            known.append('the same backwards' if symmetry[0] == 'even'
                         else f"backwards it turns around {symmetry[1]:.4f}")
        return '; '.join(known)

    def _draw_highlights(self) -> None:
        for artist in self._highlights:
            artist.remove()
        self._highlights = []
        s, ax = self._series, self.ax
        selection = self.state.selection
        if s is None or ax is None or selection is None or len(selection) != s['depth']:
            return
        index = tcoord(selection)
        if not s['indices'][0] <= index <= s['indices'][-1]:
            return
        local = index - s['indices'][0]
        positions = np.flatnonzero(s['subcycle'] == local)
        if not len(positions):
            return
        plot = self.plot.currentData()
        if plot == 'return' and self._points is not None:
            shown = positions[positions < len(self._points[0])]
            if len(shown):
                self._highlights.append(ax.scatter(self._points[0][shown], self._points[1][shown], s=120,
                                                   facecolors='none', edgecolors=SELECTION_COLOR, linewidths=2,
                                                   zorder=5))
        elif plot in ('recurrence', 'changes'):
            first, last = s['x'][positions[0]], s['x'][positions[-1]]
            self._highlights.append(ax.axvspan(first, last, color=SELECTION_COLOR, alpha=0.35, lw=1.5)
                                    if last > first else ax.axvline(first, color=SELECTION_COLOR, lw=1.5))
            if plot == 'recurrence':
                self._highlights.append(ax.axhline(first, color=SELECTION_COLOR, lw=1.0))

    # -- interaction

    def _clicked(self, event) -> None:
        s = self._series
        if event.button != 1 or s is None or self.ax is None or event.inaxes is not self.ax:
            return
        plot = self.plot.currentData()
        position = None
        if plot == 'return' and self._points is not None:
            points = self.ax.transData.transform(np.column_stack(self._points))
            distances = np.hypot(points[:, 0] - event.x, points[:, 1] - event.y)
            k = int(np.argmin(distances))
            if distances[k] <= PICK_RADIUS * self.canvas.devicePixelRatioF():
                position = k
        elif plot in ('recurrence', 'changes') and event.xdata is not None:
            position = int(np.argmin(np.abs(s['x'] - event.xdata)))
        if position is not None:
            index = int(s['indices'][s['subcycle'][position]])
            self.state.reveal(address_of(index, s['depth']))
