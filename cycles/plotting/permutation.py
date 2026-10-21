import numpy as np
import matplotlib.pyplot as plt

from cycles.plotting.helpers import format_plot


def plot_timeline_permutations(
    durations: np.ndarray,
    starts: np.ndarray,
    colors: np.ndarray,
    indices: np.ndarray,
    permutation_matrix: np.ndarray,
    title: str,
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int, bool]|None=None
):
    height = 1
    hspace = 2

    fig, axs = plt.subplots(nrows=2, ncols=1, height_ratios=[7, 1])

    axs[0].set_title(title)
    axs[0].set_axis_off()
    axs[0].margins(x=0, y=0)

    for i, idx in enumerate(indices):
        axs[0].barh(
            y=i * (height + hspace),
            width=durations[idx],
            left=starts[idx],
            height=height,
            align='edge',
            color=colors
        )

    for i in range(len(indices) - 1):
        x0 = starts[indices[i]] + durations[indices[i]] / 2
        x1 = starts[indices[i + 1]] + durations[indices[i + 1]] / 2

        for j in range(len(x0)):
            axs[0].annotate(
                text='',
                xy=(x1[j], (i + 1) * (height + hspace)),
                xytext=(x0[j], i * (height + hspace) + height),
                arrowprops=dict(
                    arrowstyle='-',
                    color=colors[j],
                    linewidth=0.7,
                    antialiased=True,
                    shrinkA=0,
                    shrinkB=0
                )
            )

    axs[1].pcolormesh(
        np.arange(0, permutation_matrix.shape[0], 1),
        np.arange(0, permutation_matrix.shape[1], 1),
        permutation_matrix
    )
    axs[1].axis('off')
    # axs[1].set_aspect('equal')

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.show()


def plot_permutation_matrices(
    matrices: list[np.ndarray],
    permutation_labels: list[tuple],
    save_fig: bool = False,
    fig_data: tuple[str, str, str, int, bool] | None = None
):
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
