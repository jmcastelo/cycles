import sys, warnings, matplotlib
matplotlib.use('Agg'); warnings.simplefilter('ignore')
OUT = sys.argv[1]
import cycles.functions.nbody_ephemeris as nbe
from cycles.gui.sky import ephemeris_parts, DEFAULT_TABLE
from cycles.plotting.equinoctial_precession import plot_zodiac_with_planets, plot_zodiac_planets_grid
from cycles.functions.cycle_model import load_presets
tables = [nbe.load_ephemeris(p) for p in ephemeris_parts(DEFAULT_TABLE)]
m = load_presets()['Kali 3102 BC, midnight at Ujjain']
b = m.boundaries()
plot_zodiac_with_planets(float(b[3]), tables, time_scale='UT', epoch_display=('year', 'date'), save_path=f"{OUT}/planetas_inicio_kali.png", show=False)
plot_zodiac_planets_grid(list(map(float, b)), tables, labels=['Inicio del Satya', 'Inicio del Treta', 'Inicio del Dvapara', 'Inicio del Kali', 'Fin del ciclo'],
                         time_scale='UT', table=False, save_path=f"{OUT}/cuadricula_fronteras.png", show=False)
print('ok')
