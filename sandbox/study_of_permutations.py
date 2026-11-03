import numpy as np
import matplotlib.pyplot as plt
from fontTools.merge import layout
from matplotlib.gridspec import GridSpec
from symmetrymath import SymmetricGroup

from cycles.functions.conversion import lcoords_to_tcoord, tcoord_to_lcoords
from cycles.functions.color import lcoords_to_lrgb
from cycles.functions.division import compute_level, compute_duration
from cycles.functions.permutation import permutation_matrix
from cycles.plotting.permutation import plot_timeline_permutations, plot_permutation_matrices


if __name__ == "__main__":
    depth = 3
    bases = [4, 2, 2]
    scales = [1 / 2, 2 / 3, 0.5]
    colors = np.array([[1, 1, 0], [0, 1, 1], [1, 0, 1], [0, 0, 0]])

    lcoords, durations, starts, cmyks, rgbs, dharmas, purities = compute_level(depth, bases, scales, colors)

    lrgbs = np.apply_along_axis(lcoords_to_lrgb, 1, lcoords)
    dharma_colors = np.array([np.full(3, dharma) for dharma in dharmas])
    purity_colors = np.array([np.full(3, purity) for purity in purities])

    fdurations = np.ones(4 ** depth)
    fstarts = np.cumsum(fdurations)

    colors = {
        'cmyk': rgbs[:, 0],
        'cmyk_normalised': rgbs[:, 1],
        'cmyk_scaled': rgbs[:, 2],
        'cmyk_kscaled': rgbs[:, 3],
        'cmyk_composition': rgbs[:, 4],
        'wcmy': rgbs[:, 5],
        'tetrahedron': rgbs[:, 6],
        'lrgb': lrgbs[:, -1],
        'dharma': dharma_colors,
        'purity': purity_colors
    }

    color_key = 'lrgb'

    base_dir = f"./plots/study_of_permutations"

    study = {
        'plot_timeline_permutations': True,
        'permutation_matrices': False
    }

    if study['plot_timeline_permutations']:
        SG = SymmetricGroup(depth)

        element_groups = [[(1, 0, 2), (0, 2, 1), (2, 1, 0)], [(1, 2, 0)]]
        # elements = [(4, 1, 2, 3, 0)]

        # tcoord_perm_pow = [np.array([
        #     [lcoords_to_tcoord(np.array(SG.operation(tuple(lcoord), p))) for lcoord in lcoords]
        #     for p in SG.powers(element)
        # ]) for element in elements]

        indices = []
        ax_texts = []
        for elements in element_groups:
            texts = []
            lcs = np.array(lcoords)
            tcoord_perm_pow = [np.array([lcoords_to_tcoord(lc) for lc in lcs])]
            for el in elements:
                for order in range(SG.order_of(el)):
                    tcoords = np.array([lcoords_to_tcoord(np.array(SG.operation(tuple(lc), el))) for lc in lcs])
                    tcoord_perm_pow.append(tcoords)
                    lcs = [tcoord_to_lcoords(tc, bases[0], depth) for tc in tcoords]
                    texts.append(f"{SG.identity} → {el}")
            indices.append(np.array(tcoord_perm_pow))
            ax_texts.append(texts)

        color_keys = ['cmyk_normalised', 'lrgb', 'dharma']
        selected_colors = [colors[key] for key in color_keys]

        relpath = f"{base_dir}/powers/{'+'.join(color_keys)}/depth_{depth}_permutations_{len(elements)}.png"
        fig_data = ('a2', 'landscape', relpath, 600, False)

        fig = plt.figure()
        gs = GridSpec(1, 2, figure=fig, left=0.01, right=0.99, bottom=0.02, top=0.98, wspace=0.02)
        axes = [
            fig.add_subplot(gs[0, 0]),
            fig.add_subplot(gs[0, 1]),
            # fig.add_subplot(gs[2, 0]),
            # fig.add_subplot(gs[:, 1]),
        ]

        plot_timeline_permutations(
            fdurations,
            fstarts,
            selected_colors,
            indices,
            ax_texts,
            fig,
            axes,
            False,
            fig_data
        )

    if study['permutation_matrices']:
        SG = SymmetricGroup(depth)

        # perm_matrices = [permutation_matrix(tuple(element), lcoords) for element in SG.elements]
        # plot_permutation_matrices(perm_matrices, list(SG.elements))

        element = (1, 0, 3, 2)
        pow_matrices = [permutation_matrix((tuple(p)), lcoords) for p in SG.powers(element)]
        plot_permutation_matrices(pow_matrices, list(SG.powers(element)))