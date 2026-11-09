"""
Study of the time evolution of the durations and the measures as dynamical systems (cycles.functions.dynamics):
return maps, fluctuation analysis (Hurst exponents), roughness, spectra, ordinal patterns, recurrences and return
times. Each series is read in two ways:

* **index**: one value per subcycle of a level, in time order (every subcycle counts the same);
* **time**: sampled at moments evenly spread in years of the cycle model (each subcycle counts as long as it lasts).

The durations and dharma have exact answers (``dynamics.exact_*``), which test the estimators; the surrogates
(shuffled, phase-randomized) tell which part of what is measured comes from the order of the values and which from
linear correlations alone.
"""

import matplotlib.pyplot as plt
import numpy as np

import common
from cycles.functions import dynamics as dy
from cycles.functions.division import compute_level
from common import PLOTS_DIR, save_figure
from runner import run, study
from study_of_measures import _model, all_measures

BASE_DIR = PLOTS_DIR / "study_of_dynamics"
QS = np.array([-4, -2, -1, 0, 1, 2, 3, 4], dtype=float)


def setup():
    depth, measure_depth = 9, 8
    model = _model()
    level = compute_level(depth, common.BASES)
    measured = compute_level(measure_depth, common.BASES)
    values = {'duration': measured.durations, **all_measures(measured, model)}
    samples = 2 ** 18
    time_map = model.time_map()
    in_time = {name: dy.time_samples(measured.starts, v, samples, time_map) for name, v in values.items()}
    return dict(depth=depth, level=level, measured=measured, values=values, in_time=in_time, model=model,
                time_map=time_map, samples=samples)


def _finish(fig, opts, name: str) -> None:
    if opts.save:
        save_figure(fig, BASE_DIR / name, dpi=150)
    if opts.show:
        plt.show()
    plt.close(fig)


def _varying(values: dict) -> dict:
    return {k: v for k, v in values.items() if np.ptp(v) > 1e-12}


@study
def exact_numbers(ctx, opts):
    """What is known exactly: the zoom map, the Hurst exponents of the durations, the roughness of dharma."""
    zoom = dy.zoom_dynamics()
    print("Zooming in (T(x) = (x − o_a)/p_a, four branches of slopes 2.5, 3.33, 5, 10):")
    print(f"  entropy = Lyapunov exponent = H(p) = {zoom['entropy']:.4f} nats ({zoom['entropy'] / np.log(2):.4f} bits)"
          f" per level; typical magnification {zoom['mean_zoom']:.3f} per level")
    print(f"  topological entropy log 4 = {zoom['topological_entropy']:.4f}; the count measure: Lyapunov "
          f"{zoom['count_lyapunov']:.4f}, dimension {zoom['count_dimension']:.4f}")
    print("Along time (the next subcycle, address + 1 in base 4): an odometer, entropy 0, period 4^d at depth d")
    h = dy.exact_duration_hurst(QS)
    print("Generalized Hurst exponents of the durations (index): "
          + ", ".join(f"h({q:g}) = {v:.3f}" for q, v in zip(QS, h)))
    print(f"  H = h(2) = {h[QS == 2][0]:.4f}; spectral exponent β = 2H − 1 = {2 * h[QS == 2][0] - 1:.4f}")
    for base in (1.5, 2, 3, 4):
        r = dy.exact_dharma_roughness(base)
        print(f"Dharma with base {base:g}: roughness H = log₄ b = {r['roughness']:.4f}, "
              f"graph dimension {r['graph_dimension']:.4f}")


@study
def return_maps(ctx, opts):
    """d(n + 1) against d(n): the durations jump between straight lines, one per number of Kali digits carried."""
    level = ctx.level
    x = level.durations
    carries = dy.carry_lengths(level.lcoords)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
    ax = axes[0]
    cmap = plt.get_cmap('viridis')
    top = carries.max()
    for k in range(top + 1):
        sel = carries == k
        ax.plot(x[:-1][sel], x[1:][sel], '.', ms=1.5, color=cmap(k / max(top, 1)), label=f"{k} Kali carried")
    ax.set_xscale('log')
    ax.set_yscale('log')
    lims = np.array([x.min(), x.max()])
    ax.plot(lims, lims, color='0.6', lw=0.6, ls=':')
    ax.set_xlabel('duration of the subcycle n')
    ax.set_ylabel('duration of the subcycle n + 1')
    ax.set_title(f"Return map of the durations, depth {ctx.depth} (index)", fontsize=10)
    ax.legend(fontsize=7, markerscale=5, loc='lower right')
    ratios = x[1:] / x[:-1]
    exact = dy.exact_duration_ratios(level.lcoords)
    print(f"Ratio of consecutive durations = (p_(j+1)/p_j)·4^k: exact for all {len(ratios)} pairs: "
          f"{np.allclose(ratios, exact)}; {len(np.unique(np.round(np.log(ratios), 9)))} different ratios")
    for k in range(min(top, 4) + 1):
        print(f"  {k} Kali carried: {np.mean(carries == k):.4f} of the steps (exactly 3/4^{k + 1} = "
              f"{3 / 4 ** (k + 1):.4f})")
    # dharma: each step is fixed by the carries too, one value per number of Kali digits carried
    ax = axes[1]
    steps = np.diff(level.dharmas)
    exact_steps = dy.exact_dharma_steps(ctx.depth, common.BASES[1])
    seen = np.array([np.unique(np.round(steps[carries == k], 12)) for k in range(top + 1)], dtype=object)
    print(f"Steps of dharma (base {common.BASES[1]}): {len(np.unique(np.round(steps, 12)))} values, as many as "
          f"carries; exact: {all(np.allclose(v, exact_steps[k]) for k, v in enumerate(seen))}")
    print("  " + ", ".join(f"k = {k}: {v:+.6f}" for k, v in enumerate(exact_steps)))
    share = np.array([np.mean(carries == k) for k in range(top + 1)])
    ax.semilogy(np.arange(top + 1), np.abs(exact_steps[:top + 1]), color='black', lw=1, label='exact |step|')
    ax.scatter(np.arange(top + 1), np.abs([v[0] for v in seen]), s=400 * share ** 0.5, color='#1f77b4',
               alpha=0.7, label='seen (area ∝ √frequency)')
    ax.annotate('the only step down', (0, abs(exact_steps[0])), xytext=(10, 14), textcoords='offset points',
                fontsize=8)
    ax.set_xlabel('Kali digits carried')
    ax.set_ylabel('|dharma(n + 1) − dharma(n)|')
    ax.set_title(f"The steps of dharma, depth {ctx.depth} (base {common.BASES[1]})", fontsize=10)
    ax.legend(fontsize=8, loc='upper left', markerscale=0.5)
    fig.tight_layout()
    _finish(fig, opts, 'return_maps.png')


def _estimates(x) -> dict:
    """The estimators of dynamics on one series."""
    scales = dy.scales_between(len(x))
    lags = dy.scales_between(len(x), 4)
    f, p = dy.binned_spectrum(*dy.power_spectrum(x))
    s = dy.structure_functions(x, lags, [1, 2])
    pe, c = dy.statistical_complexity(x, 5)
    return {'DFA α': dy.fit_exponent(scales, dy.dfa(x, scales)),
            'R/S': dy.fit_exponent(scales, dy.rescaled_range(x, scales)),
            'H(q=1)': dy.fit_exponent(lags, s[0]), 'H(q=2)': dy.fit_exponent(lags, s[1]),
            'Higuchi D': dy.higuchi_dimension(x), 'β': -dy.fit_exponent(f, p), 'PE': pe, 'C': c}


@study
def exponents(ctx, opts):
    """Every estimator on the durations and on every measure, in the index order and in time, and on surrogates."""
    rows = {}
    for name, x in _varying(ctx.values).items():
        rows[f"{name} (index)"] = _estimates(x)
        rows[f"{name} (time)"] = _estimates(ctx.in_time[name])
    for name in ('duration', 'dharma', 'trend'):
        x = ctx.values[name]
        rows[f"{name} shuffled"] = _estimates(dy.shuffled(x))
        rows[f"{name} phase-rand."] = _estimates(dy.phase_randomized(x))
    keys = list(next(iter(rows.values())))
    print(f"{'series':<24}" + "".join(f"{k:>10}" for k in keys))
    for name, est in rows.items():
        # in time the ordinal patterns see the sampling (a subcycle repeats over many samples): not shown
        print(f"{name:<24}" + "".join(f"{'—':>10}" if name.endswith('(time)') and k in ('PE', 'C')
                                      else f"{est[k]:>10.3f}" for k in keys))
    print(f"Exact: durations H = {dy.exact_duration_hurst([2])[0]:.3f} (index); dharma (base {common.BASES[1]}) "
          f"roughness {dy.exact_dharma_roughness(common.BASES[1])['roughness']:.3f}, "
          f"graph dimension {dy.exact_dharma_roughness(common.BASES[1])['graph_dimension']:.3f}")
    # the figure: index against time for each measure
    names = [n for n in rows if n.endswith('(index)')]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, key in zip(axes, ('DFA α', 'H(q=1)', 'Higuchi D')):
        a = [rows[n][key] for n in names]
        b = [rows[n.replace('(index)', '(time)')][key] for n in names]
        ax.plot(a, b, 'o', color='#1f77b4')
        for n, u, v in zip(names, a, b):
            ax.annotate(n.split(' ')[0], (u, v), fontsize=7, xytext=(3, 3), textcoords='offset points')
        lo, hi = min(a + b), max(a + b)
        ax.plot([lo, hi], [lo, hi], color='0.6', lw=0.8, ls=':')
        ax.set_xlabel(f"{key}, index order")
        ax.set_ylabel(f"{key}, in time")
        ax.set_title(key, fontsize=10)
    fig.suptitle('The measures as time series: in the order of the subcycles against in years')
    fig.tight_layout()
    _finish(fig, opts, 'exponents.png')


@study
def fluctuations(ctx, opts):
    """MF-DFA of the durations: the estimated h(q) against the exact one, and against the surrogates."""
    x = ctx.level.durations
    scales = dy.scales_between(len(x))
    q = np.linspace(-4, 4, 17)
    exact = dy.exact_duration_hurst(q)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    series = {'index': x, 'time': dy.time_samples(ctx.level.starts, x, ctx.samples, ctx.time_map),
              'shuffled': dy.shuffled(x), 'phase-randomized': dy.phase_randomized(x)}
    colors = dict(zip(series, ('#1f77b4', '#2ca02c', '0.5', '#ff7f0e')))
    for name, s in series.items():
        f = dy.mfdfa(s, scales, q)
        h = [dy.fit_exponent(scales, row) for row in f]
        # in time the samples repeat along each subcycle: windows inside a long one barely fluctuate, and the
        # negative q (which look at the calmest windows) measure the sampling, not the series
        shown = q > 0 if name == 'time' else q == q
        axes[1].plot(q[shown], np.array(h)[shown], 'o-', ms=3, color=colors[name], label=name)
        if name in ('index', 'shuffled'):
            axes[0].loglog(scales, f[q == 2][0], 'o-', ms=3, color=colors[name], label=f"{name}, q = 2")
        print(f"{name:>17}: h(2) = {h[list(q).index(2)]:.3f}, h(−4) − h(4) = {h[0] - h[-1]:.3f}, "
              f"h(0.5) − h(4) = {h[list(q).index(0.5)] - h[-1]:.3f}")
    print(f"{'exact (index)':>17}: h(2) = {exact[list(q).index(2)]:.3f}, h(−4) − h(4) = {exact[0] - exact[-1]:.3f}, "
          f"h(0.5) − h(4) = {exact[list(q).index(0.5)] - exact[-1]:.3f}")
    axes[1].plot(q, exact, color='black', lw=1.4, label='exact (index)')
    axes[0].set_xlabel('window s (points)')
    axes[0].set_ylabel('F₂(s)')
    axes[0].set_title('Fluctuation function of the durations', fontsize=10)
    axes[0].legend(fontsize=8)
    axes[1].set_xlabel('q')
    axes[1].set_ylabel('h(q)')
    axes[1].set_title('Generalized Hurst exponents', fontsize=10)
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    _finish(fig, opts, 'fluctuations.png')


@study
def spectra(ctx, opts):
    """The spectrum of the durations (exactly a Riesz product, peaks at k/4^m) and of the measures."""
    x = ctx.level.durations
    f, p = dy.power_spectrum(x)
    exact = dy.exact_duration_spectrum(f, ctx.depth)
    print(f"Periodogram of the durations against the Riesz product: largest difference "
          f"{np.max(np.abs(p - exact)) / exact.max():.1e} of the peak")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    axes[0].loglog(f, p, color='#1f77b4', lw=0.4, label='periodogram')
    fb, pb = dy.binned_spectrum(f, p)
    beta = -dy.fit_exponent(fb, pb)
    axes[0].loglog(fb, pb, 'o', ms=3, color='black', label=f"binned: β = {beta:.3f}")
    axes[0].set_xlabel('frequency (cycles per subcycle)')
    axes[0].set_ylabel('power')
    axes[0].set_title(f"Durations, depth {ctx.depth} (index): exact 2H − 1 = "
                      f"{2 * dy.exact_duration_hurst([2])[0] - 1:.3f}", fontsize=10)
    axes[0].legend(fontsize=8)
    cmap = plt.get_cmap('tab20')
    for i, (name, v) in enumerate(_varying(ctx.values).items()):
        fb, pb = dy.binned_spectrum(*dy.power_spectrum(v))
        axes[1].loglog(fb, pb / pb[0], '-', lw=1, color=cmap(i % 20), label=name)
    axes[1].set_xlabel('frequency (cycles per subcycle)')
    axes[1].set_ylabel('power (relative)')
    axes[1].set_title('The measures, depth 8 (index, binned)', fontsize=10)
    axes[1].legend(fontsize=7, ncol=2)
    fig.tight_layout()
    _finish(fig, opts, 'spectra.png')


@study
def complexity_plane(ctx, opts):
    """Permutation entropy against statistical complexity: where each series lies between order and noise."""
    fig, ax = plt.subplots(figsize=(7.5, 6))
    # in the index order only: sampled in time, a subcycle repeats its value over many samples, and those ties are
    # ordered at random, so the patterns would measure the sampling rather than the series
    for name, v in _varying(ctx.values).items():
        h, c = dy.statistical_complexity(v, 5)
        hs, cs = dy.statistical_complexity(dy.shuffled(v), 5)
        ax.plot(h, c, 'o', color='#1f77b4', ms=5)
        ax.plot(hs, cs, 'x', color='0.5')
        ax.annotate(name, (h, c), fontsize=7, xytext=(3, 3), textcoords='offset points')
        print(f"{name:<12} entropy {h:.3f}, complexity {c:.3f} (shuffled: {hs:.3f}, {cs:.3f})")
    ax.plot([], [], 'o', color='#1f77b4', label='index order (depth 8)')
    ax.plot([], [], 'x', color='0.5', label='shuffled')
    ax.set_xlim(0, 1.02)
    ax.set_xlabel('permutation entropy (order 5)')
    ax.set_ylabel('statistical complexity')
    ax.set_title('The complexity–entropy plane')
    ax.legend(fontsize=8)
    fig.tight_layout()
    _finish(fig, opts, 'complexity_plane.png')


@study
def recurrences(ctx, opts):
    """Recurrence plots at depth 5 (1024 subcycles), and their quantification."""
    level = compute_level(5, common.BASES)
    values = {'duration': level.durations, **all_measures(level, ctx.model)}
    names = [n for n in ('duration', 'dharma', 'purity', 'trend', 'tension', 'density') if np.ptp(values[n]) > 0]
    fig, axes = plt.subplots(2, 3, figsize=(12, 8.8))
    print(f"{'measure':<12}{'rate':>8}{'DET':>8}{'LAM':>8}{'L':>8}   shuffled DET")
    for ax, name in zip(axes.flat, names):
        v = values[name]
        radius = 0.05 * np.ptp(v)
        r = dy.recurrence_matrix(v, radius)
        q = dy.rqa(r)
        qs = dy.rqa(dy.recurrence_matrix(dy.shuffled(v), radius))
        print(f"{name:<12}{q['rate']:>8.3f}{q['determinism']:>8.3f}{q['laminarity']:>8.3f}"
              f"{q['mean_diagonal']:>8.2f}   {qs['determinism']:.3f}")
        ax.imshow(r, cmap='Greys', origin='lower', interpolation='nearest')
        ax.set_title(f"{name}: DET {q['determinism']:.2f}", fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    print("Under time reversal (each digit a becomes 3 − a): "
          + "; ".join(f"{n} {'even' if r[0] == 'even' else f'odd about {r[1]:.4f}'}"
                      for n, r in ((n, dy.reversal_symmetry(v)) for n, v in values.items()) if r)
          + "; the rest without symmetry")
    fig.suptitle('Recurrence plots, depth 5 (index), radius 5% of the range')
    fig.tight_layout(h_pad=2.0)
    _finish(fig, opts, 'recurrences.png')


@study
def return_times(ctx, opts):
    """Waiting times between Kali periods: fixed in subcycles (the odometer), spread over a decade in years."""
    level = ctx.level
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    axes = [ax]
    years = np.diff(np.asarray(ctx.time_map.to_physical(np.r_[level.starts, 1.0]), dtype=float))
    for depth, color in zip((2, 3, 4), ('#1f77b4', '#ff7f0e', '#2ca02c')):
        members = level.lcoords[:, depth - 1] == 3        # in a Kali at this level
        starts = np.flatnonzero(members & ~np.r_[False, members[:-1]])
        mark = np.zeros(len(members), dtype=bool)
        mark[starts] = True                               # the first subcycle of each Kali period
        in_index = dy.return_times(mark)
        in_years = dy.return_times(mark, years)
        print(f"Kali of level {depth}: {len(starts)} periods; between their starts {in_index.mean():.1f} subcycles "
              f"(exactly 4^{ctx.depth - depth + 1} = {4 ** (ctx.depth - depth + 1)}), "
              f"{in_years.mean():.0f} ± {in_years.std():.0f} years (from {in_years.min():.0f} to {in_years.max():.0f})")
        axes[0].hist(in_years, bins=40, color=color, alpha=0.6, label=f"Kali of level {depth}")
    axes[0].set_xscale('log')
    axes[0].set_xlabel('years between the starts of consecutive Kali periods')
    axes[0].set_ylabel('count')
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    _finish(fig, opts, 'return_times.png')


@study
def embedding(ctx, opts):
    """Correlation dimension in delay embeddings: it stops growing for dharma (its exact value) and not for noise."""
    dims = [1, 2, 3, 4, 5, 6]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    colors = plt.get_cmap('viridis')(np.linspace(0.1, 0.85, 4))
    for base, color in zip((2, 3, 8, 16), colors):
        x = compute_level(8, [4, base, common.BASES[2]]).dharmas
        d2 = dy.correlation_dimensions(x, dims)['dimensions']
        d2s = dy.correlation_dimensions(dy.shuffled(x), dims)['dimensions']
        exact = dy.exact_dharma_dimension(base)
        axes[0].plot(dims, d2, 'o-', color=color, label=f"dharma, base {base} (exact {exact:.3f})")
        axes[0].plot(dims, d2s, 'x:', color=color)
        print(f"dharma base {base:>2}: D₂ = {', '.join(f'{v:.3f}' for v in d2)} (exact {exact:.3f}); "
              f"shuffled {', '.join(f'{v:.2f}' for v in d2s)}")
    axes[0].plot([], [], 'x:', color='0.4', label='shuffled')
    axes[0].set_xlabel('embedding dimension')
    axes[0].set_ylabel('correlation dimension D₂')
    axes[0].set_title('Dharma, depth 8 (index): deterministic, D₂ saturates', fontsize=10)
    axes[0].legend(fontsize=8)
    print("The measures, depth 8 (index), embedding dimensions 1 to 6:")
    for i, (name, v) in enumerate(_varying(ctx.values).items()):
        d2 = dy.correlation_dimensions(v, dims)['dimensions']
        axes[1].plot(dims, d2, 'o-', ms=3, color=plt.get_cmap('tab20')(i % 20), label=name)
        print(f"  {name:<12}{', '.join(f'{x:.2f}' for x in d2)}")
    axes[1].plot(dims, dims, color='0.6', ls=':', label='noise (D₂ = m)')
    axes[1].set_xlabel('embedding dimension')
    axes[1].set_ylabel('correlation dimension D₂')
    axes[1].set_title('Every measure, depth 8 (index)', fontsize=10)
    axes[1].legend(fontsize=7, ncol=2)
    fig.tight_layout()
    _finish(fig, opts, 'embedding.png')


def _cut_levels(cuts, depth, subcycles=None) -> np.ndarray:
    """The level of the boundary each cut falls on (depth + 1: inside a subcycle). ``subcycles``: the subcycle of
    each sample, for a series sampled in time."""
    if subcycles is None:
        return dy.boundary_levels(cuts, depth)
    on_boundary = subcycles[cuts] != subcycles[cuts - 1]
    return np.where(on_boundary, dy.boundary_levels(subcycles[cuts], depth), depth + 1)


@study
def change_points(ctx, opts):
    """Where the measures change regime (binary segmentation): on the boundaries of which levels, against the null
    of the digits in another order."""
    level, depth, count = ctx.measured, 8, 15
    _, moments = dy.time_samples(level.starts, level.durations, ctx.samples, ctx.time_map, moments=True)
    subcycles = np.clip(np.searchsorted(level.starts, moments, side='right') - 1, 0, len(level.starts) - 1)
    print(f"The first {count} cuts of each series, by the shallowest level whose boundary they fall on "
          f"(1 = an age; {depth + 1} = inside a subcycle). The share of the starts that are boundaries of levels 1–3 "
          f"is {4 ** 3 / 4 ** depth:.4f}.")
    print(f"{'series':<12}{'index':>34}   {'digits permuted':>34}   {'time':>34}")
    rows = {}
    for name, v in _varying(ctx.values).items():
        found = _cut_levels(dy.change_points(v, count), depth)
        null = _cut_levels(dy.change_points(dy.digit_permuted(v, level.lcoords), count), depth)
        in_time = _cut_levels(dy.change_points(ctx.in_time[name], count), depth, subcycles)
        rows[name] = (found, null, in_time)
        print(f"{name:<12}{' '.join(map(str, found)):>34}   {' '.join(map(str, null)):>34}   "
              f"{' '.join(map(str, in_time)):>34}")
    fig, ax = plt.subplots(figsize=(10, 5))
    names = list(rows)
    shallow = np.array([[np.mean(r <= 3) for r in rows[n]] for n in names])
    width = 0.27
    for k, (label, color) in enumerate((('index', '#1f77b4'), ('digits permuted', '0.6'), ('time', '#2ca02c'))):
        ax.bar(np.arange(len(names)) + (k - 1) * width, shallow[:, k], width, color=color, label=label)
    ax.set_xticks(np.arange(len(names)), names, rotation=45, ha='right')
    ax.set_ylabel(f"share of the first {count} cuts on boundaries of levels 1–3")
    ax.set_title('Change points of the measures (depth 8) on the boundaries of the division')
    ax.legend(fontsize=8)
    fig.tight_layout()
    _finish(fig, opts, 'change_points.png')


@study
def digit_null(ctx, opts):
    """The estimators on each measure with the digits of every address in a random order (the durations stay):
    what comes from which level each age is at."""
    keys = ('DFA α', 'H(q=1)', 'Higuchi D', 'β', 'PE', 'C')
    print(f"{'measure':<12}" + "".join(f"{k:>16}" for k in keys) + "   (original → digits permuted)")
    for name, v in _varying(ctx.values).items():
        a, b = _estimates(v), _estimates(dy.digit_permuted(v, ctx.measured.lcoords))
        print(f"{name:<12}" + "".join(f"{a[k]:>8.3f}→{b[k]:<7.3f}" for k in keys))


@study(default=False)
def roughness_by_base(ctx, opts):
    """Dharma's roughness and graph dimension for color bases from 1.25 to 4: estimates against log₄ b."""
    bases = np.linspace(1.25, 4, 12)
    est_h, est_d = [], []
    for b in bases:
        x = compute_level(ctx.depth, [4, b, common.BASES[2]]).dharmas
        lags = dy.scales_between(len(x), 4)
        est_h.append(dy.fit_exponent(lags, dy.structure_functions(x, lags, [1])[0]))
        est_d.append(dy.higuchi_dimension(x))
    exact = np.log(bases) / np.log(4)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(bases, exact, color='black', label='exact roughness log₄ b')
    ax.plot(bases, est_h, 'o', color='#1f77b4', label='structure function, q = 1')
    ax.plot(bases, 2 - np.array(est_d), 's', color='#ff7f0e', label='2 − Higuchi dimension')
    ax.set_xlabel('color base b')
    ax.set_ylabel('roughness H')
    ax.set_title(f"The roughness of dharma, depth {ctx.depth} (index)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    for b, e, h, d in zip(bases, exact, est_h, est_d):
        print(f"b = {b:.2f}: exact {e:.3f}, q = 1 {h:.3f}, 2 − Higuchi {2 - d:.3f}")
    _finish(fig, opts, 'roughness_by_base.png')


if __name__ == "__main__":
    run(setup)
