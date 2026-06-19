import numpy as np

from cycles import compute_level, dharma_measure
from functions.plotting.duration_plots import plot_bars

if __name__ == "__main__":
    bases = [4, 2]
    depth = 5
    level = compute_level(depth, bases)

    lcoords, durations, starts, rgbs, cmyks = level

    # indices = np.argsort(durations)
    # dharma = np.array([dharma_measure(cmyk) for cmyk in cmyks[indices]])
    # plot_bars(durations[indices], np.tile(dharma[:, np.newaxis], (len(dharma), 3)))

    u, uc = np.unique(np.round(durations, decimals=10), return_counts=True, sorted=True)
    print(u)
    plot_bars(uc)