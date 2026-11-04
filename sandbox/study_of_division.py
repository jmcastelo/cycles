"""Study of the division of the cycle itself: consistency checks and ring diagrams."""

import numpy as np
import matplotlib.pyplot as plt

from cycles.functions.conversion import (
    lcoords_to_tcoord, tcoord_to_lcoords, lcoords_to_fractional, fractional_to_lcoords,
)
from cycles.functions.division import find_identical, find_lcoords, select_subcycle
from cycles.plotting.sector import plot_comparison_graph, plot_identical_graph, plot_circle_diagram
from common import PLOTS_DIR, compute_levels, save_figure
from runner import study, run

BASE_DIR = PLOTS_DIR / "study_of_division"


def setup():
    return dict(levels=compute_levels(4))


@study
def checks(ctx, opts):
    """Check durations, starts and the conversions between address forms at every depth."""
    for depth, level in enumerate(ctx.levels, 1):
        lcoords, durations, starts = level.lcoords, level.durations, level.starts
        results = {
            'durations add up to 1': np.isclose(durations.sum(), 1),
            'subcycles are contiguous': np.allclose(starts[1:], starts[:-1] + durations[:-1]),
            'last subcycle ends at 1': np.isclose(starts[-1] + durations[-1], 1),
            'tcoord <-> lcoords': all(
                lcoords_to_tcoord(tcoord_to_lcoords(i, 4, depth)) == i and (tcoord_to_lcoords(i, 4, depth) == lc).all()
                for i, lc in enumerate(lcoords)),
            'fraction <-> lcoords': all(
                list(fractional_to_lcoords(lcoords_to_fractional(lc, 4), 4)) == list(np.trim_zeros(lc, 'b'))
                for lc in lcoords),
            'time -> lcoords': all(
                (find_lcoords(s + d / 2, depth) == lc).all() for lc, s, d in zip(lcoords, starts, durations)),
        }
        print(f"depth {depth}: " + ', '.join(f"{name} {'OK' if ok else 'FAILED'}" for name, ok in results.items()))


@study(default=False)
def level_table(ctx, opts):
    """Print every subcycle of depth 3: index, address, base-4 fraction, duration and start."""
    level = ctx.levels[2]
    print(f"{'index':>5}  lcoords  {'fraction':>8}  {'duration':>8}  {'start':>8}")
    for lcoords, duration, start in zip(level.lcoords, level.durations, level.starts):
        print(f"{lcoords_to_tcoord(lcoords):5d}  {''.join(map(str, lcoords)):>7}  "
              f"{lcoords_to_fractional(lcoords, 4):8.6f}  {duration:8.6f}  {start:8.6f}")


@study
def comparison_rings(ctx, opts):
    """Rings of the four ages and of the four subdivisions of each age."""
    selectors = [([], ctx.levels[0])] + [([age], ctx.levels[1]) for age in range(4)]
    plot_comparison_graph([select_subcycle(prefix, level) for prefix, level in selectors])


@study(default=False)
def identical_rings(ctx, opts):
    """Rings of depths 2 and 3 with arcs joining the subcycles of equal duration."""
    fig, axs = plt.subplots(1, 2, figsize=(25, 50))
    for ax, level in zip(axs, ctx.levels[1:3]):
        plot_identical_graph(ax, level, find_identical(level.durations), ref_level=ctx.levels[0],
                             one_to_many=True, show_labels=False)
    plt.tight_layout()
    if opts.save:
        save_figure(fig, BASE_DIR / "identical_rings_depths_2_3.png")
    plt.show()


@study(default=False)
def circle_diagram(ctx, opts):
    """Nested circles: each subcycle a circle around the circle of its parent."""
    plot_circle_diagram(ctx.levels, 4)


if __name__ == "__main__":
    run(setup)
