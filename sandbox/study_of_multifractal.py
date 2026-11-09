"""
Study of the multifractal spectrum of the division (cycles.functions.multifractal): how unevenly the time is spread
over the subcycles, and the subcycles over the time.
"""

import matplotlib.pyplot as plt
import numpy as np

from cycles.functions.multifractal import MEASURES, histogram_spectrum, key_values, spectrum
from common import PLOTS_DIR, save_figure
from runner import run, study

BASE_DIR = PLOTS_DIR / "study_of_multifractal"
TITLES = {
    'time': 'Time on the index line (the durations)',
    'count': 'Count on the time line (equal weights)',
}
AXES = {
    'time': ('α: duration of a subcycle ≈ (4⁻ᵈ)^α', 'f(α)'),
    'count': ('α: 4⁻ᵈ ≈ (its duration)^α', 'f(α)'),
}


def setup():
    return dict(depths=(10, 40, 160), width=0.02, q=np.linspace(-40, 40, 4001))


@study
def key_numbers(ctx, opts):
    """The ends, the typical exponent, and the information and correlation dimensions of both measures."""
    for name, (weights, sizes) in MEASURES.items():
        values = key_values(weights, sizes)
        print(f"{TITLES[name]}:")
        ends = np.log(weights) / np.log(sizes)          # the exponent of an address all of one age
        print(f"  α from {values['alpha_min']:.4f} to {values['alpha_max']:.4f}; all Satya {ends[0]:.4f}, "
              f"all Kali {ends[3]:.4f}")
        print(f"  the most numerous pieces: α₀ = {values['alpha_0']:.4f} (f = 1)")
        print(f"  information dimension D₁ = {values['D1']:.4f}, correlation dimension D₂ = {values['D2']:.4f}")
    t, c = key_values(*MEASURES['time']), key_values(*MEASURES['count'])
    print(f"Duality: D₁(time) = 1/α₀(count): {t['D1']:.4f} = {1 / c['alpha_0']:.4f}; "
          f"D₁(count) = 1/α₀(time): {c['D1']:.4f} = {1 / t['alpha_0']:.4f}")


@study
def spectra(ctx, opts):
    """The exact f(α) of both measures (Legendre transform) and the histogram estimates at finite depths."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    colors = plt.get_cmap('viridis')(np.linspace(0.15, 0.85, len(ctx.depths)))
    for ax, (name, (weights, sizes)) in zip(axes, MEASURES.items()):
        exact = spectrum(ctx.q, weights, sizes)
        values = key_values(weights, sizes)
        for depth, color in zip(ctx.depths, colors):
            estimate = histogram_spectrum(depth, weights, sizes, ctx.width)
            ax.plot(estimate['alpha'], estimate['f'], 'o', ms=2.5, color=color, label=f"depth {depth}")
        ax.plot(exact['alpha'], exact['f'], color='black', lw=1.4, label='exact (d → ∞)')
        ax.plot([0, 2], [0, 2], color='0.6', lw=0.8, ls=':', label='f = α')
        ax.axvline(values['D1'], color='#d62728', lw=0.8, ls='--')
        ax.annotate(f"D₁ = {values['D1']:.4f}", (values['D1'], values['D1']), xytext=(8, -18),
                    textcoords='offset points', color='#d62728', fontsize=9)
        ax.annotate(f"α₀ = {values['alpha_0']:.4f}", (values['alpha_0'], 1), xytext=(6, 6),
                    textcoords='offset points', fontsize=9)
        ax.set_xlim(values['alpha_min'] - 0.05, values['alpha_max'] + 0.05)
        ax.set_ylim(0, 1.08)
        ax.set_xlabel(AXES[name][0])
        ax.set_ylabel(AXES[name][1])
        ax.set_title(TITLES[name], fontsize=10)
        ax.legend(fontsize=8, loc='lower center')
    fig.suptitle('The multifractal spectrum of the 4:3:2:1 division')
    fig.tight_layout()
    if opts.save:
        save_figure(fig, BASE_DIR / 'multifractal_spectra.png', dpi=150)
    if opts.show:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    run(setup)
