# 5. Calendarios, días julianos y escalas de tiempo

*Revisión del documento homónimo de `efemerides_precesion_tiempo`.*

Casi todos los errores de «no me coincide la posición» en fechas antiguas vienen de tres cosas: el calendario
con que se escribió la fecha, el significado de «año decimal» y la escala de tiempo (UT o TDB). El módulo
`cycles.functions.astro_dates` las resuelve con aritmética entera y solo la biblioteca estándar.

## 5.1 Numeración de los años

Se usa la **numeración astronómica**: el 1 a. C. es el año 0, el 2 a. C. el −1, y así sucesivamente; 3102 a. C.
es −3101. `bc_to_astronomical(3102)` da −3101. `parse_date` acepta «3102 BC-02-18», «3014 a. C.-02-07»,
«2026 d. C.-11-02» o «-3013-02-07» (un año negativo sin era se toma como astronómico). El modelo de ciclo usa
este mismo formato para la fecha del ancla (capítulo 8).

## 5.2 Calendarios

Ambos **prolépticos** (extendidos sin límite):

- **Juliano**: un bisiesto cada cuatro años, siempre.
- **Gregoriano**: omite tres bisiestos cada 400 años.

Con `calendar="auto"` (por defecto) se usa el juliano hasta el 4 de octubre de 1582 y el gregoriano desde el 15;
los días intermedios no existen y dan `ValueError`. Lejos de 1582 la fecha de calendario no tiene sentido
estacional: el juliano se desvía unos 0,0078 días por año de las estaciones. El inicio tradicional del Kali Yuga,
el **18 de febrero de 3102 a. C. juliano**, es el **23 de enero de 3102 a. C. gregoriano proléptico**, y su
medianoche es el **JD 588 465,5**. El día juliano es siempre exacto; la fecha es una etiqueta.

## 5.3 El día juliano

- Cuenta continua de días; el JD 0,0 es el mediodía del 1 de enero de 4713 a. C. juliano.
- El mediodía de un día civil tiene JD entero; la medianoche que lo empieza, JD − 0,5.
- Conversiones con aritmética entera, exactas incluso para días negativos (probadas en ±70 000 años y contra
  `datetime` en 5000 fechas gregorianas).
- J2000.0 = **JD 2 451 545,0** (2000-01-01 12:00).

## 5.4 El año decimal

```
año = 2000 + (JD − 2 451 545,0) / 365,25
```

Son **años julianos** de 365,25 días anclados en J2000.0: la unidad de la tasa de precesión y la variable de
las funciones de precesión, de los mapas de tiempo y del explorador. Un año decimal entero **no cae en el 1 de
enero**: en el calendario juliano, el año decimal Y,0 es siempre el **19 de diciembre a las 12:00 del año
anterior**; en el gregoriano el desfase varía con el tiempo. Ejemplos: 0,0 es el 19 dic 2 a. C. (juliano), JD
1 721 045,0; −2000,0 es el 19 dic 2002 a. C. Para una fecha de calendario se usa `date_to_year`; el 18 de
febrero de 3102 a. C. (juliano) es el año decimal −3100,834.

## 5.5 Escalas de tiempo

| Escala | Qué es |
|---|---|
| **UT** | tiempo universal, ligado a la rotación de la Tierra: el de los relojes civiles |
| **TT** | tiempo terrestre, uniforme |
| **TDB** | tiempo dinámico baricéntrico, la variable de las efemérides; difiere de TT en a lo sumo 1,7 ms |

**TT = UT + ΔT**, y TDB ≈ TT. Las efemérides y las coordenadas eclípticas trabajan en **TDB**; las fechas civiles
(textos, calendarios, el ancla de un modelo de ciclo) están en **UT**. El explorador trabaja en UT y convierte a
TDB al calcular el cielo (`time_scale="UT"`). ΔT crece hacia el pasado: unos 2 minutos hacia 1600, 2,9 horas en
el año 0 y unas **21,5 horas** hacia 3100 a. C.; un día de error mueve el Sol casi 1°.

## 5.6 El ΔT: `delta_t_seconds`

Expresiones polinómicas de **Espenak y Meeus** (NASA), por tramos entre −500 y 2050 y la parábola
−20 + 32·u² (u en siglos desde 1820) fuera de ellos, con un empalme entre 2050 y 2150. Valores de referencia:
63,9 s en 2000, 120,0 s en 1600, 10 584 s en el año 0, 77 440 s (21,5 h) en −3100. El salto máximo entre tramos
es de 0,25 s. Fuera de −1999 a 3000 avisa de que extrapola (el explorador silencia ese aviso).

Comparación con el ΔT de Swiss Ephemeris:

| Año | Espenak-Meeus (s) | Swiss (s) | Diferencia (s) |
|---:|---:|---:|---:|
| −3100 | 77 440,5 | 78 218,1 | −777,6 (13 min) |
| −2000 | 46 675,7 | 46 980,7 | −305,0 |
| −500 | 17 203,7 | 16 769,5 | +434,1 |
| 0 | 10 583,6 | 10 557,3 | +26,3 |
| 1000 | 1 574,2 | 1 463,6 | +110,6 |
| 2000 | 63,9 | 63,8 | 0,0 |
| 2026,84 | 75,6 | 68,8 | +6,8 |

- **Antes de −700, ΔT se extrapola.** Que dos parábolas coincidan a 13 minutos no mide la incertidumbre real,
  que puede ser de **horas** hacia 3100 a. C.
- **Más allá de unos milenios la parábola no tiene sentido físico** (para −61 146 da unos 147 días). A esas
  distancias, convertir tiempo civil no significa nada; las fronteras lejanas se tratan como TDB.

## 5.7 Convertir fechas

```python
from cycles.functions.astro_dates import parse_date, date_to_year, date_to_tdb_year

date_to_year(2026, 11, 2)                                          # 2026.835 (sin cambiar de escala)
date_to_year(*parse_date("3102 BC-02-18"), calendar="julian")      # -3100.8337
date_to_tdb_year(*parse_date("3102 BC-02-18"), calendar="julian")  # en TDB
```

- `date_to_year` no cambia de escala; `date_to_tdb_year` convierte antes de UT a TDB.
- Inversas: `year_to_date(year, calendar)` y `tdb_year_to_date(year, calendar)`.
- `format_date(-3101, 2, 18, 'julian')` da «18 feb 3102 a. C. (calendario juliano)»; el explorador muestra
  las fechas en inglés («17 Feb 3102 BC, 18:57 UT»), con `state.date_text` y `datetime_text`.
- `ut_to_tdb(jd)` y `tdb_to_ut(jd)` convierten días julianos; la ida y vuelta es exacta.

Caso comprobado (7 de febrero de 3104 a. C., 1 h 51 min UT): ΔT = 77 531 s; frente a PyEphem, las longitudes
trópicas de la efeméride propia difieren hasta 1,09° si se ignora la conversión y 0,04° o menos si se aplica
(capítulo 7).

## 5.8 La hora y los desfases horarios

- `day_with_time(día, hora, minuto, segundo)` da el día con fracción; `split_day` es la inversa.
- `date_time_to_julian_day(año, mes, día, hora, minuto, segundo, calendar, utc_offset_hours)` da el JD (UT) de
  una fecha y hora con un desfase opcional, **positivo hacia el este** (UT = hora − desfase). La hora solar
  local de un lugar tiene desfase = longitud este / 15.

```python
# medianoche del 18 feb 3102 a. C. en Ujjain (75,77° E): 17 feb, 18:57 UT
jd = date_time_to_julian_day(-3101, 2, 18, 0, 0, calendar="julian", utc_offset_hours=75.77 / 15)
```

Es exactamente como el modelo de ciclo interpreta su ancla: «fecha y hora locales en una longitud»
(capítulo 8). Por eso el explorador muestra el inicio del Kali el **17 de febrero, a las 18:57 UT**.

## 5.9 Qué escala usar en cada sitio

| Dato | Escala |
|---|---|
| fecha escrita en un texto, ancla de un modelo de ciclo | UT (o local, convertida a UT) |
| años de los mapas de tiempo, del explorador, de las fechas marcadas | UT |
| año para `geocentric_direction`, `ecliptic_coordinates_of_date`, `planet_positions` | TDB |
| `plot_zodiac_with_planets(year, ..., time_scale="UT")` | UT; convierte a TDB |
| fronteras lejanas del ciclo (−61 146, −35 081…) | se tratan como TDB |

## 5.10 Trampas habituales

1. **Olvidar la conversión UT → TDB** con fechas antiguas: ~1° en el Sol.
2. **Aplicarla dos veces** (`date_to_tdb_year` y además `time_scale="UT"`).
3. **Confundir el año decimal con el de calendario.**
4. **Calendario por defecto en fechas antiguas**: `auto` es juliano antes de 1582.
5. **Años de las tablas**: `years` en `build_ephemeris` se cuenta desde J2000.
