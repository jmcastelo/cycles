from cycles.plotting.equinoctial_precession import (
    plot_equinoctial_precession,
    plot_ayanamsa_comparison,
    year_from_ayanamsa
)

if __name__ == "__main__":
    tk = -3101
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

    fig, ax, ayanamsa = plot_equinoctial_precession(2026)