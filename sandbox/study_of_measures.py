"""Study of the dharma and purity measures of subcycles."""

import numpy as np

from cycles.functions.division import partition_level
from cycles.plotting.color import plot_quality_grid, plot_purity_vs_dharma, plot_quality_scatter_3d
from cycles.plotting.generic import plot_y_vs_x
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


if __name__ == "__main__":
    run(setup)
