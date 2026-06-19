import numpy as np
import matplotlib.pyplot as plt

from cycles.plotting.helpers import save_plot


def plot_bars(
    values: np.ndarray,
    colors: np.ndarray,
    title: str='',
    xlabel: str='',
    ylabel: str='',
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int]|None=None
):
    indices = [n+1 for n in range(len(values))]

    fig, ax = plt.subplots()

    ax.bar(
        x=indices,
        height=values,
        width=1,
        bottom=0,
        align='center',
        color=colors,
        # edgecolor='gray',
        linewidth=0
    )

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.margins(x=0, y=0)

    plt.tight_layout()
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


def plot_stacked_bars(
    colors: list[list[np.ndarray]],
    tick_labels: list[str],
    title: str = '',
    xlabel: str = '',
    ylabel: str = '',
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int]|None=None
):
    fig, ax = plt.subplots()

    for x, cc in enumerate(colors, 1):
        bottom = [b for b in range(len(cc))]
        # for b, c in enumerate(cc):
        ax.bar(
            x=x,
            height=1,
            width=1,
            bottom=bottom,
            align='center',
            color=cc,
            # edgecolor='gray',
            linewidth=0,
        )

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.margins(x=0, y=0)

    ax.set_xticks([x for x in range(1, len(colors) + 1)])
    formatted_labels = [f"{val:.3e}" for val in tick_labels]
    ax.set_xticklabels(formatted_labels, rotation=90, ha='center', va='top', fontsize=7)

    plt.tight_layout()
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)