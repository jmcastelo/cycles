import sys, warnings, numpy as np, matplotlib
matplotlib.use('Agg'); warnings.simplefilter('ignore')
import matplotlib.pyplot as plt
OUT = sys.argv[1]
from cycles.plotting.equinoctial_precession import plot_equinoctial_precession, plot_ayanamsa_comparison, plot_zodiac_with_planets, long_term_ayanamsa
from cycles.functions.cycle_model import load_presets
from cycles.functions.cycle_analysis import precession_rate
plot_equinoctial_precession(2026.85, save_path=f"{OUT}/esquema_precesion_2026.png", show=False)
plot_ayanamsa_comparison(-30215, 34215, save_path=f"{OUT}/ayanamsa_lineal_vs_largo_plazo.png", show=False)
m = load_presets()['Kali 3102 BC, midnight at Ujjain']
# rate across +-100k years with the default cycle span
ys = np.linspace(-100000, 100000, 4000); r = precession_rate(m, ys)
s = m.solve(); b = m.boundaries()
fig, ax = plt.subplots(figsize=(9, 3.4))
ax.plot(ys, r, color='0.25', lw=1)
ax.axvspan(s['start'], s['end'], color='#1f77b4', alpha=0.12)
for y in b: ax.axvline(y, color='#1f77b4', lw=0.8, ls='--')
ax.set_xlabel('año'); ax.set_ylabel('tasa de precesión (″/año)')
ax.set_title('Tasa de precesión del modelo de largo plazo; en azul, el ciclo del modelo por defecto y sus yugas', fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/tasa_precesion.png", dpi=170); plt.close(fig)
print('ok')
