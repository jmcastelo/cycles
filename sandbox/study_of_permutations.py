from symmetrymath import SymmetricGroup

from cycles.functions.composition import *
from cycles.functions.conversion import lcoords_to_tcoords
from cycles.functions.division import compute_level, compute_duration
from cycles.functions.permutation import permutation_matrix
from cycles.plotting.permutation import plot_timeline_permutations, plot_permutation_matrices


if __name__ == "__main__":
    depth = 3
    bases = [4, 2, 2]
    scale = 2/3

    lcoords, durations, starts, cmyks, rgbs, dharmas, purities = compute_level(depth, bases, scale)

    fdurations = np.ones(4 ** depth)
    fstarts = np.cumsum(fdurations)

    colors = {
        'cmyk': rgbs[:, 0],
        'cmyk_normalised': rgbs[:, 1],
        'cmyk_scaled': rgbs[:, 2],
        'cmyk_kscaled': rgbs[:, 3],
        'cmyk_composition': rgbs[:, 4],
        'wcmy': rgbs[:, 5]
    }

    color_key = 'cmyk_kscaled'

    base_dir = f"./plots/study_of_permutations"

    study = {
        'duration_equivalent_compositions': False,
        'plot_timeline_permutations': True,
        'permutation_matrices': False
    }

    if study['duration_equivalent_compositions']:
        eq_comps = [duration_equivalent_compositions(c) for c in compositions(5)]
        for eqc in eq_comps:
            print([c for c in eqc])
            for c in eqc:
                print([[lcoords_to_tcoords(lcoord), lcoord, compute_duration(lcoord)] for lcoord in lexmin_enumeration(c)])

    if study['plot_timeline_permutations']:
        SG = SymmetricGroup(depth)

        element = (0, 2, 1)

        tcoord_perm_pow = np.array([
            [lcoords_to_tcoords(np.array(SG.operation(tuple(lcoord), p))) for lcoord in lcoords]
            for p in SG.powers(element)
        ])

        perm_matrix = permutation_matrix(element, lcoords)

        title = f"Permutation {SG.identity} → {element} of level coordinates at depth {depth}"
        relpath = f"{base_dir}/powers/{color_key}/depth_{depth}_permutation_{''.join(str(element))}.png"
        fig_data = ('a2', 'landscape', relpath, 600, True)

        plot_timeline_permutations(
            fdurations,
            fstarts,
            colors[color_key],
            tcoord_perm_pow,
            perm_matrix,
            title,
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