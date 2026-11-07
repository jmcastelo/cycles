# Changelog

Versions follow MAJOR.MINOR.PATCH: while below 1.0, a new feature raises MINOR and a fix raises PATCH. The version
is `cycles.__version__` (`cycles/__init__.py`), shown by the explorer (title bar, *Help → About*) and recorded in
sessions and dossiers. The Spanish documentation in `docs/es` states the version it describes, which must be the
current one: `tests/test_version.py` checks it, and the docs' LaTeX converter refuses to build otherwise.

When releasing a version: describe it here, raise `__version__`, update the docs (and their version line), and tag
the commit `vX.Y.Z`.

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
