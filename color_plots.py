import numpy as np
import matplotlib.pyplot as plt
import colorsys as csys

from measure_functions import dharma_measure, purity_measure
from cycle_division_functions import partition_level

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

def plot_level_bars(levels: list[tuple]) -> plt.Figure:
    fig, axs = plt.subplots(nrows=len(levels), ncols=1, sharex=True)
    for i, ax in enumerate(axs):
        plot_level_bar(ax, i, levels[i])
    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()
    return fig

def plot_cmyk_graph(level: tuple) -> plt.Figure:
    _, durations, starts, _, cmyk = level

    t = starts + durations / 2

    fig, ax = plt.subplots()
    for i, c in enumerate([(0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 0, 0)]):
        ax.plot(t, cmyk[:, i], color=c)

    plt.tight_layout()
    plt.show()
    return fig

def plot_rgb_graph(level: tuple) -> plt.Figure:
    _, durations, starts, rgb, _ = level

    fig, ax = plt.subplots()
    ax.plot(starts + durations / 2, rgb[:, 0], color='red')
    ax.plot(starts + durations / 2, rgb[:, 1], color='green')
    ax.plot(starts + durations / 2, rgb[:, 2], color='blue')

    plt.tight_layout()
    plt.show()
    return fig

def plot_hsv_graph(level: tuple):
    lcoords, durations, starts, rgb, cmyk = level

    hsv = np.array([csys.rgb_to_hsv(c[0], c[1], c[2]) for c in rgb])

    fig, axs = plt.subplots(nrows=3, sharex='col')
    for i, title in enumerate(['Hue', 'Saturation', 'Value']):
        axs[i].plot(starts + durations / 2, hsv[:, i])
        axs[i].set_title(title)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()

def plot_hls_graph(level: tuple):
    lcoords, durations, starts, rgb, cmyk = level

    hls = np.array([csys.rgb_to_hls(c[0], c[1], c[2]) for c in rgb])

    fig, axs = plt.subplots(nrows=3, sharex='col')
    for i, title in enumerate(['Hue', 'Lightness', 'Saturation']):
        axs[i].plot(starts + durations / 2, hls[:, i])
        axs[i].set_title(title)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()

def plot_overlay(level: tuple):
    lcoords, durations, starts, rgb, cmyk = level

    # hsv = np.array([csys.rgb_to_hsv(rgb[0], rgb[1], rgb[2]) for rgb in colors])
    # hls = np.array([csys.rgb_to_hls(rgb[0], rgb[1], rgb[2]) for rgb in colors])
    dharma = np.array([dharma_measure(c) for c in cmyk])

    fig, ax = plt.subplots()
    ax.barh(
        y=0,
        width=durations,
        left=starts,
        height=dharma,
        align='edge',
        color=rgb
    )
    ax.margins(x=0, y=0)
    plt.tight_layout()
    plt.show()

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

def plot_rgb_scatter_3d(level: tuple, views: list[dict], subdepth: int|None=None, base: int|None=None) -> plt.Figure:
    _, durations, _, rgb, _ = level

    max_duration = np.max(durations, axis=0)
    sizes = 100 * durations / max_duration

    plot_part = subdepth is not None and base is not None
    if plot_part:
        _, _, _, part_rgb, _ = partition_level(level, subdepth, base)

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
                alpha=0.5
            )

            if plot_part:
                for prgb in part_rgb:
                    for i in range(2, len(prgb) + 2):
                        ax.plot(
                            xs=prgb[i-2:i, 0],
                            ys=prgb[i-2:i, 1],
                            zs=prgb[i-2:i, 2],
                            c=prgb[i-2]
                        )

            # ax.axis('off')
            ax.set_xlabel('Red')
            ax.set_ylabel('Green')
            ax.set_zlabel('Blue')
            ax.set_aspect('equal')
            ax.set_proj_type('ortho')
            ax.view_init(views[k]['elev'], views[k]['azim'], views[k]['roll'])
            ax.set_title(views[k]['description'])
            k += 1

    plt.tight_layout()
    plt.subplots_adjust(hspace=0, wspace=0)
    plt.show()

    return fig