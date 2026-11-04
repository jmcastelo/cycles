"""
Study of the yugas against the precession of the equinoxes, with the sky of
the N-body ephemeris at their boundaries.
"""

import cycles.functions.nbody_ephemeris as nbe
from cycles.functions.astro_dates import date_time_to_julian_day, julian_day_to_year
from cycles.functions.timescale import TimeMap, addresses_with_prefix, address_label
from cycles.plotting.equinoctial_precession import (
    plot_equinoctial_precession,
    precession_time_map,
    year_from_ayanamsa,
    plot_zodiac_with_planets,
    plot_zodiac_planets_grid,
)
from common import PLOTS_DIR, DATA_DIR
from runner import study, run

BASE_DIR = PLOTS_DIR / "study_of_precession"
# Ephemeris tables (back, forward): standard (epsilon 1e-6) and precise (1e-9)
TABLES = {'': 'tabla70k70k', '_p': 'tabla70k70kp'}
EPOCH_DISPLAY = ("year", "date", "julian_day")

# Subcycles for subcycle_charts: those of depth DEPTH whose address starts with PREFIX
# (e.g. depth 2, prefix [3]: the four subdivisions of the Kali Yuga)
DEPTH = 2
PREFIX = [3]


def setup():
    # Start of the Kali Yuga: 6:30 local solar time in Ujjain
    tk = julian_day_to_year(date_time_to_julian_day(-3103, 2, 7, 6, 30, utc_offset_hours=75.77 / 15))
    td = year_from_ayanamsa(-1 / 2, unit='turns', reference_year=tk)
    tt = year_from_ayanamsa(-3 / 4, unit='turns', reference_year=td)
    ts = year_from_ayanamsa(-1, unit='turns', reference_year=tt)
    tm = year_from_ayanamsa(1 / 4, unit='turns', reference_year=tk)
    # Normalized time -> year, dividing precession angle: the yugas are 1, 3/4, 1/2
    # and 1/4 turns (4:3:2:1 in angle), and so is every subdivision
    time_map = precession_time_map(ts, 1 + 3 / 4 + 1 / 2 + 1 / 4)
    return dict(
        starts={'Satya': ts, 'Treta': tt, 'Dvapara': td, 'Kali': tk, 'end': tm},
        time_map=time_map,
        # Alternatives for comparison, dividing time instead of angle:
        # each yuga fitted to its boundaries, linear inside it
        fitted_map=TimeMap.from_age_boundaries([ts, tt, td, tk, tm]),
        # one linear map over the whole span (the yugas then are exactly 4:3:2:1 in years)
        linear_map=TimeMap.linear(ts, tm),
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
    plot_zodiac_with_planets(ctx.now, ctx.ephemerides[''], time_scale='UT', epoch_display=EPOCH_DISPLAY,
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
        for depth in range(1, 6):
            lcoords = time_map.subcycle_at(ctx.now, depth)
            start, end = time_map.interval(lcoords)
            print(f"  depth {depth}: {address_label(lcoords):45s} {start:10.1f} to {end:10.1f} ({end - start:.1f} years)")


if __name__ == "__main__":
    run(setup)
