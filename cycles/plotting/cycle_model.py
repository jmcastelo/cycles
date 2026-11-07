"""
Plots of a cycle model against the precession: the precession rate across the
cycle, how far the time shares are from 4:3:2:1 at each depth, and the scans
of ``cycle_analysis.fit_anchor``.

Each function draws on ``ax`` if given (and then shows nothing), or creates a
figure; ``save_path`` writes it (creating folders) and ``show`` displays it.
All return the Axes.
"""

from pathlib import Path

import numpy as np

from cycles.functions.cycle_analysis import FitResult, boundary_fractions, precession_rate, subdivision_deviations
from cycles.functions.cycle_model import CycleModel
from cycles.functions.timescale import YUGA_NAMES

YUGA_COLORS = ('#00a6d6', '#d6008f', '#d6b400', '#333333')    # cyan, magenta, yellow, black inks


def _axes(ax, figsize):
    import matplotlib.pyplot as plt
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize, layout='constrained')
        return ax, True
    return ax, False


def _finish(ax, own: bool, save_path, show: bool):
    import matplotlib.pyplot as plt
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        ax.figure.savefig(save_path, dpi=200)
    if own and show:
        plt.show()
    return ax


def plot_precession_rate(model: CycleModel, ax=None, depth: int = 2, samples: int = 4000, save_path=None,
                         show: bool = True):
    """
    Precession rate across the cycle, with the mean rate of each yuga, the
    cycle's mean rate, and the boundaries of the yugas (solid) and of their
    parts down to ``depth`` (dotted).
    """
    ax, own = _axes(ax, (11, 5))
    solution = model.solve()
    time_map = model.time_map()
    start, end = solution['start'], solution['end']
    margin = 0.02 * (end - start)
    years = np.linspace(start - margin, end + margin, samples)
    ax.plot(years, precession_rate(model, years), color='0.2', lw=1.2, label='Precession rate')
    mean = solution['turns'] * 1296000 / solution['years']
    ax.axhline(mean, color='0.5', lw=0.8, ls='--', label=f"Cycle mean ({mean:.2f}″/yr)")
    for d in range(depth, 1, -1):
        for t in time_map.to_physical(boundary_fractions(d)):
            ax.axvline(t, color='0.75', lw=0.5, ls=':', zorder=0)
    yugas = time_map.to_physical(boundary_fractions(1))
    for k in range(4):
        t0, t1 = yugas[k], yugas[k + 1]
        rate = (model.ayanamsa(t1) - model.ayanamsa(t0)) * 3600 / (t1 - t0)
        ax.axvspan(t0, t1, color=YUGA_COLORS[k], alpha=0.08, lw=0)
        ax.hlines(rate, t0, t1, color=YUGA_COLORS[k], lw=2.5, label=f"{YUGA_NAMES[k]} mean ({rate:.2f}″/yr)")
    for t in yugas:
        ax.axvline(t, color='0.3', lw=0.8)
    ax.set_xlim(years[0], years[-1])
    ax.set_xlabel('Year (astronomical numbering: 0 = 1 BC)')
    ax.set_ylabel('Precession rate (arcsec per year)')
    ax.set_title(f"Precession rate across the cycle: {model.name}", fontsize=10)
    ax.legend(fontsize=8, loc='best')
    return _finish(ax, own, save_path, show)


def plot_mismatch_by_depth(model: CycleModel, max_depth: int = 5, ax=None, save_path=None, show: bool = True):
    """
    For each depth, how far each subcycle's share of its parent's time is from
    0.4, 0.3, 0.2 or 0.1 when dividing by angle: every deviation (points, by
    age), the largest and the RMS.
    """
    ax, own = _axes(ax, (8, 5))
    largest, rms = [], []
    rng = np.random.default_rng(0)
    for depth in range(1, max_depth + 1):
        deviations = np.abs(subdivision_deviations(model, depth))
        largest.append(deviations.max())
        rms.append(np.sqrt(np.mean(deviations ** 2)))
        for k in range(4):
            values = np.maximum(deviations[:, k], 1e-12)
            jitter = depth + (k - 1.5) * 0.12 + rng.uniform(-0.04, 0.04, len(values))
            ax.scatter(jitter, values, s=6, color=YUGA_COLORS[k], alpha=0.6,
                       label=f"part {YUGA_NAMES[k]}" if depth == 1 else None)
    depths = np.arange(1, max_depth + 1)
    ax.plot(depths, largest, color='0.2', marker='o', label='largest')
    ax.plot(depths, rms, color='0.5', marker='s', ls='--', label='RMS')
    ax.set_yscale('log')
    ax.set_xticks(depths)
    ax.set_xlabel('Depth of the parts')
    ax.set_ylabel('|share of the parent’s time − 4:3:2:1 share|')
    ax.set_title(f"Time vs angle criteria by depth: {model.name}", fontsize=10)
    ax.legend(fontsize=8)
    return _finish(ax, own, save_path, show)


def plot_fit_scan(result: FitResult, original: CycleModel | None = None, ax=None, save_path=None,
                  show: bool = True):
    """
    The mismatch scanned by ``fit_anchor``: against the anchor year (one arc),
    or as a map over anchor year and arc. Marks the best point and, if given,
    the model the fit started from.
    """
    ax, own = _axes(ax, (11, 5))
    grid = np.where(np.isfinite(result.grid), result.grid, np.nan)
    anchor_name = 'anchor'
    if original is not None:
        anchor_name = {'satya': 'start of Satya', 'treta': 'start of Treta', 'dvapara': 'start of Dvapara',
                       'kali': 'start of Kali', 'end': 'end of the cycle'}[original.anchor_point]
    if len(result.turn_values) == 1:
        ax.plot(result.anchors, grid[:, 0], color='0.2', lw=1)
        ax.plot(result.anchor_year, result.mismatch, 'o', color='#2ca02c', label=f"best ({result.mismatch:.5f})")
        if original is not None:
            ax.plot(original.solve()['anchor'], result.original_mismatch, 'o', color='#d62728',
                    label=f"{original.name} ({result.original_mismatch:.5f})")
        ax.set_ylabel('Largest deviation of the time shares')
        ax.set_title(f"Agreement of the criteria against the {anchor_name}, {result.turns:g} turns", fontsize=10)
    else:
        mesh = ax.pcolormesh(result.anchors, result.turn_values, grid.T, shading='auto', cmap='viridis_r')
        ax.figure.colorbar(mesh, ax=ax, label='Largest deviation of the time shares')
        ax.plot(result.anchor_year, result.turns, 'o', color='white', mec='black', label='best')
        if original is not None:
            solution = original.solve()
            ax.plot(solution['anchor'], solution['turns'], 'o', color='#d62728', mec='black', label=original.name)
        ax.set_ylabel('Precession arc of the cycle (turns)')
        ax.set_title(f"Agreement of the criteria over the {anchor_name} and the arc", fontsize=10)
    ax.set_xlabel(f"Year of the {anchor_name} (astronomical numbering)")
    ax.legend(fontsize=8)
    return _finish(ax, own, save_path, show)
