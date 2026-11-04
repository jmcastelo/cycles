from pathlib import Path
import matplotlib.pyplot as plt

import cycles.functions.nbody_ephemeris as nbe
from cycles.functions.astro_dates import (
    date_time_to_julian_day,
    julian_day_to_year
)
from cycles.plotting.equinoctial_precession import (
    plot_equinoctial_precession,
    year_from_ayanamsa,
    plot_zodiac_with_planets,
    plot_zodiac_planets_grid,

)

SANDBOX_DIR = Path(__file__).resolve().parent
PLOTS_DIR = SANDBOX_DIR / "plots"
DATA_DIR = SANDBOX_DIR / "data"


if __name__ == "__main__":
    # tk = -3101
    tk_jd = date_time_to_julian_day(
        -3103,
        2,
        7,
        6,
        30,
        utc_offset_hours=75.77 / 15
    )  # 6:30 solar local en Ujjain

    tk = julian_day_to_year(tk_jd)
    td = year_from_ayanamsa(-1 / 2, unit='turns', reference_year=tk)
    tt = year_from_ayanamsa(-3 / 4, unit='turns', reference_year=td)
    ts = year_from_ayanamsa(-1, unit='turns', reference_year=tt)
    tm = year_from_ayanamsa(1 / 4, unit='turns', reference_year=tk)

    print(ts, tt, td, tk, tm)

    dm = tm - ts
    ds = tt - ts
    dt = td - tt
    dd = tk - td
    dk = tm - tk

    print(dm, ds, dt, dd, dk)
    print(dm / dm, ds / dm, dt / dm, dd / dm, dk / dm)

    sub_kali = [tk, tk + dk * 0.4, tk + dk * 0.7, tk + dk * 0.9, tk + dk]

    # fig, ax, ayanamsa = plot_equinoctial_precession(2026, dpi=600)

    eph_f = nbe.load_ephemeris(DATA_DIR / 'tabla70k70k' / 'forward')
    eph_b = nbe.load_ephemeris(DATA_DIR / 'tabla70k70k' / 'back')

    eph_fp = nbe.load_ephemeris(DATA_DIR / 'tabla70k70kp' / 'forward')
    eph_bp = nbe.load_ephemeris(DATA_DIR / 'tabla70k70kp' / 'back')

    now_jd = date_time_to_julian_day(2026, 11, 3, 19, 49, 0)
    now = julian_day_to_year(now_jd)

    eq_jd = date_time_to_julian_day(1979, 6, 6, 3, 0 ,0, utc_offset_hours=2)
    eq = julian_day_to_year(eq_jd)

    plot_zodiac_with_planets(
        now,
        [eph_b, eph_f],
        time_scale='UT',
        epoch_display=("year", "date", "julian_day"),
        sign_labels='symbol'
    )

    """
    plot_zodiac_with_planets(
        ts,
        [eph_b, eph_f],
        time_scale='UT',
        epoch_display=("year", "date", "julian_day"),
        save_path=PLOTS_DIR / 'study_of_precession' / 'satya.png'
    )

    plot_zodiac_with_planets(
        ts,
        [eph_bp, eph_fp],
        time_scale='UT',
        epoch_display=("year", "date", "julian_day"),
        save_path=PLOTS_DIR / 'study_of_precession' / 'satya_p.png'
    )
    """
    """
    plot_zodiac_planets_grid(
        sub_kali,
        [eph_b, eph_f],
        time_scale='UT',
        epoch_display=("year", "date", "julian_day"),
        save_path=PLOTS_DIR / 'study_of_precession' / 'sub_kali.png'
    )

    plot_zodiac_planets_grid(
        sub_kali,
        [eph_bp, eph_fp],
        time_scale='UT',
        epoch_display=("year", "date", "julian_day"),
        save_path=PLOTS_DIR / 'study_of_precession' / 'sub_kali_p.png'
    )
    """