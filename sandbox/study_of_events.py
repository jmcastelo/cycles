"""Study of planetary events against the boundaries of the subcycles, with significance tests.

Three hypotheses, tested in the sidereal (Lahiri, Jyotiṣa) and the tropical (Western) zodiac where it matters:

* H1, Sūrya Siddhānta: at the boundaries of the yugas the planets stand together at the start of Aries
  (measured on the true planets Sun to Saturn, the Moon left out: their mean angle from 0° Aries); tested on the
  five boundaries and on the four that are not the model's anchor, since the traditional epoch may have been
  chosen for its gathering of planets;
* H2, great conjunctions: the boundaries of depths 1 to 5 fall near the Jupiter–Saturn conjunctions, or near
  the changes of their trigon (element), as in the Persian doctrine of world ages;
* H3, outer conjunctions: the boundaries fall near the Uranus–Neptune or Neptune–Pluto conjunctions.

Each test compares the boundaries with rigid rotations of them (the same spacing, placed anywhere in the cycle);
``summary`` corrects the whole family with Holm's method. The event catalogues are computed once and kept in
``sandbox/data/events/``.
"""

import hashlib
import warnings

import numpy as np
import matplotlib.pyplot as plt

from runner import study, run
from common import DATA_DIR, PLOTS_DIR, save_figure

from cycles.functions.cycle_analysis import boundary_fractions
from cycles.functions.cycle_model import DEFAULT_PRESET, load_presets
from cycles.functions.events import CLASSICAL, ZODIACS, around_point, conjunctions, first_of_series, trigon_changes
from cycles.functions.significance import holm, proximity_test, rotations, value_test

BASE_DIR = PLOTS_DIR / "study_of_events"
CACHE_DIR = DATA_DIR / "events"
TABLE = DATA_DIR / "tabla70k70k"
PRESET = DEFAULT_PRESET           # the cycle model, unless a session gives one (--session)
DEPTHS = (1, 2, 3, 4, 5)
ROTATIONS = 5000                  # rigid rotations of the boundaries in each test
PAIRS = {'great': ('jupiter', 'saturn'), 'uranus_neptune': ('uranus', 'neptune'),
         'neptune_pluto': ('neptune', 'pluto')}
MARGIN = 200.0                    # years of events beyond the cycle, so that the nearest one exists at the ends
YUGA_LABELS = ('start of Satya', 'start of Treta', 'start of Dvapara', 'start of Kali', 'end')


def setup():
    import common
    import cycles.functions.nbody_ephemeris as nbe
    from cycles.gui.sky import ephemeris_parts
    from cycles.plotting.equinoctial_precession import _tdb_year
    model = common.MODEL or load_presets()[PRESET]
    print(f"Cycle model: {model.name}")
    tables = [nbe.load_ephemeris(part) for part in ephemeris_parts(TABLE)]
    time_map = model.time_map()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')          # DeltaT extrapolation far from the present
        boundaries = {d: np.array([_tdb_year(float(y), 'UT')
                                   for y in time_map.to_physical(boundary_fractions(d))]) for d in DEPTHS}
    start, end = boundaries[1][0], boundaries[1][-1]
    print(f"Boundaries in TDB years, from {start:.1f} to {end:.1f}; depths {DEPTHS[0]} to {DEPTHS[-1]}")
    return dict(model=model, tables=tables, boundaries=boundaries, start=start, end=end, catalogs={}, results={})


# -- the event catalogues

def catalog(ctx, name: str) -> dict:
    """The conjunctions of a pair over the cycle, from the cache or computed (and cached)."""
    if name in ctx.catalogs:
        return ctx.catalogs[name]
    a, b = PAIRS[name]
    start, end = ctx.start - MARGIN, ctx.end + MARGIN
    key = hashlib.sha1(f"{TABLE.resolve()}|{a}|{b}|{start:.3f}|{end:.3f}|v1".encode()).hexdigest()[:16]
    path = CACHE_DIR / f"{name}_{key}.npz"
    if path.exists():
        data = dict(np.load(path))
    else:
        print(f"Computing the {a}–{b} conjunctions from {start:.0f} to {end:.0f}…", flush=True)
        data = conjunctions(ctx.tables, a, b, start, end)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.savez(path, **data)
    ctx.catalogs[name] = data
    return data


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
    """All the tests of H1, H2 and H3, with p-values corrected for the whole family (Holm)."""
    rows = h1_tests(ctx) + h2_tests(ctx) + h3_tests(ctx)
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


def finish(fig, opts, name: str) -> None:
    if opts.save:
        save_figure(fig, BASE_DIR / name, dpi=150)
    if opts.show:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    run(setup)
