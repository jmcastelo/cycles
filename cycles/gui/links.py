"""
Lines joining the highlighted subcycles in the plots (Measures, Color space): the steps of the ⟨σ⟩ orbit of the
selection, in order and with arrows, or the swaps of neighbouring digits between the orderings of its ages (the
subcycles of the same composition). See ``CycleState.highlight_links``.
"""

import numpy as np
from matplotlib.collections import LineCollection
from mpl_toolkits.mplot3d.art3d import Line3DCollection

from cycles.gui.state import PERMUTATION_COLOR


def draw_links(ax, links, positions: dict, points: np.ndarray) -> list:
    """
    Draw ``links`` (``CycleState.highlight_links``) on ``ax``, 2D or 3D. ``positions`` maps level indices to rows
    of ``points`` (the plotted coordinates, (N, 2) or (N, 3)); pairs with an end not plotted are left out.
    Returns the artists drawn.
    """
    if links is None:
        return []
    kind, pairs = links
    kept = [(positions[int(a)], positions[int(b)]) for a, b in pairs if int(a) in positions and int(b) in positions]
    if not kept:
        return []
    starts = points[[a for a, _ in kept]]
    ends = points[[b for _, b in kept]]
    three_d = points.shape[1] == 3
    if kind == 'swaps':
        alpha = 0.6 if len(kept) <= 100 else 0.35 if len(kept) <= 600 else 0.2
        segments = np.stack([starts, ends], axis=1)
        collection = (Line3DCollection if three_d else LineCollection)(
            segments, colors='0.25', linewidths=0.7, alpha=alpha, zorder=3)
        if three_d:
            ax.add_collection3d(collection)
        else:
            ax.add_collection(collection)
        return [collection]
    # the orbit: one arrow per step, curved a little so that a step and its way back (a swap) both show
    if three_d:
        segments = np.stack([starts, ends], axis=1)
        collection = Line3DCollection(segments, colors=PERMUTATION_COLOR, linewidths=1.4, alpha=0.9, zorder=3)
        ax.add_collection3d(collection)
        # a dot near the end of each step gives its direction
        heads = starts + 0.8 * (ends - starts)
        dots = ax.scatter(heads[:, 0], heads[:, 1], heads[:, 2], s=26, color=PERMUTATION_COLOR, depthshade=False)
        return [collection, dots]
    return [ax.annotate('', xy=tuple(b), xytext=tuple(a),
                        arrowprops=dict(arrowstyle='-|>', color=PERMUTATION_COLOR, lw=1.3, alpha=0.9,
                                        shrinkA=4, shrinkB=4, mutation_scale=10,
                                        connectionstyle='arc3,rad=0.15'), zorder=3)
            for a, b in zip(starts, ends)]
