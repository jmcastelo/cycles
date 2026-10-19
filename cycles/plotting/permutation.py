import numpy as np
import matplotlib.pyplot as plt

from cycles.plotting.helpers import format_plot
from cycles.plotting.color import plot_level_bar


def plot_timeline_permutations(
    durations: np.ndarray,
    starts: np.ndarray,
    colors: np.ndarray,
    indices: np.ndarray,
    title: str,
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int, bool]|None=None
):
    height = 1
    hspace = 1

    fig, ax = plt.subplots(nrows=1, ncols=1)

    ax.set_title(title)
    ax.yaxis.set_visible(False)
    ax.xaxis.set_visible(False)
    ax.margins(x=0, y=0)

    for i, idx in enumerate(indices):
        ax.barh(
            y=i * (height + hspace),
            width=durations,
            left=starts,
            height=height,
            align='center',
            color=colors[idx]
        )

    for i in range(len(indices) - 1):
        x0 = starts[indices[i]] + durations[indices[i]] / 2
        x1 = starts[indices[i + 1]] + durations[indices[i + 1]] / 2

        for j in range(len(x0)):
            ax.annotate(
                text='',
                xy=(x0[j], i * (height + hspace) + height / 2),
                xytext=(x1[j], (i + 1) * (height + hspace) - height / 2),
                annotation_clip=False,
                arrowprops=dict(
                    arrowstyle='-',
                    color='k',
                    linewidth=0.5,
                    shrinkA=0,
                    shrinkB=0,
                    antialiased=True
                )
            )

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.show()