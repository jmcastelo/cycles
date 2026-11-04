"""Plots of permutations of the subcycles of a level."""

import numpy as np
import matplotlib.pyplot as plt

from cycles.plotting.helpers import format_plot


def plot_timeline_permutations(
    durations: np.ndarray,
    starts: np.ndarray,
    colors: list[np.ndarray],
    perm_indices: list[np.ndarray],
    ax_texts: list[str],
    fig,
    axes,
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int, bool]|None=None
):
    """
    Timelines of a level under successive permutations.

    Each axis in ``axes`` gets the arrays of ``perm_indices`` (one per row): in a
    row, subcycle ``k`` is drawn at the time slot of subcycle ``indices[k]``.
    Each subcycle is split into sub-rows, one per color array in ``colors``.
    Lines join the positions of each subcycle in consecutive rows, and
    ``ax_texts`` label the rows.

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    """
    height = 1
    hspace = 2
    sub_height = height / len(colors)

    for k, (ax, indices, texts) in enumerate(zip(axes, perm_indices, ax_texts)):
        # ax.spines['bottom'].set_color('w')
        # ax.spines['top'].set_color('w')
        # ax.spines['right'].set_color('w')
        # ax.spines['left'].set_color('w')
        # ax.xaxis.set_visible(False)
        # ax.yaxis.set_visible(False)
        ax.axis('off')
        ax.set_xmargin(0)
        ax.set_ymargin(0)

        for i, idx in enumerate(indices):
            for j, clrs in enumerate(colors):
                ax.barh(
                    y=i * (height + hspace) + j * sub_height,
                    width=durations[idx],
                    left=starts[idx],
                    height=sub_height,
                    align='edge',
                    color=clrs,
                    edgecolor='k',
                    linewidth=0.1
                )

        for i, text in enumerate(texts):
            ax.text(
                starts[0],
                i * (height + hspace) + height + hspace / 2,
                text,
                fontsize=8,
                rotation=90,
                ha='center',
                va='center',
                color='k'
            )
            # t.set_in_layout(in_layout=False)

        for i in range(len(indices) - 1):
            x0 = starts[indices[i]] + durations[indices[i]] / 2
            x1 = starts[indices[i + 1]] + durations[indices[i + 1]] / 2

            for j in range(len(x0)):
                ax.annotate(
                    text='',
                    xy=(x1[j], (i + 1) * (height + hspace)),
                    xytext=(x0[j], i * (height + hspace) + height),
                    arrowprops=dict(
                        arrowstyle='-',
                        color='k',
                        linewidth=0.25,
                        antialiased=True,
                        shrinkA=0,
                        shrinkB=0
                    )
                )

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    # plt.tight_layout()
    plt.show()


def plot_permutation_matrices(
    matrices: list[np.ndarray],
    permutation_labels: list[tuple],
    save_fig: bool = False,
    fig_data: tuple[str, str, str, int, bool] | None = None
):
    """
    Grid of permutation matrices drawn as images, titled with their permutations.

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    """
    nrows = int(np.sqrt(len(matrices)))
    ncols = int(len(matrices) / nrows)

    fig = plt.figure()
    k = 0
    for i in range(nrows):
        for j in range(ncols):
            ax = fig.add_subplot(nrows, ncols, k+1)
            ax.pcolormesh(
                np.arange(0, matrices[k].shape[0], 1),
                np.arange(0, matrices[k].shape[1], 1),
                matrices[k]
            )
            ax.set_title(permutation_labels[k])
            ax.axis('off')
            ax.set_aspect('equal')
            k += 1

    fig.tight_layout()
    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0.2, wspace=0.2)
    plt.show()
