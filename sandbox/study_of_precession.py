"""
Study of the yugas against the precession of the equinoxes, with the sky of
the N-body ephemeris at their boundaries.
"""

import cycles.functions.nbody_ephemeris as nbe
from cycles.functions.astro_dates import date_time_to_julian_day, julian_day_to_year
from cycles.functions.timescale import addresses_with_prefix, address_label
from cycles.functions.cycle_analysis import fit_anchor, mismatch_by_depth
from cycles.functions.cycle_model import DEFAULT_PRESET, load_presets
from cycles.functions.astro_dates import year_to_date
from cycles.plotting.cycle_model import plot_fit_scan, plot_mismatch_by_depth, plot_precession_rate
from cycles.plotting.equinoctial_precession import (
    plot_equinoctial_precession,
    plot_zodiac_with_planets,
    plot_zodiac_planets_grid,
)
from common import PLOTS_DIR, DATA_DIR
from runner import study, run

BASE_DIR = PLOTS_DIR / "study_of_precession"
# Ephemeris tables (back, forward): standard (epsilon 1e-6) and precise (1e-9)
TABLES = {'': 'tabla70k70k', '_p': 'tabla70k70kp'}
EPOCH_DISPLAY = ("year", "date", "julian_day")

# Cycle model: a preset name (see cycles.functions.cycle_model; your own presets
# are in sandbox/cycle_presets.json, written by the GUI), unless a session gives one (--session)
PRESET = DEFAULT_PRESET

# Subcycles for subcycle_charts: those of depth DEPTH whose address starts with PREFIX
# (e.g. depth 2, prefix [3]: the four subdivisions of the Kali Yuga)
DEPTH = 3
PREFIX = [3]


def setup():
    import common
    model = common.MODEL or load_presets()[PRESET]          # a session's model (runner --session) comes first
    print(f"Cycle model: {model.name}")
    # Normalized time -> year with the model's division (by default precession
    # angle: the yugas are 1, 3/4, 1/2 and 1/4 turns, and so is every subdivision)
    time_map = model.time_map()
    ts, tt, td, tk, tm = model.boundaries()
    return dict(
        model=model,
        starts={'Satya': ts, 'Treta': tt, 'Dvapara': td, 'Kali': tk, 'end': tm},
        time_map=time_map,
        # Alternatives for comparison, same anchor and arc but dividing time instead of angle:
        # each yuga fitted to its boundaries, linear inside it
        fitted_map=model.replace(division='hybrid').time_map(),
        # time divided throughout (the yugas then are exactly 4:3:2:1 in years)
        linear_map=model.replace(division='time').time_map(),
        # Kali Yuga divided like a whole cycle (0.4, 0.3, 0.2, 0.1 of its arc), and its end
        sub_kali=[time_map.interval(lcoords)[0] for lcoords in addresses_with_prefix([3], 2)] + [tm],
        now=julian_day_to_year(date_time_to_julian_day(2026, 11, 3, 19, 49, 0)),
        eq=julian_day_to_year(date_time_to_julian_day(1979, 6, 6, 3, 0, 0, utc_offset_hours=2)),
        ephemerides={suffix: [nbe.load_ephemeris(DATA_DIR / name / 'back'),
                              nbe.load_ephemeris(DATA_DIR / name / 'forward')]
                     for suffix, name in TABLES.items()},
    )


def _save_path(opts, name: str):
    return BASE_DIR / name if opts.save else None


@study
def yuga_epochs(ctx, opts):
    """Print the yuga boundaries and the lengths of the yugas, absolute and relative."""
    names = list(ctx.starts)
    years = list(ctx.starts.values())
    total = years[-1] - years[0]
    for name, start, end in zip(names[:-1], years[:-1], years[1:]):
        print(f"{name:8s} from {start:10.1f} to {end:10.1f}: {end - start:8.1f} years ({(end - start) / total:.4f})")
    print(f"{'Total':8s} {total:.1f} years")


@study
def zodiac_now(ctx, opts):
    """Zodiac with the planets at the present date."""
    plot_zodiac_with_planets(ctx.eq, ctx.ephemerides[''], time_scale='UT', epoch_display=EPOCH_DISPLAY,
                             sign_labels='symbol', save_path=_save_path(opts, 'now.png'), show=opts.show)


@study(default=False)
def precession(ctx, opts):
    """Equinoctial and solstitial axes against the sidereal zodiac at the present date."""
    plot_equinoctial_precession(2026, dpi=600, save_path=_save_path(opts, 'precession_2026.png'), show=opts.show)


@study(default=False)
def satya(ctx, opts):
    """Zodiac with the planets at the start of the Satya Yuga, with both ephemeris tables."""
    for suffix, ephemeris in ctx.ephemerides.items():
        plot_zodiac_with_planets(ctx.starts['Satya'], ephemeris, time_scale='UT', epoch_display=EPOCH_DISPLAY,
                                 save_path=_save_path(opts, f'satya{suffix}.png'), show=opts.show)


@study(default=False)
def sub_kali(ctx, opts):
    """Zodiacs at the boundaries of the Kali Yuga subdivisions, with both ephemeris tables."""
    for suffix, ephemeris in ctx.ephemerides.items():
        plot_zodiac_planets_grid(ctx.sub_kali, ephemeris, time_scale='UT', epoch_display=EPOCH_DISPLAY,
                                 save_path=_save_path(opts, f'sub_kali{suffix}.png'), show=opts.show)


@study(default=False)
def subcycle_charts(ctx, opts):
    """Zodiacs at the starts of the subcycles of depth DEPTH beginning with PREFIX."""
    addresses = addresses_with_prefix(PREFIX, DEPTH)
    years = [ctx.time_map.interval(lcoords)[0] for lcoords in addresses]
    name = f"subcycles_depth_{DEPTH}_prefix_{''.join(map(str, PREFIX)) or 'none'}.png"
    plot_zodiac_planets_grid(years, ctx.ephemerides[''], labels=[address_label(a) for a in addresses],
                             columns=min(4, len(years)), time_scale='UT', epoch_display=EPOCH_DISPLAY,
                             save_path=_save_path(opts, name), show=opts.show)


@study(default=False)
def current_subcycle(ctx, opts):
    """Print the subcycle containing the present date at depths 1 to 5, with each time map."""
    maps = [('dividing precession angle', ctx.time_map),
            ('dividing time, fitted to the yugas', ctx.fitted_map),
            ('dividing time linearly', ctx.linear_map)]
    for label, time_map in maps:
        print(f"Time map {label}:")
        for depth in range(1, 7):
            lcoords = time_map.subcycle_at(ctx.eq, depth)
            start, end = time_map.interval(lcoords)
            print(f"  depth {depth}: {address_label(lcoords):45s} {start:10.1f} to {end:10.1f} ({end - start:.1f} years)")



@study(default=False)
def precession_rate(ctx, opts):
    """Precession rate across the cycle, with the mean rate of each yuga and the boundaries."""
    plot_precession_rate(ctx.model, depth=2, save_path=_save_path(opts, 'precession_rate.png'), show=opts.show)


@study(default=False)
def criteria_by_depth(ctx, opts):
    """How far the time shares are from 4:3:2:1 at each depth, dividing by angle."""
    for row in mismatch_by_depth(ctx.model, 5):
        print(f"  depth {row['depth']}: largest {row['max']:.5f}, RMS {row['rms']:.5f}")
    plot_mismatch_by_depth(ctx.model, 5, save_path=_save_path(opts, 'criteria_by_depth.png'), show=opts.show)


def _fit_text(result, model) -> str:
    y, m, d = year_to_date(result.anchor_year)
    date = f"{int(d)}/{m}/{1 - y} BC" if y <= 0 else f"{int(d)}/{m}/AD {y}"
    years = result.model.solve()['years']
    return (f"anchor {date} ({result.anchor_year:.1f}), {result.turns:.4f} turns ({years:,.0f} years): "
            f"largest deviation {result.mismatch:.5f} (the preset: {result.original_mismatch:.5f})")


@study(default=False)
def best_fit(ctx, opts):
    """Anchor (and arc) that best satisfy 4:3:2:1 in years and in angle at once, with the scans."""
    model = ctx.model
    searches = [
        ('Anchor anywhere in 100,000 BC to AD 100,000, same arc', {}),
        ('Anchor within 20,000 BC to AD 10,000, same arc', {'anchor_range': (-20000.0, 10000.0)}),
        ('Anchor anywhere, arc from 1 to 5 turns', {'turn_range': (1.0, 5.0)}),
        ('Same anchor, arc from 1 to 5 turns',
         {'anchor_range': (model.anchor_year(), model.anchor_year()), 'turn_range': (1.0, 5.0)}),
    ]
    results = []
    for label, options in searches:
        result = fit_anchor(model, **options)
        results.append(result)
        print(f"{label}:\n  {_fit_text(result, model)}")
    plot_fit_scan(results[0], model, save_path=_save_path(opts, 'best_fit_anchor.png'), show=opts.show)
    plot_fit_scan(results[2], model, save_path=_save_path(opts, 'best_fit_anchor_arc.png'), show=opts.show)


if __name__ == "__main__":
    run(setup)
