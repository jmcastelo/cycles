import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib import colormaps
from matplotlib.ticker import MaxNLocator

from cycles.plotting.helpers import format_plot
from cycles.cycle_division_functions import same_digit_counts


def plot_bars(
    values: np.ndarray,
    colors: np.ndarray,
    title: str='',
    xlabel: str='',
    ylabel: str='',
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int, bool]|None=None
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

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.show()


def plot_stacked_bars(
    xxx: list,
    values: list[np.ndarray],
    title: str='',
    xlabel: str='',
    ylabel: str='',
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int]|None=None
):
    fig, ax = plt.subplots()

    fig.suptitle(title)

    max_value = np.max(np.array([np.max(values[i], axis=0) if len(values[i]) > 0 else 0 for i in range(len(values))]))

    for i, x in enumerate(xxx):
        colors = plt.colormaps['RdYlGn'](values[i] / max_value)
        bottoms = np.insert(np.cumsum(values[i][:-1], axis=0), 0, 0)
        for j, (value, color) in enumerate(zip(values[i], colors)):
            bar = ax.bar(
                x=i,
                height=value,
                width=1,
                bottom=bottoms[j],
                align='center',
                linewidth=0.5,
                edgecolor='gray',
                color=color
            )
            r, g, b, _ = tuple(color)
            text_color = 'white' if r * g * b < 0.5 else 'darkgrey'
            ax.bar_label(bar, label_type='center', color=text_color, fmt='%.3f')

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.margins(x=0, y=0)

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.show()


def plot_stacked_counts(
    idd: list[tuple],
    coords: np.ndarray,
    colors: np.ndarray,
    title: str = '',
    xlabel: str = '',
    ylabel: str = '',
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int]|None=None
):
    fig, ax = plt.subplots()

    fig.suptitle(title)

    # Counts
    for i, (dur, idx) in enumerate(idd):
        for j in range(len(idx)):
            hatch = '///'
            if same_digit_counts(coords[idx[0]], coords[idx[j]]):
                hatch = None
            color = colors[idx[j]]
            r, g, b = tuple(color)
            text_color = 'white' if (r + g + b) / 3 < 0.5 else 'black'
            bar = ax.bar(
                x=i+1,
                width=1,
                height=1,
                bottom=j,
                align='center',
                color=color,
                linewidth=0.1,
                edgecolor='gray',
                hatch=hatch,
                hatchcolor=text_color
            )
            label = ''.join([str(c) for c in coords[idx[j]]])
            ax.bar_label(bar, labels=[label], label_type='center', color=text_color, fontsize=8)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.margins(x=0, y=0)

    ax.set_xticks([x for x in range(1, len(idd) + 1)])
    formatted_labels = [f"{val:.3e}" for val, _ in idd]
    ax.set_xticklabels(formatted_labels, rotation=90, ha='center', va='top', fontsize=9)

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.show()


def plot_stacked_spaced_bars(
    idd: list[tuple],
    level: tuple,
    title: str = '',
    xlabel: str = '',
    ylabel: str = '',
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int]|None=None
):
    fig, axs = plt.subplots(
        nrows=2,
        ncols=1,
        sharex=True,
        sharey=False,
        height_ratios=[10, 1],
        gridspec_kw=dict(hspace=0, wspace=0)
    )

    _, durations, starts, rgbs = level
    for i, (dur, idx) in enumerate(idd):
        axs[0].barh(
            y=i+1,
            width=dur,
            height=1,
            left=starts[idx],
            align='center',
            color=rgbs[idx],
            linewidth=0
        )

    axs[0].set_title(title)
    axs[0].xaxis.set_visible(False)
    axs[0].set_ylabel(ylabel)
    axs[0].margins(x=0, y=0)

    axs[0].set_yticks([x+1 for x in range(len(idd))])
    formatted_labels = [f"{val:.3e}" for val, _ in idd]
    axs[0].set_yticklabels(formatted_labels, rotation=0, ha='right', va='center', fontsize=7)

    axs[1].barh(
        y=0,
        width=durations,
        height=1,
        left=starts,
        align='center',
        color=rgbs
    )
    axs[1].yaxis.set_visible(False)
    axs[1].set_xlabel(xlabel)
    axs[1].margins(x=0, y=0)

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.show()


def plot_durations_trigraph(
    idd: list[tuple],
    coords: np.ndarray,
    durations: np.ndarray,
    starts: np.ndarray,
    colors: np.ndarray,
    title: str = '',
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int]|None=None
):
    fig, axs = plt.subplots(
        nrows=2,
        ncols=2,
        sharex=False,
        sharey=False,
        height_ratios=[10, 1],
        width_ratios=[4, 1],
        gridspec_kw=dict(hspace=0.01, wspace=0.01)
    )

    fig.suptitle(title)

    # Unique durations at their location
    for i, (dur, idx) in enumerate(idd):
        for j in range(len(idx)):
            hatch = '///'
            if same_digit_counts(coords[idx[0]], coords[idx[j]]):
                hatch = None
            axs[0, 0].barh(
                y=i+1,
                width=dur,
                height=1,
                left=starts[idx[j]],
                align='center',
                color=colors[idx[j]],
                linewidth=0.1,
                edgecolor='gray',
                hatch=hatch,
                hatchcolor=(1-colors[idx[j]]) * 0.5
            )

    axs[0, 0].xaxis.set_visible(False)
    axs[0, 0].set_ylabel('Duration (norm. units)')
    axs[0, 0].margins(x=0, y=0)
    # axs[0, 0].spines['bottom'].set_color('white')
    # axs[0, 0].spines['right'].set_color('white')

    axs[0, 0].set_yticks([x for x in range(1, len(idd) + 1)])
    formatted_labels = [f"{val:.3e}" for val, _ in idd]
    axs[0, 0].set_yticklabels(formatted_labels, rotation=0, ha='right', va='center', fontsize=9)

    # Time line
    axs[1, 0].barh(
        y=0,
        width=durations,
        height=1,
        left=starts,
        align='center',
        color=colors,
        linewidth=0
    )
    axs[1, 0].yaxis.set_visible(False)
    axs[1, 0].set_xlabel('Time (norm. units)')
    axs[1, 0].margins(x=0, y=0)
    # axs[1, 0].spines['top'].set_color('white')

    times = [0.0, 0.4, 0.7, 0.9, 1.0]
    axs[1, 0].set_xticks(times)
    formatted_labels = [f"{t:.1f}" for t in times]
    axs[1, 0].set_xticklabels(formatted_labels, rotation=0, ha='center', va='top', fontsize=9)

    # Counts
    for i, (dur, idx) in enumerate(idd):
        for j in range(len(idx)):
            hatch = '///'
            if same_digit_counts(coords[idx[0]], coords[idx[j]]):
                hatch = None
            bar = axs[0, 1].barh(
                y=i+1,
                height=1,
                width=1,
                left=j,
                align='center',
                color=colors[idx[j]],
                linewidth=0.1,
                edgecolor='gray',
                hatch=hatch,
                hatchcolor=(1-colors[idx[j]]) * 0.5
            )
            label = ''.join([str(c) for c in coords[idx[j]]])
            axs[0, 1].bar_label(bar, labels=[label], label_type='center', fontsize=8/len(label), rotation=-90)

    axs[0, 1].xaxis.set_visible(False)

    axs[0, 1].set_ylabel('Count')
    axs[0, 1].yaxis.tick_right()
    axs[0, 1].yaxis.set_label_position('right')
    axs[0, 1].set_yticks([x for x in range(1, len(idd) + 1)])
    formatted_labels = [f"{len(idx):.0f}" for _, idx in idd]
    axs[0, 1].set_yticklabels(formatted_labels, rotation=0, ha='left', va='center', fontsize=9)

    axs[0, 1].margins(x=0, y=0)
    # axs[0, 1].spines['left'].set_color('white')

    axs[1, 1].axis('off')
    axs[1, 1].text(0.5, 0.5, f"{len(idd)} Unique durations",
         transform=plt.gca().transAxes,
         fontsize=10, ha='center', va='center')
    axs[1, 1].margins(x=0, y=0)

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    # plt.tight_layout()
    plt.show()


def plot_equality_test(
    starts: np.ndarray,
    durations: np.ndarray,
    z: np.ndarray,
    title: str = '',
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int]|None=None
):

    fig, ax = plt.subplots()

    n = np.insert(starts + durations, 0, 0)
    x, y = np.meshgrid(n, n)

    viridis = colormaps['viridis'].resampled(50)
    newcolors = viridis(np.linspace(0, 1, 50))
    pink = np.array([248 / 256, 24 / 256, 148 / 256, 1])
    newcolors[0, :] = pink
    cmap = ListedColormap(newcolors)

    levels = MaxNLocator(nbins=50).tick_values(0, 50)
    norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

    im = ax.pcolormesh(x, y, z, cmap=cmap, norm=norm, shading='flat')
    fig.colorbar(im, ax=ax)
    ax.set_aspect('equal')

    plt.show()


def plot_duration_bars(
    levels: list[tuple],
    l1: int,
    l2: int,
    aspect: tuple[int, int]=(408, 577),
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int]|None=None
):
    fig, ax = plt.subplots()

    for level in levels[l1-1:l2+1]:
        _, durations, starts, rgb, _ = level
        ax.barh(
            y=0,
            width=durations,
            left=starts,
            height=durations,
            align='edge',
            color=rgb,
            edgecolor='gray',
            linewidth=0.1
        )

    ax.set_title(f"Cycle subdivisions: {l1} to {l2}")
    ax.set_xlabel('Time (norm. units)')
    ax.set_ylabel('Subcycle Duration (norm. units)')
    ax.margins(x=0, y=0)
    if aspect == (0, 0):
        ax.set_aspect('auto')
    else:
        ax.set_aspect(float(aspect[0]/aspect[1]))

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.show()