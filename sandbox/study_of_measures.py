"""
Study of the measures of subcycles: dharma and purity (with the bases of the original study, the purity weights
equal), and every measure of ``measure.MEASURES`` with the explorer's bases: the measures over time and how much
they repeat each other (rank correlations by depth).
"""

import numpy as np

from cycles.functions.division import partition_level
from cycles.plotting.measure import plot_quality_grid, plot_purity_vs_dharma, plot_quality_scatter_3d
from cycles.plotting.generic import plot_y_vs_x
import matplotlib.pyplot as plt

import common
from cycles.functions.measure import MEASURES, address_measures
from common import PLOTS_DIR, compute_levels, fig_data, save_figure
from runner import study, run

BASE_DIR = PLOTS_DIR / "study_of_measures"


def setup():
    bases = [4, 2, 1]
    return dict(
        bases=bases,
        levels=compute_levels(5, bases=bases),
        rgb_key='cmyk_kscaled',  # Level RGB variant (division.RGB_KEYS)
    )


def _measure_plot(ctx, opts, measure: str, axis: str, paper: str, dpi: int):
    """Plot dharma or purity against time or index, one figure per depth."""
    for depth, level in enumerate(ctx.levels, 1):
        values = level.dharmas if measure == 'dharma' else level.purities
        if axis == 'time':
            x, xlabel = level.starts + level.durations / 2, 'Time (norm. units)'
        else:
            x, xlabel = np.arange(len(values)), 'Index'
        path = BASE_DIR / f"{measure}/base_{ctx.bases[1]}/{measure}_vs_{axis}_at_depth_{depth}.png"
        plot_y_vs_x(x, values, (None, None), f"{measure.capitalize()} vs {axis} at depth {depth}",
                    xlabel, measure.capitalize(), opts.save, fig_data(path, paper, dpi))


@study
def quality_grid(ctx, opts):
    """Purity against dharma, one panel per depth."""
    plot_quality_grid(ctx.levels, ctx.rgb_key)


@study(default=False)
def quality_by_age(ctx, opts):
    """Purity against dharma at the deepest level, one panel per top-level age."""
    plot_quality_grid(partition_level(ctx.levels[-1], 1, ctx.bases[0]), ctx.rgb_key)


@study(default=False)
def quality_by_subage(ctx, opts):
    """Purity against dharma at the deepest level, one panel per depth-2 subcycle."""
    plot_quality_grid(partition_level(ctx.levels[-1], 2, ctx.bases[0]), ctx.rgb_key)


@study(default=False)
def purity_vs_dharma(ctx, opts):
    """Purity against dharma at the deepest level, in one figure."""
    fig = plot_purity_vs_dharma(ctx.levels[-1], ctx.rgb_key)
    if opts.save:
        save_figure(fig, BASE_DIR / f"{ctx.rgb_key}/purity_vs_dharma_at_depth_{len(ctx.levels)}.png")


@study(default=False)
def quality_scatter_3d(ctx, opts):
    """Dharma, purity and time of the subcycles of the deepest level, in 3D."""
    fig = plot_quality_scatter_3d(ctx.levels[-1], ctx.rgb_key)
    if opts.save:
        save_figure(fig, BASE_DIR / f"{ctx.rgb_key}/quality_scatter_3d_at_depth_{len(ctx.levels)}.png")


@study(default=False)
def dharma_purity_lines(ctx, opts):
    """Purity against dharma as a line through the subcycles in time order, per depth."""
    for depth, level in enumerate(ctx.levels, 1):
        path = BASE_DIR / f"{ctx.rgb_key}/dharma_vs_purity_at_depth_{depth}.png"
        plot_y_vs_x(level.dharmas, level.purities, (None, None), f"Purity vs Dharma at depth {depth}",
                    'Dharma', 'Purity', opts.save, fig_data(path, 'a3', 600))


@study(default=False)
def dharma_vs_time(ctx, opts):
    """Dharma against time, one figure per depth."""
    _measure_plot(ctx, opts, 'dharma', 'time', 'a3', 600)


@study(default=False)
def dharma_vs_index(ctx, opts):
    """Dharma against time-order index, one figure per depth."""
    _measure_plot(ctx, opts, 'dharma', 'index', 'a4', 300)


@study(default=False)
def purity_vs_time(ctx, opts):
    """Purity against time, one figure per depth."""
    _measure_plot(ctx, opts, 'purity', 'time', 'a4', 300)


@study(default=False)
def purity_vs_index(ctx, opts):
    """Purity against time-order index, one figure per depth."""
    _measure_plot(ctx, opts, 'purity', 'index', 'a4', 300)


# -- every measure (the explorer's bases, common.BASES, and the cycle model of the session or the default preset)

def _model():
    from cycles.functions.cycle_model import BUILTIN_PRESETS, DEFAULT_PRESET
    return common.MODEL if common.MODEL is not None else BUILTIN_PRESETS[DEFAULT_PRESET]


def all_measures(level, model=None) -> dict[str, np.ndarray]:
    """Every measure of ``MEASURES`` for ``level`` (the angular density with ``model``, if given)."""
    values = address_measures(level.lcoords, level.durations, level.dharmas, level.purities, common.BASES)
    if model is not None:
        from cycles.functions.cycle_analysis import angular_density
        values['density'] = angular_density(model, level.starts, level.durations)
    return values


def ranks(values: np.ndarray) -> np.ndarray:
    """Ranks of ``values`` (from 0), ties sharing their mean rank."""
    order = np.argsort(values, kind='stable')
    sorted_values = values[order]
    r = np.empty(len(values))
    starts = np.flatnonzero(np.r_[True, np.diff(sorted_values) != 0])
    ends = np.r_[starts[1:], len(values)]
    for a, b in zip(starts, ends):
        r[order[a:b]] = (a + b - 1) / 2
    return r


def rank_correlations(values: dict[str, np.ndarray]) -> tuple[list[str], np.ndarray]:
    """Spearman correlations between the measures (those not constant)."""
    keys = [k for k, v in values.items() if np.ptp(v) > 1e-12]
    return keys, np.corrcoef(np.array([ranks(values[k]) for k in keys]))


def _finish(fig, opts, name: str) -> None:
    if opts.save:
        save_figure(fig, BASE_DIR / 'all' / name, dpi=150)
    if opts.show:
        plt.show()
    plt.close(fig)


@study
def measures_over_time(ctx, opts, depth: int = 4):
    """Every measure against time at depth 4 (years of the cycle model), one panel each."""
    from cycles.functions.division import compute_level
    model = _model()
    level = compute_level(depth, common.BASES, common.SCALES, common.TETRAHEDRON_COLORS)
    values = all_measures(level, model)
    years = np.asarray(model.time_map().to_physical(level.starts + level.durations / 2), dtype=float)
    colors = level.rgb('cmyk_normalised')
    fig, axes = plt.subplots(3, 3, figsize=(16, 10), sharex=True)
    for ax, (key, v) in zip(axes.ravel(), values.items()):
        ax.plot(years, v, color='0.75', lw=0.6, zorder=1)
        ax.scatter(years, v, c=colors, s=6, zorder=2)
        ax.set_title(MEASURES[key]['label'], fontsize=10)
        if key in ('trend', 'contrast', 'balance'):
            ax.axhline(0, color='0.5', lw=0.5)
        if key == 'density':
            ax.axhline(1, color='0.5', lw=0.5)
    for ax in axes[-1]:
        ax.set_xlabel('Year')
    fig.suptitle(f"The measures of the {4 ** depth} subcycles of depth {depth} ({model.name}, bases {common.BASES})")
    fig.tight_layout()
    _finish(fig, opts, f"measures_over_time_at_depth_{depth}.png")


@study
def measure_correlations(ctx, opts, depths=(2, 3, 4, 5, 6)):
    """
    Rank (Spearman) correlations between the measures at each depth: which carry information of their own and
    which repeat dharma or purity.
    """
    from cycles.functions.division import compute_level
    model = _model()
    tables = []
    for depth in depths:
        level = compute_level(depth, common.BASES, common.SCALES, common.TETRAHEDRON_COLORS)
        keys, r = rank_correlations(all_measures(level, model))
        tables.append((depth, keys, r))
        print(f"\nDepth {depth} ({4 ** depth} subcycles): Spearman correlations")
        labels = [MEASURES[k]['label'][:9] for k in keys]
        print(' ' * 10 + ''.join(f"{name:>10}" for name in labels))
        for name, row in zip(labels, r):
            print(f"{name:<10}" + ''.join(f"{x:>10.2f}" for x in row))
        # how much of each measure the others explain: the largest |r| with another measure
        np.fill_diagonal(r_off := np.abs(r.copy()), 0)
        print('Largest |r| with another measure: '
              + ', '.join(f"{MEASURES[k]['label'].lower()} {m:.2f} ({MEASURES[keys[j]]['label'].lower()})"
                          for k, m, j in zip(keys, r_off.max(axis=1), r_off.argmax(axis=1))))
    shown = [t for t in tables if t[0] in (depths[0], depths[len(depths) // 2], depths[-1])]
    fig, axes = plt.subplots(1, len(shown), figsize=(5.2 * len(shown), 6.2), layout='constrained')
    for k, (ax, (depth, keys, r)) in enumerate(zip(np.atleast_1d(axes), shown)):
        image = ax.imshow(r, cmap='RdBu_r', vmin=-1, vmax=1)
        labels = [MEASURES[key]['label'].replace('Angular density', 'Ang. density') for key in keys]
        ax.set_xticks(range(len(keys)), labels, rotation=90, fontsize=8)
        ax.set_yticks(range(len(keys)), labels if k == 0 else [], fontsize=8)
        for i in range(len(keys)):
            for j in range(len(keys)):
                ax.text(j, i, f"{r[i, j]:.1f}".replace('-', '−'), ha='center', va='center', fontsize=7,
                        color='white' if abs(r[i, j]) > 0.6 else 'black')
        ax.set_title(f"Depth {depth} ({4 ** depth} subcycles)", fontsize=10)
    fig.colorbar(image, ax=axes, shrink=0.7, label='Spearman correlation')
    fig.suptitle(f"Rank correlations between the measures ({model.name}, bases {common.BASES})")
    _finish(fig, opts, 'measure_correlations.png')


if __name__ == "__main__":
    run(setup)
