"""Study of compositions (digit counts) and the subcycles that share a duration."""

from cycles.functions.composition import analyse_level
from cycles.functions.division import compute_levels_by_duration
from cycles.plotting.duration import plot_multilevel_trigraph
from common import BASES, SCALES, PLOTS_DIR, fig_data
from runner import study, run

BASE_DIR = PLOTS_DIR / "study_of_compositions"


@study
def multilevel_trigraph(ctx, opts):
    """Subcycles of depths 1 to 4 grouped by duration: location, timelines and counts."""
    depths = [1, 2, 3, 4]
    color_key = 'cmyk_kscaled'
    subcycles = compute_levels_by_duration(depths, BASES, SCALES)
    path = BASE_DIR / f"multilevel/{color_key}/multilevel_{''.join(str(d) for d in depths)}.png"
    plot_multilevel_trigraph(subcycles, color_key, "Multilevel duration equivalent subcycles",
                             opts.save, fig_data(path, 'a2', 600))


@study(default=False)
def duration_equivalent_compositions(ctx, opts):
    """Print the addresses, durations, starts and colors of depth 3, by duration class."""
    names = ['lcoords', 'durations', 'starts', 'cmyks', 'rgbs']
    for name, values in zip(names, analyse_level(3, SCALES, 2)):
        print(f"--- {name}")
        print(values)


if __name__ == "__main__":
    run()
