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
- **Astronomy**: the yugas placed on the precession of the equinoxes, with
  charts of the planets at the start of any subcycle, computed with a
  long-term N-body ephemeris.

## Key concepts

- **Address (`lcoords`)**: one digit (0–3) per depth level, naming the age
  chosen at that level, from the outermost cycle inwards. `[0, 3, 1]` is the
  Silver part of the Iron part of the Golden age.
- **Index (`tcoord`)**: the address read as a base-4 number; it is the
  subcycle's position in time order among all subcycles of its depth.
- **Level**: all `4^depth` subcycles of one depth, returned by
  `compute_level` as a `Level` with their addresses, durations, starts (as
  fractions of the whole cycle), color variants, dharma and purity.
- **Time map**: links the normalized time of a cycle (0 to 1) to physical
  time, such as years (see below).

## From normalized to physical time

The division works on the unit interval. A `TimeMap`
(`cycles.functions.timescale`) sends normalized time to physical time and
back, and gives the physical start and end of any subcycle:

```python
from cycles.functions.timescale import TimeMap, address_label
from cycles.plotting.equinoctial_precession import precession_time_map

time_map = TimeMap.linear(-61148.5, 3391.6)   # 0 -> start year, 1 -> end year
start, end = time_map.interval([3, 1])        # years of Kali › Treta
lcoords = time_map.subcycle_at(2026.8, 4)     # subcycle containing a date
print(address_label(lcoords))                 # 'Kali › Dvapara › Treta › Satya'
```

Three kinds of map are available:

| Map | Divides | Use |
|---|---|---|
| `TimeMap.linear(start, end)` | time, uniformly | ages exactly 4:3:2:1 in years |
| `TimeMap.from_age_boundaries([...])` | time, fitted to 5 given age boundaries | each age fits its dates; linear inside it |
| `precession_time_map(start, turns)` | precession angle | every subcycle boundary is a precession boundary |

### The cycle model

How the yuga cycle sits in history is an open question: sources differ on
the moment the Kali Yuga starts and on the length of the cycle. A
`CycleModel` (`cycles.functions.cycle_model`) makes each choice explicit and
gives the time map:

- **anchor**: a date and time (local mean time at a longitude, or UT), or a
  value of the ayanamsa (a position of the vernal point), and the point of
  the cycle that falls on it (start of Satya, Treta, Dvapara or Kali, or the
  end);
- **scale**: the total precession arc in turns, or the length in years (one
  determines the other);
- **division**: what 4:3:2:1 divides at every level: precession angle,
  time, or angle for the yugas and time inside them;
- **precession**: the long-term model (varying rate) or a constant rate
  given by its period. With a constant rate both divisions coincide.

```python
from cycles.functions.cycle_model import load_presets

model = load_presets()['Kali 3102 BC, midnight at Ujjain']
model.boundaries()                          # years of the yuga boundaries
model.replace(division='time').time_map()   # same anchor and arc, dividing time
```

Because the precession rate varies, the two criteria (4:3:2:1 in years and
in angle) cannot both hold exactly: a yuga's share of the time is its share
of the arc times the cycle's mean rate over the yuga's own mean rate. With
2.5 turns, dividing angle, the yugas take 0.4039, 0.2915, 0.2040 and 0.1006
of the time; inside them the deviation shrinks with depth.

Built-in presets:

| Preset | Anchor (start of Kali) | Scale |
|---|---|---|
| Kali 3102 BC, midnight at Ujjain (default) | midnight 17/18 Feb 3102 BC, Ujjain (Surya Siddhanta; Aryabhata's midnight system) | 2.5 turns |
| Kali 3102 BC, sunrise at Lanka | mean sunrise 18 Feb 3102 BC on the Ujjain meridian (Aryabhata's sunrise system) | 2.5 turns |
| Kali 3104 BC, Abhyankar 1993 | sunrise at Ujjain, 7 Feb 3104 BC (Bull. Astr. Soc. India 21, 475) | 2.5 turns |
| Precession period at constant rate | as the default | 64,430 years (Satya = 25,772 years) |

`cycles.functions.cycle_analysis` measures how well the two criteria agree
(`mismatch_by_depth`: the largest and RMS deviation of the time shares at each
depth) and searches for the anchor, and optionally the arc, that makes them
agree best (`fit_anchor`). With 2.5 turns, the agreement rises and falls about
every 20,000 years as the cycle slides along the precession rate; the
traditional anchor is near a worst placement (largest deviation 0.0085, against
about 0.002 at the best ones), because Treta then covers the peak of the rate
and Dvapara its trough. A free arc tends to the longest allowed, since a longer
cycle averages out the variation of the rate. `cycles.plotting.cycle_model`
plots the rate across the cycle, the deviations by depth and the fit scans;
the `precession_rate`, `criteria_by_depth` and `best_fit` studies of
`study_of_precession.py` use them.

Presets you save (from the GUI, or with `save_user_presets`) go to
`sandbox/cycle_presets.json`, or to `$CYCLES_PRESETS`. `study_of_precession.py`
uses the preset named in its `PRESET` constant.

### Color parameters

The colorings keep every subcycle of a level a different color when their
parameters (see `compute_level`) stay within these ranges, checked by
`color.color_parameter_problems`:

| Parameter | Range | Why |
|---|---|---|
| `bases[1]`, color weight base | ≥ 2 | each weight then outweighs all the later ones together, so the ink sums give back the address (below 2 colors repeat at isolated bases, e.g. the golden ratio) |
| `scales[0]`, cmyk_scaled | (0, 1] | the CMYK to RGB conversion is then one-to-one |
| `scales[1]`, cmyk_kscaled black | [0, 0.25] or [0.5, 1] | in between the conversion can have two preimages |
| `scales[2]`, tetrahedron step | [0.5, 1) | the last digit then outweighs all the earlier ones |
| `colors`, tetrahedron vertices | four RGB colors not in one plane | each color then gives back its barycentric coordinates; flat sets may repeat colors (four on a line, from depth 2) |

`bases[1]` also weights dharma; `bases[2]` weights purity and needs no
bound (1 weighs all levels equally). Within the ranges, larger bases and
steps keep the colors different but bring deep levels closer than a display
can show: at depth 7, base 2 gives 15,764 colors apart on screen out of
16,384, and base 3 only 4,442.

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
| `gui`   | PySide6                  | the graphical explorer             |
| `all`   | all of the above         |                                    |

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
    timescale.py        normalized time <-> physical time (TimeMap)
    cycle_model.py      the yuga cycle in history: anchor, scale, division, presets
    cycle_analysis.py   agreement of the time and angle criteria; best-fit anchor and arc
    astro_dates.py      calendar dates <-> Julian Day <-> decimal year, UT <-> TDB
    nbody_ephemeris.py  long-term planetary ephemeris by N-body integration
    view.py             3D camera angles for matplotlib
  plotting/       figures (one module per topic: color, measure, duration, sector,
                  partition, permutation, generic, equinoctial_precession)
  gui/            graphical explorer (PySide6)
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

In VS Code / Code OSS, the tasks in `.vscode/tasks.json` run the study script
that is open: `Ctrl+Shift+B` asks for the studies and options to run (empty
runs the defaults), and *Terminal → Run Task…* also offers listing the studies
and a batch run that saves every figure. They use the interpreter in `.venv`.

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
| `study_of_precession.py`     | yugas against precession; charts at subcycle starts       |

New studies are plain functions marked with `@study` (see
`sandbox/runner.py`); shared paths and default parameters are in
`sandbox/common.py`.

## The graphical explorer

```bash
pip install -e ".[gui]"
cycles-gui                 # or: python -m cycles.gui
```

The window shows the subdivisions of the subcycle you have zoomed into, one
row per depth, each subcycle in its color. A strip at the top shows the
whole cycle, with the zoomed part framed and the marked date and sky moment;
clicking a yuga there zooms to it. Click a subcycle to select it,
double-click to zoom in, right-click to zoom out; the breadcrumb above
returns to any outer level. In the navigator, the arrow keys move to the
previous or next subcycle, the parent and the first part, Enter zooms in and
Backspace zooms out.

The panel on the right shows the selected subcycle: address, index, start,
duration, composition, how many subcycles share its duration or its
composition (and its place in time among the latter), its image under the σ
of the *Permutations* tab and the size of its orbit, dharma, purity, and its
color in every variant. The toolbar
chooses the coloring, how many levels to draw, whether widths follow
duration (time) or are equal (index), the names of the ages (yugas or
Golden/Silver/Bronze/Iron), the labels (names, which run vertically in
tall narrow cells; dots, four for Satya, three for Treta, two for Dvapara and
one for Kali; both; or none), whether cells have borders, and what to
highlight around the selection: the subcycles of its depth with the same
duration, with the same composition (the orderings of its ages, a class
inside those of equal duration), or its orbit under the powers of the σ of
the *Permutations* tab (with its image under σ outlined in dashed purple);
the others are dimmed in the navigator and the highlighted ones ringed in
the plots. *Parameters…*, next
to the coloring, sets the bases and scales of the colorings and measures
(the color weight base, which also weights dharma; the purity weight base;
the cmyk_scaled and cmyk_kscaled scales; the tetrahedron step and its four
vertex colors, one per age) within the
ranges that keep the colors of each level unique, and shows for any depth
how many colors are different and how many a display can show apart. Changes
apply as they are made, so the plots recolor while you edit; *Revert* goes
back to the values the window opened with.

*File → Save graph…* (`Ctrl+S`), or the *Save…* button of the Sky, Measures,
Color space and Permutations panels, saves the navigator or a panel's graph as it is shown
(view angles, selection and moment included): on a paper format (A5 to A1,
Letter, Legal, Tabloid; portrait or landscape), at the size on screen, or at a
custom size in mm, cm or inches, with margins and an optional title, as PNG or
JPEG at a chosen resolution, or as PDF, SVG or EPS (vectors; EPS for the
panels only), on a white or transparent background.

The *Cycle* box chooses how the cycle is placed in history: one of the
cycle model presets, or normalized time. *Model…* opens the cycle model
editor, which shows the resulting yuga dates, lengths, arcs, ayanamsa and
mean precession rates as you change the anchor, scale, division or
precession, and applies the model or saves it as a preset. Its *Best fit*
menu searches for the anchor and/or arc that best satisfy both criteria
and loads the result into the form. For the selected subcycle, the
inspector also shows the ayanamsa at its start and end, its arc and its
place on the cycle's arc, and the mean precession rate over it. With a map in years, the axis below the rows
shows years or dates, the inspector shows when the selected subcycle starts
and ends, and a red line marks a date (the present, at start). Its tag, in
the band between the cycle strip and the rows, can be dragged along the rows
to move the date (Escape cancels the drag). In the *Date*
tab, enter a date (`2026-11-05`, `3102 BC-02-18`) or a decimal year
(`-3101.5`) to mark it and select the subcycle that contains it; the table
lists the subcycle containing it at every depth, and clicking a row selects
it.

The *Sky* tab draws the zodiac with the planets (as in
`study_of_precession.py`) at a moment of the zoomed span (what the navigator
shows), with a table of their sidereal longitudes, signs and nakshatras.
The moment is the dashed blue line in the navigator: the slider moves it
across the span, dragging its *sky* tag or Shift+clicking on the navigator
puts it anywhere, and the play
button advances it from where it is to the end of the span, by a chosen
step (years, days or hours per frame; the number of frames left is shown)
and delay. *To marked date* moves it to the marked date and *Mark this
moment* does the reverse. With *Follow* on, every plot highlights in orange
its subcycle that contains the moment: each row of the navigator at its own
depth, and the point of the measures and color space plots, when they show
it; the selection (in blue) is left as it is. The tab also lists the
subcycles that contain the moment. The tab needs the ephemeris tables (see below): it looks
in `$CYCLES_EPHEMERIS`, then in the folder last chosen with *Ephemeris…*,
then in `sandbox/data/tabla70k70k`.

The *Measures* tab plots dharma and purity (against each other, against
time, or against index, or in 3D: dharma, purity and time or index, with
a faint line in time order, camera presets looking along each axis, and
dragging to rotate) for the level of the selected subcycle, or for a
chosen depth, inside the zoomed subcycle or over the whole cycle, with
points sized by duration or all alike. The
selected subcycle is ringed in blue and, with a highlight chosen in the
toolbar, those sharing its duration, its composition or its ⟨σ⟩ orbit in black; clicking a point selects that subcycle.

The *Color space* tab shows the colors of the subcycles of a level as
points in 3D, the path joining them in time order, or both: in the RGB cube
(with its corners named) or, for the CMYK colorings, in CMY ink
coordinates. It follows the coloring and the color parameters as they
change, draws the tetrahedron of the tetrahedron coloring, can size points
by duration, and has camera presets (gray axis vertical, down or up the gray
axis, the faces of the cube); drag to rotate. Like the measures plot, it
rings the selected subcycle (and those of equal duration), and clicking a
point selects it.

The *Permutations* tab shows how a permutation σ of the digit positions of
the addresses (as in `study_of_permutations.py`: an address `a` becomes
`a ∘ σ`) moves the subcycles of a level, keeping their durations. σ is a
preset (cyclic shift, inverse shift, reversal, a swap of the first or last
two positions, random) or typed in one-line notation (`1 2 0`) or as cycles
(`(0 1 2)(3 4)`); the panel gives its order, parity and cycle type, how many
subcycles it fixes and in how many orbits ⟨σ⟩ moves them. It acts on the
digits below the zoom (the subcycles stay inside it) or on all of them (the
whole cycle), at a chosen depth or automatically (as in the other panels:
the depth of the selection, or the level below the zoom; a single digit gives
only the identity). The views are the timelines of the
powers σ⁰, σ¹, … back to the identity, with lines following each subcycle
(drawn automatically up to 1024 subcycles), the permutation matrix of σ,
and the matrices of all its powers. The selection (blue) and, with
*Follow*, the sky moment (orange) are traced through the powers, and
clicking a subcycle selects it.

The six panels (Subcycle, Date, Sky, Measures, Color space, Permutations) can be open at the same
time, to compare a chart with a measure plot and the inspector. The
*Panels* menu shows or hides each one (`Alt+1` to `Alt+6`) and arranges the
open ones as tabs, side by side, stacked, in a 2 × 2 grid, or side by side
below the navigator; panels can also be dragged anywhere, docked or
floating. The arrangement is remembered between sessions (*Panels → Reset
layout* restores the tabs).

*File → Studies…* (`Ctrl+T`) opens the study launcher: every study of the
sandbox scripts, with each script's defaults checked. It runs the checked
ones (or a double-clicked one) as on the command line, each script in its
own process, with *Save figures* and *Show figures* as `--save` and
`--no-show`, and shows their output. The list comes from
`python sandbox/runner.py --catalog`. Levels down to depth 8 are available; the deepest take a few
seconds the first time.

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
