"""Study of subcycle durations: which subcycles share a duration, where and how many."""

import numpy as np

from cycles.functions.analysis import autocorrelation
from cycles.functions.conversion import lcoords_to_tcoord
from cycles.functions.division import RGB_KEYS, DEFAULT_COLOR_KEY, find_identical, indentical_duration_lcoords, compute_duration
from cycles.functions.duration import count_digits, duration_quotient, compute_consecutive_distances
from cycles.plotting.duration import (
    plot_bars, plot_stacked_bars, plot_stacked_counts, plot_stacked_spaced_bars,
    plot_durations_trigraph, plot_equality_test, plot_duration_bars,
)
from cycles.plotting.generic import return_plot, grid_of_plots
from common import PLOTS_DIR, compute_levels, level_colors, fig_data
from runner import study, run

BASE_DIR = PLOTS_DIR / "study_of_durations"


def setup():
    max_depth = 4
    levels = compute_levels(max_depth)
    color_key = 'cmyk_scaled'  # any of common.COLOR_KEYS
    return dict(
        max_depth=max_depth,
        levels=levels,
        color_key=color_key,
        # Level RGB variant for the plots that take a whole Level
        variant=color_key if color_key in RGB_KEYS else DEFAULT_COLOR_KEY,
        colors=[level_colors(level)[color_key] for level in levels],
        identical=[find_identical(level.durations) for level in levels],
    )


@study
def trigraph(ctx, opts):
    """Location and count of the subcycles of each duration, per depth."""
    for depth, (idd, level, colors) in enumerate(zip(ctx.identical, ctx.levels, ctx.colors), 1):
        title = f"Location and count of subcycle durations. Total of {4 ** depth} subcycles at depth {depth}"
        path = BASE_DIR / f"trigraphs/{ctx.color_key}/trigraph_at_depth_{depth}.png"
        plot_durations_trigraph(idd, level.lcoords, level.durations, level.starts, colors, title,
                                opts.save, fig_data(path, 'a3', 600))


@study(default=False)
def sorted_durations(ctx, opts):
    """Subcycle durations sorted from the shortest, as bars, per depth."""
    for depth, (level, colors) in enumerate(zip(ctx.levels, ctx.colors), 1):
        idx = np.argsort(np.round(level.durations, 10), stable=True)
        path = PLOTS_DIR / f"unique_durations/{ctx.color_key}/sorted_durations_at_depth_{depth}.png"
        plot_bars(level.durations[idx], colors[idx], f"Sorted subcycle durations for depth {depth}",
                  "Index", "Duration (norm. units)", opts.save, fig_data(path))


@study(default=False)
def counts(ctx, opts):
    """Number of subcycles with each duration, labelled with their addresses, per depth."""
    for depth, (idd, level, colors) in enumerate(zip(ctx.identical, ctx.levels, ctx.colors), 1):
        title = f"Count of subcycle durations. Total of {4 ** depth} subcycles at depth {depth}"
        path = BASE_DIR / f"count/{ctx.color_key}/count_at_depth_{depth}.png"
        plot_stacked_counts(idd, level.lcoords, colors, title, "Duration (norm. units)", "Count",
                            opts.save, fig_data(path))


@study(default=False)
def spaced_bars(ctx, opts):
    """Where in time the subcycles of each duration lie, per depth."""
    for depth, (idd, level) in enumerate(zip(ctx.identical, ctx.levels), 1):
        title = f"Location of unique subcycle durations for depth {depth}.\n# Unique durations: {len(idd)}"
        path = PLOTS_DIR / f"unique_durations/{ctx.variant}/unique_durations_location_at_depth_{depth}.png"
        plot_stacked_spaced_bars(idd, level, title, "Time (norm. units)", "Duration (norm. units)",
                                 opts.save, fig_data(path), rgb_key=ctx.variant)


@study(default=False)
def equality_test(ctx, opts):
    """Duration ratio of every pair of subcycles, as a color map, per depth."""
    for level in ctx.levels:
        digit_counts = np.array([count_digits(lcoords) for lcoords in level.lcoords])
        cdiffs = digit_counts[:, None, :] - digit_counts[None, :, :]
        plot_equality_test(level.starts, level.durations, np.apply_along_axis(duration_quotient, 2, cdiffs))


@study(default=False)
def consecutive_distances(ctx, opts):
    """Distances between consecutive subcycles of equal duration, stacked per duration, per depth."""
    for idd, level in zip(ctx.identical, ctx.levels):
        durations, data = zip(*[(duration, compute_consecutive_distances(level.starts, idx)) for duration, idx in idd])
        _, distances, _, _ = zip(*data)
        plot_stacked_bars(list(durations), list(distances))


@study(default=False)
def return_plots(ctx, opts):
    """Return maps of the sequence of durations (log-log), per depth."""
    max_delay = 20
    for depth, (level, colors) in enumerate(zip(ctx.levels, ctx.colors), 1):
        path = BASE_DIR / f"return_plots/{ctx.color_key}/return_plots_max_delay_{max_delay}_at_depth_{depth}.png"
        return_plot(level.durations, max_delay, colors, f"Return plots (log-log) at depth {depth}",
                    'Duration', False, opts.save, fig_data(path, 'a3'))


@study(default=False)
def autocorrelations(ctx, opts):
    """Autocorrelation of the durations, ordered by the reversed-digit index, per depth."""
    series = []
    for level in ctx.levels:
        indices = [lcoords_to_tcoord(lcoords, reverse=True) for lcoords in level.lcoords]
        series.append(autocorrelation(level.durations[indices]))
    lags, acorrs = zip(*series)
    labels = [f"Depth {depth}" for depth in range(1, ctx.max_depth + 1)]
    path = BASE_DIR / f"auto_correlations/auto_correlations_up_to_depth_{ctx.max_depth}.png"
    grid_of_plots(lags, acorrs, 'Auto-correlation of subcycle durations', labels, 'Lag', (0, 1),
                  opts.save, fig_data(path, tight_layout=True))


@study(default=False)
def duration_bars(ctx, opts):
    """All subcycles of every depth as squares of side equal to their duration."""
    aspect = (1, 1)
    path = BASE_DIR / f"durations/durations_1_to_{ctx.max_depth}_aspect_{aspect[0]}_{aspect[1]}.png"
    plot_duration_bars(ctx.levels, 1, ctx.max_depth, aspect, opts.save, fig_data(path, dpi=600),
                       rgb_key=ctx.variant)


@study(default=False)
def unique_across_depths(ctx, opts):
    """Check that subcycles of different depths never share a duration."""
    durations = [u for level in ctx.levels for u in np.unique(np.round(level.durations, 10))]
    _, repeats = np.unique(durations, return_counts=True)
    print("Durations shared between depths:", int(np.sum(repeats > 1)))


@study(default=False)
def equal_duration_groups(ctx, opts):
    """Print the groups of equal duration at depth 3, and the reorderings of one address."""
    level = ctx.levels[2]
    for duration, idx in ctx.identical[2]:
        print(f"{duration:.6f}: " + ' '.join(''.join(map(str, level.lcoords[i])) for i in idx))
    lcoords = [0, 3, 1]
    print(f"\nReorderings of {lcoords} (all of duration {compute_duration(lcoords):.6f}):")
    for reordering in sorted(indentical_duration_lcoords(lcoords)):
        print(reordering, 'tcoord', lcoords_to_tcoord(np.array(reordering)))


if __name__ == "__main__":
    run(setup)
