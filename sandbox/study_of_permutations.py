"""Study of permutations of the digit positions of subcycle addresses."""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from symmetrymath import SymmetricGroup

from cycles.functions.conversion import lcoords_to_tcoord, tcoord_to_lcoords
from cycles.functions.division import compute_level
from cycles.functions.permutation import permutation_matrix
from cycles.plotting.permutation import plot_timeline_permutations, plot_permutation_matrices
from common import BASES, SCALES, TETRAHEDRON_COLORS, PLOTS_DIR, level_colors, fig_data
from runner import study, run

BASE_DIR = PLOTS_DIR / "study_of_permutations"


def setup():
    depth = 3
    level = compute_level(depth, BASES, SCALES, TETRAHEDRON_COLORS)
    return dict(
        depth=depth,
        level=level,
        group=SymmetricGroup(depth),
        colors=level_colors(level),
        # Subcycles drawn with equal widths, one after another
        durations=np.ones(4 ** depth),
        starts=np.cumsum(np.ones(4 ** depth)),
    )


@study
def timeline_permutations(ctx, opts):
    """Timelines of the level as the digit positions are permuted, power after power."""
    element_groups = [[(1, 0, 2), (0, 2, 1), (2, 1, 0)], [(1, 2, 0)]]
    color_keys = ['cmyk_normalised', 'lrgb', 'dharma']

    indices = []
    ax_texts = []
    for elements in element_groups:
        texts = []
        lcs = np.array(ctx.level.lcoords)
        tcoord_rows = [np.array([lcoords_to_tcoord(lc) for lc in lcs])]
        for element in elements:
            for _ in range(ctx.group.order_of(element)):
                tcoords = np.array([lcoords_to_tcoord(np.array(ctx.group.operation(tuple(lc), element))) for lc in lcs])
                tcoord_rows.append(tcoords)
                lcs = [tcoord_to_lcoords(tc, BASES[0], ctx.depth) for tc in tcoords]
                texts.append(f"{ctx.group.identity} → {element}")
        indices.append(np.array(tcoord_rows))
        ax_texts.append(texts)

    fig = plt.figure()
    gs = GridSpec(1, 2, figure=fig, left=0.01, right=0.99, bottom=0.02, top=0.98, wspace=0.02)
    axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])]
    path = BASE_DIR / f"powers/{'+'.join(color_keys)}/depth_{ctx.depth}_permutations_{len(element_groups[-1])}.png"
    plot_timeline_permutations(ctx.durations, ctx.starts, [ctx.colors[key] for key in color_keys],
                               indices, ax_texts, fig, axes, opts.save, fig_data(path, 'a2', 600))


@study(default=False)
def power_matrices(ctx, opts):
    """Permutation matrices of the powers of the cyclic shift of the digit positions."""
    element = tuple(range(1, ctx.depth)) + (0,)
    powers = list(ctx.group.powers(element))
    path = BASE_DIR / f"matrices/depth_{ctx.depth}_powers_of_{''.join(map(str, element))}.png"
    plot_permutation_matrices([permutation_matrix(p, ctx.level.lcoords) for p in powers], powers,
                              opts.save, fig_data(path))


@study(default=False)
def all_matrices(ctx, opts):
    """Permutation matrices of every element of the symmetric group."""
    elements = list(ctx.group.elements)
    path = BASE_DIR / f"matrices/depth_{ctx.depth}_all.png"
    plot_permutation_matrices([permutation_matrix(e, ctx.level.lcoords) for e in elements], elements,
                              opts.save, fig_data(path))


if __name__ == "__main__":
    run(setup)
