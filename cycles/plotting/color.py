"""
Plots of the colors of subcycles.

Functions taking a ``Level`` select the color variant with ``rgb_key`` or
``cmyk_key`` (names in ``division.RGB_KEYS`` / ``division.CMYK_KEYS``).
"""

import numpy as np
import matplotlib.pyplot as plt
import colorsys as csys

from cycles.plotting.helpers import format_plot
from cycles.functions.division import Level, DEFAULT_COLOR_KEY


def plot_level_bar(
    ax,
    index: int,
    durations: np.ndarray,
    starts: np.ndarray,
    colors: np.ndarray
):
    """
    One timeline on ``ax``: a bar per subcycle, placed at its start, as long as
    its duration and filled with its color.
    """
    ax.barh(
        y=index,
        width=durations,
        left=starts,
        height=1,
        align='center',
        color=colors,
        lw=0.0
    )
    ax.yaxis.set_visible(False)
    ax.xaxis.set_visible(False)
    ax.margins(x=0, y=0)


def plot_level_bars(
    durations: tuple[np.ndarray],
    starts: tuple[np.ndarray],
    colors: list[np.ndarray],
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int, bool]|None=None
):
    """
    Stacked timelines, one per depth (``durations``, ``starts``, ``colors`` hold
    one array per depth).

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    """
    depth = len(durations)
    fig, axs = plt.subplots(nrows=depth, ncols=1, sharex=True, gridspec_kw={'hspace': 0.1, 'wspace': 0}, layout='compressed')

    for i, (ax, d, s, c) in enumerate(zip(axs, durations, starts, colors)):
        plot_level_bar(ax, i, d, s, c)

    # axs[0].set_title(f"Cycle subdivisions down to depth {depth}")
    # axs[-1].xaxis.set_visible(True)
    axs[-1].set_xlabel('Time (norm. units)')

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    # plt.tight_layout()
    plt.subplots_adjust(hspace=0.1, wspace=0)
    plt.show()


# Corners of the RGB cube and their names (for draw_rgb_cube)
CUBE_CORNERS = {'K': (0, 0, 0), 'R': (1, 0, 0), 'G': (0, 1, 0), 'B': (0, 0, 1),
                'Y': (1, 1, 0), 'M': (1, 0, 1), 'C': (0, 1, 1), 'W': (1, 1, 1)}


def draw_colors_3d(ax, coords: np.ndarray, rgbs: np.ndarray, sizes=10.0, alpha: float = 0.8):
    """
    Points at ``coords`` (N, 3) on the 3D Axes ``ax``, filled with ``rgbs``
    (N, 3) and ``sizes`` (areas, scalar or (N,)). Returns the scatter.
    """
    coords = np.asarray(coords, dtype=float)
    return ax.scatter(xs=coords[:, 0], ys=coords[:, 1], zs=coords[:, 2], c=np.clip(rgbs, 0, 1), s=sizes,
                      alpha=alpha, lw=0.3, edgecolors='gray', depthshade=False)


def draw_color_path_3d(ax, coords: np.ndarray, rgbs: np.ndarray, lw: float = 0.5):
    """
    Path joining consecutive points ``coords`` (N, 3) on the 3D Axes ``ax``,
    each segment in the color (``rgbs``) of its first point. Returns the lines.
    """
    from mpl_toolkits.mplot3d.art3d import Line3DCollection
    coords = np.asarray(coords, dtype=float)
    segments = np.stack([coords[:-1], coords[1:]], axis=1)
    lines = Line3DCollection(segments, colors=np.clip(rgbs[:-1], 0, 1), linewidths=lw)
    ax.add_collection3d(lines)
    return lines


def draw_rgb_cube(ax, labels: bool = True, color: str = '0.6', lw: float = 0.6) -> None:
    """Edges of the unit RGB cube on the 3D Axes ``ax``, with its corners named (K, R, G, B, C, M, Y, W)."""
    corners = CUBE_CORNERS
    for a, pa in corners.items():
        for b, pb in corners.items():
            if a < b and sum(abs(x - y) for x, y in zip(pa, pb)) == 1:      # cube edge
                ax.plot(*zip(pa, pb), color=color, lw=lw)
    if labels:
        for name, (x, y, z) in corners.items():
            offset = 0.06
            ax.text(x + (offset if x else -offset), y + (offset if y else -offset), z + (offset if z else -offset),
                    name, fontsize=8, color='0.35', ha='center', va='center')


def setup_color_axes_3d(ax, view: tuple | None = None, orthographic: bool = True) -> None:
    """Equal aspect, no panes or ticks, and optionally the camera ``view`` (elev, azim, roll)."""
    ax.axis('off')
    ax.set_aspect('equal')
    ax.set_proj_type('ortho' if orthographic else 'persp')
    if view is not None:
        ax.view_init(*view)


def plot_colors_scatter_3d(
    colors: list[np.ndarray],
    rgbs: np.ndarray,
    durations: np.ndarray,
    views: list[tuple],
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int, bool]|None=None
):
    """
    Colors as points in a 3D color space, seen from several camera ``views``
    (``(elev, azim, roll)``, e.g. from ``functions.view``).

    ``colors`` holds the three coordinate arrays and ``rgbs`` the color of each
    point. ``durations`` is currently unused.

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    """
    nrows = int(np.sqrt(len(views)))
    ncols = int(len(views) / nrows)
    coords = np.column_stack(colors)

    fig = plt.figure()
    for k in range(nrows * ncols):
        ax = fig.add_subplot(nrows, ncols, k + 1, projection='3d')
        draw_colors_3d(ax, coords, rgbs)
        setup_color_axes_3d(ax, views[k])

    fig.tight_layout()
    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0, wspace=0)
    plt.show()


def plot_rgb_lines_3d(
    rgb: np.ndarray,
    views: list[tuple],
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int, bool]|None=None
):
    """
    Path through the RGB cube joining the colors of consecutive subcycles, seen
    from several camera ``views``.

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    """
    nrows = int(np.sqrt(len(views)))
    ncols = int(len(views) / nrows)

    fig = plt.figure()
    for k in range(nrows * ncols):
        ax = fig.add_subplot(nrows, ncols, k + 1, projection='3d')
        draw_color_path_3d(ax, rgb, rgb)
        ax.auto_scale_xyz(rgb[:, 0], rgb[:, 1], rgb[:, 2])
        setup_color_axes_3d(ax, views[k])

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0, wspace=0)
    plt.show()


def plot_cmyk_vs_time(level: Level, save_fig: bool=False, fig_data: tuple[str, str, str, int, bool]|None=None, cmyk_key: str=DEFAULT_COLOR_KEY):
    """
    CMYK components of each subcycle against the time of its midpoint.

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    """
    lcoords, durations, starts = level.lcoords, level.durations, level.starts
    cmyk = level.cmyk(cmyk_key)

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

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.show()


def plot_cmyk_vs_index(level: Level, save_fig: bool=False, fig_data: tuple[str, str, str, int, bool]|None=None, cmyk_key: str=DEFAULT_COLOR_KEY):
    """
    CMYK components of each subcycle against its time-order index.

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    """
    lcoords = level.lcoords
    cmyk = level.cmyk(cmyk_key)

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

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.show()


def plot_rgb_vs_time(level: Level, save_fig: bool=False, fig_data: tuple[str, str, str, int, bool]|None=None, rgb_key: str=DEFAULT_COLOR_KEY):
    """
    RGB components of each subcycle against the time of its midpoint.

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    """
    lcoords, durations, starts = level.lcoords, level.durations, level.starts
    rgb = level.rgb(rgb_key)

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

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.show()


def plot_rgb_vs_index(level: Level, save_fig: bool=False, fig_data: tuple[str, str, str, int, bool]|None=None, rgb_key: str=DEFAULT_COLOR_KEY):
    """
    RGB components of each subcycle against its time-order index.

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    """
    lcoords = level.lcoords
    rgb = level.rgb(rgb_key)

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

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.show()


def plot_hsv_vs_time(level: Level, save_fig: bool=False, fig_data: tuple[str, str, str, int, bool]|None=None, rgb_key: str=DEFAULT_COLOR_KEY):
    """
    Hue, saturation and value of each subcycle against the time of its midpoint.

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    """
    lcoords, durations, starts = level.lcoords, level.durations, level.starts
    rgb = level.rgb(rgb_key)

    depth = len(lcoords[0])
    t = starts + durations / 2

    hsv = np.array([csys.rgb_to_hsv(c[0], c[1], c[2]) for c in rgb])

    fig, axs = plt.subplots(nrows=3, sharex='col')
    for i, label in enumerate(['Hue', 'Saturation', 'Value']):
        axs[i].plot(t, hsv[:, i], lw=0.5)
        axs[i].set_xlabel('Time (norm. units)')
        axs[i].set_ylabel(label)

    axs[0].set_title(f"HSV for level: {depth}")

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()


def plot_hsv_vs_index(level: Level, save_fig: bool=False, fig_data: tuple[str, str, str, int, bool]|None=None, rgb_key: str=DEFAULT_COLOR_KEY):
    """
    Hue, saturation and value of each subcycle against its time-order index.

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    """
    lcoords = level.lcoords
    rgb = level.rgb(rgb_key)

    depth = len(lcoords[0])
    indices = [n for n in range(len(lcoords))]

    hsv = np.array([csys.rgb_to_hsv(c[0], c[1], c[2]) for c in rgb])

    fig, axs = plt.subplots(nrows=3, sharex='col')
    for i, label in enumerate(['Hue', 'Saturation', 'Value']):
        axs[i].plot(indices, hsv[:, i], lw=0.5)
        axs[i].set_xlabel('Index')
        axs[i].set_ylabel(label)

    axs[0].set_title(f"HSV for level: {depth}")

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()


def plot_hls_vs_time(level: Level, save_fig: bool=False, fig_data: tuple[str, str, str, int, bool]|None=None, rgb_key: str=DEFAULT_COLOR_KEY):
    """
    Hue, lightness and saturation of each subcycle against the time of its
    midpoint.

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    """
    lcoords, durations, starts = level.lcoords, level.durations, level.starts
    rgb = level.rgb(rgb_key)

    depth = len(lcoords[0])
    t = starts + durations / 2

    hls = np.array([csys.rgb_to_hls(c[0], c[1], c[2]) for c in rgb])

    fig, axs = plt.subplots(nrows=3, sharex='col')
    for i, label in enumerate(['Hue', 'Lightness', 'Saturation']):
        axs[i].plot(t, hls[:, i], lw=0.5)
        axs[i].set_xlabel('Time (norm. units)')
        axs[i].set_ylabel(label)

    axs[0].set_title(f"HLS for level: {depth}")

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()


def plot_hls_vs_index(level: Level, save_fig: bool=False, fig_data: tuple[str, str, str, int, bool]|None=None, rgb_key: str=DEFAULT_COLOR_KEY):
    """
    Hue, lightness and saturation of each subcycle against its time-order index.

    save_fig, fig_data : see ``cycles.plotting.helpers.format_plot``.
    """
    lcoords = level.lcoords
    rgb = level.rgb(rgb_key)

    depth = len(lcoords[0])
    indices = [n for n in range(len(lcoords))]

    hls = np.array([csys.rgb_to_hls(c[0], c[1], c[2]) for c in rgb])

    fig, axs = plt.subplots(nrows=3, sharex='col')
    for i, label in enumerate(['Hue', 'Lightness', 'Saturation']):
        axs[i].plot(indices, hls[:, i], lw=0.5)
        axs[i].set_xlabel('Index')
        axs[i].set_ylabel(label)

    axs[0].set_title(f"HLS for level: {depth}")

    if fig_data is not None:
        format_plot(fig, fig_data, save_fig)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()
