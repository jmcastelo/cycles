"""
nbody_ephemeris.py

Self-made planetary ephemeris for very long time spans, by direct N-body
integration of the solar system, stored once and queried afterwards.

Model
-----
* Bodies: Sun, Mercury, Venus, Earth, Moon, Mars, Jupiter, Saturn, Uranus,
  Neptune and Pluto (the Earth and the Moon are integrated separately: treating
  the Earth-Moon barycentre as one point mass makes it drift by ~117 km/year).
* Initial conditions at J2000.0 (JD 2451545.0 TDB), barycentric ICRF, and the
  masses (GM): JPL DE421 (Folkner, Williams & Boggs 2009, IPN PR 42-178). They
  are embedded below, so only REBOUND, REBOUNDx and NumPy are needed.
* Forces: Newtonian N-body gravity + full first post-Newtonian relativity
  (REBOUNDx ``gr_full``). Integrator: IAS15 (adaptive, 15th order).
* Not modelled: asteroids, the Sun's oblateness and mass loss, Earth's
  oblateness and tides. Mass loss of the Sun alone (~1e-13 per year) would
  shift the Earth's mean longitude by roughly 0.2 degrees after 61000 years
  (order-of-magnitude estimate).

Accuracy
--------
Against DE421 itself over -100 / +50 years the integration agrees to a few km
(Earth-Moon barycentre: 8 km at -100 years; Jupiter: 28 km; Mercury: 10 km).
Relaxing the IAS15 tolerance from 1e-9 to the default 1e-6 changes the result
by less than 0.001 km per century (speed-up 1.65x). Far beyond the range of
any reference ephemeris no independent check was available when this script
was written: treat results as a model prediction.
The Moon's own trajectory is NOT reliable beyond a few decades (tidal
acceleration is not modelled); only the Earth-Moon barycentre is stored, which
differs from the Earth by at most ~4700 km.

Storage
-------
The integrator takes its own adaptive steps (about 3.4 days with the default
``epsilon``). Every step is counted and each stored body is sampled once every
``stride`` steps (Mercury every step, Venus every 2, the Earth-Moon barycentre
every 3, Mars every 5, Jupiter every 24, ...), giving each body
roughly 25-65 samples per orbit with no extra cost for forcing output times.
For each stored body two raw binary files are written: ``<body>.t.f64`` (time,
in days along the integration direction, increasing) and ``<body>.f64`` (rows
of 9 doubles: x, y, z in AU; vx, vy, vz in AU/day; ax, ay, az in AU/day^2,
barycentric ICRF). The Sun is not stored: it is recovered exactly from the
other bodies (the barycentre of the system is at the origin). The
accelerations are Newtonian, computed from the
positions (the missing relativistic part, ~1e-7 relative, is irrelevant for
interpolation). Queries use quintic Hermite interpolation (position, velocity
and acceleration at both ends).

Measured against DE421 over +/-30 years (model, storage and interpolation
together; worst of 300 random-time queries per direction): Mercury 37 km
(0.16 arcsec as seen from the Sun), Venus 1 km (0.002"), Earth-Moon barycentre
3 km (0.004"), Mars 20 km (0.02"), Jupiter 9 km (0.002"), Saturn 6 km (0.001").
The run takes about 0.10 s per simulated year on one core (about 100 minutes
for 61200 years) and about 1.1 GB of disk. It can be interrupted, resumed or
extended; a resumed run is bit-identical to an uninterrupted one (the
integrator state is checkpointed in ``state.bin``).

Parallelism
-----------
A single N-body integration cannot be split across cores: every time step
needs the result of the previous one. Parallel-in-time schemes (parareal) were
tested on this problem and do not converge faster than the serial run
(Mercury makes about 415 orbits per century, and the correction amplifies
phase errors; with N segments the boundaries became exact only at iteration N,
and the intermediate iterations were worse than the coarse start).
What does run in parallel, and what ``build_many`` and the ``--workers``
option do, is several independent integrations at once: both time directions,
or several variants (for example different tolerances or perturbed initial
conditions to estimate the numerical uncertainty).

Usage
-----
    # NOTE: the span counts years from J2000.0: 63300 years back reach the year -61300
    # (to cover the start of the Satya Yuga at about -61138 you need at least 63138).
    python -m cycles.functions.nbody_ephemeris build back_63k 63300 --direction back      # ~2 h, ~1.2 GB
    python -m cycles.functions.nbody_ephemeris build forward_4k 4000 --direction forward  # ~6 min

    python -m cycles.functions.nbody_ephemeris build all_dirs 63300 --direction both --forward-years 4000 --workers 2

    >>> import cycles.functions.nbody_ephemeris as ne
    >>> eph = ne.load_ephemeris("back_63k")
    >>> ne.body_state(eph, "jupiter", jd_tdb)            # (position AU, velocity AU/day)
    >>> ne.geocentric_direction(eph, "jupiter", jd_tdb)  # unit vector, ICRF, from the EMB

Time scale: TDB (the integration variable). Year <-> JD: JD = 2451545.0 + (year - 2000) * 365.25
(see astro_dates.year_to_julian_day).
"""

from __future__ import annotations

import argparse
import json
import math
import os
from typing import Dict, Iterable, Optional, Tuple

import numpy as np

__all__ = ["build_ephemeris", "build_many", "load_ephemeris", "body_state",
           "body_states", "body_position", "geocentric_direction", "geocentric_directions", "year_to_jd", "BODIES"]

JD_J2000 = 2451545.0

_AU_KM = 149597870.6996262
_EMRAT = 81.3005690699153
_C_KM_S = 299792.458
_GM = {  # AU^3/day^2 (DE421)
    'sun': 0.0002959122082855911,
    'mercury': 4.91254957186794e-11,
    'venus': 7.243452332698441e-10,
    'earthmoon': 8.997011408268049e-10,
    'mars': 9.54954869562239e-11,
    'jupiter': 2.82534584085505e-07,
    'saturn': 8.459706073308477e-08,
    'uranus': 1.29202482579265e-08,
    'neptune': 1.52435910924974e-08,
    'pluto': 2.17844105199052e-12,
}

# Barycentric ICRF (equatorial J2000) state at JD 2451545.0 TDB, from JPL DE421: position (km), velocity (km/day)
_STATE_J2000 = {
    'sun': ([-1067598.6810692835, -395988.8328895459, -138071.03627114184],
        [804.6059865894003, -1011.0102609264592, -453.7077987317826]),
    'mercury': ([-20529325.13779666, -60323955.47999059, -30130845.755306263],
        [3197171.899107159, -737974.9064424891, -725619.4560076986]),
    'venus': ([-108524092.74345127, -7318517.511718462, 3548115.874377055],
        [120201.28600173171, -2767350.5230370136, -1252548.292218931]),
    'earthmoon': ([-27570175.523305077, 132358187.77292642, 57417722.69397782],
        [-2572743.8782232874, -435269.9934809916, -188724.0700127081]),
    'mars': ([206980541.97099587, -186369.83560887945, -5667233.104433829],
        [101259.50513634938, 2065539.5878701336, 944690.7441880401]),
    'jupiter': ([597499986.022755, 408990381.9073647, 160756218.96564138],
        [-682605.3653812814, 878843.2219042062, 393333.1805513901]),
    'saturn': ([957317526.140572, 923319670.9530276, 340162788.99582416],
        [-641322.0944087183, 526821.8248405388, 245175.7501100833]),
    'uranus': ([2157907516.5187907, -1871306812.9278584, -850106410.6385199],
        [401443.4202387816, 367299.6621879186, 155189.23889468334]),
    'neptune': ([2513979090.5353255, -3438170415.3282285, -1469851221.0963404],
        [386658.6135116859, 248581.799856577, 92119.73367780648]),
    'pluto': ([-1478399422.3240037, -4185975816.4338465, -860878354.068843],
        [453899.24246590276, -169696.52033813033, -189714.59830479333]),
    # Moon relative to the Earth
    'moon_geocentric': ([-291608.3853096409, -266716.83294678753, -76102.48714678355],
        [55601.11182206067, -57549.97608398343, -26034.54084846684]),
}

BODIES = ("sun", "mercury", "venus", "earthmoon", "mars", "jupiter", "saturn",
          "uranus", "neptune", "pluto")
# Integrated bodies, in the order they are added to the simulation.
_SIM_BODIES = ("sun", "mercury", "venus", "earth", "moon", "mars", "jupiter",
               "saturn", "uranus", "neptune", "pluto")
# Stored bodies and the stride (in integrator steps) at which each is sampled
# (tuned for the default epsilon, ~3.4 day steps). The Sun is not stored: with
# the barycentre at the origin, Sun = -sum(GM_i r_i) / GM_sun.
_STORED = {"mercury": 1, "venus": 2, "earthmoon": 3, "mars": 5,
           "jupiter": 24, "saturn": 48, "uranus": 120, "neptune": 240,
           "pluto": 240}
_ROW = 9                      # doubles per stored row
_ROW_BYTES = 8 * _ROW


def year_to_jd(year: float) -> float:
    """Julian Day of a decimal year (Julian years from J2000.0)."""
    return JD_J2000 + (year - 2000.0) * 365.25


# ----------------------------------------------------------------------------
# Initial conditions
# ----------------------------------------------------------------------------

def _initial_conditions():
    """Return (masses, positions AU, velocities AU/day) for the 11 integrated bodies."""
    em = _EMRAT
    gm_b = _GM["earthmoon"]
    gm = dict(_GM)
    gm["earth"] = gm_b * em / (1.0 + em)
    gm["moon"] = gm_b / (1.0 + em)
    pos, vel = {}, {}
    for name in ("sun", "mercury", "venus", "mars", "jupiter", "saturn",
                 "uranus", "neptune", "pluto"):
        p, v = _STATE_J2000[name]
        pos[name], vel[name] = np.array(p) / _AU_KM, np.array(v) / _AU_KM
    p_emb, v_emb = (np.array(x) for x in _STATE_J2000["earthmoon"])
    p_moon, v_moon = (np.array(x) for x in _STATE_J2000["moon_geocentric"])
    p_earth, v_earth = p_emb - p_moon / (1.0 + em), v_emb - v_moon / (1.0 + em)
    pos["earth"], vel["earth"] = p_earth / _AU_KM, v_earth / _AU_KM
    pos["moon"], vel["moon"] = (p_earth + p_moon) / _AU_KM, (v_earth + v_moon) / _AU_KM
    masses = np.array([gm[n] for n in _SIM_BODIES])
    return (masses, np.array([pos[n] for n in _SIM_BODIES]),
            np.array([vel[n] for n in _SIM_BODIES]))


def _add_relativity(sim):
    import reboundx
    extras = reboundx.Extras(sim)
    force = extras.load_force("gr_full")
    extras.add_force(force)
    force.params["c"] = _C_KM_S * 86400.0 / _AU_KM
    return extras


def _new_simulation(epsilon: float):
    import rebound
    masses, pos, vel = _initial_conditions()
    sim = rebound.Simulation()
    sim.G = 1.0                      # units: AU, day, GM in AU^3/day^2
    sim.integrator = "ias15"
    sim.integrator.epsilon = epsilon
    for m, p, v in zip(masses, pos, vel):
        sim.add(m=m, x=p[0], y=p[1], z=p[2], vx=v[0], vy=v[1], vz=v[2])
    sim.move_to_com()
    sim.t = 0.0
    return sim, _add_relativity(sim)


def _acceleration_of(i, xyz, masses):
    """Newtonian acceleration (AU/day^2, G = 1) of body ``i`` from the positions."""
    d = xyz - xyz[i]
    r2 = np.einsum("ij,ij->i", d, d)
    r2[i] = 1.0
    w = masses * r2 ** -1.5
    w[i] = 0.0
    return w @ d


def _snapshot(sim, masses, wanted=None):
    """
    Rows (position, velocity, acceleration) of the ``wanted`` stored bodies
    (all of them by default), the Earth-Moon barycentre included.
    """
    wanted = tuple(_STORED) if wanted is None else wanted
    n = len(_SIM_BODIES)
    xyz = np.zeros((n, 3))
    vxyz = np.zeros((n, 3))
    sim.serialize_particle_data(xyz=xyz)
    sim.serialize_particle_data(vxvyvz=vxyz)
    ie, im = _SIM_BODIES.index("earth"), _SIM_BODIES.index("moon")
    out = {}
    for name in wanted:
        if name == "earthmoon":
            w = masses[ie] + masses[im]
            acc = (masses[ie] * _acceleration_of(ie, xyz, masses)
                   + masses[im] * _acceleration_of(im, xyz, masses)) / w
            out[name] = np.concatenate([
                (masses[ie] * xyz[ie] + masses[im] * xyz[im]) / w,
                (masses[ie] * vxyz[ie] + masses[im] * vxyz[im]) / w, acc])
        else:
            i = _SIM_BODIES.index(name)
            out[name] = np.concatenate([xyz[i], vxyz[i],
                                        _acceleration_of(i, xyz, masses)])
    return out


# ----------------------------------------------------------------------------
# Build (long run, resumable)
# ----------------------------------------------------------------------------

def build_ephemeris(
    out_dir: str,
    years: float,
    direction: str = "back",
    epsilon: float = 1e-6,
    chunk_steps: int = 20000,
    stored: Optional[Iterable[str]] = None,
    verbose: bool = True,
) -> Dict:
    """
    Integrate from J2000.0 for at least ``years`` years in ``direction`` ("back"
    or "forward") and write the table to ``out_dir``. The run stops at the first
    step beyond the requested span that is a multiple of the least common
    multiple of the strides, so every stored body covers the whole span (the
    overshoot is under ~1.5 years). If ``out_dir`` already holds a run with the
    same settings, it is resumed or extended from its checkpoint.
    """
    import rebound
    if direction not in ("back", "forward"):
        raise ValueError("direction must be 'back' or 'forward'")
    if years <= 0:
        raise ValueError("years must be positive")
    sign = -1.0 if direction == "back" else 1.0
    stored = tuple(stored) if stored is not None else tuple(_STORED)
    unknown = [b for b in stored if b not in _STORED]
    if unknown:
        raise ValueError(f"unknown bodies: {unknown}")
    strides = {b: _STORED[b] for b in stored}
    block = math.lcm(*strides.values())
    target_days = years * 365.25
    os.makedirs(out_dir, exist_ok=True)
    meta_path = os.path.join(out_dir, "meta.json")
    state_path = os.path.join(out_dir, "state.bin")
    masses = _initial_conditions()[0]

    if os.path.exists(meta_path) and os.path.exists(state_path):
        meta = json.load(open(meta_path))
        for key, value in (("direction", direction), ("epsilon", epsilon),
                           ("strides", strides)):
            if meta[key] != value:
                raise ValueError(f"existing run in {out_dir} has {key}={meta[key]!r}")
        sim = rebound.Simulation(state_path)
        _add_relativity(sim)
        steps = meta["steps_done"]
        for name in stored:                       # drop anything written after the checkpoint
            rows = steps // strides[name] + 1
            for suffix, width in ((".f64", _ROW_BYTES), (".t.f64", 8)):
                with open(os.path.join(out_dir, name + suffix), "r+b") as f:
                    f.truncate(rows * width)
        if verbose:
            print(f"[{out_dir}] Reanudando en el paso {steps} (año {2000 + sim.t / 365.25:.1f}).")
    else:
        sim, _ = _new_simulation(epsilon)
        sim.dt = sign * 0.5
        steps = 0
        meta = {"direction": direction, "epsilon": epsilon, "strides": strides,
                "steps_done": 0, "jd0": JD_J2000, "block_steps": block,
                "rebound_version": rebound.__version__,
                "model": "DE421 initial conditions, 11 bodies, IAS15, gr_full"}
        first = _snapshot(sim, masses, stored)
        for name in stored:
            with open(os.path.join(out_dir, name + ".f64"), "wb") as f:
                f.write(first[name].astype("<f8").tobytes())
            with open(os.path.join(out_dir, name + ".t.f64"), "wb") as f:
                f.write(np.zeros(1, dtype="<f8").tobytes())
        json.dump(meta, open(meta_path, "w"))
    handles = {b: (open(os.path.join(out_dir, b + ".f64"), "ab"),
                   open(os.path.join(out_dir, b + ".t.f64"), "ab")) for b in stored}
    try:
        finished = abs(sim.t) >= target_days and steps % block == 0
        while not finished:
            rows = {b: [] for b in stored}
            times = {b: [] for b in stored}
            for _ in range(chunk_steps):
                sim.steps(1)
                steps += 1
                due = [b for b in stored if steps % strides[b] == 0]
                if due:
                    snap = _snapshot(sim, masses, due)
                    for b in due:
                        rows[b].append(snap[b])
                        times[b].append(abs(sim.t))
                if abs(sim.t) >= target_days and steps % block == 0:
                    finished = True
                    break
            for b in stored:
                if rows[b]:
                    handles[b][0].write(np.array(rows[b], dtype="<f8").tobytes())
                    handles[b][1].write(np.array(times[b], dtype="<f8").tobytes())
                handles[b][0].flush()
                handles[b][1].flush()
            sim.save_to_file(state_path)
            meta["steps_done"] = steps
            json.dump(meta, open(meta_path, "w"))
            if verbose:
                print(f"[{out_dir}] {steps} pasos, año {2000 + sim.t / 365.25:.1f} "
                      f"({100 * min(1.0, abs(sim.t) / target_days):.1f} %)", flush=True)
    finally:
        for f_rows, f_times in handles.values():
            f_rows.close()
            f_times.close()
    return meta


def _run_job(kwargs: Dict) -> Dict:
    return build_ephemeris(**kwargs)


def build_many(jobs: Iterable[Dict], workers: Optional[int] = None) -> list:
    """
    Run several independent integrations, in parallel when ``workers`` > 1.

    ``jobs`` is a list of dictionaries of keyword arguments for
    ``build_ephemeris`` (at least ``out_dir`` and ``years``). Each integration
    still runs on a single core (one integration cannot be split across
    cores); the speed-up is in doing several at once, for example both time
    directions, or variants with different ``epsilon``. ``workers`` defaults to
    the number of jobs, limited by the number of CPU cores. Returns the list of
    metadata dictionaries, in the order of ``jobs``.
    """
    from concurrent.futures import ProcessPoolExecutor
    jobs = [dict(job) for job in jobs]
    if not jobs:
        return []
    if workers is None:
        workers = min(len(jobs), os.cpu_count() or 1)
    if workers < 1:
        raise ValueError("workers must be >= 1")
    if workers == 1 or len(jobs) == 1:
        return [_run_job(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=min(workers, len(jobs))) as pool:
        return list(pool.map(_run_job, jobs))


# ----------------------------------------------------------------------------
# Query
# ----------------------------------------------------------------------------

def load_ephemeris(directory: str) -> Dict:
    """Open a table written by ``build_ephemeris`` (memory-mapped, read-only)."""
    meta = json.load(open(os.path.join(directory, "meta.json")))
    tables, times = {}, {}
    for name in meta["strides"]:
        path = os.path.join(directory, name + ".f64")
        n_rows = os.path.getsize(path) // _ROW_BYTES
        tables[name] = np.memmap(path, dtype="<f8", mode="r", shape=(n_rows, _ROW))
        times[name] = np.memmap(os.path.join(directory, name + ".t.f64"),
                                dtype="<f8", mode="r", shape=(n_rows,))
    meta["tables"], meta["times"] = tables, times
    meta["sign"] = -1.0 if meta["direction"] == "back" else 1.0
    return meta


def body_state(eph: Dict, body: str, jd_tdb: float) -> Tuple[np.ndarray, np.ndarray]:
    """Barycentric ICRF position (AU) and velocity (AU/day) by quintic Hermite interpolation."""
    pos, vel = body_states(eph, body, np.array([float(jd_tdb)]))
    return pos[0], vel[0]


def body_states(eph: Dict, body: str, jd_tdb) -> Tuple[np.ndarray, np.ndarray]:
    """
    ``body_state`` at many moments at once: ``jd_tdb`` of shape (N,) gives
    positions and velocities of shape (N, 3). Raises ValueError if any moment
    is outside the stored span.
    """
    jd_tdb = np.atleast_1d(np.asarray(jd_tdb, dtype=float))
    if body == "sun" and "sun" not in eph["tables"]:
        missing = [b for b in _STORED if b not in eph["tables"]]
        if missing:
            raise ValueError(f"the Sun needs all planets stored; missing: {missing}")
        total_p, total_v = np.zeros((len(jd_tdb), 3)), np.zeros((len(jd_tdb), 3))
        for name in _STORED:
            p, v = body_states(eph, name, jd_tdb)
            total_p += _GM[name] * p
            total_v += _GM[name] * v
        return -total_p / _GM["sun"], -total_v / _GM["sun"]
    if body not in eph["tables"]:
        raise ValueError(f"{body!r} is not in this ephemeris: {list(eph['tables'])}")
    table, tau_all = eph["tables"][body], eph["times"][body]
    sign = eph["sign"]
    tau = sign * (jd_tdb - eph["jd0"])             # days along the integration direction
    outside = (tau < 0) | (tau > tau_all[-1]) | ~np.isfinite(tau)
    if outside.any():
        jd = jd_tdb[np.argmax(outside)]
        raise ValueError(f"JD {jd} is outside the stored span "
                         f"({eph['jd0']} to {eph['jd0'] + sign * tau_all[-1]:.1f})")
    k = np.minimum(np.searchsorted(tau_all, tau, side="right") - 1, len(table) - 2)
    t0, t1 = np.asarray(tau_all[k]), np.asarray(tau_all[k + 1])
    h = (t1 - t0)[:, None]
    s = ((tau - t0) / (t1 - t0))[:, None]
    r0, r1 = np.asarray(table[k]), np.asarray(table[k + 1])
    p0, p1 = r0[:, :3], r1[:, :3]
    m0, m1 = sign * r0[:, 3:6] * h, sign * r1[:, 3:6] * h    # dr/ds
    c0, c1 = r0[:, 6:9] * h * h, r1[:, 6:9] * h * h          # d2r/ds2
    s2, s3, s4, s5 = s * s, s**3, s**4, s**5
    pos = ((1 - 10 * s3 + 15 * s4 - 6 * s5) * p0 + (s - 6 * s3 + 8 * s4 - 3 * s5) * m0
           + (0.5 * s2 - 1.5 * s3 + 1.5 * s4 - 0.5 * s5) * c0
           + (0.5 * s3 - s4 + 0.5 * s5) * c1 + (-4 * s3 + 7 * s4 - 3 * s5) * m1
           + (10 * s3 - 15 * s4 + 6 * s5) * p1)
    vel = sign * ((-30 * s2 + 60 * s3 - 30 * s4) * p0 + (1 - 18 * s2 + 32 * s3 - 15 * s4) * m0
                  + (s - 4.5 * s2 + 6 * s3 - 2.5 * s4) * c0
                  + (1.5 * s2 - 4 * s3 + 2.5 * s4) * c1 + (-12 * s2 + 28 * s3 - 15 * s4) * m1
                  + (30 * s2 - 60 * s3 + 30 * s4) * p1) / h
    return pos, vel


def body_position(eph: Dict, body: str, jd_tdb: float) -> np.ndarray:
    """Barycentric ICRF position (AU)."""
    return body_state(eph, body, jd_tdb)[0]


def geocentric_direction(eph: Dict, body: str, jd_tdb: float,
                         origin: str = "earthmoon") -> np.ndarray:
    """
    Unit vector (ICRF, geometric, no light time) from ``origin`` (the Earth-Moon
    barycentre by default) to ``body``.
    """
    d = body_position(eph, body, jd_tdb) - body_position(eph, origin, jd_tdb)
    return d / np.linalg.norm(d)


def geocentric_directions(eph: Dict, bodies, jd_tdb, origin: str = "earthmoon") -> Dict[str, np.ndarray]:
    """
    ``geocentric_direction`` of several bodies at many moments: maps each body
    to unit vectors of shape (N, 3). The origin is interpolated once.
    """
    here = body_states(eph, origin, jd_tdb)[0]
    directions = {}
    for body in bodies:
        d = body_states(eph, body, jd_tdb)[0] - here
        directions[body] = d / np.linalg.norm(d, axis=1, keepdims=True)
    return directions


# ----------------------------------------------------------------------------
# Command line
# ----------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(description="Efeméride propia por integración N-cuerpos")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="integrar y guardar (reanudable)")
    b.add_argument("out_dir")
    b.add_argument("years", type=float, help="años hacia el pasado o hacia el futuro")
    b.add_argument("--direction", choices=("back", "forward", "both"), default="back",
                   help="con 'both' se crean out_dir/back y out_dir/forward")
    b.add_argument("--forward-years", type=float, default=4000.0,
                   help="años hacia el futuro cuando direction es 'both'")
    b.add_argument("--workers", type=int, default=1,
                   help="procesos en paralelo (solo útil con 'both': una integración no se divide)")
    b.add_argument("--epsilon", type=float, default=1e-6)
    args = parser.parse_args()
    if args.command == "build":
        if args.direction == "both":
            build_many([
                {"out_dir": os.path.join(args.out_dir, "back"), "years": args.years,
                 "direction": "back", "epsilon": args.epsilon},
                {"out_dir": os.path.join(args.out_dir, "forward"),
                 "years": args.forward_years, "direction": "forward",
                 "epsilon": args.epsilon}], workers=args.workers)
        else:
            build_ephemeris(args.out_dir, args.years, args.direction, args.epsilon)


if __name__ == "__main__":
    _main()
