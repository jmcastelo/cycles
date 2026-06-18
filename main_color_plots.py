from cycle_division_functions import compute_level, partition_level
from color_plots import *
from view_functions import camera_view_angles, top_view

if __name__ == "__main__":
    # Compute levels

    bases = [4, 2]

    num_levels = 6
    levels = [compute_level(depth, bases) for depth in range(1, num_levels + 1)]

    # depth = 6
    # level = compute_level(depth, bases)

    # Plot level bars
    # plot_level_bars(levels, True, ('a4', 'landscape', f"./plots/levels/levels_down_to_{num_levels}.png", 600))

    # Plot duration bars
    # aspect = (1, 1)
    # l1, l2 = 1, 5
    # plot_name = f"./plots/durations/durations_{l1}_to_{l2}_aspect_{aspect[0]}_{aspect[1]}.png"
    # plot_duration_bars(levels, l1, l2, aspect, False, ('a4', 'landscape', plot_name, 600))

    # Plot color graphs
    # for depth, level in enumerate(levels, 1):
        # plot_cmyk_graph(level, False, ('a4', 'landscape', f"./plots/cmyk/cmyk_level_{depth}.png", 300))
        # plot_rgb_graph(level, False, ('a4', 'landscape', f"./plots/rgb/rgb_level_{depth}.png", 300))
        # plot_hsv_graph(level, False, ('a4', 'landscape', f"./plots/hsv/hsv_level_{depth}.png", 300))
        # plot_hls_graph(level, True, ('a4', 'landscape', f"./plots/hls/hls_level_{depth}.png", 300))

    # Plot RGB 3D scatter
    axis = (1, 1, 1)
    views = [
        top_view(axis),
        camera_view_angles(axis, 0, 0,True),
        camera_view_angles(axis, 60, 0.25, True),
        camera_view_angles(axis, 0, 0.25, True)
    ]
    for d, level in enumerate(levels, 1):
        plot_name = f"./plots/rgb_3d/rgb_3d_scatter_level_{d}.png"
        plot_rgb_scatter_3d(level, views, save_fig=False, fig_data=('a3', 'landscape', plot_name, 600))
    # for d, level in enumerate(levels, 1):
    #     plot_name = f"./plots/rgb_3d/rgb_3d_lines_level_{d}.png"
    #     partitions = partition_level(level, 0, bases[0])
    #     plot_rgb_lines_3d(partitions, views, save_fig=True, fig_data=('a3', 'landscape', plot_name, 600))

    # plot_rgb_scatter_3d(level, 1, bases[0])

    # fig = plot_quality_scatter_3d(level)
    # figname = 'quality_scatter_3d.png'
    # plot_circle_diagram(levels, bases[0])

    # fig = plot_purity_vs_dharma(level)
    # figname = f"purity_vs_dharma_depth_{depth}.png"

    # fig.set_size_inches(figsize)
    # fig.savefig('./PNGs/' + figname, dpi=300)