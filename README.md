# cycles

Mathematical analysis of cycles divided fractally into four ages.

A cycle is split into four ages whose lengths are in the ratio 4 : 3 : 2 : 1
(0.4, 0.3, 0.2 and 0.1 of the whole): Golden, Silver, Bronze and Iron, or, in
the Hindu tradition, Satya, Treta, Dvapara and Kali Yuga. Each age is split
again in the same ratio, and so on to any depth. This project studies the
resulting structure from several angles:

- **Durations**: which subcycles share a duration, where they lie in time, and
  how many there are. At a given depth, duration depends only on how many
  times each age appears in a subcycle's address, not on their order.
- **Colors**: each age is mapped to a printing ink (Golden → cyan,
  Silver → magenta, Bronze → yellow, Iron → black), and each subcycle gets a
  color blended from its address. Variants include weighted CMYK and a
  Sierpinski-tetrahedron coloring.
- **Measures**: *dharma* (weighted "virtue" of the ages in an address, from 1
  for all-Golden to 1/4 for all-Iron) and *purity* (how dominated an address
  is by a single age).
- **Permutations**: how the subcycles move when the digits of their addresses
  are permuted.
- **Sound**: subcycles rendered as tones and wavelets, with scalograms of the
  result.
- **Astronomy**: the yugas placed on the precession of the equinoxes, with the
  positions of the planets at their boundaries, computed with a long-term
  N-body ephemeris.

## Key concepts

- **Address (`lcoords`)**: one digit (0–3) per depth level, naming the age
  chosen at that level, from the outermost cycle inwards. `[0, 3, 1]` is the
  Silver part of the Iron part of the Golden age.
- **Index (`tcoord`)**: the address read as a base-4 number; it is the
  subcycle's position in time order among all subcycles of its depth.
- **Level**: all `4^depth` subcycles of one depth, returned by
  `compute_level` as a `Level` with their addresses, durations, starts (as
  fractions of the whole cycle), color variants, dharma and purity.

## Installation

Requires Python 3.11 or later.

```bash
git clone https://github.com/jmcastelo/cycles.git
cd cycles
python -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
```

The core needs only NumPy, Matplotlib, `papersize` and `symmetry-math`. Two
optional extras add the heavier dependencies:

| Extra   | Adds                     | Needed for                         |
|---------|--------------------------|------------------------------------|
| `astro` | REBOUND, REBOUNDx        | building the N-body ephemeris      |
| `sound` | PyWavelets, sounddevice  | scalograms and sound playback      |
| `all`   | both of the above        |                                    |

For example, `pip install -e .` installs the core only and
`pip install -e ".[astro]"` adds the ephemeris.

## Project layout

```
cycles/
  functions/      computation
    division.py         the fractal division, Level, compute_level
    conversion.py       address <-> index <-> base-4 fraction
    composition.py      digit counts and classes of equal duration
    duration.py         duration relations between subcycles
    color.py            colorings of subcycles
    measure.py          dharma and purity
    permutation.py      permutations of address digits
    sound.py            sound synthesis and scalograms
    analysis.py         autocorrelation
    astro_dates.py      calendar dates <-> Julian Day <-> decimal year, UT <-> TDB
    nbody_ephemeris.py  long-term planetary ephemeris by N-body integration
    view.py             3D camera angles for matplotlib
  plotting/       figures (one module per topic)
sandbox/          study scripts, one per topic
```

All functions are documented with docstrings, e.g. `help(compute_level)`.

## Running the studies

Each script in `sandbox/` is a collection of studies (analyses or plots) that
can be listed and run from the command line:

```bash
python sandbox/study_of_durations.py --list          # available studies (* = default)
python sandbox/study_of_durations.py                 # run the default studies
python sandbox/study_of_durations.py counts trigraph # run the named studies
python sandbox/study_of_durations.py --all           # run every study
```

Options:

- `--save` writes the figures to `sandbox/plots/` (and sounds to
  `sandbox/sounds/`).
- `--no-show` runs without opening windows or playing sounds, for batch runs.

| Script                       | Topic                                                     |
|------------------------------|-----------------------------------------------------------|
| `study_of_division.py`       | consistency checks, ring and circle diagrams              |
| `study_of_durations.py`      | equal durations: location, counts, distances, correlations |
| `study_of_compositions.py`   | subcycles of several depths grouped by duration           |
| `study_of_colors.py`         | colorings: timelines, 3D color spaces, color components   |
| `study_of_measures.py`       | dharma and purity                                         |
| `study_of_permutations.py`   | permutations of address digits                            |
| `study_of_fill_partitions.py`| covering a time span with subcycles                       |
| `study_of_sound.py`          | tones, wavelets and scalograms                            |
| `study_of_precession.py`     | yugas against the precession of the equinoxes             |

New studies are plain functions marked with `@study` (see
`sandbox/runner.py`); shared paths and default parameters are in
`sandbox/common.py`.

## The ephemeris data

`study_of_precession.py` reads planetary positions from precomputed ephemeris
tables in `sandbox/data/`, which are not part of the repository. Build them
with:

```bash
# about 70,000 years in each direction from J2000.0
python -m cycles.functions.nbody_ephemeris build sandbox/data/tabla70k70k 70000 \
    --direction both --forward-years 70000 --workers 2

# the same with a tighter integrator tolerance
python -m cycles.functions.nbody_ephemeris build sandbox/data/tabla70k70kp 70000 \
    --direction both --forward-years 70000 --workers 2 --epsilon 1e-9
```

The first table takes a few hours and about 2.4 GB of disk; the second takes
longer and about 6.4 GB. Interrupted builds resume from their checkpoint.

The integration uses DE421 initial conditions, Newtonian gravity with
first-order relativistic corrections, and the IAS15 integrator. Over the span
of the study, the two tolerances agree to within a tenth of an arcsecond; the
larger uncertainty comes from what the model leaves out (such as the Sun's
mass loss), not from the integrator. See the docstring of
`cycles/functions/nbody_ephemeris.py` for details and accuracy figures.

## License

GNU General Public License v3.0 only. See [LICENSE](LICENSE).
