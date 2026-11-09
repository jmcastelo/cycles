# 13. Pruebas

## 13.1 Cómo se ejecutan

```bash
pip install -e ".[test]"        # o ".[all,test]" para las del explorador
pytest -n 8                     # todas, en 8 procesos a la vez (pytest-xdist; menos de un minuto)
pytest                          # todas, en un solo proceso (unos 9 minutos)
pytest -m "not gui"             # solo las de cálculo (segundos)
pytest -m "not ephemeris"       # sin las que necesitan las tablas de efemérides
pytest tests/test_landscape.py  # un fichero
```

`-n` reparte las pruebas entre varios procesos (`pytest-xdist`, en el extra `test`); cada uno abre su propio
explorador sin pantalla y con sus ajustes, así que no se estorban. Conviene no pasar de la mitad de los núcleos
(`nproc`), para que el equipo siga respondiendo; `-n auto` los usa todos.

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

En total hay **324 pruebas** en 28 ficheros.

### Cálculo

| Fichero | Pruebas | Qué comprueba |
|---|---:|---|
| `test_division.py` | 21 | duraciones, inicios y conversiones entre formas de dirección; `compute_level`, vectorizado, igual que las funciones de un subciclo (dos juegos de parámetros) y la profundidad 9 en segundos |
| `test_durations_compositions.py` | 20 | la regla (1, 0, −2, 1): las composiciones de igual duración y nada más |
| `test_permutation.py` | 28 | las permutaciones frente a `symmetry-math` y el estudio; conservan las duraciones; lema de Burnside; notaciones |
| `test_color.py` | 20 | los valores por defecto y otros dentro de los rangos dan colores únicos; los de fuera se avisan; vértices coplanarios se rechazan y cuatro colores alineados repiten colores |
| `test_cycle_model.py` | 13 | los presets, sus mapas de tiempo y fronteras (por ejemplo, el inicio del Kali el 17 de febrero de 3102 a. C. a las 18:57 UT) |
| `test_events.py` | 13 | distancia al acontecimiento más cercano, rotaciones que conservan el espaciado, contrastes con acontecimientos en las fronteras (p pequeño) y sin relación (p uniforme), Holm; grandes conjunciones y de planetas exteriores frente a fechas conocidas; cambios de trígono asentados (1603, 2020); la reunión de planetas al inicio del Kali; el trígono vigente con un catálogo de prueba (una racha de paso no cuenta) |
| `test_colorings.py` | 12 | los coloreados nuevos: OKLab (blanco, negro y rojo de referencia, ida y vuelta); el tetraedro en OKLab encogido por un mismo factor, dentro de la gama y con regiones de las cuatro edades iguales (en RGB no); un color por clase de duración (36 a profundidad 5); los mapas de las medidas (0 neutro, densidad centrada en 1); el punto vernal (hoy en Piscis, agua; en 3102 a. C., tierra); y en el explorador: medidas, modelo (gris sin él), el inspector y todos los coloreados en el navegador; los mapas de las medidas: el dharma y la pureza siguen al secuencial (en gris, grises), mapas desconocidos rechazados, cambiar de mapa solo recolorea las medidas (los niveles se conservan) y el diálogo los elige; el cielo: la reunión al inicio del Kali (más de 0,85), el trígono vigente al inicio de los yugas (agua, tierra, agua, fuego en el trópico), y el inspector y el panel *Measures* sin la efeméride (cinco de ellas, del explorador) |
| `test_query.py` | 15 | las consultas: condiciones con medidas, dígitos, edades, `count` y `abs`, comparaciones encadenadas; lo que se rechaza (importaciones, atributos, índices, textos, otras funciones); en el explorador: el estado (nombres desconocidos, dígitos que no existen, sin modelo), la barra (el resaltado, la cuenta, una consulta en rojo, vaciarla), los anillos del panel *Measures* y las sesiones |
| `test_multifractal.py` | 6 | el espectro multifractal: τ(0) = −1 y τ(1) = 0, máximo de f = 1 y f ≤ α, las dimensiones en forma cerrada y la dualidad de las dos medidas, las (*d* + 1)² clases de igual exponente, y la estimación por histogramas que tiende a la curva exacta |
| `test_dynamics.py` | 20 | la dinámica: las razones de duraciones consecutivas y los pasos del dharma fijados por los acarreos (con sus frecuencias $3/4^{k+1}$); el periodograma igual al producto de Riesz; el MF-DFA frente a $h(q)$ exacto, con $h(0) = \alpha_0$, y las sustitutas (desordenada: 0,5; fases al azar: sin multifractalidad); la aspereza del dharma con bases 2 y 3 (Higuchi y orden 1); la aplicación de ampliación frente a las $D_1$; patrones ordinales (monótona, ruido, seno; empates al azar); recurrencias; retornos y Kac; la inversión del tiempo; el muestreo en años (también en un tramo, con sus instantes); lo que conservan las sustitutas; la dimensión de correlación del dharma con bases 3, 8 y 16 igual en toda dimensión e igual a la exacta, y la del ruido creciente; las sumas de correlación de una variable uniforme; los puntos de cambio de una escalera, los niveles de las fronteras y los de la tendencia en los inicios de las edades; el nulo de los dígitos (las duraciones iguales, la aspereza perdida, una permutación fija) |
| `test_measures.py` | 8 | las medidas de 2.4: cada una en su rango; una sola edad da 0 en mezcla, tensión, tendencia y aspereza; los extremos (cuatro edades iguales, mitad Satya y mitad Kali, Kali › Satya); la mezcla distingue lo que la pureza no; el contraste y el balance siguen el orden temporal y el balance cierra en 0; la densidad angular (1 para el ciclo entero y con precesión constante, media ponderada 1); el microcosmos (1 para las cuotas del ciclo, 0 para todo Kali) y la complejidad de Lempel–Ziv (el ejemplo de Kaspar y Schuster, 0 para una edad repetida) |
| `test_landscape.py` | 9 | `mismatch_grid` frente a `mismatch_by_depth`; los periodos de 41 000 y 20 000 años; el panel del paisaje |
| `test_version.py` | 5 | la versión: formato MAJOR.MINOR.PATCH, `pyproject.toml` la lee del paquete, el `CHANGELOG.md` empieza por ella, los documentos describen esa versión (si están en el equipo) y el explorador la muestra |
| `test_session_studies.py` | 3 | los estudios con `--session`: el modelo, los colores y los mapas de las medidas de la sesión llegan al estudio; una sesión inválida se rechaza |

### Explorador

| Fichero | Pruebas | Qué comprueba |
|---|---:|---|
| `test_gui_panels.py` | 6 | los paneles existen; al reordenarlos, los cerrados siguen colocados y se pueden abrir |
| `test_gui_dynamics.py` | 6 | el panel *Dynamics*: los cinco gráficos en las dos lecturas; el mapa de retorno del dharma con lo exacto (aspereza 0,5, giro en torno a 0,625) y la selección marcada; las duraciones con la sustituta desordenada (menos memoria) y la de los dígitos (la misma serie), en escala logarítmica; dentro del zoom y en años; pulsar selecciona; la densidad sin modelo; la sesión guarda el panel |
| `test_gui_layouts.py` | 13 | los paneles con QtAds: el navegador en el centro; cada tipo de panel en su lado (los cerrados, colocados), con espacio para el navegador; flotantes y barras laterales; disposiciones con nombre (perspectivas, en los ajustes); la sesión guarda la disposición; mover marca la sesión; el menú *Panels*; volver a acoplar los paneles flotantes, solos o en grupo (el botón, pulsado, y el menú); los títulos de las pestañas legibles con una paleta oscura; el botón *Attach* solo en las ventanas flotantes, con su icono, también al cambiar de pestaña |
| `test_gui_navigator.py` | 13 | la banda de etiquetas, arrastrar las etiquetas, Mayús + clic; las nueve profundidades a la vez: las filas densas como tiras de píxeles, pulsar en ellas, y un subciclo resaltado que no se pierde en su píxel; la ventana: la rueda estrecha y ensancha alrededor del puntero (hasta un subciclo de profundidad 8 y hasta el ciclo entero), el zoom es el subciclo más pequeño que la contiene (y solo avisa al cambiar), arrastrar mueve sin seleccionar y un clic selecciona, el mapa (arrastrar el marco y su borde, clic en una edad), la barra de desplazamiento y las teclas `+` e `Inicio`, ajustes, el mismo tramo con anchos iguales, mostrar un subciclo fuera de la vista, y la sesión guarda la ventana |
| `test_gui_measures.py` | 8 | el panel Measures con dos medidas cualesquiera (2D, tiempo, 3D), coloreado por una medida con su barra, la densidad angular sin modelo, la línea de medidas del inspector, sesiones; las uniones de los resaltados (36 intercambios entre las 24 ordenaciones de cuatro edades distintas, los pasos de la órbita en orden) en Measures y Color space |
| `test_gui_highlight.py` | 6 | los resaltados alrededor de la selección y el momento con *Follow*; el menú *View* dibuja el navegador y sigue al estado |
| `test_gui_export.py` | 10 | guardar gráficos: tamaños, formatos, resolución; los paneles conservan su tamaño en pantalla |
| `test_gui_permutations.py` | 13 | el panel de permutaciones y el explorador de grupo; el explorador de grupo llega hasta S₈ |
| `test_gui_compositions.py` | 8 | el tetraedro de composiciones y las medidas por nivel |
| `test_gui_sky_colors.py` | 4 | el gráfico del cielo (tamaño fijo, leyenda) y el diálogo de colores |
| `test_gui_criteria_skycompare.py` | 21 | los dos criterios en el navegador; el panel Sky comparison (conjuntos, orden por parecido, franja, concentración, ajuste de las cartas al tamaño); posiciones vectorizadas frente a escalares |
| `test_gui_session.py` | 12 | sesiones: ida y vuelta completa (con los mapas de las medidas), restaurar al arrancar, ficheros inválidos, partes que no encajan, σ al azar, marcadores, recientes, el lanzador con la sesión; al cerrar con cambios sin guardar: guardar, no guardar (el próximo arranque reabre la sesión guardada, o una nueva) o cancelar, y tras un cierre brusco vuelven los cambios |
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
