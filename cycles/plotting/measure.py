"""
Plots of the dharma and purity measures of subcycles.

Functions taking a ``Level`` color the points with ``rgb_key`` (names in
``division.RGB_KEYS``). Those that draw a single panel accept an existing
``ax`` to draw on (nothing is shown then) and return what they drew.
"""

import numpy as np
import matplotlib.pyplot as plt

from cycles.plotting.helpers import format_plot
from cycles.functions.division import Level, DEFAULT_COLOR_KEY


def plot_dharma_vs_index(level: Level, save_fig: bool=False, fig_data: tuple[str, str, str, int, bool]|None=None,
                         ax=None, show: bool=True, indices=None):
    """
    Dharma of each subcycle against its time-order index.

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    ax : existing Axes to draw on (then nothing is shown); ``show`` as usual
        otherwise.
    indices : x values (default 0, 1, 2...; e.g. the indices in the whole level
        when ``level`` is part of one).

    Returns the line.
    """
    lcoords = level.lcoords
    dharma = level.dharmas

    depth = len(lcoords[0])
    if indices is None:
        indices = np.arange(len(lcoords))

    own_figure = ax is None
    if own_figure:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    line, = ax.plot(indices, dharma, lw=0.5)
    ax.set_title(f"Dharma for level: {depth}")
    ax.set_xlabel('Index')
    ax.set_ylabel('Dharma')

    if own_figure:
        if fig_data is not None:
            format_plot(fig, fig_data, save_fig)
        plt.tight_layout()
        if show:
            plt.show()
    return line


def plot_purity_vs_dharma(level: Level, rgb_key: str=DEFAULT_COLOR_KEY) -> plt.Figure:
    """
    Scatter plot of purity against dharma for one level (see
    ``plot_purity_and_dharma``). Returns the figure.
    """
    fig, ax = plt.subplots()
    plot_purity_and_dharma(ax, level, rgb_key)
    plt.tight_layout()
    plt.show()
    return fig


def plot_purity_and_dharma(ax, level: Level, rgb_key: str=DEFAULT_COLOR_KEY, colors=None, max_size: float=500,
                           sizes=None):
    """
    Scatter of purity against dharma on ``ax``: one point per subcycle, sized by
    its duration (the longest gets area ``max_size``; ``sizes``, areas, override
    it) and filled with its color (``colors``, an (N, 3) array, overrides
    ``rgb_key``). Returns the scatter.
    """
    durations, dharma, purity = level.durations, level.dharmas, level.purities
    rgb = level.rgb(rgb_key) if colors is None else colors
    if sizes is None:
        sizes = max_size * durations / np.max(durations, axis=0)

    scatter = ax.scatter(
        x=dharma,
        y=purity,
        c=rgb,
        s=sizes,
        alpha=0.3
    )
    ax.set_xlabel('Dharma')
    ax.set_ylabel('Purity')
    ax.label_outer()
    ax.grid(False)
    return scatter


def plot_quality_grid(levels: list[Level], rgb_key: str=DEFAULT_COLOR_KEY):
    """Grid of purity-against-dharma scatter plots, one panel per level."""
    ncols = int(np.sqrt(len(levels)))
    nrows = int(np.ceil(len(levels) / ncols))

    w, h = 16.5, 11.7

    fig, axs = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        squeeze=False,
        sharex='all',
        sharey='all',
        subplot_kw=dict(aspect=h/w),
        gridspec_kw=dict(hspace=0, wspace=0)
    )
    fig.set_size_inches(w, h)
    k = 0
    for i in range(nrows):
        for j in range(ncols):
            if k >= len(levels):
                axs[i, j].axis('off')
                continue
            plot_purity_and_dharma(axs[i, j], levels[k], rgb_key)
            # axs[i, j].text(1/4, 1, f"{k+1}", ha='left', va='top')
            axs[i, j].set_title(f"{k+1}")
            k += 1
    plt.tight_layout()
    plt.subplots_adjust(hspace=0, wspace=0)
    plt.show()


def plot_quality_scatter_3d(level: Level, rgb_key: str=DEFAULT_COLOR_KEY, ax=None, show: bool=True,
                            axis: str='time', values=None, colors=None, sizes=10, path: bool=False,
                            alpha: float=0.5):
    """
    3D scatter of dharma, purity and time (subcycle midpoint), colored by
    subcycle.

    ax : existing 3D Axes to draw on (then nothing is shown); ``show`` as usual
        otherwise.
    axis : third coordinate, ``'time'`` (subcycle midpoints) or ``'index'``;
        ``values`` replaces its values (e.g. years, or indices within a whole
        level) keeping the label (``'Year'`` for time given this way).
    colors, sizes : point colors ((N, 3), overriding ``rgb_key``) and areas.
    path : also join the points in time order with a faint line.

    Returns the figure.
    """
    durations, starts, dharma, purity = level.durations, level.starts, level.dharmas, level.purities
    rgb = level.rgb(rgb_key) if colors is None else colors
    if axis == 'index':
        z, zlabel = np.arange(len(dharma), dtype=float), 'Index'
    else:
        z, zlabel = starts + durations / 2, 'Location' if values is None else 'Year'
    if values is not None:
        z = np.asarray(values, dtype=float)

    own_figure = ax is None
    if own_figure:
        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')
    else:
        fig = ax.figure
    if path:
        ax.plot(dharma, purity, z, color='0.75', lw=0.5, zorder=1)
    ax.scatter(xs=dharma, ys=purity, zs=z, c=rgb, s=sizes, alpha=alpha, depthshade=False)
    ax.set_xlabel('Dharma')
    ax.set_ylabel('Purity')
    ax.set_zlabel(zlabel)
    if own_figure:
        plt.margins(x=0, y=0)
        plt.tight_layout()
        if show:
            plt.show()
    return fig
