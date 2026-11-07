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

Dividing the arc, each yuga takes 4:3:2:1 of it, the same shares as in
years: 0.4, 0.3, 0.2 and 0.1 of the total. With the presets' 2.5 turns
(900°), Satya takes exactly one turn of the vernal point around the zodiac:

| Yuga | Arc | Degrees | Share of the 2.5 turns |
|---|---|---|---|
| Satya | 1 turn | 360° | 1 / 2.5 = 0.4 |
| Treta | ¾ turn | 270° | 0.75 / 2.5 = 0.3 |
| Dvapara | ½ turn | 180° | 0.5 / 2.5 = 0.2 |
| Kali | ¼ turn | 90° | 0.25 / 2.5 = 0.1 |

The division repeats at every level, so a subcycle's arc is the total times
the product of the shares along its address: Kali › Kali is
2.5 × 0.1 × 0.1 = 0.025 turn (9°), Satya › Kali 2.5 × 0.4 × 0.1 = 0.1 turn
(36°). This is why the preset at a constant rate gives Satya one precession
period (25,772 years).

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
every 20,000 years as the cycle slides along the precession rate. That period
comes from the precession model, not from the division: the rate varies with
the obliquity, about every 41,000 years, each yuga's share deviates one way
while the rate rises and the other way while it falls (Treta's deviation
changes sign about every 20,000 years), and the largest deviation, which
ignores the sign, peaks twice per period, for any arc; the
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
| `test`  | pytest                   | the tests                          |

For example, `pip install -e .` installs the core only and
`pip install -e ".[astro]"` adds the ephemeris.

## Project layout

```
cycles/
  functions/              computation
    division.py             the fractal division, Level, compute_level
    conversion.py           address <-> index <-> base-4 fraction
    composition.py          digit counts and classes of equal duration
    duration.py             duration relations between subcycles
    color.py                colorings of subcycles
    measure.py              dharma and purity
    permutation.py          permutations of address digits
    sound.py                sound synthesis and scalograms
    analysis.py             autocorrelation
    timescale.py            normalized time <-> physical time (TimeMap)
    cycle_model.py          the yuga cycle in history: anchor, scale, division, presets
    cycle_analysis.py       agreement of the time and angle criteria; mismatch grid, best-fit anchor and arc
    astro_dates.py          calendar dates <-> Julian Day <-> decimal year, UT <-> TDB
    nbody_ephemeris.py      long-term planetary ephemeris by N-body integration (one moment or many)
    view.py                 3D camera angles for matplotlib
  plotting/               figures
    helpers.py              shared figure formatting
    generic.py              general-purpose plots of numeric sequences
    sector.py               ring (pie) diagrams of subcycles
    partition.py            ring diagrams of the partitions of a time span
    color.py                colors of subcycles
    measure.py              dharma and purity
    duration.py             which subcycles share a duration, where and how many
    permutation.py          permutations of the subcycles of a level
    cycle_model.py          a cycle model against the precession: rate, deviations by depth, fit scans
    equinoctial_precession.py  ayanamsa and long-term precession, ecliptic coordinates of date,
                            planet positions and zodiac charts
  gui/                    graphical explorer (PySide6); run with cycles-gui or python -m cycles.gui
    __main__.py             entry point
    app.py                  main window: toolbar, menus, dock panels, saving graphs and sessions
    state.py                shared state of the views and the data behind them
    navigator.py            overview strip and rows of subdivisions, markers and tags, criteria overlay
    inspector.py            Subcycle panel: everything about the selection, measures by level
    datepanel.py            Date panel: mark a date and list the subcycles that contain it
    sky.py                  Sky panel: the zodiac with the planets at a moment
    skycompare.py           Sky comparison panel: the skies of a set of subcycles against the selection's
    measures.py             Measures panel: dharma and purity in 2D or 3D
    colorspace.py           Color space panel: the colors of a level in RGB or CMY
    permutations.py         Permutations panel: σ acting on the digit positions
    groupexplorer.py        group explorer: every element of S_m in a sortable table
    compositions.py         Compositions panel: the tetrahedron of compositions
    landscape.py            Model landscape panel: the criteria mismatch over anchor × arc
    notes.py                Notes panel: the notes and bookmarks of the session
    layouts.py              placing the panels around the navigator: moves, arrangements, corners, named layouts
    session.py              sessions: saving and opening everything shown, restoring the last one
    dossier.py              subcycle dossier: a PDF about the selection
    modeldialog.py          cycle model dialog: anchor, scale, division, precession, presets, best fit
    colordialog.py          color parameters dialog
    export.py               save dialog: paper sizes, resolution, formats
    studies.py              launcher of the sandbox studies
sandbox/                  study scripts, one per topic
  common.py                 paths, default parameters and helpers shared by the studies; sessions
  runner.py                 command-line runner (see Running the studies), --session
  study_of_division.py      the division itself: consistency checks and ring diagrams
  study_of_fill_partitions.py  the partition of a time span into subcycles
  study_of_durations.py     which subcycles share a duration, where and how many
  study_of_compositions.py  compositions and the subcycles that share a duration
  study_of_colors.py        colorings of subcycles
  study_of_measures.py      dharma and purity
  study_of_permutations.py  permutations of the digit positions
  study_of_precession.py    the yugas against the precession, with the sky at their boundaries
  study_of_sound.py         sounds synthesised from subcycles
  data/, plots/, docs/      ephemeris tables, saved figures, reference papers (not in the repository)
tests/                    pytest tests (see Tests)
  conftest.py               shared fixtures: offscreen main window, temporary settings, ephemeris
  test_division.py          durations, starts and address conversions
  test_durations_compositions.py  shared durations: compositions and the (1, 0, -2, 1) rule
  test_permutation.py       permutations of the digit positions
  test_color.py             color parameter ranges that keep each level's colors unique
  test_cycle_model.py       the presets, their time maps and boundaries
  test_landscape.py         the mismatch over anchor × arc, its period, the Model landscape panel
  test_gui_panels.py        dock arrangements and reopening closed panels
  test_gui_layouts.py       panels around the navigator: moves, arrangements, corners, named layouts
  test_gui_navigator.py     tag band, dragging the tags, Shift+click
  test_gui_highlight.py     highlights around the selection, Follow
  test_gui_export.py        saving graphs: sizes, formats, resolution
  test_gui_permutations.py  Permutations panel and group explorer
  test_gui_compositions.py  Compositions panel and measures by level
  test_gui_sky_colors.py    sky chart and color parameters dialog
  test_gui_criteria_skycompare.py  criteria overlay and Sky comparison panel
  test_gui_session.py       sessions, restoring the last one, bookmarks, the launcher's session
  test_gui_dossier.py       the dossier: summary, paper, sections, dialog
  test_session_studies.py   studies run with a session (--session)
pyproject.toml            package metadata, dependencies, the cycles-gui command, pytest settings
```

All functions are documented with docstrings, e.g. `help(compute_level)`.

## Tests

```bash
pip install -e ".[gui,test]"
pytest                    # everything (about 40 s)
pytest -m "not gui"       # only the computations (under a second)
```

The computation tests check the division (durations, starts, address
conversions), the rule of equal durations (compositions that differ by a
multiple of (1, 0, -2, 1)), the permutations of digit positions (against
`symmetry-math` and the study, durations kept, Burnside's lemma), the
parameter ranges that keep the colors unique, and the cycle model presets.
The GUI tests run offscreen with their own settings (yours are not touched);
those of the sky chart need the ephemeris tables and are skipped without
them.

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
- `--session FILE` uses the cycle model and the color parameters of a session
  saved by the explorer (see below), so that the figures match what it showed;
  the whole session is available to the studies as `opts.session`.

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
color in every variant. *Measures by level* shows how each level makes up
dharma (its weight times the virtue of its age: 1, 3/4, 1/2, 1/4) and the
shares of the ages whose spread is purity, and how far both range over the
orderings of its ages: the weights fall with depth (bases of the *Parameters*
dialog), so the order matters; a base of 1 would make both depend only on the
composition. The toolbar
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
the plots. *Criteria* compares the two criteria for dividing the cycle,
4:3:2:1 of the precession arc and 4:3:2:1 of the years, over the span of
the cycle model: where the one that is not the model's division puts the
boundaries is drawn in each row (dashed, with the gap to the cell's own
boundary shaded; in rows whose cells are at least a few pixels wide, so zoom
in for the deeper levels), and the tooltip of a subcycle gives the date it
would start by it and the difference in years. *Parameters…*, next
to the coloring, sets the bases and scales of the colorings and measures
(the color weight base, which also weights dharma; the purity weight base;
the cmyk_scaled and cmyk_kscaled scales; the tetrahedron step and its four
vertex colors, one per age) within the
ranges that keep the colors of each level unique, and shows for any depth
how many colors are different and how many a display can show apart. Changes
apply as they are made, so the plots recolor while you edit; *Revert* goes
back to the values the window opened with.

*File → Save graph…* (`Ctrl+E`), or the *Save…* button of the Sky, Measures,
Color space, Permutations, Compositions, Sky comparison and Model landscape panels, saves the navigator or a panel's graph as it is shown
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
subcycles that contain the moment. *Compare…* opens the *Sky comparison*
tab, described below. The Sky tab needs the ephemeris tables (see below): it looks
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

*Group…* opens the group explorer: every element of S_m acting where σ acts,
in a table that sorts by any column and filters by cycle type and parity.
Besides the cycle type, order, parity, fixed subcycles and orbits of ⟨σ⟩,
it gives, as means over the subcycles, how many σ moves, how far in time
(in % of the span), how well it keeps the time order (the correlation
between the order of the subcycles and that of their images), and how much
it changes the color (in the current coloring), dharma and purity. The
columns are filled in progressively (S_8 at depth 8 takes about a minute
and a half; *Stop* interrupts it), and a line checks Burnside's lemma: the
mean number of fixed subcycles is the number of compositions. Clicking a
row loads that element into the panel.

The *Compositions* tab draws the compositions (n₀, n₁, n₂, n₃) of a level,
how many digits of each age its addresses have, as the points of a discrete
tetrahedron with one vertex per age (a composition at the mean of the
vertices of its digits), sized by how many subcycles have it (inside the
zoom, or in the whole cycle) and colored by duration, by the
cmyk_composition coloring or by that number. Compositions of equal duration
differ by multiples of (1, 0, −2, 1) (one Satya and one Kali digit last as
long as two Dvapara ones), so they lie on parallel lines, drawn joining them;
the view *Along the lines of equal duration* turns each class into a single
point. The selection's composition is ringed in blue and its class drawn in
black, the moment's composition in orange; clicking a composition selects
its first subcycle and highlights all of them (*Same composition*).

The *Sky comparison* tab sets the sky of the selection beside the skies of
other subcycles, at their starts (or middles, or ends): all of the
selection's depth, or those with its composition, its duration or its ⟨σ⟩
orbit, or the selection's parts, inside the zoom or everywhere. It draws a
number of small charts (laid out in the rows and columns that make them
largest for the size of the panel, or of the page when saved), evenly spread in time or, with *Most similar first*,
the selection's own followed by the closest ones. The distance Δ between
two skies is the mean angle between the sidereal longitudes of the compared
bodies: the slow ones (Mars and beyond) by default, since over years and
more the Sun, Mercury and Venus are set by the time of the year rather than
by the cycle; or all of them. Unrelated skies are 90° apart on average.
A strip under the charts plots the Δ of every subcycle of the set along
the span, the charts circled and, for all of a depth, the subcycles the
navigator highlights in red; the dashed line is the distance below which
5 % of random moments of the span fall, and the note compares the closest
Δ found and the median with what the same number of random moments would
give: if the subcycles come no closer than random moments, the resemblance
comes from the planets' own periods (Jupiter and Saturn meet about every
20 years and return about every 60), not from the division. The table gives,
for each body, the mean of its sidereal longitudes over the set and their
concentration R (1 if all equal, about √(π/4n) for n random ones, shown
beside it; bold when more than three times that). Clicking a chart or a
point of the strip selects that subcycle (which then becomes the reference)
and moves the sky moment there. The tab uses the Sky tab's ephemeris and
outer-planets option, computes the positions of all the subcycles at once
(a whole level of 65,536 takes under a second; beyond 100,000 they are
sampled evenly), and draws only while it is in view.

The *Model landscape* tab (also the *Landscape* button of the toolbar) maps
how far the two criteria disagree for every anchor (the year of the model's
anchor point) and arc in turns: the largest or the RMS deviation of the time
shares from 4:3:2:1 at depth 1 to 3, on a logarithmic color scale (yellow:
closest), grey where the cycle leaves the range of the long-term precession
model. It fills in an arc at a time from the model's own, so the window
stays usable. The current model is the blue circle: drag it, or double-click
anywhere, to place the cycle there, and every panel follows (Escape cancels
a drag; the model keeps its name, shown as modified in the toolbar). The
presets with the same anchor point are triangles (named in the line above
the map when the pointer is over them) and the best point of the range a
star. Under the map, the precession rate along the same years, with the span
of the current cycle shaded, shows where the landscape's period comes from
(see *The cycle model*). With a constant rate there is no landscape: both
criteria always coincide.

The *Notes* tab holds the notes of the session (free text) and its
bookmarks: subcycles with a label and a note. *View → Bookmark the
selection* (`Ctrl+B`), or the tab's button, adds the selection and lets you
name it; double-click a label or a note to edit it, and a subcycle to go to
it. Bookmarked subcycles have a green corner in the navigator and a tick on
the overview strip, and their label and note in its tooltip.

The ten panels (Subcycle, Date, Sky, Measures, Color space, Permutations, Compositions, Sky comparison,
Model landscape, Notes) can be open at the same
time, to compare a chart with a measure plot and the inspector. The
*Panels* menu shows or hides each one (`Alt+1` to `Alt+9`, and `Alt+0`) and arranges the
open ones as tabs, side by side, stacked, in a 2 × 2 grid, or side by side
below the navigator. Panels can go on any side of the navigator: *Panels →
Arrange around the navigator* puts each kind of panel on its side, in tabs
(information — Subcycle, Date, Notes — on the left; the sky and the graphs on
the right, or the sky on the right and the graphs below, or the sky on the
left too and the graphs below), and *Panels → Move a panel*, or a right
click on a panel's title bar or tab, puts one panel left of, right of, above
or below the navigator (beside the panels already there), floating, or in a
tab with another panel. Panels can also be dragged anywhere, a group of tabs
as a whole by its title bar; the navigator always keeps some room.
*Panels → Corners* chooses whether the side columns take the full height of
the window or the top and bottom rows its full width. *Panels → Layouts*
keeps named arrangements (*Save layout as…*) to switch between, whatever the
session. The arrangement is kept with the session, and between runs
(*Panels → Reset layout* restores the tabs).

*File → Studies…* (`Ctrl+T`) opens the study launcher: every study of the
sandbox scripts, with each script's defaults checked. It runs the checked
ones (or a double-clicked one) as on the command line, each script in its
own process, with *Save figures* and *Show figures* as `--save` and
`--no-show`, and *With the explorer's session* as `--session` (the cycle
model and color parameters shown), and shows their output. The list comes from
`python sandbox/runner.py --catalog`. Levels down to depth 8 are available; the deepest take a few
seconds the first time.

### Sessions

A session is everything the explorer shows, kept in a file
(`*.cycles.json`, JSON): the cycle model in full (so that later changes to
a preset do not change it), the color parameters and display options, the
zoom, the selection, the marked date and the sky moment, the settings of
every panel (with the camera of the 3D views), the window layout, the
notes and the bookmarks, and, to know what produced it, the version of the
code (its git commit, and whether it had uncommitted changes) and the
ephemeris folder used. *File → New session* (`Ctrl+N`, which keeps the
layout), *Open session…* (`Ctrl+O`), *Open recent*, *Save session*
(`Ctrl+S`) and *Save session as…* (`Ctrl+Shift+S`) handle them; the title
bar shows the session's name, with `*` while it has unsaved changes. The
explorer reopens the last session when it starts: it is kept automatically
when the window closes (and every minute while there are unsaved changes),
with its file and its unsaved changes, so nothing is asked on quitting. A
session whose ephemeris folder is not on this computer keeps the current
one, and parts that no longer fit are reported in the status bar.

*File → Subcycle dossier…* (`Ctrl+D`) writes a PDF about the selected
subcycle, on a chosen paper (A5 to A1, Letter, Legal, Tabloid; portrait or
landscape) with chosen margins. It can hold a summary (everything the
inspector shows, the measures by level, its colors, its bookmarks, and the
cycle model, session and code it comes from), the navigator around it, the
sky at its start, middle and end, the Measures, Color space, Compositions,
Permutations, Sky comparison and Model landscape graphs as they are set up
(laid out again for the page), and the notes and bookmarks of the session.
Text and the navigator are vectors; the graphs are vectors too, or images
at a chosen resolution (lighter for graphs with many points). The options
are remembered.

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
