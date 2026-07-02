import numpy as np

from cycles.cycle_division_functions import compute_level, find_identical, count_digits, equality_test, \
    duration_quotient, compute_all_distances, compute_consecutive_distances
from cycles.measure_functions import dharma_measure
from cycles.plotting.duration_plots import *
from cycles.plotting.generic_plots import *
from cycles.color_functions import lcoords_to_lrgb
from cycles.analysis_functions import autocorrelation
from cycles.conversion_functions import lcoords_to_int


if __name__ == "__main__":
    # Let's compute several levels.
    bases = [4, 2, 1]
    max_depth = 6
    levels = [compute_level(depth, bases) for depth in range(1, max_depth + 1)]
    lcoords, durations, starts, cmyks, rgbs, dharmas, purities = zip(*levels)

    lrgbs = [np.apply_along_axis(lcoords_to_lrgb, 1, coords) for coords in lcoords]
    dharma_colors = [np.array([np.full(3, d) for d in dharma]) for dharma in dharmas]
    purity_colors = [np.array([np.full(3, p) for p in purity]) for purity in purities]

    colors = {
        'cmyk': [rgb[:, 0] for rgb in rgbs],
        'wcmy': [rgb[:, 1] for rgb in rgbs],
        'lrgb': [lrgb[:, -1] for lrgb in lrgbs],
        'dharma': dharma_colors,
        'purity': purity_colors
    }

    color_key = 'lrgb'

    idurations = [find_identical(durs) for durs in durations]

    base_dir = f"./plots/study_of_durations"

    '''
    for depth, (idd, coords, durs, strs, clrs) in enumerate(zip(idurations, lcoords, durations, starts, colors[color_key]), 1):
        title = f"Location and count of subcycle durations. Total of {4 ** depth} subcycles at depth {depth}"
        fig_data = ('a3', 'landscape', f"{base_dir}/trigraphs/{color_key}/trigraph_at_depth_{depth}.png", 300)
        plot_durations_trigraph(idd, coords, durs, strs, clrs, title, True, fig_data)
    '''
    '''
    # Let's sort the subcycle durations and plot them as bars
    for depth, (durs, colors) in enumerate(zip(durations, colors[color_key]), 1):
        idx = np.argsort(np.round(durs, 10), stable=True)
        title = f"Sorted subcycle durations for depth {depth}"
        fig_data = ('a4', 'landscape', f"./plots/unique_durations/{color_key}/sorted_durations_at_depth_{depth}.png", 300)
        plot_bars(durs[idx], colors[idx], title, "Index", "Duration (norm. units)", False, fig_data)
    '''
    '''
    # The plots show many subcycles with equal durations! Let's count them
    for depth, (idd, coords, colors) in enumerate(zip(idurations, lcoords, colors[color_key]), 1):
        title = f"Count of subcycle durations. Total of {4 ** depth} subcycles at depth {depth}"
        fig_data = ('a4', 'landscape', f"{base_dir}/count/{color_key}/count_at_depth_{depth}.png", 300)
        plot_stacked_counts(idd, coords, colors, title, "Duration (norm. units)", "Count", True, fig_data)
    '''
    '''
    title = f"Location of unique subcycle durations for depth {depth}.\n# Unique durations: {len(idd)}"
    fig_data = ('a4', 'landscape', f"./plots/unique_durations/{color_key}/unique_durations_location_at_depth_{depth}.png", 300)
    plot_stacked_spaced_bars(idd, level, title, "Time (norm. units)", "Duration (norm. units)", True, fig_data)
    '''
    '''
    counts = [count_digits(lcoord) for lcoord in lcoords]
    cdiffs = [[c1 - c2 for c2 in counts] for c1 in counts]
    # test = np.apply_along_axis(equality_test, 2, count_diffs)
    # plot_equality_test(starts, durations, test)
    dquot = np.apply_along_axis(duration_quotient, 2, cdiffs)
    plot_equality_test(starts, durations, dquot)
    '''
    '''
    lcdistances = [[(dur, compute_consecutive_distances(strs, idx)) for dur, idx in idd] for idd, strs in zip(idurations, starts)]
    for cdistances in lcdistances:
        durs, data = zip(*cdistances)
        idx, dists, ndists, ratios = zip(*data)
        plot_stacked_bars(list(durs), list(dists))
    '''
    '''
    for depth, (duration, color) in enumerate(zip(durations, colors[color_key]), 1):
        max_delay = 20
        title = f"Return plots (log-log) at depth {depth}"
        label = 'Duration'
        fig_data = (
            'a3',
            'landscape',
            f"{base_dir}/return_plots/{color_key}/return_plots_max_delay_{max_delay}_at_depth_{depth}.png",
            300,
            False
        )
        return_plot(duration, max_delay, color, title, label, False, True, fig_data)
    '''

    indices = [[lcoords_to_int(coord, True) for coord in coords] for coords in lcoords]
    print(durations[1])
    print(durations[1][indices[1]])
    print(indices[1])
    acorr_data = [autocorrelation(durs[indices[i]]) for i, durs in enumerate(durations)]
    lags, acorrs = zip(*acorr_data)
    title = 'Auto-correlation of subcycle durations'
    labels = [f"Depth {d}" for d in range(1, max_depth + 1)]
    fig_data = (
        'a4',
        'landscape',
        f"{base_dir}/auto_correlations/auto_correlations_up_to_depth_{max_depth}.png",
        300,
        True
    )
    grid_of_plots(lags, acorrs, title, labels, 'Lag', (0, 1), False, fig_data)
    # plot_auto_correlations(durations, title, labels, True, fig_data)

    # There are no subcycles of different depth with equal durations:
    # 1. We find unique subcycle durations for each level.
    # 2. Then find those unique among all the previously found, and count them: all ones, no repetitions.
    # udurations = [u for level in levels for u in np.unique(np.round(level[1], decimals=10), sorted=True)]
    # u, uc = np.unique(udurations, return_counts=True, sorted=True)
    # print(np.all(uc == np.ones(len(uc)), axis=0))

