import numpy as np

from cycles.cycle_division_functions import find_total_lcoords, compute_duration, compute_start, fill_partition, weights
from cycles.color_functions import lcoords_to_cmyk, cmyk_to_rgb, lcoords_to_lrgb
from cycles.plotting.partition_plots import plot_partition_sectors

if __name__ == "__main__":
    t = 64800
    dt = 10

    # rpart_times = np.arange(0, t, dt, dtype=float)
    # rpart_lcoords = [find_total_lcoords(x, dt, t) for x in rpart_times]
    # rpart_durations = [np.round(t * compute_duration(lcoords), 6) for lcoords in rpart_lcoords]

    # for time, lcoords, duration in zip(rpart_times, rpart_lcoords, rpart_durations):
    #     print(time, t * compute_start(lcoords), lcoords, duration)

    t1 = t - 1000
    t2 = t
    flcoords, flocs, fdurs, ddurs, nref = fill_partition(t1, t2, t, dt, 1)

    # for i, (loc, coord, dur) in enumerate(zip(flocs, flcoords, fdurs), 1):
    #     print(i, coord, np.round(loc, 10), np.round(dur, 10))
    print(nref)
    print(t2 - t1, np.sum(fdurs), t2 - t1 - np.sum(fdurs))
    dlocs, dd = zip(*ddurs)
    print(sum(dd))

    # colors = np.array([np.apply_along_axis(cmyk_to_rgb, 1, lcoords_to_cmyk(lcoords, weights(2, len(lcoords))) if lcoords is not None else np.zeros((2, 4))) for lcoords in flcoords])
    colors = np.array([lcoords_to_lrgb(lcoords)[-1] if lcoords is not None else np.zeros((3,)) for lcoords in flcoords])

    # plot_partition_sectors(t1, t2, dt, fdurs, colors[:, 1])
    plot_partition_sectors(t1, t2, dt, fdurs, colors)