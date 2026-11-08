# 13. Pruebas

## 13.1 Cómo se ejecutan

```bash
pip install -e ".[test]"        # o ".[all,test]" para las del explorador
pytest                          # todas (unos 3 minutos)
pytest -m "not gui"             # solo las de cálculo (segundos)
pytest -m "not ephemeris"       # sin las que necesitan las tablas de efemérides
pytest tests/test_landscape.py  # un fichero
```

La configuración está en `pyproject.toml` (`[tool.pytest.ini_options]`): carpeta `tests`, el proyecto en el
`sys.path` y dos marcas:

| Marca | Significado |
|---|---|
| `gui` | pruebas del explorador: se ejecutan sin pantalla (`QT_QPA_PLATFORM=offscreen`) y necesitan PySide6 |
| `ephemeris` | necesitan las tablas de la efeméride; sin ellas se saltan |

`tests/conftest.py` prepara el entorno: cada prueba del explorador tiene una **ventana nueva** con ajustes en una
carpeta temporal (los del usuario no se tocan), sin la sesión de una ventana anterior, con las preguntas
respondidas «sí» y sin que el paisaje del modelo se calcule solo (sin pantalla, los paneles de pestañas ocultas
cuentan como visibles; sus pruebas lo calculan explícitamente). El accesorio `spin` procesa los eventos
pendientes y `ephemeris` localiza las tablas.

## 13.2 Qué se comprueba

En total hay **251 pruebas** en 24 ficheros.

### Cálculo

| Fichero | Pruebas | Qué comprueba |
|---|---:|---|
| `test_division.py` | 18 | duraciones, inicios y conversiones entre formas de dirección |
| `test_durations_compositions.py` | 20 | la regla (1, 0, −2, 1): las composiciones de igual duración y nada más |
| `test_permutation.py` | 28 | las permutaciones frente a `symmetry-math` y el estudio; conservan las duraciones; lema de Burnside; notaciones |
| `test_color.py` | 20 | los valores por defecto y otros dentro de los rangos dan colores únicos; los de fuera se avisan; vértices coplanarios se rechazan y cuatro colores alineados repiten colores |
| `test_cycle_model.py` | 13 | los presets, sus mapas de tiempo y fronteras (por ejemplo, el inicio del Kali el 17 de febrero de 3102 a. C. a las 18:57 UT) |
| `test_events.py` | 12 | distancia al acontecimiento más cercano, rotaciones que conservan el espaciado, contrastes con acontecimientos en las fronteras (p pequeño) y sin relación (p uniforme), Holm; grandes conjunciones y de planetas exteriores frente a fechas conocidas; cambios de trígono asentados (1603, 2020); la reunión de planetas al inicio del Kali |
| `test_colorings.py` | 7 | los coloreados nuevos: OKLab (blanco, negro y rojo de referencia, ida y vuelta); el tetraedro en OKLab encogido por un mismo factor, dentro de la gama y con regiones de las cuatro edades iguales (en RGB no); un color por clase de duración (36 a profundidad 5); los mapas de las medidas (0 neutro, densidad centrada en 1); el punto vernal (hoy en Piscis, agua; en 3102 a. C., tierra); y en el explorador: medidas, modelo (gris sin él), el inspector y todos los coloreados en el navegador (una de ellas) |
| `test_measures.py` | 6 | las medidas de 2.4: cada una en su rango; una sola edad da 0 en mezcla, tensión, tendencia y aspereza; los extremos (cuatro edades iguales, mitad Satya y mitad Kali, Kali › Satya); la mezcla distingue lo que la pureza no; el contraste y el balance siguen el orden temporal y el balance cierra en 0; la densidad angular (1 para el ciclo entero y con precesión constante, media ponderada 1) |
| `test_landscape.py` | 9 | `mismatch_grid` frente a `mismatch_by_depth`; los periodos de 41 000 y 20 000 años; el panel del paisaje |
| `test_version.py` | 5 | la versión: formato MAJOR.MINOR.PATCH, `pyproject.toml` la lee del paquete, el `CHANGELOG.md` empieza por ella, los documentos describen esa versión (si están en el equipo) y el explorador la muestra |
| `test_session_studies.py` | 3 | los estudios con `--session`: el modelo y los colores de la sesión llegan al estudio; una sesión inválida se rechaza |

### Explorador

| Fichero | Pruebas | Qué comprueba |
|---|---:|---|
| `test_gui_panels.py` | 6 | los paneles existen; al reordenarlos, los cerrados siguen colocados y se pueden abrir |
| `test_gui_layouts.py` | 12 | mover un panel a cada lado, flotante, en pestaña; disposiciones por tipo; esquinas; disposiciones con nombre; menús; el espacio del navegador |
| `test_gui_navigator.py` | 5 | la banda de etiquetas, arrastrar las etiquetas, Mayús + clic |
| `test_gui_measures.py` | 8 | el panel Measures con dos medidas cualesquiera (2D, tiempo, 3D), coloreado por una medida con su barra, la densidad angular sin modelo, la línea de medidas del inspector, sesiones; las uniones de los resaltados (36 intercambios entre las 24 ordenaciones de cuatro edades distintas, los pasos de la órbita en orden) en Measures y Color space |
| `test_gui_highlight.py` | 5 | los resaltados alrededor de la selección y el momento con *Follow* |
| `test_gui_export.py` | 10 | guardar gráficos: tamaños, formatos, resolución; los paneles conservan su tamaño en pantalla |
| `test_gui_permutations.py` | 12 | el panel de permutaciones y el explorador de grupo |
| `test_gui_compositions.py` | 8 | el tetraedro de composiciones y las medidas por nivel |
| `test_gui_sky_colors.py` | 4 | el gráfico del cielo (tamaño fijo, leyenda) y el diálogo de colores |
| `test_gui_criteria_skycompare.py` | 21 | los dos criterios en el navegador; el panel Sky comparison (conjuntos, orden por parecido, franja, concentración, ajuste de las cartas al tamaño); posiciones vectorizadas frente a escalares |
| `test_gui_session.py` | 8 | sesiones: ida y vuelta completa, restaurar al arrancar, ficheros inválidos, partes que no encajan, σ al azar, marcadores, recientes, el lanzador con la sesión |
| `test_gui_events.py` | 8 | el panel Events: la prueba coincide con el cálculo directo, el mapa sobre los modelos, los planetas medios, cambios de trígono y planetas en 0° de Aries, solo dentro del zoom, pulsar un acontecimiento, la capa del navegador, sesiones, sin efeméride |
| `test_gui_dossier.py` | 3 | el dosier: el resumen, todas las secciones, papel y orientación en el PDF, opciones recordadas |

## 13.3 Comprobaciones notables

- **Burnside:** la media de los puntos fijos de S_m sobre las direcciones es C(m + 3, 3), el número de
  composiciones.
- **Unicidad de los colores** dentro de los rangos (profundidades 1 a 5), y repeticiones con cuatro vértices
  alineados.
- **El inicio del Kali** del modelo por defecto es el 17 de febrero de 3102 a. C., 18:57 UT: la medianoche local en
  Ujjain (75,77° E) del 18.
- **El periodo del paisaje**: los picos de la tasa cada 36 000–46 000 años; los cambios de signo de la desviación
  del Treta y los máximos del desajuste cada 17 000–23 000 años, con cualquier arco.
- **La efeméride vectorizada** coincide con la escalar y da NaN fuera de las tablas.
