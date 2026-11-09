"""Figures and screenshots of the explorer for the Spanish docs (run offscreen, with temporary settings)."""
import os, sys, tempfile
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
OUT = sys.argv[1]
WHICH = sys.argv[2:] or ['part1']
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())
app = QApplication([]); app.setOrganizationName('cycles-docs'); app.setApplicationName('cycles-docs')
from cycles.gui.app import MainWindow
from cycles.gui.export import ExportOptions
w = MainWindow(); w.resize(1500, 900); w.show()
def spin(n=40):
    for _ in range(n): app.processEvents()
spin()
s = w.state
def save_panel_figure(panel, name, width=7.0, height=5.5, relayout=None):
    if panel._dirty: panel.render()
    fig = panel.figure; prev = fig.get_size_inches().copy()
    fig.set_size_inches(width, height, forward=False)
    if relayout: relayout()
    fig.savefig(f"{OUT}/{name}", dpi=160, facecolor='white')
    fig.set_size_inches(*prev, forward=False)
    if relayout: relayout()
if 'part1' in WHICH:
    s.set_focus(()); s.select((3, 1, 2, 0)); spin()
    cp = w.compositions_panel; cp.depth.setValue(4); s.set_highlight('composition'); spin(); cp.render()
    save_panel_figure(cp, 'tetraedro_composiciones.png', 6.5, 6.0)
    cs = w.colorspace_panel
    cs.plot.setCurrentIndex(0); cs.depth.setValue(6); cs.inside.setChecked(False)
    s.set_color_key('tetrahedron'); spin(); cs.render()
    save_panel_figure(cs, 'sierpinski_tetraedro.png', 6.5, 6.0)
    s.set_color_key('cmyk_normalised')
    pp = w.permutations_panel; pp.preset.setCurrentText('Cyclic shift'); pp.acts.setCurrentIndex(pp.acts.findData('all')); pp.depth.setValue(3); spin(); pp.render()
    save_panel_figure(pp, 'permutacion_potencias.png', 9.0, 4.5)
if 'part2' in WHICH:
    w.show_panel('landscape'); spin()
    lp = w.landscape_panel; lp.resolution.setCurrentIndex(lp.resolution.findData('medium')); lp.render(); lp.finish()
    save_panel_figure(lp, 'paisaje_modelo.png', 9.0, 6.0)
if 'shots' in WHICH:
    import time
    def wait(seconds):
        end = time.time() + seconds
        while time.time() < end: app.processEvents()
    def dock_shot(name, file, size=(950, 680), prepare=None):
        from cycles.gui.layouts import float_panel
        float_panel(w, name, size); dock = w.docks[name]; spin(60)
        panel = dock.widget()
        if prepare: prepare(panel)
        if hasattr(panel, '_dirty') and panel._dirty: panel.render()
        if hasattr(panel, 'fit_charts'): panel.fit_charts()
        if hasattr(panel, 'canvas'): panel.canvas.draw()
        spin(30)
        panel.grab().save(f"{OUT}/{file}")
        w.arrange_panels('tabs'); spin()
    w.reset_layout(); w.resize(1500, 900); spin()
    s.set_focus((3,)); s.select((3, 1, 2)); s.set_labels('names'); s.set_highlight('composition'); s.set_compare_criteria(True)
    s.set_sky_time(-1500.0)
    s.add_bookmark((3, 1, 2), 'Semilla', 'misma composición que el presente'); s.add_bookmark((3, 0), 'Kali › Satya', '')
    s.set_notes('Comparar el modelo por defecto con el de Abhyankar.\nMirar las subdivisiones del Kali.')
    w.show_panel('inspector'); spin(60)
    w.grab().save(f"{OUT}/ventana_principal.png")
    w.navigator.grab().save(f"{OUT}/navegador.png")
    dock_shot('inspector', 'panel_subciclo.png', (520, 960))
    dock_shot('date', 'panel_fecha.png', (620, 520))
    dock_shot('sky', 'panel_cielo.png', (700, 900))
    def compare_prep(p):
        p.kind.setCurrentIndex(p.kind.findData('all')); p.order.setCurrentIndex(p.order.findData('similar')); p.render()
    dock_shot('skycompare', 'panel_comparacion_cielos.png', (1000, 900), compare_prep)
    def measures_prep(p):
        p.kind.setCurrentIndex(p.kind.findData('scatter'))
        p.x_measure.setCurrentIndex(p.x_measure.findData('tension')); p.y_measure.setCurrentIndex(p.y_measure.findData('trend'))
        p.color_by.setCurrentIndex(p.color_by.findData('dharma')); p.inside.setChecked(False); p.depth.setValue(4); p.render()
    dock_shot('measures', 'panel_medidas.png', (980, 680), measures_prep)
    dock_shot('colorspace', 'panel_espacio_color.png', (800, 700))
    def perm_prep(p):
        p.preset.setCurrentText('Swap the last two'); p.acts.setCurrentIndex(p.acts.findData('below')); p.depth.setValue(4); spin(); p.render()
    dock_shot('permutations', 'panel_permutaciones.png', (1000, 650), perm_prep)
    dock_shot('compositions', 'panel_composiciones.png', (800, 750))
    def land_prep(p):
        p.resolution.setCurrentIndex(p.resolution.findData('medium')); p.render(); p.finish()
    dock_shot('landscape', 'panel_paisaje.png', (1000, 780), land_prep)
    dock_shot('notes', 'panel_notas.png', (800, 520))
    pp = w.permutations_panel; pp.depth.setValue(4); pp.acts.setCurrentIndex(pp.acts.findData('all')); spin(); pp.show_group(); ex = pp.explorer; ex.resize(1150, 620); wait(6)
    ex.grab().save(f"{OUT}/explorador_grupo.png"); ex.close()
    w.show_model_dialog(); spin(30); w.model_dialog.grab().save(f"{OUT}/dialogo_modelo.png"); w.model_dialog.close()
    w.show_color_dialog(); spin(30); w.color_dialog.grab().save(f"{OUT}/dialogo_colores.png"); w.color_dialog.close()
    w.save_graph('measures'); spin(30); w.export_dialog.grab().save(f"{OUT}/dialogo_guardar.png"); w.export_dialog.close()
    w.show_studies(); wait(8); w.launcher.resize(1100, 650); spin(30); w.launcher.grab().save(f"{OUT}/lanzador_estudios.png"); w.launcher.close()
    w.show_dossier(); spin(30); w.dossier_dialog.grab().save(f"{OUT}/dialogo_dosier.png"); w.dossier_dialog.close()
    w.arrange_panels('around'); w.resize(1600, 950); spin(60)
    w.grab().save(f"{OUT}/disposicion_alrededor.png")
if 'model' in WHICH:
    import time
    w.show_model_dialog(); end = time.time() + 1.0
    while time.time() < end: app.processEvents()
    w.model_dialog.grab().save(f"{OUT}/dialogo_modelo.png")
    w.show_color_dialog(); end = time.time() + 3.0
    while time.time() < end: app.processEvents()
    w.color_dialog.grab().save(f"{OUT}/dialogo_colores.png")
if 'events' in WHICH:
    s.set_focus((3,)); s.select((3, 1)); spin()
    w.show_panel('events'); spin()
    from cycles.gui.layouts import float_panel
    ep = w.events_panel; float_panel(w, 'events', (900, 760)); dock = w.docks['events']; spin(60)
    ep.kind.setCurrentIndex(ep.kind.findData('great')); ep.depth.setValue(2); ep.render(); ep.canvas.draw(); spin(30)
    dock.widget().grab().save(f"{OUT}/panel_eventos.png")
    w.arrange_panels('tabs'); spin()
if 'dynamics' in WHICH:
    s.set_focus(()); s.select((3, 1, 2, 0, 1, 2)); spin()
    w.show_panel('dynamics'); spin()
    from cycles.gui.layouts import float_panel
    dp = w.dynamics_panel; float_panel(w, 'dynamics', (900, 720)); dock = w.docks['dynamics']; spin(60)
    dp.plot.setCurrentIndex(dp.plot.findData('return')); dp.series_box.setCurrentIndex(dp.series_box.findData('duration'))
    dp.surrogate.setCurrentIndex(dp.surrogate.findData('shuffled')); dp.render(); dp.canvas.draw(); spin(30)
    dock.widget().grab().save(f"{OUT}/panel_dinamica.png")
    w.arrange_panels('tabs'); spin()
print('ok')
