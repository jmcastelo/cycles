"""Study of planetary events against the boundaries of the subcycles, with significance tests.

Three hypotheses, tested in the sidereal (Lahiri, Jyotiṣa) and the tropical (Western) zodiac where it matters:

* H1, Sūrya Siddhānta: at the boundaries of the yugas the planets stand together at the start of Aries
  (measured on the true planets Sun to Saturn, the Moon left out: their mean angle from 0° Aries); tested on the
  five boundaries and on the four that are not the model's anchor, since the traditional epoch may have been
  chosen for its gathering of planets;
* H1m, the same with the mean planets the text speaks of (the mean Sun, the heliocentric mean longitudes of
  Mercury and Venus, their śīghra, and of Mars, Jupiter and Saturn; Simon et al. 1994), on the five boundaries,
  without the anchor, on the two where the text's own mean motions put a conjunction (Treta and Kali: all its
  revolutions per Mahāyuga are even), and on Treta alone (not the anchor); and how far the text's mean motions drift from the real mean planets;
* H2, great conjunctions: the boundaries of depths 1 to 5 fall near the Jupiter–Saturn conjunctions, or near
  the changes of their trigon (element), as in the Persian doctrine of world ages;
* H3, outer conjunctions: the boundaries fall near the Uranus–Neptune or Neptune–Pluto conjunctions.

Each test compares the boundaries with rigid rotations of them (the same spacing, placed anywhere in the cycle);
``summary`` corrects the whole family with Holm's method. The event catalogues are computed once and kept in
``sandbox/data/events/``.
"""

import numpy as np
import matplotlib.pyplot as plt

from runner import study, run
from common import DATA_DIR, PLOTS_DIR, save_figure

from cycles.functions.cycle_analysis import boundary_fractions, boundary_grid
from cycles.functions.cycle_model import DEFAULT_PRESET, load_presets
from cycles.functions.events import (
    CLASSICAL, ZODIACS, around_point, cached_conjunctions, first_of_series, mean_longitudes,
    surya_siddhanta_longitudes, table_span, tdb_years, trigon_changes,
)
from cycles.functions.significance import holm, proximity_test, rotations, scan_models, value_test

BASE_DIR = PLOTS_DIR / "study_of_events"
CACHE_DIR = DATA_DIR / "events"
TABLE = DATA_DIR / "tabla70k70k"
PRESET = DEFAULT_PRESET           # the cycle model, unless a session gives one (--session)
DEPTHS = (1, 2, 3, 4, 5)
ROTATIONS = 5000                  # rigid rotations of the boundaries in each test
PAIRS = {'great': ('jupiter', 'saturn'), 'uranus_neptune': ('uranus', 'neptune'),
         'neptune_pluto': ('neptune', 'pluto')}
MARGIN = 200.0                    # years of events beyond the cycle, so that the nearest one exists at the ends
# The map over the models: anchors around the model's, arcs in turns, depths, event shifts
MAP_ANCHORS = 30000.0, 1000.0     # half-width and step (years)
MAP_TURNS = (1.0, 4.0, 0.25)
MAP_DEPTHS = (1, 2, 3)
MAP_SHIFTS = 1000
YUGA_LABELS = ('start of Satya', 'start of Treta', 'start of Dvapara', 'start of Kali', 'end')


def setup():
    import common
    import cycles.functions.nbody_ephemeris as nbe
    from cycles.gui.sky import ephemeris_parts
    model = common.MODEL or load_presets()[PRESET]
    print(f"Cycle model: {model.name}")
    tables = [nbe.load_ephemeris(part) for part in ephemeris_parts(TABLE)]
    time_map = model.time_map()
    boundaries = {d: tdb_years(time_map.to_physical(boundary_fractions(d))) for d in DEPTHS}
    start, end = boundaries[1][0], boundaries[1][-1]
    print(f"Boundaries in TDB years, from {start:.1f} to {end:.1f}; depths {DEPTHS[0]} to {DEPTHS[-1]}")
    return dict(model=model, tables=tables, boundaries=boundaries, start=start, end=end, catalogs={}, results={})


# -- the event catalogues

def catalog(ctx, name: str) -> dict:
    """The conjunctions of a pair over the cycle (with a margin), from the shared cache or computed once."""
    if name not in ctx.catalogs:
        a, b = PAIRS[name]
        start, end = ctx.start - MARGIN, ctx.end + MARGIN
        print(f"{a}–{b} conjunctions from {start:.0f} to {end:.0f} (cached in {CACHE_DIR})…", flush=True)
        ctx.catalogs[name] = cached_conjunctions(ctx.tables, TABLE, a, b, start, end, CACHE_DIR)
    return ctx.catalogs[name]


def series_times(data: dict) -> np.ndarray:
    """One moment per series of conjunctions (its first)."""
    return data['times'][first_of_series(data)]


@study
def event_catalog(ctx, opts):
    """Compute (or load) the conjunction catalogues and describe them."""
    for name, (a, b) in PAIRS.items():
        data = catalog(ctx, name)
        first = series_times(data)
        inside = (first >= ctx.start) & (first <= ctx.end)
        print(f"{a}–{b}: {len(data['times'])} conjunctions in {len(first)} series "
              f"({inside.sum()} inside the cycle), one series every {np.diff(first).mean():.1f} years")
        if name == 'great':
            for zodiac in ZODIACS:
                changes = trigon_changes(data, zodiac)
                print(f"   trigon changes ({zodiac}): {len(changes)}, every {np.diff(changes).mean():.0f} years "
                      f"on average (median {np.median(np.diff(changes)):.0f})")


# -- H1: the Sūrya Siddhānta claim

def h1_tests(ctx) -> list[dict]:
    """
    The planets around 0° Aries at the five yuga boundaries, and at the four that are not the model's anchor:
    the anchor (the start of Kali, by default) is the traditional epoch, which may have been chosen for its
    gathering of planets, so a result that rests on it alone is circular.
    """
    if 'h1' in ctx.results:
        return ctx.results['h1']
    from cycles.functions.cycle_model import ANCHOR_POINTS
    rows = []
    yugas = ctx.boundaries[1]
    anchor = list(ANCHOR_POINTS).index(ctx.model.anchor_point)
    keep = np.arange(len(yugas)) != anchor
    for zodiac in ZODIACS:
        def value(times, zodiac=zodiac):
            return around_point(ctx.tables, times, CLASSICAL, 0.0, zodiac)['mean_distance']
        result = value_test(yugas, value, ctx.start, ctx.end, ROTATIONS, seed=1)
        result.update(hypothesis='H1 Sūrya Siddhānta', test=f"planets at 0° Aries ({zodiac})", depth=1,
                      unit='°', zodiac=zodiac)
        rows.append(result)
        # the same rotations, scored on the boundaries other than the anchor
        shifted = rotations(yugas, ctx.start, ctx.end, ROTATIONS, seed=1)[:, keep]
        null = value(shifted.ravel()).reshape(shifted.shape).mean(axis=1)
        observed = float(value(yugas[keep]).mean())
        result = {'observed': observed, 'null': null, 'expected': float(null.mean()),
                  'p': float((1 + np.count_nonzero(null <= observed)) / (1 + len(null))),
                  'ratio': observed / float(null.mean()), 'hypothesis': 'H1 Sūrya Siddhānta',
                  'test': f"… without the anchor ({zodiac})", 'depth': 1, 'unit': '°', 'zodiac': zodiac}
        rows.append(result)
    ctx.results['h1'] = rows
    return rows


@study
def surya_siddhanta(ctx, opts):
    """H1: are the planets together at 0° Aries at the yuga boundaries, more than chance?"""
    yugas = ctx.boundaries[1]
    rng = np.random.default_rng(7)
    randoms = rng.uniform(ctx.start, ctx.end, 20000)
    for zodiac in ZODIACS:
        at = around_point(ctx.tables, yugas, CLASSICAL, 0.0, zodiac)
        ref = around_point(ctx.tables, randoms, CLASSICAL, 0.0, zodiac)
        print(f"\nZodiac {zodiac}: mean angle of Sun…Saturn from 0° Aries, and the arc that holds them all")
        for label, year, distance, spread in zip(YUGA_LABELS, yugas, at['mean_distance'], at['spread']):
            p_d = np.mean(ref['mean_distance'] <= distance)
            p_s = np.mean(ref['spread'] <= spread)
            print(f"  {label:17s} {year:10.1f}  mean angle {distance:6.1f}° (random ≤: {100 * p_d:5.1f} %)"
                  f"   spread {spread:6.1f}° (random ≤: {100 * p_s:5.1f} %)")
    rows = h1_tests(ctx)
    fig, axes = plt.subplots(1, len(rows), figsize=(15, 3.6))
    for ax, row in zip(np.atleast_1d(axes), rows):
        ax.hist(row['null'], bins=60, color='0.75')
        ax.axvline(row['observed'], color='#d62728', lw=2, label=f"yuga boundaries: {row['observed']:.1f}°")
        ax.set_title(f"{row['test']}\np = {row['p']:.3f}", fontsize=9)
        ax.set_xlabel('mean angle from 0° Aries over the 5 boundaries (°)')
        ax.legend(fontsize=7)
    fig.tight_layout()
    for row in rows:
        print(f"\n{row['test']}: observed {row['observed']:.1f}°, rotations {row['expected']:.1f}° on average, "
              f"p = {row['p']:.3f}")
    finish(fig, opts, 'h1_surya_siddhanta.png')


# -- H1m: the mean planets

def h1m_tests(ctx) -> list[dict]:
    """The mean planets around 0° Aries: all five boundaries, without the anchor, and Treta and Kali (the text's)."""
    if 'h1m' in ctx.results:
        return ctx.results['h1m']
    from cycles.functions.cycle_model import ANCHOR_POINTS
    yugas = ctx.boundaries[1]
    anchor = list(ANCHOR_POINTS).index(ctx.model.anchor_point)
    treta = list(ANCHOR_POINTS).index('treta')
    kali = list(ANCHOR_POINTS).index('kali')
    subsets = {'': np.arange(5), ', without the anchor': np.delete(np.arange(5), anchor),
               ', Treta and Kali': np.array([treta, kali]),        # where the text's own motions conjoin them
               ', Treta': np.array([treta])}                      # the text's other conjunction, not the anchor
    rows = []
    for zodiac in ZODIACS:
        def value(times, zodiac=zodiac):
            return around_point(None, times, CLASSICAL, 0.0, zodiac, mean=True)['mean_distance']
        shifted = rotations(yugas, ctx.start, ctx.end, ROTATIONS, seed=2)
        for name, keep in subsets.items():
            null = value(shifted[:, keep].ravel()).reshape(len(shifted), len(keep)).mean(axis=1)
            observed = float(value(yugas[keep]).mean())
            rows.append({'observed': observed, 'null': null, 'expected': float(null.mean()),
                         'p': float((1 + np.count_nonzero(null <= observed)) / (1 + len(null))),
                         'ratio': observed / float(null.mean()), 'hypothesis': 'H1m mean planets',
                         'test': f"mean planets{name} ({zodiac})", 'depth': 1, 'unit': '°',
                         'zodiac': zodiac})
    ctx.results['h1m'] = rows
    return rows


@study
def mean_planets(ctx, opts):
    """H1m: the mean planets of the Sūrya Siddhānta at 0° Aries at the yuga boundaries; the drift of its motions."""
    yugas = ctx.boundaries[1]
    rng = np.random.default_rng(7)
    randoms = rng.uniform(ctx.start, ctx.end, 20000)
    for zodiac in ZODIACS:
        at = around_point(None, yugas, CLASSICAL, 0.0, zodiac, mean=True)
        ref = around_point(None, randoms, CLASSICAL, 0.0, zodiac, mean=True)
        print(f"\nZodiac {zodiac}: mean planets (Sun, Mercury, Venus, Mars, Jupiter, Saturn) from 0° Aries")
        for label, year, distance, spread in zip(YUGA_LABELS, yugas, at['mean_distance'], at['spread']):
            lon = '  '.join(f"{at['longitudes'][b][list(yugas).index(year)]:5.1f}" for b in CLASSICAL)
            print(f"  {label:17s} {year:10.1f}  [{lon}]  mean angle {distance:5.1f}° "
                  f"(random ≤: {100 * np.mean(ref['mean_distance'] <= distance):5.1f} %)  spread {spread:5.1f}° "
                  f"(random ≤: {100 * np.mean(ref['spread'] <= spread):5.1f} %)")
    rows = h1m_tests(ctx)
    print()
    for r in rows:
        print(f"{r['test']:44s} observed {r['observed']:6.1f}°, rotations {r['expected']:5.1f}°, p = {r['p']:.3f}")
    # how far the text's mean motions (0 at its epoch, the start of Kali) are from the real mean planets
    epoch = yugas[3]
    years = np.arange(np.ceil(epoch), 2501.0, 1.0)
    real = mean_longitudes(years, CLASSICAL, 'sidereal')
    text = surya_siddhanta_longitudes(years, epoch, CLASSICAL)
    gap = np.vstack([np.abs((real[b] - text[b] + 180) % 360 - 180) for b in CLASSICAL])
    print("\nThe text's mean planets (all at 0° at the start of Kali) against the real ones (sidereal, Lahiri):")
    print(f"  {'year':>7s} " + ' '.join(f"{b:>8s}" for b in CLASSICAL) + '   mean')
    for year in (epoch, 0.0, 499.0, 1000.0, 1500.0, 2000.0):
        k = int(np.argmin(np.abs(years - year))) if year != epoch else None
        real_y = mean_longitudes([year], CLASSICAL)
        text_y = surya_siddhanta_longitudes([year], epoch, CLASSICAL)
        diffs = [((real_y[b][0] - text_y[b][0] + 180) % 360) - 180 for b in CLASSICAL]
        print(f"  {year:7.0f} " + ' '.join(f"{d:8.1f}" for d in diffs) + f"   {np.mean(np.abs(diffs)):5.1f}")
    best = int(np.argmin(gap.mean(axis=0)))
    without_mercury = int(np.argmin(np.delete(gap, 1, axis=0).mean(axis=0)))
    print(f"  closest overall in year {years[best]:.0f} (mean gap {gap.mean(axis=0)[best]:.1f}°); without Mercury in "
          f"{years[without_mercury]:.0f} ({np.delete(gap, 1, axis=0).mean(axis=0)[without_mercury]:.1f}°)")
    fig, axes = plt.subplots(1, 2, figsize=(13, 3.8), gridspec_kw={'width_ratios': [1, 1.4]})
    for b in CLASSICAL:
        axes[1].plot(years, ((real[b] - text[b] + 180) % 360) - 180, lw=1, label=b)
    axes[1].axhline(0, color='0.5', lw=0.6)
    axes[1].set_xlabel('year'); axes[1].set_ylabel('real − text (°)')
    axes[1].set_title("The text's mean motions against the real mean planets (0 at the start of Kali)", fontsize=9)
    axes[1].legend(fontsize=7, ncols=3)
    row = rows[0]
    axes[0].hist(row['null'], bins=60, color='0.75')
    axes[0].axvline(row['observed'], color='#d62728', lw=2)
    axes[0].set_title(f"{row['test']}: p = {row['p']:.3f}", fontsize=9)
    axes[0].set_xlabel('mean angle from 0° Aries over the 5 boundaries (°)')
    fig.tight_layout()
    finish(fig, opts, 'h1m_mean_planets.png')


# -- H2 and H3: conjunctions near the boundaries

def proximity_rows(ctx, hypothesis: str, test: str, events: np.ndarray, zodiac: str = '') -> list[dict]:
    rows = []
    for depth in DEPTHS:
        result = proximity_test(ctx.boundaries[depth], events, ctx.start, ctx.end, ROTATIONS, seed=depth)
        result.update(hypothesis=hypothesis, test=test, depth=depth, unit='years', zodiac=zodiac)
        rows.append(result)
    return rows


def h2_tests(ctx) -> list[dict]:
    if 'h2' not in ctx.results:
        data = catalog(ctx, 'great')
        rows = proximity_rows(ctx, 'H2 great conjunctions', 'Jupiter–Saturn conjunctions', series_times(data))
        for zodiac in ZODIACS:
            rows += proximity_rows(ctx, 'H2 great conjunctions', f"trigon changes ({zodiac})",
                                   trigon_changes(data, zodiac), zodiac)
        ctx.results['h2'] = rows
    return ctx.results['h2']


def h3_tests(ctx) -> list[dict]:
    if 'h3' not in ctx.results:
        rows = []
        for name, label in (('uranus_neptune', 'Uranus–Neptune conjunctions'),
                            ('neptune_pluto', 'Neptune–Pluto conjunctions')):
            rows += proximity_rows(ctx, 'H3 outer conjunctions', label, series_times(catalog(ctx, name)))
        ctx.results['h3'] = rows
    return ctx.results['h3']


def print_rows(rows: list[dict]) -> None:
    print(f"  {'test':38s} {'depth':>5s} {'observed':>10s} {'rotations':>10s} {'ratio':>6s} {'p':>7s}")
    for r in rows:
        print(f"  {r['test']:38s} {r['depth']:5d} {r['observed']:10.2f} {r['expected']:10.2f} "
              f"{r['ratio']:6.2f} {r['p']:7.3f}")


def plot_rows(rows: list[dict], title: str):
    tests = list(dict.fromkeys(r['test'] for r in rows))
    fig, axes = plt.subplots(len(tests), len(DEPTHS), figsize=(13, 2.6 * len(tests)), squeeze=False)
    for i, test in enumerate(tests):
        for j, r in enumerate([r for r in rows if r['test'] == test]):
            ax = axes[i, j]
            ax.hist(r['null'], bins=50, color='0.75')
            ax.axvline(r['observed'], color='#d62728', lw=2)
            ax.set_title(f"depth {r['depth']}: p = {r['p']:.3f}", fontsize=8)
            ax.tick_params(labelsize=7)
            if j == 0:
                ax.set_ylabel(test, fontsize=8)
    fig.suptitle(title + ' (grey: mean distance for rotated boundaries; red: the boundaries), years', fontsize=10)
    fig.tight_layout()
    return fig


@study
def great_conjunctions(ctx, opts):
    """H2: do the boundaries fall near the Jupiter–Saturn conjunctions or their trigon changes?"""
    rows = h2_tests(ctx)
    print('Mean distance (years) from the boundaries to the nearest event:')
    print_rows(rows)
    finish(plot_rows(rows, 'H2: great conjunctions and trigon changes'), opts, 'h2_great_conjunctions.png')


@study
def outer_conjunctions(ctx, opts):
    """H3: do the boundaries fall near the Uranus–Neptune or Neptune–Pluto conjunctions?"""
    rows = h3_tests(ctx)
    print('Mean distance (years) from the boundaries to the nearest event:')
    print_rows(rows)
    finish(plot_rows(rows, 'H3: outer-planet conjunctions'), opts, 'h3_outer_conjunctions.png')


@study
def summary(ctx, opts):
    """All the tests of H1, H1m, H2 and H3, with p-values corrected for the whole family (Holm)."""
    rows = h1_tests(ctx) + h1m_tests(ctx) + h2_tests(ctx) + h3_tests(ctx)
    adjusted = holm([r['p'] for r in rows])
    print(f"{len(rows)} tests; p: one-sided (closer than the rotated boundaries), {ROTATIONS} rotations each\n")
    print(f"  {'hypothesis':24s} {'test':38s} {'depth':>5s} {'observed':>9s} {'expected':>9s} {'p':>7s} "
          f"{'Holm':>7s}")
    for r, p_adj in zip(rows, adjusted):
        flag = '  *' if p_adj < 0.05 else ''
        print(f"  {r['hypothesis']:24s} {r['test']:38s} {r['depth']:5d} {r['observed']:9.2f} "
              f"{r['expected']:9.2f} {r['p']:7.3f} {p_adj:7.3f}{flag}")
    significant = int(np.sum(adjusted < 0.05))
    smallest = min(r['p'] for r in rows)
    print(f"\n{significant} of {len(rows)} tests significant at 5 % after Holm's correction "
          f"(smallest raw p = {smallest:.3f}; with {len(rows)} tests about {0.05 * len(rows):.1f} raw p < 0.05 "
          f"are expected by chance alone).")
    if opts.save:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        with open(BASE_DIR / 'summary.csv', 'w', encoding='utf-8') as f:
            f.write('hypothesis,test,zodiac,depth,observed,expected,ratio,p,holm\n')
            for r, p_adj in zip(rows, adjusted):
                f.write(f"{r['hypothesis']},{r['test']},{r['zodiac']},{r['depth']},{r['observed']:.4f},"
                        f"{r['expected']:.4f},{r['ratio']:.4f},{r['p']:.5f},{p_adj:.5f}\n")
        print(f"Saved {BASE_DIR / 'summary.csv'}")


# -- the map over the models (look-elsewhere)

def wide_catalog(ctx, name: str) -> dict:
    """The conjunctions of a pair over the whole span of the ephemeris (for models placed anywhere in it)."""
    key = 'wide_' + name
    if key not in ctx.catalogs:
        a, b = PAIRS[name]
        start, end = table_span(ctx.tables)
        print(f"{a}–{b} conjunctions over the whole ephemeris, {start:.0f} to {end:.0f}…", flush=True)
        ctx.catalogs[key] = cached_conjunctions(ctx.tables, TABLE, a, b, start + 1, end - 1, CACHE_DIR)
    return ctx.catalogs[key]


MAP_TESTS = {
    'Jupiter–Saturn conjunctions': lambda ctx: series_times(wide_catalog(ctx, 'great')),
    'trigon changes (sidereal)': lambda ctx: trigon_changes(wide_catalog(ctx, 'great'), 'sidereal'),
    'trigon changes (tropical)': lambda ctx: trigon_changes(wide_catalog(ctx, 'great'), 'tropical'),
    'Uranus–Neptune conjunctions': lambda ctx: series_times(wide_catalog(ctx, 'uranus_neptune')),
    'Neptune–Pluto conjunctions': lambda ctx: series_times(wide_catalog(ctx, 'neptune_pluto')),
}


def map_grid(ctx):
    solution = ctx.model.solve()
    half, step = MAP_ANCHORS
    anchors = np.arange(solution['anchor'] - half, solution['anchor'] + half + 1, step)
    turns = np.arange(MAP_TURNS[0], MAP_TURNS[1] + 1e-9, MAP_TURNS[2])
    return anchors, turns, solution


def map_rows(ctx) -> list[dict]:
    """For each test and depth: the scan of the models, the default model's place in it, and the global p."""
    if 'map' in ctx.results:
        return ctx.results['map']
    anchors, turns, solution = map_grid(ctx)
    span = table_span(ctx.tables)
    rows = []
    for depth in MAP_DEPTHS:
        grid = boundary_grid(ctx.model, anchors, turns, depth)
        finite = np.isfinite(grid)
        tdb = np.full(grid.shape, np.nan)
        tdb[finite] = tdb_years(grid[finite])
        own = tdb_years(boundary_grid(ctx.model, [solution['anchor']], [solution['turns']], depth)[0, 0])
        for test, events in MAP_TESTS.items():
            ev = events(ctx)
            scan = scan_models(tdb, ev, span, MAP_SHIFTS, seed=depth)
            own_scan = scan_models(own[None, :], ev, span, 0)
            observed = scan['observed'][np.isfinite(scan['observed'])]
            local = proximity_test(own, ev, own[0], own[-1], ROTATIONS, seed=depth)
            best = scan['best']
            rows.append({'test': test, 'depth': depth, 'scan': scan, 'anchors': anchors, 'turns': turns,
                         'own_ratio': float(own_scan['ratio'][0]),
                         'own_rank': float(np.mean(observed <= own_scan['observed'][0])),
                         'own_p': local['p'],
                         'best_anchor': float(anchors[best[0]]) if best else np.nan,
                         'best_turns': float(turns[best[1]]) if best else np.nan,
                         'best_ratio': float(scan['ratio'][best]) if best else np.nan,
                         'p_global': scan['p_global'], 'models': int(np.sum(scan['valid']))})
    ctx.results['map'] = rows
    return rows


@study(default=False)
def model_map(ctx, opts):
    """Every model (anchor × arc, dividing the arc): which comes closest to the events, and is that chance?"""
    from cycles.gui.state import date_text
    rows = map_rows(ctx)
    anchors, turns, solution = map_grid(ctx)
    adjusted = holm([r['p_global'] for r in rows])
    print(f"Models: start of {ctx.model.anchor_point} from {anchors[0]:.0f} to {anchors[-1]:.0f} every "
          f"{MAP_ANCHORS[1]:.0f} years × arcs {turns[0]:g} to {turns[-1]:g} turns every {MAP_TURNS[2]:g}; "
          f"{MAP_SHIFTS} shifts of the events for the global p.\n")
    print(f"  {'test':30s} {'depth':>5s} {'models':>6s} {'this model: ratio, rank, p':>28s}   "
          f"{'best model: anchor, turns, ratio':>40s} {'global p':>9s} {'Holm':>6s}")
    for r, p_adj in zip(rows, adjusted):
        best = (f"{date_text(r['best_anchor']):>16s}, {r['best_turns']:4.2f}, {r['best_ratio']:.2f}"
                if np.isfinite(r['best_anchor']) else '—')                       # the grid is in UT years
        print(f"  {r['test']:30s} {r['depth']:5d} {r['models']:6d}   {r['own_ratio']:5.2f}, "
              f"{100 * r['own_rank']:5.1f} %, {r['own_p']:.3f}   {best:>40s} {r['p_global']:9.3f} {p_adj:6.3f}")
    print("\nratio: mean distance of the boundaries to the nearest event over that of a random moment (below 1: "
          "closer). rank: share of the models that come as close or closer. global p: how often shifted events "
          "give a best model as close as the real best (the search over the models taken into account).")
    tests = list(MAP_TESTS)
    fig, axes = plt.subplots(len(MAP_DEPTHS), len(tests), figsize=(17, 3.6 * len(MAP_DEPTHS)), squeeze=False)
    fig.subplots_adjust(hspace=0.55, wspace=0.3, top=0.9)
    for r in rows:
        ax = axes[MAP_DEPTHS.index(r['depth']), tests.index(r['test'])]
        da, dt = MAP_ANCHORS[1] / 2, MAP_TURNS[2] / 2
        image = ax.imshow(r['scan']['ratio'].T, origin='lower', aspect='auto', cmap='RdBu_r', vmin=0.5, vmax=1.5,
                          extent=(anchors[0] - da, anchors[-1] + da, turns[0] - dt, turns[-1] + dt))
        ax.scatter([solution['anchor']], [solution['turns']], s=50, facecolors='white', edgecolors='black', zorder=3)
        if np.isfinite(r['best_anchor']):
            ax.scatter([r['best_anchor']], [r['best_turns']], marker='*', s=90, color='yellow', edgecolors='black',
                       zorder=3)
        ax.set_title(f"{r['test']}\ndepth {r['depth']}: global p = {r['p_global']:.3f}", fontsize=8)
        ax.tick_params(labelsize=6)
        if tests.index(r['test']) == 0:
            ax.set_ylabel('arc (turns)', fontsize=7)
        if r['depth'] == MAP_DEPTHS[-1]:
            ax.set_xlabel(f"start of {ctx.model.anchor_point} (year)", fontsize=7)
    fig.colorbar(image, ax=axes, shrink=0.6, label='mean distance to the events / that of a random moment')
    fig.suptitle('Every model of the cycle against the events (blue: closer than chance); circle: this model; '
                 'star: the closest', fontsize=10)
    finish(fig, opts, 'model_map.png')


def finish(fig, opts, name: str) -> None:
    if opts.save:
        save_figure(fig, BASE_DIR / name, dpi=150)
    if opts.show:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    run(setup)
