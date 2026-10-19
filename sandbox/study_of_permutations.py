from symmetrymath import SymmetricGroup

from cycles.functions.composition import *
from cycles.functions.conversion import lcoords_to_int
from cycles.functions.division import compute_level
from cycles.plotting.permutation import plot_timeline_permutations


if __name__ == "__main__":
    '''
    eq_comps = [duration_equivalent_compositions(c) for c in compositions(5)]
    for eqc in eq_comps:
        print([c for c in eqc])
        for c in eqc:
            print([[lcoords_to_int(lcoord), lcoord, compute_duration(lcoord)] for lcoord in lexmin_enumeration(c)])
    '''

    depth = 4
    bases = [4, 2, 2]
    scale = 2/3

    lcoords, durations, starts, cmyks, rgbs, dharmas, purities = compute_level(depth, bases, scale)

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

    SG = SymmetricGroup(depth)
    element = (0,1,3,2)
    tcoord_perm_pow = np.array([
        [lcoords_to_int(np.array(SG.operation(tuple(lcoord), p))) for lcoord in lcoords]
        for p in SG.powers(element)
    ])

    title = f"Permutation {SG.identity} → {element} of level coordinates at depth {depth}"
    relpath = f"{base_dir}/powers/{color_key}/depth_{depth}_permutation_{''.join(str(element))}.png"
    fig_data = ('a3', 'landscape', relpath, 600, True)

    plot_timeline_permutations(
        durations,
        starts,
        colors[color_key],
        tcoord_perm_pow,
        title,
        False,
        fig_data
    )