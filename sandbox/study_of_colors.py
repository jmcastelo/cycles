from cycles.cycle_division_functions import compute_level
from cycles.color_functions import lcoords_to_lrgb
from cycles.plotting.color_plots import *
from cycles.plotting.generic_plots import *
from cycles.view_functions import top_view, camera_view_angles

if __name__ == "__main__":
    # Let's compute several levels.
    bases = [4, 2, 1]
    max_depth = 5
    levels = [compute_level(depth, bases) for depth in range(1, max_depth + 1)]
    lcoords, durations, starts, cmyks, rgbs, dharmas, purities = zip(*levels)

    lrgbs = [np.apply_along_axis(lcoords_to_lrgb, 1, coords) for coords in lcoords]
    dharma_colors = [np.array([np.full(3, d) for d in dharma]) for dharma in dharmas]
    purity_colors = [np.array([np.full(3, p) for p in purity]) for purity in purities]

    colors = {
        'rgb': {
            'cmyk': [rgb[:, 0] for rgb in rgbs],
            'wcmy': [rgb[:, 1] for rgb in rgbs],
            'lrgb': [lrgb[:, -1] for lrgb in lrgbs],
            'dharma': dharma_colors,
            'purity': purity_colors
        },
        'cmyk': {
            'cmyk': [cmyk[:, 0] for cmyk in cmyks],
            'wcmy': [cmyk[:, 1] for cmyk in cmyks]
        }
    }

    rgb_key = 'cmyk'
    cmyk_key = 'wcmy'

    base_dir = f"./plots/study_of_colors"

    plot = {
        'level_bars': False,
        'rgb_scatter_3d': False,
        'rgb_lines_3d': False,
        'cmyk_scatter_3d': False,
        'dharma_vs_time': False,
        'dharma_vs_index': False,
        'purity_vs_time': False,
        'purity_vs_index': False,
        'cmyk_vs_time': True
    }

    if plot['level_bars']:
        plot_level_bars(
            durations,
            starts,
            colors['rgb'][rgb_key],
            save_fig=False,
            fig_data=(
                'a4',
                'landscape',
                f"{base_dir}/levels/{rgb_key}/base_{bases[1]}/levels_down_to_{max_depth}.png",
                600,
                True
            )
        )

    if plot['rgb_scatter_3d'] or plot['rgb_lines_3d'] or plot['cmyk_scatter_3d']:
        axis = (1, 1, 1)
        views = [
            top_view(axis),
            camera_view_angles(axis, 60, 0,True),
            camera_view_angles(axis, 60, 0.25, True),
            camera_view_angles(axis, 0, 0.25, True)
        ]

    if plot['rgb_scatter_3d']:
        for depth, (components, rgb, duration) in enumerate(zip(colors['rgb'][rgb_key], colors['rgb']['lrgb'], durations), 1):
            plot_name = f"{base_dir}/rgb_3d/{rgb_key}/base_{bases[1]}/rgb_3d_scatter_at_level_{depth}.png"
            color = [components[:,0], components[:,1], components[:,2]]
            plot_colors_scatter_3d(color, rgb, duration, views, False, ('a3', 'landscape', plot_name, 600, True))

    if plot['rgb_lines_3d']:
        for depth, (rgb, d) in enumerate(zip(colors['rgb'][rgb_key], durations), 1):
            plot_name = f"{base_dir}/rgb_3d/{rgb_key}/base_{bases[1]}/rgb_3d_lines_at_level_{depth}.png"
            plot_rgb_lines_3d(rgb, views, False, ('a3', 'landscape', plot_name, 600, True))

    if plot['cmyk_scatter_3d']:
        for depth, (components, rgb, duration) in enumerate(zip(colors['cmyk'][cmyk_key], colors['rgb']['lrgb'], durations), 1):
            plot_name = f"{base_dir}/cmyk_3d/{cmyk_key}/base_{bases[1]}/rgb_3d_scatter_at_level_{depth}.png"
            color = [components[:,0], components[:,1], components[:,2]]
            plot_colors_scatter_3d(color, rgb, duration, views, False, ('a3', 'landscape', plot_name, 600, True))

    if plot['dharma_vs_time']:
        for depth, (start, duration, dharma) in enumerate(zip(starts, durations, dharmas), 1):
            title = f"Dharma vs time at depth {depth}"
            ylabel = 'Dharma'
            xlabel = 'Time (norm. units)'
            fig_data = (
                'a4',
                'landscape',
                f"{base_dir}/dharma/base_{bases[1]}/dharma_vs_time_at_depth_{depth}.png",
                300,
                False
            )
            time = start + duration / 2
            plot_y_vs_x(time, dharma, (None, None), title, xlabel, ylabel, False, fig_data)

    if plot['dharma_vs_index']:
        for depth, dharma in enumerate(dharmas, 1):
            title = f"Dharma vs index at depth {depth}"
            ylabel = 'Dharma'
            xlabel = 'Index'
            fig_data = (
                'a4',
                'landscape',
                f"{base_dir}/dharma/base_{bases[1]}/dharma_vs_index_at_depth_{depth}.png",
                300,
                False
            )
            index = np.arange(0, len(dharma))
            plot_y_vs_x(index, dharma, (None, None), title, xlabel, ylabel, False, fig_data)

    if plot['purity_vs_time']:
        for depth, (start, duration, purity) in enumerate(zip(starts, durations, purities), 1):
            title = f"Purity vs time at depth {depth}"
            ylabel = 'Purity'
            xlabel = 'Time (norm. units)'
            fig_data = (
                'a4',
                'landscape',
                f"{base_dir}/purity/base_{bases[1]}/purity_vs_time_at_depth_{depth}.png",
                300,
                False
            )
            time = start + duration / 2
            plot_y_vs_x(time, purity, (None, None), title, xlabel, ylabel, False, fig_data)

    if plot['purity_vs_index']:
        for depth, purity in enumerate(purities, 1):
            title = f"Purity vs time at depth {depth}"
            ylabel = 'Purity'
            xlabel = 'Index'
            fig_data = (
                'a4',
                'landscape',
                f"{base_dir}/purity/base_{bases[1]}/purity_vs_index_at_depth_{depth}.png",
                300,
                False
            )
            index = np.arange(0, len(purity))
            plot_y_vs_x(index, purity, (None, None), title, xlabel, ylabel, False, fig_data)

    if plot['cmyk_vs_time']:
        for depth, (start, duration, color) in enumerate(zip(starts, durations, colors['cmyk']['cmyk']), 1):
            title = f"CMYK Color components vs time at depth {depth}"
            ylabels = ['Cyan', 'Magenta', 'Yellow', 'Black']
            ycolors = [(0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 0, 0)]
            ylabel = 'Component intensity'
            xlabel = 'Time (norm. units)'
            fig_data = (
                'a4',
                'landscape',
                f"{base_dir}/cmyk/base_{bases[1]}/cmyk_vs_time_at_depth_{depth}.png",
                300,
                False
            )
            time = start + duration / 2
            cmyk = [color[:, i] for i in range(4)]
            plot_multi_y_vs_x(time, cmyk, (None, None), title, xlabel, ylabel, ylabels, ycolors, False, fig_data)

    # Plot color graphs
    # save_fig = False
    # for depth, level in enumerate(levels, 1):
    #     plot_cmyk_vs_time(level, save_fig, ('a4', 'landscape', f"./plots/cmyk/base_{bases[1]}/cmyk_vs_time_level_{depth}.png", 300))
    #     plot_rgb_vs_time(level, save_fig, ('a4', 'landscape', f"./plots/rgb/base_{bases[1]}/rgb_vs_time_level_{depth}.png", 300))
    #     plot_hsv_vs_time(level, save_fig, ('a4', 'landscape', f"./plots/hsv/base_{bases[1]}/hsv_vs_time_level_{depth}.png", 300))
    #     plot_hls_vs_time(level, save_fig, ('a4', 'landscape', f"./plots/hls/base_{bases[1]}/hls_vs_time_level_{depth}.png", 300))
    #     plot_cmyk_vs_index(level, save_fig, ('a4', 'landscape', f"./plots/cmyk/base_{bases[1]}/cmyk_vs_index_level_{depth}.png", 300))
    #     plot_rgb_vs_index(level, save_fig, ('a4', 'landscape', f"./plots/rgb/base_{bases[1]}/rgb_vs_index_level_{depth}.png", 300))
    #     plot_hsv_vs_index(level, save_fig, ('a4', 'landscape', f"./plots/hsv/base_{bases[1]}/hsv_vs_index_level_{depth}.png", 300))
    #     plot_hls_vs_index(level, save_fig, ('a4', 'landscape', f"./plots/hls/base_{bases[1]}/hls_vs_index_level_{depth}.png", 300))

    # Plot duration bars
    # aspect = (1, 1)
    # l1, l2 = 1, 5
    # plot_name = f"./plots/durations/durations_{l1}_to_{l2}_aspect_{aspect[0]}_{aspect[1]}.png"
    # plot_duration_bars(levels, l1, l2, aspect, False, ('a4', 'landscape', plot_name, 600))

    # TODO: Rewrite the following plots
    # fig = plot_quality_scatter_3d(level)
    # figname = 'quality_scatter_3d.png'
    # plot_circle_diagram(levels, bases[0])

    # fig = plot_purity_vs_dharma(level)
    # figname = f"purity_vs_dharma_depth_{depth}.png"

    # fig.set_size_inches(figsize)
    # fig.savefig('./PNGs/' + figname, dpi=300)