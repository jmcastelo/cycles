# Changelog

Versions follow MAJOR.MINOR.PATCH: while below 1.0, a new feature raises MINOR and a fix raises PATCH. The version
is `cycles.__version__` (`cycles/__init__.py`), shown by the explorer (title bar, *Help → About*) and recorded in
sessions and dossiers. The Spanish documentation in `docs/es` states the version it describes, which must be the
current one: `tests/test_version.py` checks it, and the docs' LaTeX converter refuses to build otherwise.

When releasing a version: describe it here, raise `__version__`, update the docs (and their version line), and tag
the commit `vX.Y.Z`.

## Unreleased

- **The time evolution as a dynamical system** (`cycles.functions.dynamics`, `sandbox/study_of_dynamics.py`, docs
  chapter 16): the durations and every measure as time series, in the index order and sampled in years of the
  cycle model. Estimators: DFA and MF-DFA, rescaled range, structure functions, Higuchi dimension, spectra,
  permutation entropy and statistical complexity, recurrence plots and RQA, return times, and shuffled and
  phase-randomized surrogates. Exact results to test them: each step of a duration ((p_{j+1}/p_j)·4^k) and of
  dharma is fixed by the number k of Kali digits carried; the durations have h(q) = (1 + τ(q))/q (H = 0.934) and a
  Riesz-product spectrum; dharma has roughness log₄ b; zooming in is chaotic (entropy = Lyapunov = H(p) = 1.28
  nats per level) and moving on in time an odometer with zero entropy. Purity, mixture, tension, roughness and
  complexity read the same backwards; dharma and trend turn around 5/8 and 0.
  Also delay embedding and the correlation dimension (dharma's is exact, min(1, log 4/log b), in every embedding
  dimension: it is deterministic), change points by binary segmentation and the level of the boundary each falls
  on (roughness, purity, microcosm and mixture change regime on the boundaries of levels 1–3), and a
  digit-permuted surrogate, the null model of the digit order (the durations stay; the structure of the measures
  goes: it is in the hierarchy of the levels).
- **The navigator shows a window of the cycle**, from the whole cycle down to the width of a subcycle of depth 8:
  the mouse wheel zooms in and out around the pointer, dragging the rows pans (a click without moving still
  selects), and a scroll bar under the navigator pans too. The strip of the whole cycle is a map: drag the
  frame to pan, drag its edges to zoom, click an age to fit it. Double-click, right-click, the breadcrumb and
  `Home` fit a subcycle, gliding to it; `+` and `−` zoom around the middle. The zoom of the panels and of the
  breadcrumb is now the smallest subcycle that contains the window. The axis labels the ends of the window;
  switching the widths keeps the same part of the cycle in view; selecting a subcycle out of view pans to it;
  sessions keep the window.
- **The Dynamics panel**: the durations or a measure of a level as a time series, in the order of the subcycles or
  evenly in years: return map, DFA fluctuations, spectrum, recurrence plot, or the series with its change points,
  with a surrogate drawn behind (shuffled, phase-randomized or digits permuted), the estimates and what is known
  exactly; the selection is marked and clicking selects. Layouts saved before it are not restored (the layout
  version is now 10).
- **The multifractal spectrum of the division** (`cycles.functions.multifractal`, `sandbox/study_of_multifractal.py`,
  docs 1.9): f(α) exactly by the Legendre transform for the two measures the division puts on the cycle (the time
  on the index line, the count on the time line), and estimated at finite depths by histograms of the classes of
  equal duration (the subcycles of one exponent). Almost all the time lies in a set of subcycles of dimension
  0.9232, and almost all the subcycles in a set of moments of dimension 0.9192; the two measures are dual.
- **Panels docked with QtAds** (the Qt Advanced Docking System, `PySide6-QtAds`; PySide6 upgraded to 6.12.0 and
  pinned with it): drag a panel or a group of tabs anywhere, with drop targets; float it; pin a group to a side bar
  of the window (auto-hide, sliding out on hover). The arrangements of the Panels menu remain (tabs, side by side,
  stacked, grid, below, and each kind on its side), and named layouts are now QtAds perspectives; *Move a panel*
  and *Corners* are gone, dragging does that. Sessions keep the QtAds layout; layouts saved by earlier versions
  are not translated (those sessions open with the default arrangement). Text panels scroll when short, plot
  panels resize.
- **Attach floating panels**: an *Attach* button in the title bar of a floating window (one panel, or a group of
  tabs floated with its undock button), with the same icon as QtAds' undock button, puts its panels back in the
  main window, each in the tabs of its kind; *Panels → Attach floating panels* (`Ctrl+Alt+F`) does it for all.
- **Readable tab titles in dark themes**: the tab titles take their colors from the desktop's palette (QtAds'
  style sheet left the inactive ones nearly invisible), and follow a change between light and dark.
- **Closing with unsaved changes asks** whether to save them (Save, Don't save, Cancel). Without saving, the next
  start reopens the session as last saved (or a new one); a crash still brings the unsaved changes back.

## 0.4.0 — 2026-11-09

New measures and colorings, queries, and every level down to depth 9.

- **More measures of the subcycles** (`measure.MEASURES`): mixture (entropy of the age shares), tension (weighted
  spread of the virtues), trend (inner levels better or worse than the outer ones), roughness (jumps between
  levels), contrast (the jump of dharma from the previous subcycle), balance (running sum of dharma above its mean)
  and, with a cycle model, angular density (`cycle_analysis.angular_density`: the subcycle's mean precession rate
  over the cycle's). The Measures panel plots any two of them and colors the points by any; the inspector (and
  so the dossier) shows them on one line. The study `measure_correlations` finds that trend, contrast and angular
  density carry information of their own, while mixture nearly repeats purity and roughness tension.
- **Joining the highlighted subcycles** in the Measures and Color space panels (*Join*): the steps of the ⟨σ⟩
  orbit of the selection in order, with arrows, or the swaps of neighbouring digits between the orderings of its
  ages (Same composition). The swaps of one position are parallel in the plane of two measures linear in the
  virtues, such as trend against dharma.
- **New colorings** (grouped in the toolbar by kind, with a description of each; 26 with those of the sky below): `tetrahedron_oklab`, the chaos
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
- **Queries**: a condition on the subcycles typed in the toolbar (`trend > 0.3 and dharma < 0.5`,
  `last == Kali and count(Satya) >= 2`, `year > 0`…) for a new highlight, *Matching the query*: at every depth the
  navigator keeps the matches bright and the Measures and Color space panels ring them; the number of matches is
  shown, and the query is kept in sessions. `cycles.functions.query` accepts only a small, checked part of
  Python's expressions (measures, time, digits, ages, comparisons, arithmetic, `count`, `abs`).
- **Faster levels**: `compute_level` computes a whole level at once with numpy (depth 8 in 0.06 s instead of
  5 s; identical results), so the explorer goes down to **depth 9** (262,144 subcycles). For many moments the
  time map and the ayanamsa are interpolated on a fine grid (`cycle_analysis.dense_years`, `dense_ayanamsa`; well
  under a day), and the inspector computes the measures of the sky for the selected subcycle alone. The group
  explorer lists up to S_8.
- **A tidier toolbar**: one row, grouped by topic with separators (the cycle model; the coloring; the levels; the
  highlight and the query). The drawing options set once moved to the *View* menu as checkable items: *Widths*,
  *Names*, *Labels*, *Borders* (`Ctrl+Shift+B`) and *Compare the division criteria* (`Ctrl+Shift+C`).
- **One color per role**, in the navigator and the plots (`state.SELECTION_COLOR`, `MOMENT_COLOR`, `DATE_COLOR`):
  the selection blue (a thinner border, 2 px, its parents 1 px), the sky moment orange (its cursor and tag, as the
  Follow boxes already were), the marked date red. The cursors are solid lines, and borders and cursors have a
  light edge so that they stand out over cells of any color.
- **The navigator's tags below the rows**: the tags of the marked date and the sky moment, the key of the criteria
  and the label of the planetary events moved from between the overview and the rows to a band under the rows,
  above the time axis (one line per tag shown), so the rows start right under the overview; the event ticks are
  under the last row.
- **Every level in the navigator**: *Levels* goes up to 9, the deepest. Rows of subcycles narrower than a couple of
  pixels are drawn as a strip of pixels, each the width-weighted mean color of the subcycles under it (with a
  highlight, the bright ones, so that no match is lost); clicking, the selection, Follow, bookmarks, cursors and
  events work in them as in the others. Nine levels of the whole cycle repaint in about 30 ms.
- **Tests in parallel**: `pytest-xdist` in the `test` extra; `pytest -n 8` runs the suite in under a minute instead
  of nine.
- **README**: a short introduction with installation, a quick start, the chapters of the documentation and the
  references; everything else lives in `docs/es` (the VS Code tasks are now described in chapter 11).

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
- **Docs**: the formulas are LaTeX in the Markdown (`$…$`, `$$…$$`, as GitHub renders them), typeset in the PDF
  with `unicode-math` and Libertinus Math.
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
