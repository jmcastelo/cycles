"""
Study of the yugas against the precession of the equinoxes, with the sky of
the N-body ephemeris at their boundaries.
"""

import cycles.functions.nbody_ephemeris as nbe
from cycles.functions.astro_dates import date_time_to_julian_day, julian_day_to_year
from cycles.plotting.equinoctial_precession import (
    plot_equinoctial_precession,
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


def setup():
    # Start of the Kali Yuga: 6:30 local solar time in Ujjain
    tk = julian_day_to_year(date_time_to_julian_day(-3103, 2, 7, 6, 30, utc_offset_hours=75.77 / 15))
    td = year_from_ayanamsa(-1 / 2, unit='turns', reference_year=tk)
    tt = year_from_ayanamsa(-3 / 4, unit='turns', reference_year=td)
    ts = year_from_ayanamsa(-1, unit='turns', reference_year=tt)
    tm = year_from_ayanamsa(1 / 4, unit='turns', reference_year=tk)
    dk = tm - tk
    return dict(
        starts={'Satya': ts, 'Treta': tt, 'Dvapara': td, 'Kali': tk, 'end': tm},
        # Kali Yuga divided like a whole cycle (0.4, 0.3, 0.2, 0.1)
        sub_kali=[tk, tk + dk * 0.4, tk + dk * 0.7, tk + dk * 0.9, tk + dk],
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


if __name__ == "__main__":
    run(setup)
