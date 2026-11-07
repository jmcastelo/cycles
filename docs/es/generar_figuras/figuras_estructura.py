import sys, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cycles.functions.division import compute_level, level_colors, COLOR_KEYS
OUT = sys.argv[1]
NAMES = ('Satya', 'Treta', 'Dvapara', 'Kali')

# 1. levels 1-4 as bars, cmyk_normalised
fig, ax = plt.subplots(figsize=(9, 3.2))
for d in range(1, 5):
    lv = compute_level(d); col = level_colors(lv)['cmyk_normalised']
    for k in range(len(lv.starts)):
        ax.barh(-d, lv.durations[k], left=lv.starts[k], height=0.8, color=col[k], edgecolor='white', linewidth=0.4 if d < 4 else 0.15)
        if d == 1:
            ax.text(lv.starts[k] + lv.durations[k] / 2, -d, f"{NAMES[k]}\n{lv.durations[k]:.1f}", ha='center', va='center', fontsize=8,
                    color='white' if k == 3 else 'black')
ax.set_yticks([-1, -2, -3, -4], [f"profundidad {d}" for d in range(1, 5)])
ax.set_xlim(0, 1); ax.set_xlabel('tiempo normalizado')
for s in ('top', 'right', 'left'): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(f"{OUT}/division_niveles.png", dpi=170); plt.close(fig)

# 2. color variants, depth 3
keys = COLOR_KEYS
lv = compute_level(3); cols = level_colors(lv)
fig, ax = plt.subplots(figsize=(9, 4.2))
for r, key in enumerate(keys):
    for k in range(len(lv.starts)):
        ax.barh(-r, lv.durations[k], left=lv.starts[k], height=0.85, color=np.clip(cols[key][k], 0, 1), linewidth=0)
ax.set_yticks([-r for r in range(len(keys))], keys); ax.set_xlim(0, 1); ax.set_xlabel('tiempo normalizado (profundidad 3)')
for s in ('top', 'right', 'left'): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(f"{OUT}/variantes_color.png", dpi=170); plt.close(fig)

# 3. dharma vs purity depth 5, size by duration, color cmyk_normalised
lv = compute_level(5); col = level_colors(lv)['cmyk_normalised']
fig, ax = plt.subplots(figsize=(7, 5))
ax.scatter(lv.dharmas, lv.purities, s=3 + 4000 * lv.durations, c=np.clip(col, 0, 1), alpha=0.8, edgecolors='0.3', linewidths=0.2)
ax.set_xlabel('dharma'); ax.set_ylabel('pureza'); ax.set_title('Profundidad 5: dharma y pureza (tamaño ∝ duración)', fontsize=10)
fig.tight_layout(); fig.savefig(f"{OUT}/dharma_pureza.png", dpi=170); plt.close(fig)

# 4. durations at depth 4 against index, colored by class
lv = compute_level(4)
u, inv = np.unique(np.round(lv.durations, 14), return_inverse=True)
fig, ax = plt.subplots(figsize=(9, 3.6))
ax.scatter(np.arange(256), lv.durations, c=inv, cmap='tab20', s=9)
ax.set_yscale('log'); ax.set_xlabel('índice (tcoord) a profundidad 4'); ax.set_ylabel('duración')
ax.set_title(f"256 subciclos, {len(u)} duraciones distintas = (4+1)²", fontsize=10)
fig.tight_layout(); fig.savefig(f"{OUT}/duraciones_profundidad4.png", dpi=170); plt.close(fig)
print('ok')
