import papersize as ps

from cycle_division_functions import compute_level
from color_plots import *
from view_functions import get_symmetry_axis_views

if __name__ == "__main__":
    # Compute levels
    # bases = [4, 2]
    # num_levels = 5
    # levels = [compute_level(depth, bases) for depth in range(1, num_levels + 1)]

    # Paper size
    psize = ps.rotate(ps.parse_papersize('A3', 'in'), ps.LANDSCAPE)
    figsize = (float(psize[0]), float(psize[1]))

    # Plot level bars
    # fig = plot_level_bars(levels)
    # fig.set_size_inches(figsize)
    # fig.savefig('./PNGs/level_bars.png', dpi=600)


    # Plot color graphs
    bases = [4, 2]
    depth = 7
    level = compute_level(depth, bases)

    # fig = plot_cmyk_graph(level)
    # figname = 'cmyk_graph.png'

    # fig = plot_rgb_graph(level)
    # figname = 'rgb_graph.png'

    # plot_hsv_graph(level)
    # plot_hls_graph(level)
    # plot_overlay(level, bases[1])

    # views = get_symmetry_axis_views(axis_direction=[1, 1, 1], center=[0.5, 0.5, 0.5], height=0)
    # fig = plot_rgb_scatter_3d(level, views)
    # figname = 'rgb_scatter.png'

    # plot_rgb_scatter_3d(level, 1, bases[0])

    # fig = plot_quality_scatter_3d(level)
    # figname = 'quality_scatter_3d.png'
    # plot_circle_diagram(levels, bases[0])

    fig = plot_purity_vs_dharma(level)
    figname = f"purity_vs_dharma_depth_{depth}.png"

    fig.set_size_inches(figsize)
    fig.savefig('./PNGs/' + figname, dpi=300)