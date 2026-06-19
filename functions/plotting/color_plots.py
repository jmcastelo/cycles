import numpy as np
import matplotlib.pyplot as plt
import colorsys as csys

from helpers import save_plot
from functions.measure_functions import dharma_measure, purity_measure


# Color plots


def plot_level_bar(ax, index: int, level: tuple):
    _, durations, starts, rgb, _ = level

    ax.barh(
        y=index,
        width=durations,
        left=starts,
        height=1,
        align='center',
        color=rgb
    )
    ax.yaxis.set_visible(False)
    ax.xaxis.set_visible(False)
    ax.margins(x=0, y=0)


def plot_level_bars(levels: list[tuple], save_fig: bool=False, fig_data: tuple[str, str, str, int]|None=None):
    fig, axs = plt.subplots(nrows=len(levels), ncols=1, sharex=True)

    for i, ax in enumerate(axs):
        plot_level_bar(ax, i, levels[i])

    axs[0].set_title(f"Cycle subdivisions down to depth {len(levels)}")
    axs[-1].xaxis.set_visible(True)
    axs[-1].set_xlabel('Time (norm. units)')

    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


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

    plt.tight_layout()
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


def plot_cmyk_vs_time(level: tuple, save_fig: bool=False, fig_data: tuple[str, str, str, int]|None=None):
    lcoords, durations, starts, _, cmyk = level

    depth = len(lcoords[0])
    t = starts + durations / 2

    fig, ax = plt.subplots()
    for i, (l, c) in enumerate(zip(['Cyan', 'Magenta', 'Yellow', 'Black'], [(0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 0, 0)])):
        ax.plot(t, cmyk[:, i], color=c, label=l, lw=0.5)

    ax.set_title(f"CMYK for level: {depth}")
    ax.set_xlabel('Time (norm. units)')
    ax.set_ylabel('Component intensity')
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.legend(loc='center left')

    plt.tight_layout()
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


def plot_cmyk_vs_index(level: tuple, save_fig: bool=False, fig_data: tuple[str, str, str, int]|None=None):
    lcoords, _, _, _, cmyk = level

    depth = len(lcoords[0])
    indices = [n for n in range(len(lcoords))]

    fig, ax = plt.subplots()
    for i, (l, c) in enumerate(zip(['Cyan', 'Magenta', 'Yellow', 'Black'], [(0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 0, 0)])):
        ax.plot(indices, cmyk[:, i], color=c, label=l, lw=0.5)

    ax.set_title(f"CMYK for level: {depth}")
    ax.set_xlabel('Index')
    ax.set_ylabel('Component intensity')
    ax.set_ylim(0.0, 1.0)
    ax.legend(loc='center left')

    plt.tight_layout()
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


def plot_rgb_vs_time(level: tuple, save_fig: bool=False, fig_data: tuple[str, str, str, int]|None=None):
    lcoords, durations, starts, rgb, _ = level

    depth = len(lcoords[0])
    t = starts + durations / 2

    fig, ax = plt.subplots()
    for i, c in enumerate(['red', 'green', 'blue']):
        ax.plot(t, rgb[:, i], color=c, label=c, lw=0.5)

    ax.set_title(f"RGB for level: {depth}")
    ax.set_xlabel('Time (norm. units)')
    ax.set_ylabel('Component intensity')
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.legend(loc='center left')

    plt.tight_layout()
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


def plot_rgb_vs_index(level: tuple, save_fig: bool=False, fig_data: tuple[str, str, str, int]|None=None):
    lcoords, _, _, rgb, _ = level

    depth = len(lcoords[0])
    indices = [n for n in range(len(lcoords))]

    fig, ax = plt.subplots()
    for i, c in enumerate(['red', 'green', 'blue']):
        ax.plot(indices, rgb[:, i], color=c, label=c, lw=0.5)

    ax.set_title(f"RGB for level: {depth}")
    ax.set_xlabel('Index')
    ax.set_ylabel('Component intensity')
    ax.set_ylim(0.0, 1.0)
    ax.legend(loc='center left')

    plt.tight_layout()
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


def plot_hsv_vs_time(level: tuple, save_fig: bool=False, fig_data: tuple[str, str, str, int]|None=None):
    lcoords, durations, starts, rgb, _ = level

    depth = len(lcoords[0])
    t = starts + durations / 2

    hsv = np.array([csys.rgb_to_hsv(c[0], c[1], c[2]) for c in rgb])

    fig, axs = plt.subplots(nrows=3, sharex='col')
    for i, label in enumerate(['Hue', 'Saturation', 'Value']):
        axs[i].plot(t, hsv[:, i], lw=0.5)
        axs[i].set_xlabel('Time (norm. units)')
        axs[i].set_ylabel(label)

    axs[0].set_title(f"HSV for level: {depth}")
    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


def plot_hsv_vs_index(level: tuple, save_fig: bool=False, fig_data: tuple[str, str, str, int]|None=None):
    lcoords, _, _, rgb, _ = level

    depth = len(lcoords[0])
    indices = [n for n in range(len(lcoords))]

    hsv = np.array([csys.rgb_to_hsv(c[0], c[1], c[2]) for c in rgb])

    fig, axs = plt.subplots(nrows=3, sharex='col')
    for i, label in enumerate(['Hue', 'Saturation', 'Value']):
        axs[i].plot(indices, hsv[:, i], lw=0.5)
        axs[i].set_xlabel('Index')
        axs[i].set_ylabel(label)

    axs[0].set_title(f"HSV for level: {depth}")
    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


def plot_hls_vs_time(level: tuple, save_fig: bool=False, fig_data: tuple[str, str, str, int]|None=None):
    lcoords, durations, starts, rgb, _ = level

    depth = len(lcoords[0])
    t = starts + durations / 2

    hls = np.array([csys.rgb_to_hls(c[0], c[1], c[2]) for c in rgb])

    fig, axs = plt.subplots(nrows=3, sharex='col')
    for i, label in enumerate(['Hue', 'Lightness', 'Saturation']):
        axs[i].plot(t, hls[:, i], lw=0.5)
        axs[i].set_xlabel('Time (norm. units)')
        axs[i].set_ylabel(label)

    axs[0].set_title(f"HLS for level: {depth}")
    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


def plot_hls_vs_index(level: tuple, save_fig: bool=False, fig_data: tuple[str, str, str, int]|None=None):
    lcoords, _, _, rgb, _ = level

    depth = len(lcoords[0])
    indices = [n for n in range(len(lcoords))]

    hls = np.array([csys.rgb_to_hls(c[0], c[1], c[2]) for c in rgb])

    fig, axs = plt.subplots(nrows=3, sharex='col')
    for i, label in enumerate(['Hue', 'Lightness', 'Saturation']):
        axs[i].plot(indices, hls[:, i], lw=0.5)
        axs[i].set_xlabel('Time (norm. units)')
        axs[i].set_ylabel(label)

    axs[0].set_title(f"HLS for level: {depth}")
    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


def plot_dharma_vs_time(level: tuple, save_fig: bool=False, fig_data: tuple[str, str, str, int]|None=None):
    lcoords, durations, starts, _, cmyk = level

    depth = len(lcoords[0])
    t = starts + durations / 2

    dharma = np.array([dharma_measure(c) for c in cmyk])

    fig, ax = plt.subplots()

    ax.plot(t, dharma, lw=0.5)
    ax.set_title(f"Dharma for level: {depth}")
    ax.set_xlabel('Time (norm. units)')
    ax.set_ylabel('Dharma')
    ax.set_xlim(0.0, 1.0)

    plt.tight_layout()
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


def plot_dharma_vs_index(level: tuple, save_fig: bool=False, fig_data: tuple[str, str, str, int]|None=None):
    lcoords, _, _, _, cmyk = level

    depth = len(lcoords[0])
    indices = [n for n in range(len(lcoords))]

    dharma = np.array([dharma_measure(c) for c in cmyk])

    fig, ax = plt.subplots()

    ax.plot(indices, dharma, lw=0.5)
    ax.set_title(f"Dharma for level: {depth}")
    ax.set_xlabel('Index')
    ax.set_ylabel('Dharma')

    plt.tight_layout()
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


def plot_purity_vs_dharma(level: tuple) -> plt.Figure:
    fig, ax = plt.subplots()
    plot_purity_and_dharma(ax, level)
    plt.tight_layout()
    plt.show()
    return fig


def plot_purity_and_dharma(ax, level: tuple):
    _, durations, _, rgb, cmyk = level

    dharma = np.array([dharma_measure(c) for c in cmyk])
    purity = np.array([purity_measure(c) for c in cmyk])
    max_duration = np.max(durations, axis=0)
    sizes = 500 * durations / max_duration

    ax.scatter(
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

def plot_quality_grid(levels: list[tuple]):
    ncols = int(np.sqrt(len(levels)))
    nrows = int(len(levels) / ncols)

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
            plot_purity_and_dharma(axs[i, j], levels[k])
            # axs[i, j].text(1/4, 1, f"{k+1}", ha='left', va='top')
            axs[i, j].set_title(f"{k+1}")
            k += 1
    plt.tight_layout()
    plt.subplots_adjust(hspace=0, wspace=0)
    plt.show()

def plot_quality_scatter_3d(level: tuple) -> plt.Figure:
    _, durations, starts, rgb, cmyk = level

    dharma = np.array([dharma_measure(c) for c in cmyk])
    purity = np.array([purity_measure(c) for c in cmyk])
    t = starts + durations / 2

    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.scatter(
        xs=dharma,
        ys=purity,
        zs=t,
        c=rgb,
        # s=durations,
        s=10,
        alpha=0.5
    )
    ax.set_xlabel('Dharma')
    ax.set_ylabel('Purity')
    ax.set_zlabel('Location')
    plt.margins(x=0, y=0)
    plt.tight_layout()
    plt.show()

    return fig


def plot_rgb_scatter_3d(
    level: tuple,
    views: list[tuple],
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int]|None=None
):
    _, durations, _, rgb, _ = level


    sizes = 100 * durations / np.max(durations, axis=0)

    nrows = int(np.sqrt(len(views)))
    ncols = int(len(views) / nrows)

    fig = plt.figure()
    k = 0
    for i in range(nrows):
        for j in range(ncols):
            ax = fig.add_subplot(nrows, ncols, k+1, projection='3d')
            ax.scatter(
                xs=rgb[:, 0],
                ys=rgb[:, 1],
                zs=rgb[:, 2],
                c=rgb,
                s=sizes,
                alpha=0.8,
                lw=0
            )

            ax.axis('off')
            ax.set_aspect('equal')
            ax.set_proj_type('ortho')
            ax.view_init(*views[k])
            k += 1

    plt.tight_layout()
    plt.subplots_adjust(hspace=0, wspace=0)
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)


def plot_rgb_lines_3d(
    level: tuple,
    views: list[tuple],
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int]|None=None
):
    _, _, _, rgb, _ = level

    nrows = int(np.sqrt(len(views)))
    ncols = int(len(views) / nrows)

    fig = plt.figure()
    k = 0
    for i in range(nrows):
        for j in range(ncols):
            ax = fig.add_subplot(nrows, ncols, k+1, projection='3d')
            for n in range(2, len(rgb) + 2):
                ax.plot(
                    xs=rgb[n - 2:n, 0],
                    ys=rgb[n - 2:n, 1],
                    zs=rgb[n - 2:n, 2],
                    c=rgb[n - 2],
                    lw=0.5
                )

            ax.axis('off')
            ax.set_aspect('equal')
            ax.set_proj_type('ortho')
            ax.view_init(*views[k])
            k += 1

    plt.tight_layout()
    plt.subplots_adjust(hspace=0, wspace=0)
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)