# Changelog

Versions follow MAJOR.MINOR.PATCH: while below 1.0, a new feature raises MINOR and a fix raises PATCH. The version
is `cycles.__version__` (`cycles/__init__.py`), shown by the explorer (title bar, *Help → About*) and recorded in
sessions and dossiers. The Spanish documentation in `docs/es` states the version it describes, which must be the
current one: `tests/test_version.py` checks it, and the docs' LaTeX converter refuses to build otherwise.

When releasing a version: describe it here, raise `__version__`, update the docs (and their version line), and tag
the commit `vX.Y.Z`.

## 0.3.0 — 2026-11-08

Planetary events and significance tests.

- **Planetary events and significance tests** (`cycles.functions.events`, `cycles.functions.significance`,
  `sandbox/study_of_events.py`): exact conjunctions over the whole cycle from the ephemeris, grouped into series;
  the trigon (element) changes of the great conjunctions in the sidereal and the tropical zodiac; the planets
  around a point of the zodiac; tests against rigid rotations of the subcycle boundaries, with Holm's correction.
  Three hypotheses: the Sūrya Siddhānta gathering at 0° Aries, the great conjunctions and their trigon changes,
  the outer-planet conjunctions.
- **Events panel** in the explorer: each test interactively (catalogue, depth, whole cycle or the zoom,
  rotations), the null distribution with the observed value, the events of the zoomed span (click one to show
  its sky) and a layer of event marks in the navigator. Sessions and dossiers include it.
- **Significance over all the models** (look-elsewhere): `cycle_analysis.boundary_grid` gives the boundaries of a
  grid of models (anchor × arc, dividing the arc), `significance.scan_models` the distance of each to the events and
  a global p from rigid shifts of the event catalogue (the best model of each shift); `expected_distance` gives the
  distance of a random moment exactly. In the study (`model_map`) and in the Events panel (view *Over the models*:
  the map, the closest models, a double click places the cycle there). With the default ranges no model comes
  closer than chance once the search is taken into account.
- **H1 with the mean planets** the Sūrya Siddhānta speaks of (`events.mean_longitudes`, from the mean elements of
  Simon et al. 1994; `surya_siddhanta_longitudes`, from the text's revolutions per Mahāyuga): the study
  `mean_planets` (five boundaries, without the anchor, Treta and Kali where the text's even revolutions conjoin
  them, Treta alone) and the drift of the text's mean motions from the sky (closest around AD 1172, more than 20°
  off at its own epoch); two more tests in the Events panel. Still nothing significant after Holm (37 tests).
- **More measures of the subcycles** (`measure.MEASURES`): mixture (entropy of the age shares), tension (weighted
  spread of the virtues), trend (inner levels better or worse than the outer ones), roughness (jumps between
  levels), contrast (the jump of dharma from the previous subcycle), balance (running sum of dharma above its mean)
  and, with a cycle model, angular density (`cycle_analysis.angular_density`: the subcycle's mean precession rate
  over the cycle's). The Measures panel plots any two of them and colors the points by any; the inspector (and
  so the dossier) shows them on one line. The study `measure_correlations` finds that trend, contrast and angular
  density carry information of their own, while mixture nearly repeats purity and roughness tension.
- **Docs**: the formulas are LaTeX in the Markdown (`$…$`, `$$…$$`, as GitHub renders them), typeset in the PDF
  with `unicode-math` and Libertinus Math.
- **Joining the highlighted subcycles** in the Measures and Color space panels (*Join*): the steps of the ⟨σ⟩
  orbit of the selection in order, with arrows, or the swaps of neighbouring digits between the orderings of its
  ages (Same composition). The swaps of one position are parallel in the plane of two measures linear in the
  virtues, such as trend against dharma.
- **New colorings** (21 in all, grouped in the toolbar with a description of each): `tetrahedron_oklab`, the chaos
  game of the tetrahedron coloring in OKLab, a perceptual color space (the regions of the four ages look equally
  large; the vertices are shrunk to keep every color in the sRGB gamut; screens tell fewer of its colors apart, so
  it is an alternative, not a replacement); `duration_class`, one color per class of equal duration; the
  measures (dharma, purity, mixture, tension, trend, roughness, contrast, balance), all alike on a sequential or
  a diverging color map chosen in *Parameters…* (viridis, cividis, magma, plasma, inferno or gray; blue–red,
  coolwarm, orange–purple or brown–teal), kept in sessions, and changing them only recolors; and, with a cycle
  model, the angular density and the sign and element of the vernal point at the start of each subcycle.
  `CycleState.colors` gives every coloring to the panels. Dharma and purity are no longer gray by default (the
  gray map shows them as before).
- **Three more measures** and three more colorings: *microcosm* (how closely the age shares match the whole
  cycle's 0.4, 0.3, 0.2, 0.1) and *complexity* (Lempel–Ziv, of the order of the ages), from the address; and,
  with a cycle model and the ephemeris of the Sky panel (now also given to the state), *gathering* (how gathered
  Sun to Saturn are at the start of each subcycle) and the colorings of the **trigon of the great conjunctions
  in force** at each start, sidereal and tropical (`events.trigon_periods`, `events.trigon_in_force`). The
  correlation study finds microcosm close to dharma, complexity close to mixture, and gathering independent of
  the address measures.
- **README**: a short introduction with installation, a quick start, the chapters of the documentation and the
  references; everything else lives in `docs/es` (the VS Code tasks are now described in chapter 11).
- The panel arrangements put Events with the sky panels; the eleventh panel has no `Alt` shortcut.

## 0.2.0 — 2026-11-07

The graphical explorer, the cycle model and the research tools.

- **Explorer** (`cycles-gui`): navigator with overview strip, rows of subdivisions, date and sky tags, highlights
  (equal duration, same composition, ⟨σ⟩ orbit) and the comparison of the two division criteria; panels
  Subcycle (with measures by level), Date, Sky, Sky comparison, Measures, Color space, Permutations (with the group
  explorer), Compositions, Model landscape and Notes.
- **Cycle model**: anchor, scale, division and precession, with presets and an editor; analysis of the time and
  angle criteria (mismatch by depth, best fit, landscape over anchor × arc).
- **Color parameters** dialog with the ranges that keep colors unique.
- **Saving graphs** on paper formats in PNG, JPEG, PDF, SVG and EPS.
- **Research sessions**: everything shown, the layout included, saved as JSON and restored at start-up; bookmarks
  with label and note; subcycle dossier in PDF; studies run with a session (`--session`).
- **Panels anywhere around the navigator**: move menus, arrangements by kind, corners, named layouts.
- **Ephemeris**: vectorised queries (`body_states`, `geocentric_directions`, `planet_positions_many`).
- **Tests**: a pytest suite of the computations and of the explorer (offscreen).
- **Spanish documentation** (`docs/es`): chapters in Markdown with their figures, and a LaTeX document generated
  from them (its PDF is attached to the release).

## 0.1.0 — 2026-11-05

The computation library and the studies.

- The fractal division (addresses, levels, durations, starts), compositions and classes of equal duration,
  colorings (CMYK variants, Sierpinski tetrahedron), dharma and purity, permutations of the digit positions,
  sound synthesis.
- Time maps, long-term precession and ayanamsa, calendars and time scales, the N-body ephemeris and the zodiac
  charts.
- The sandbox studies with their command-line runner.
