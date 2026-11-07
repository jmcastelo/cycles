"""Study of the colorings of subcycles."""

import numpy as np

from cycles.functions.view import top_view, camera_view_angles
from cycles.plotting.color import (
    plot_level_bars, plot_colors_scatter_3d, plot_rgb_lines_3d,
    plot_cmyk_vs_index, plot_rgb_vs_time, plot_rgb_vs_index,
    plot_hsv_vs_time, plot_hsv_vs_index, plot_hls_vs_time, plot_hls_vs_index,
)
from cycles.plotting.generic import plot_multi_y_vs_x
from common import BASES, PLOTS_DIR, compute_levels, level_colors, fig_data
from runner import study, run

BASE_DIR = PLOTS_DIR / "study_of_colors"


def setup():
    max_depth = 3
    levels = compute_levels(max_depth)
    axis = (1, 1, 1)
    return dict(
        max_depth=max_depth,
        levels=levels,
        colors=[level_colors(level) for level in levels],
        rgb_key='lrgb',             # any of common.COLOR_KEYS
        cmyk_key='wcmy',            # any of division.CMYK_KEYS
        variant='cmyk_normalised',  # Level RGB variant for the component graphs
        views=[
            top_view(axis),
            camera_view_angles(axis, 60, 0, True),
            camera_view_angles(axis, 60, 0.25, True),
            camera_view_angles(axis, 0, 0.25, True),
        ],
    )


@study
def level_bars(ctx, opts):
    """Timelines of all depths, colored."""
    plot_level_bars(
        [level.durations for level in ctx.levels],
        [level.starts for level in ctx.levels],
        [colors[ctx.rgb_key] for colors in ctx.colors],
        opts.save,
        fig_data(BASE_DIR / f"levels/{ctx.rgb_key}/base_{BASES[1]}/levels_down_to_{ctx.max_depth}.png", 'a5', 600),
    )


@study(default=False)
def unique_colors(ctx, opts):
    """Check, for each depth and color, whether all subcycles get distinct colors."""
    for depth, colors in enumerate(ctx.colors, 1):
        n = len(ctx.levels[depth - 1].lcoords)
        counts = {key: len(np.unique(np.round(rgb, 10), axis=0)) for key, rgb in colors.items()}
        print(f"depth {depth} ({n} subcycles): " + ', '.join(
            f"{key} {'unique' if count == n else f'{count} distinct'}" for key, count in counts.items()))


@study(default=False)
def rgb_scatter_3d(ctx, opts):
    """Colors as points in the RGB cube, seen from several views."""
    for depth, (colors, level) in enumerate(zip(ctx.colors, ctx.levels), 1):
        rgb = colors[ctx.rgb_key]
        path = BASE_DIR / f"rgb_3d/{ctx.rgb_key}/base_{BASES[1]}/rgb_3d_scatter_at_level_{depth}.png"
        plot_colors_scatter_3d(list(rgb.T), rgb, level.durations, ctx.views, opts.save, fig_data(path, 'a3', 600, True))


@study(default=False)
def rgb_lines_3d(ctx, opts):
    """Path through the RGB cube joining consecutive subcycles."""
    for depth, colors in enumerate(ctx.colors, 1):
        path = BASE_DIR / f"rgb_3d/{ctx.rgb_key}/base_{BASES[1]}/rgb_3d_lines_at_level_{depth}.png"
        plot_rgb_lines_3d(colors[ctx.rgb_key], ctx.views, opts.save, fig_data(path, 'a3', 600, True))


@study(default=False)
def cmyk_scatter_3d(ctx, opts):
    """CMY components as points in 3D, colored with lrgb."""
    for depth, (colors, level) in enumerate(zip(ctx.colors, ctx.levels), 1):
        cmyk = level.cmyk(ctx.cmyk_key)
        path = BASE_DIR / f"cmyk_3d/{ctx.cmyk_key}/base_{BASES[1]}/rgb_3d_scatter_at_level_{depth}.png"
        plot_colors_scatter_3d(list(cmyk[:, :3].T), colors['lrgb'], level.durations, ctx.views,
                               opts.save, fig_data(path, 'a3', 600, True))


@study(default=False)
def cmyk_vs_time(ctx, opts):
    """Raw CMYK components against time, one figure per depth."""
    for depth, level in enumerate(ctx.levels, 1):
        cmyk = level.cmyk('cmyk')
        plot_multi_y_vs_x(
            level.starts + level.durations / 2,
            [cmyk[:, i] for i in range(4)],
            (None, None),
            f"CMYK Color components vs time at depth {depth}",
            'Time (norm. units)',
            'Component intensity',
            ['Cyan', 'Magenta', 'Yellow', 'Black'],
            [(0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 0, 0)],
            opts.save,
            fig_data(BASE_DIR / f"cmyk/base_{BASES[1]}/cmyk_vs_time_at_depth_{depth}.png"),
        )


def _component_study(name: str, plot_function, key_argument: str):
    """Register a study that draws ``plot_function`` for every depth."""
    space, _, axis = name.split('_')

    def component_study(ctx, opts):
        key = ctx.variant if key_argument == 'rgb_key' else ctx.cmyk_key
        for depth, level in enumerate(ctx.levels, 1):
            path = BASE_DIR / f"{space}/{key}/base_{BASES[1]}/{name}_at_depth_{depth}.png"
            plot_function(level, opts.save, fig_data(path), **{key_argument: key})

    component_study.__name__ = name
    component_study.__doc__ = f"{space.upper()} components against {axis}, one figure per depth."
    study(component_study, default=False)


_component_study('cmyk_vs_index', plot_cmyk_vs_index, 'cmyk_key')
for _name, _function in [
    ('rgb_vs_time', plot_rgb_vs_time), ('rgb_vs_index', plot_rgb_vs_index),
    ('hsv_vs_time', plot_hsv_vs_time), ('hsv_vs_index', plot_hsv_vs_index),
    ('hls_vs_time', plot_hls_vs_time), ('hls_vs_index', plot_hls_vs_index),
]:
    _component_study(_name, _function, 'rgb_key')


if __name__ == "__main__":
    run(setup)
