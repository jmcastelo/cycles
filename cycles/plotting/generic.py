import numpy as np
import matplotlib.pyplot as plt

from cycles.plotting.helpers import format_plot


def plot_y_vs_x(
    x: np.ndarray,
    y: np.ndarray,
    xlim: tuple[float|None, float|None],
    title: str = '',
    xlabel: str = '',
    ylabel: str = '',
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int, bool]|None=None
):
    fig, ax = plt.subplots()

    fig.suptitle(title)

    ax.plot(x, y, lw=0.5)
    ax.scatter(x, y, s=4.0)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xlim(*xlim)

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.show()


def plot_multi_y_vs_x(
    x: np.ndarray,
    multi_y: list[np.ndarray],
    xlim: tuple[float|None, float|None],
    title: str,
    xlabel: str,
    ylabel: str,
    ylabels: list[str],
    ycolors: list[tuple],
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int, bool]|None=None
):
    fig, ax = plt.subplots()

    fig.suptitle(title)

    for y, label, color in zip(multi_y, ylabels, ycolors):
        ax.plot(x, y, color=color, label=label, lw=0.5)
        ax.scatter(x, y, color=color, s=4.0)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xlim(*xlim)
    ax.legend()

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.show()


def grid_of_plots(
    x: list[np.ndarray],
    y: list[np.ndarray],
    title: str,
    labels: list[str],
    xlabel: str,
    ylim: tuple,
    save_fig: bool = False,
    fig_data: tuple[str, str, str, int, bool] | None = None
):
    nrows = int(np.sqrt(len(x)))
    ncols = int(len(x) / nrows)

    fig, axs = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        squeeze=False,
        sharex='none',
        sharey='none'
        # subplot_kw=dict(aspect='equal'),
        # gridspec_kw=dict(hspace=0, wspace=0)
    )

    fig.suptitle(title)

    k = 0
    for i in range(nrows):
        for j in range(ncols):
            axs[i, j].plot(x[k], y[k], lw=0.5, marker='o', markersize=2.5)
            axs[i, j].grid(True)
            axs[i, j].set_title(labels[k])
            axs[i, j].set_ylim(*ylim)
            axs[i, j].set_xlabel(xlabel)
            k += 1

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    if not save_fig:
        plt.tight_layout()
        plt.show()


def return_plot(
    points: np.ndarray,
    max_delay: int,
    colors: np.ndarray,
    title: str = '',
    label: str = '',
    plot_lines: bool=False,
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int, bool]|None=None
):
    nrows = int(np.sqrt(max_delay))
    ncols = int(max_delay / nrows)

    fig, axs = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        squeeze=False,
        sharex='all',
        sharey='all'
        # subplot_kw=dict(aspect='equal'),
        # gridspec_kw=dict(hspace=0, wspace=0)
    )

    fig.suptitle(title)

    delay = 1
    for i in range(nrows):
        for j in range(ncols):
            if plot_lines:
                axs[i, j].plot(points[:-delay], points[delay:], lw=0.5)
            axs[i, j].scatter(points[:-delay], points[delay:], c=colors[:-delay], s=1.0, lw=0.2, alpha=0.3)

            axs[i, j].set_xscale('log')
            axs[i, j].set_yscale('log')

            axs[i, j].set_xlim(np.min(points), np.max(points))
            axs[i, j].set_ylim(np.min(points), np.max(points))

            axs[i, j].set_aspect(1)

            axs[i, j].set_xlabel(f"{label}[N]")
            axs[i, j].set_ylabel(f"{label}[N+{delay}]")
            delay += 1

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    if not save_fig:
        plt.tight_layout()
        plt.show()


def plot_auto_correlations(
    x: tuple[np.ndarray],
    title: str,
    labels: list[str],
    save_fig: bool = False,
    fig_data: tuple[str, str, str, int, bool] | None = None
):
    nrows = int(np.sqrt(len(x)))
    ncols = int(len(x) / nrows)

    fig, axs = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        squeeze=False,
        sharex='none',
        sharey='none'
        # subplot_kw=dict(aspect='equal'),
        # gridspec_kw=dict(hspace=0, wspace=0)
    )

    fig.suptitle(title)

    k = 0
    for i in range(nrows):
        for j in range(ncols):
            lags, acorr, vlines, hline = axs[i, j].acorr(x[k], usevlines=False, normed=True, maxlags=None)
            axs[i, j].cla()
            mask = lags >= 0
            axs[i, j].plot(lags[mask], acorr[mask], lw=0.5, marker='o', markersize=2.5)
            axs[i, j].grid(True)
            axs[i, j].set_title(labels[k])
            axs[i, j].set_ylim(0, 1)
            axs[i, j].set_xlabel('Lag')
            k += 1

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    if not save_fig:
        plt.tight_layout()
        plt.show()