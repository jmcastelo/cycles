from cycles.functions.composition import analyse_level
from cycles.functions.division import compute_levels_by_duration
from cycles.plotting.duration import plot_multilevel_duration_equivalences, plot_multilevel_trigraph

if __name__ == "__main__":
    bases = [4, 2, 2]
    scale = 2 / 3

    base_dir = f"./plots/study_of_compositions"

    study = {
        'duration_equivalent_compositions': False,
        'multilevel_duration_equivalences': True
    }

    if study['duration_equivalent_compositions']:
        glcoords, gdurations, gstarts, gcmyks, grgbs = analyse_level(3, scale, 2)
        print(glcoords)
        print(gdurations)
        print(gstarts)
        print(gcmyks)
        print(grgbs)

    if study['multilevel_duration_equivalences']:
        depths = [1, 2, 3, 4]
        subcycles = compute_levels_by_duration(depths, bases, scale)

        color_key = 'cmyk_kscaled'
        title = f"Multilevel duration equivalent subcycles"
        fig_data = ('a2', 'landscape', f"{base_dir}/multilevel/{color_key}/multilevel_{''.join(str(d) for d in depths)}.png", 600, False)
        plot_multilevel_trigraph(subcycles, color_key, title, True, fig_data)