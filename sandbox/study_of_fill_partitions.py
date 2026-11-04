"""Study of the partition of a time span into subcycles."""

import numpy as np

from cycles.functions.color import lcoords_to_lrgb
from cycles.functions.division import fill_partition, find_total_lcoords, compute_duration, compute_start
from cycles.plotting.partition import plot_partition_sectors
from runner import study, run


def setup():
    t = 64800    # length of the whole cycle
    dt = 10      # length of the reference windows
    t1, t2 = t - 1000, t
    lcoords, locs, durations, gaps, n_windows = fill_partition(t1, t2, t, dt, 1)
    return dict(t=t, dt=dt, t1=t1, t2=t2, lcoords=lcoords, locs=locs, durations=durations,
                gaps=gaps, n_windows=n_windows)


@study
def partition_sectors(ctx, opts):
    """Fill the last 1000 units with subcycles and draw them against the reference windows."""
    total = np.sum(ctx.durations)
    print(f"windows: {ctx.n_windows}; span {ctx.t2 - ctx.t1}, covered {total}, missing {ctx.t2 - ctx.t1 - total}")
    print(f"total gap: {sum(gap for _, gap in ctx.gaps)}")
    colors = np.array([lcoords_to_lrgb(lc)[-1] if lc is not None else np.zeros(3) for lc in ctx.lcoords])
    plot_partition_sectors(ctx.t1, ctx.t2, ctx.dt, ctx.durations, colors)


@study(default=False)
def partition_listing(ctx, opts):
    """Print the subcycles of the partition with their start and duration."""
    subcycles = [(lc, d) for lc, d in zip(ctx.lcoords, ctx.durations) if lc is not None]
    for i, (loc, (lc, duration)) in enumerate(zip(ctx.locs, subcycles), 1):
        print(i, lc, np.round(loc, 10), np.round(duration, 10))


@study(default=False)
def regular_partition(ctx, opts):
    """Print, for each window start of the whole cycle, the subcycle found there."""
    for time in np.arange(0, ctx.t, ctx.dt, dtype=float):
        lcoords = find_total_lcoords(time, ctx.dt, ctx.t)
        print(time, ctx.t * compute_start(lcoords), lcoords, np.round(ctx.t * compute_duration(lcoords), 6))


if __name__ == "__main__":
    run(setup)
