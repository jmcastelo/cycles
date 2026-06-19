import numpy as np

from cycles.cycle_division_functions import compute_level, find_identical
from cycles.measure_functions import dharma_measure
from cycles.plotting.duration_plots import plot_bars, plot_stacked_bars

if __name__ == "__main__":
    # Let's compute several levels.
    bases = [4, 2]
    max_depth = 6
    levels = [compute_level(depth, bases) for depth in range(1, max_depth + 1)]

    # Let's focus on a single level
    depth = 1
    lcoords, durations, starts, rgbs, cmyks = levels[depth - 1]

    # Let's sort the subcycle durations of that level.
    idx = np.argsort(np.round(durations, 10), stable=True)

    # And plot them as bars, colored by their RGB.
    # title = f"Sorted subcycle durations for depth {depth}"
    # fig_data = ('a4', 'landscape', f"./plots/unique_durations/sorted_durations_at_depth_{depth}.png", 300)
    # plot_bars(durations[idx], rgbs[idx], title, "Index", "Duration (norm. units)", False, fig_data)

    # What about using Dharma measure for the colors?
    # dharma = np.array([dharma_measure(cmyk) for cmyk in cmyks[idx]])
    # plot_bars(durations[idx], np.tile(dharma[:, np.newaxis], (len(dharma), 3)))

    # The plots show many subcycles with equal durations!
    # Let's count them.
    idd = find_identical(durations)
    colors = [[rgbs[i] for i in idx] for d, idx in idd]
    tick_labels = [d for d, _ in idd]
    title = f"Count of unique subcycle durations for depth {depth}.\n# Unique durations: {len(idd)}"
    fig_data = ('a4', 'landscape', f"./plots/unique_durations/unique_durations_count_at_depth_{depth}.png", 300)
    plot_stacked_bars(colors, tick_labels, title, "Duration (norm. units)", "Count", False, fig_data)

    # There are no subcycles of different depth with equal durations:
    # 1. We find unique subcycle durations for each level.
    # 2. Then find those unique among all the previously found, and count them: all ones, no repetitions.
    # udurations = [u for level in levels for u in np.unique(np.round(level[1], decimals=10), sorted=True)]
    # u, uc = np.unique(udurations, return_counts=True, sorted=True)
    # print(np.all(uc == np.ones(len(uc)), axis=0))

