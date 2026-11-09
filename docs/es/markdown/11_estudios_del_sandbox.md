# 11. Los estudios del sandbox

## 11.1 Cómo se ejecutan

Cada guion `sandbox/study_of_*.py` es una colección de **estudios** (análisis o figuras) que se listan y se
ejecutan desde la línea de órdenes. Un estudio es una función marcada con `@study` (las de
`@study(default=False)` solo se ejecutan si se nombran o con `--all`); un `setup()` opcional calcula una vez los
datos que comparten. El ejecutor está en `sandbox/runner.py`.

```bash
python sandbox/study_of_durations.py --list            # estudios disponibles (* = por defecto)
python sandbox/study_of_durations.py                   # los de por defecto
python sandbox/study_of_durations.py counts trigraph   # los nombrados, en ese orden
python sandbox/study_of_durations.py --all             # todos
python sandbox/study_of_durations.py trigraph --save   # además, guarda las figuras
python sandbox/study_of_durations.py --no-show         # sin ventanas ni sonido (por lotes)
python sandbox/study_of_precession.py --session sandbox/sessions/mi_sesion.cycles.json
```

| Opción | Efecto |
|---|---|
| `--save` | guarda las figuras en `sandbox/plots/` (y los sonidos en `sandbox/sounds/`) |
| `--no-show` | no abre ventanas ni reproduce sonido |
| `--session FICHERO` | usa el **modelo de ciclo** y los **parámetros de color** de una sesión guardada por el explorador; la sesión entera queda en `opts.session` |
| `--list`, `--all` | listar; ejecutar todos |

Cada estudio recibe `ctx` (lo que devolvió `setup`) y `opts` (`save`, `show`, `session`).
`python sandbox/runner.py --catalog` imprime en JSON los estudios de todos los guiones: lo usa el lanzador del
explorador (*File → Studies…*, capítulo 12).

En VS Code (o Code OSS), las tareas de `.vscode/tasks.json` ejecutan el guion de estudios que está abierto, con el
intérprete de `.venv`: `Ctrl+Mayús+B` pregunta qué estudios y opciones ejecutar (en blanco, los de por defecto), y
*Terminal → Run Task…* ofrece además listar los estudios y una ejecución por lotes que guarda todas las figuras.

### Con una sesión

`common.apply_session(datos, módulo)` pone los parámetros de la sesión en `common` (`BASES`, `SCALES`,
`TETRAHEDRON_COLORS`, `MODEL`, `SESSION`) y también en el guion en ejecución, que los importó por nombre;
`compute_levels` toma los valores vigentes en el momento de la llamada. `study_of_precession` usa
`common.MODEL` si lo hay, y si no el preset de su constante `PRESET`. Una sesión que no lo es se rechaza con un
error. El lanzador del explorador pasa por defecto su propia sesión (casilla *With the explorer's session*).

## 11.2 Los guiones y sus estudios

(* = por defecto)

### `study_of_division.py`: la propia división

| Estudio | Qué hace |
|---|---|
| `checks`* | comprueba duraciones, inicios y las conversiones entre formas de dirección en cada profundidad |
| `level_table` | imprime los 64 subciclos de profundidad 3: índice, dirección, fracción en base 4, duración, inicio |
| `comparison_rings`* | anillos de las cuatro edades y de sus subdivisiones |
| `identical_rings` | anillos de profundidad 2 y 3 con arcos que unen los de igual duración |
| `circle_diagram` | círculos anidados: cada subciclo, un círculo alrededor del de su padre |

### `study_of_durations.py`: duraciones

| Estudio | Qué hace |
|---|---|
| `trigraph`* | dónde y cuántos subciclos de cada duración, por profundidad |
| `sorted_durations` | duraciones ordenadas, en barras |
| `counts` | número de subciclos por duración, con sus direcciones |
| `spaced_bars` | dónde caen en el tiempo los de cada duración |
| `equality_test` | cociente de duraciones de cada par, como mapa de color |
| `consecutive_distances` | distancias entre subciclos consecutivos de igual duración |
| `return_plots` | mapas de retorno de la sucesión de duraciones (log-log) |
| `autocorrelations` | autocorrelación de las duraciones, ordenadas por el índice de dígitos invertidos |
| `duration_bars` | todos los subciclos de cada profundidad como cuadrados de lado su duración |
| `unique_across_depths` | comprueba que subciclos de profundidades distintas nunca comparten duración |
| `equal_duration_groups` | grupos de igual duración a profundidad 3 y las reordenaciones de una dirección |

### `study_of_compositions.py`: composiciones

| Estudio | Qué hace |
|---|---|
| `multilevel_trigraph`* | subciclos de profundidad 1 a 4 agrupados por duración: lugar, líneas de tiempo, recuentos |
| `duration_equivalent_compositions` | direcciones, duraciones, inicios y colores de profundidad 3 por clase |

### `study_of_fill_partitions.py`: particiones de un intervalo

| Estudio | Qué hace |
|---|---|
| `partition_sectors`* | llena las últimas 1000 unidades con subciclos y los dibuja frente a las ventanas |
| `partition_listing` | imprime los subciclos de la partición con inicio y duración |
| `regular_partition` | para cada inicio de ventana del ciclo, el subciclo encontrado allí |

### `study_of_colors.py`: coloreados

| Estudio | Qué hace |
|---|---|
| `level_bars`* | líneas de tiempo coloreadas de todas las profundidades |
| `unique_colors` | comprueba, por profundidad y coloreado, que todos los colores son distintos |
| `rgb_scatter_3d`, `rgb_lines_3d` | colores como puntos o camino en el cubo RGB |
| `cmyk_scatter_3d` | componentes CMY como puntos 3D, coloreados con `lrgb` |
| `cmyk_vs_time`, `rgb_vs_time`, `hsv_vs_time`, `hls_vs_time` (y `_vs_index`) | componentes frente a tiempo o índice, una figura por profundidad |

### `study_of_measures.py`: las medidas

| Estudio | Qué hace |
|---|---|
| `quality_grid`* | pureza frente a dharma, un panel por profundidad |
| `quality_by_age`, `quality_by_subage` | lo mismo en la profundidad mayor, un panel por edad o por subedad |
| `purity_vs_dharma`, `quality_scatter_3d`, `dharma_purity_lines` | en una figura, en 3D con el tiempo, como línea en orden temporal |
| `dharma_vs_time`, `dharma_vs_index`, `purity_vs_time`, `purity_vs_index` | frente a tiempo o índice |
| `measures_over_time`* | las nueve medidas de `measure.MEASURES` frente a los años del modelo, a profundidad 4 |
| `measure_correlations`* | correlaciones de rango (Spearman) entre las medidas a profundidades 2 a 6: cuáles aportan información propia (2.4) |

Los estudios del principio usan las bases de la versión original (pesos de pureza iguales, base 1); los dos
últimos, las del explorador (`common.BASES`, o las de una sesión) y su modelo (o el modelo por defecto).

### `study_of_multifractal.py`: el espectro multifractal

| Estudio | Qué hace |
|---|---|
| `key_numbers`* | los extremos, el exponente típico y las dimensiones de información y de correlación de las dos medidas, y su dualidad |
| `spectra`* | la figura de 1.9: $f(\alpha)$ exacto y estimado a profundidades 10, 40 y 160 |

### `study_of_dynamics.py`: la evolución en el tiempo

Las duraciones (profundidad 9) y todas las medidas (profundidad 8, con el modelo de la sesión o el por defecto), en el
orden de los índices y en $2^{18}$ instantes repartidos en años (capítulo 16).

| Estudio | Qué hace |
|---|---|
| `exact_numbers`* | la aplicación de ampliación (entropía, Lyapunov), $h(q)$ exacto de las duraciones, la aspereza del dharma por base |
| `return_maps`* | el mapa de retorno de las duraciones por acarreos, y los pasos del dharma, exactos frente a vistos |
| `exponents`* | DFA, R/S, funciones de estructura, Higuchi, β, entropía de permutación y complejidad de cada serie, en índice y en tiempo, y de las sustitutas |
| `fluctuations`* | el MF-DFA de las duraciones frente a $h(q)$ exacto y a las sustitutas |
| `spectra`* | el periodograma de las duraciones frente al producto de Riesz; los espectros de las medidas |
| `complexity_plane`* | el plano complejidad–entropía |
| `recurrences`* | diagramas de recurrencia y su cuantificación a profundidad 5; la simetría al invertir el tiempo |
| `return_times`* | los tiempos entre los inicios de los Kali de los niveles 2 a 4, en subciclos y en años |
| `embedding`* | la dimensión de correlación en inmersiones de 1 a 6 dimensiones: el dharma con bases 2, 3, 8 y 16 frente a lo exacto y a la serie desordenada, y todas las medidas |
| `change_points`* | los quince primeros puntos de cambio de cada medida (índice, tiempo, dígitos permutados) y el nivel de la frontera en que caen |
| `digit_null`* | los estimadores de cada medida con los dígitos de las direcciones en otro orden |
| `roughness_by_base` | la aspereza del dharma para bases de 1,25 a 4, frente a $\log_4 b$ |

### `study_of_permutations.py`: permutaciones

| Estudio | Qué hace |
|---|---|
| `timeline_permutations`* | líneas de tiempo del nivel a medida que se permutan las posiciones, potencia tras potencia |
| `power_matrices` | matrices de las potencias del desplazamiento cíclico |
| `all_matrices` | matrices de todos los elementos del grupo simétrico |

### `study_of_precession.py`: los yugas y la precesión

Usa las tablas de `sandbox/data/` (capítulo 6) y el modelo de ciclo (constante `PRESET`, o el de una sesión).

| Estudio | Qué hace |
|---|---|
| `yuga_epochs`* | imprime las fronteras y las duraciones de los yugas, absolutas y relativas |
| `zodiac_now`* | zodiaco con los planetas en la fecha actual |
| `precession` | ejes equinoccial y solsticial frente al zodiaco sidéreo, hoy |
| `satya` | zodiaco al inicio del Satya, con las dos tablas (`epsilon` 10⁻⁶ y 10⁻⁹) |
| `sub_kali` | zodiacos en las fronteras de las subdivisiones del Kali, con las dos tablas |
| `subcycle_charts` | zodiacos al inicio de los subciclos de profundidad `DEPTH` que empiezan por `PREFIX` |
| `current_subcycle` | el subciclo que contiene hoy a profundidades 1 a 5, con cada mapa de tiempo |
| `precession_rate` | tasa de precesión a lo largo del ciclo, con la media de cada yuga |
| `criteria_by_depth` | desviación de las cuotas de tiempo por profundidad, dividiendo el arco |
| `best_fit` | ancla (y arco) que mejor cumplen ambos criterios, con los barridos |

### `study_of_events.py`: acontecimientos planetarios y significación

Usa las tablas de la efeméride y el modelo de ciclo (o el de una sesión); los catálogos se guardan en
`sandbox/data/events/` (capítulo 15).

| Estudio | Qué hace |
|---|---|
| `event_catalog`* | calcula (o carga) las conjunciones de Júpiter–Saturno, Urano–Neptuno y Neptuno–Plutón, y los cambios de trígono |
| `surya_siddhanta`* | H1: los planetas en 0° de Aries en las fronteras de los yugas, con y sin el ancla, en ambos zodiacos |
| `great_conjunctions`* | H2: distancia de las fronteras (profundidad 1 a 5) a las grandes conjunciones y a los cambios de trígono |
| `outer_conjunctions`* | H3: lo mismo con las conjunciones de los planetas exteriores |
| `mean_planets`* | H1m: los planetas medios del Sūrya Siddhānta en 0° de Aries (cinco fronteras, sin el ancla, Treta y Kali, Treta) y cuánto se alejan del cielo los movimientos medios del texto |
| `model_map` | todos los modelos (ancla × arco) frente a los acontecimientos, con el p global de la búsqueda |
| `summary`* | las 37 pruebas con la corrección de Holm; con `--save`, `summary.csv` |

### `study_of_sound.py`: sonido

Necesita el extra `sound`.

| Estudio | Qué hace |
|---|---|
| `fractal_tones`* | sucesión de los tonos de los subciclos de profundidad 3, cada uno con su cuota del total |
| `multilevel_wavelets` | síntesis por ondículas de las profundidades 1 a 3 a la vez (lenta) |
| `wavelets_v01` | profundidad 3, cada subciclo un tono de 8 parciales ponderados por el color |
| `wavelets_v02_scalogram` | profundidad 4 (cada subciclo, un acorde de sus dígitos) y su escalograma (mucha memoria) |

## 11.3 `common.py`

Rutas (`SANDBOX_DIR`, `PLOTS_DIR`, `DATA_DIR`, `SOUNDS_DIR`), parámetros por defecto (`BASES`, `SCALES`,
`TETRAHEDRON_COLORS`), `MODEL` y `SESSION` (de una sesión), `compute_levels(profundidad_máxima)`,
`save_figure`, `fig_data` (tamaño de papel para `format_plot`) y `apply_session`.
