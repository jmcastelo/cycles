from cycles.functions.division import compute_level
from cycles.functions.color import lcoords_to_lrgb
from cycles.plotting.color import plot_quality_grid
from cycles.plotting.generic import *

if __name__ == "__main__":
    bases = [4, 2, 1]
    max_depth = 5
    scale = 2/3
    levels = [compute_level(depth, bases, scale) for depth in range(1, max_depth + 1)]
    lcoords, durations, starts, cmyks, rgbs, dharmas, purities = zip(*levels)

    lrgbs = [np.apply_along_axis(lcoords_to_lrgb, 1, coords) for coords in lcoords]
    dharma_colors = [np.array([np.full(3, d) for d in dharma]) for dharma in dharmas]
    purity_colors = [np.array([np.full(3, p) for p in purity]) for purity in purities]

    colors = {
        'rgb': {
            'cmyk': [rgb[:, 0] for rgb in rgbs],
            'cmyk_normalised': [rgb[:, 1] for rgb in rgbs],
            'cmyk_scaled': [rgb[:, 2] for rgb in rgbs],
            'cmyk_kscaled': [rgb[:, 3] for rgb in rgbs],
            'cmyk_composition': [rgb[:, 4] for rgb in rgbs],
            'wcmy': [rgb[:, 5] for rgb in rgbs],
            'lrgb': [lrgb[:, -1] for lrgb in lrgbs],
            'dharma': dharma_colors,
            'purity': purity_colors
        },
        'cmyk': {
            'cmyk': [cmyk[:, 0] for cmyk in cmyks],
            'wcmy': [cmyk[:, 1] for cmyk in cmyks]
        }
    }

    rgb_key = 'cmyk_kscaled'
    cmyk_key = 'wcmy'

    base_dir = f"./plots/study_of_measures"

    plot = {
        'dharma_vs_time': False,
        'dharma_vs_index': False,
        'purity_vs_time': False,
        'purity_vs_index': False,
        'dharma_vs_purity': True
    }

    if plot['dharma_vs_time']:
        for depth, (start, duration, dharma) in enumerate(zip(starts, durations, dharmas), 1):
            title = f"Dharma vs time at depth {depth}"
            ylabel = 'Dharma'
            xlabel = 'Time (norm. units)'
            fig_data = (
                'a3',
                'landscape',
                f"{base_dir}/dharma/base_{bases[1]}/dharma_vs_time_at_depth_{depth}.png",
                600,
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

    if plot['dharma_vs_purity']:
        '''
        for depth, (dharma, purity) in enumerate(zip(dharmas, purities), 1):
            title = f"Dharma vs Purity at depth {depth}"
            ylabel = 'Dharma'
            xlabel = 'Purity'
            fig_data = (
                'a3',
                'landscape',
                f"{base_dir}/{rgb_key}/dharma_vs_purity_at_depth_{depth}.png",
                600,
                False
            )
            index = np.arange(0, len(purity))
            plot_y_vs_x(dharma, purity, (None, None), title, xlabel, ylabel, False, fig_data)
        '''
        plot_quality_grid()