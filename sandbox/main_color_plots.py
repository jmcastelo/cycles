from cycles.cycle_division_functions import compute_level
from cycles.plotting.color_plots import *

if __name__ == "__main__":
    # Compute levels

    bases = [4, 2]

    num_levels = 5
    levels = [compute_level(depth, bases) for depth in range(1, num_levels + 1)]

    # depth = 6
    # level = compute_level(depth, bases)

    # Plot level bars
    # plot_level_bars(levels, True, ('a4', 'landscape', f"./plots/levels/base_{bases[1]}/levels_down_to_{num_levels}.png", 600))

    # Plot duration bars
    # aspect = (1, 1)
    # l1, l2 = 1, 5
    # plot_name = f"./plots/durations/durations_{l1}_to_{l2}_aspect_{aspect[0]}_{aspect[1]}.png"
    # plot_duration_bars(levels, l1, l2, aspect, False, ('a4', 'landscape', plot_name, 600))

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

    # Plot Dharma
    # for depth, level in enumerate(levels, 1):
    #     plot_dharma_vs_time(level, True, ('a4', 'landscape', f"./plots/dharma/base_{bases[1]}/dharma_vs_time_level_{depth}.png", 300))
    #     plot_dharma_vs_index(level, True, ('a4', 'landscape', f"./plots/dharma/base_{bases[1]}/dharma_vs_index_level_{depth}.png", 300))

    # Plot RGB 3D scatter
    # axis = (1, 1, 1)
    # views = [
    #     top_view(axis),
    #     camera_view_angles(axis, 90, 0,True),
    #     camera_view_angles(axis, 60, 0.25, True),
    #     camera_view_angles(axis, 0, 0.25, True)
    # ]
    # for depth, level in enumerate(levels, 1):
    #     plot_name = f"./plots/rgb_3d/base_{bases[1]}/rgb_3d_scatter_level_{depth}.png"
    #     plot_rgb_scatter_3d(level, views, True, ('a3', 'landscape', plot_name, 600))
    # for depth, level in enumerate(levels, 1):
    #     plot_name = f"./plots/rgb_3d/base_{bases[1]}/rgb_3d_lines_level_{depth}.png"
    #     plot_rgb_lines_3d(level, views, True, ('a3', 'landscape', plot_name, 600))

    # Plot ordered durations


    # TODO: Rewrite the following plots
    # fig = plot_quality_scatter_3d(level)
    # figname = 'quality_scatter_3d.png'
    # plot_circle_diagram(levels, bases[0])

    # fig = plot_purity_vs_dharma(level)
    # figname = f"purity_vs_dharma_depth_{depth}.png"

    # fig.set_size_inches(figsize)
    # fig.savefig('./PNGs/' + figname, dpi=300)