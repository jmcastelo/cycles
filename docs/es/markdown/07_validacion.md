# 7. Validación y comparación con otras fuentes

*Revisión del documento homónimo de `efemerides_precesion_tiempo`. Las comparaciones con Moshier, PyEphem y
Swiss Ephemeris se hicieron en la sesión original; las comprobaciones automáticas (7.6) están en `tests/`.*

## 7.1 Escalera de validaciones

| Intervalo | Fuente de referencia | Qué se comprobó |
|---|---|---|
| ±30 años | JPL DE421 | modelo, almacenamiento e interpolación (capítulo 6) |
| −100 a −2990 | Moshier (Swiss Ephemeris) | longitudes trópicas geométricas de ocho planetas (7.2) |
| 3104 a. C. | PyEphem (VSOP87) | la configuración del artículo de Abhyankar, con y sin UT → TDB (7.4) |
| 2026-11-03 | Swiss Ephemeris | posiciones aparentes y geométricas, y ayanāṃśa (7.5) |
| siempre | el propio código | consultas vectorizadas frente a escalares, posiciones frente al gráfico (7.6) |
| **más allá de −3000** | **ninguna** | **predicción del modelo** |

Las comparaciones de longitud usan la misma convención: posiciones **geométricas** referidas al **equinoccio
medio de la fecha** (con Swiss: `FLG_MOSEPH | FLG_TRUEPOS | FLG_NONUT | FLG_NOABERR | FLG_NOGDEFL`).

## 7.2 Tabla propia frente a Moshier

Diferencia (propia − Moshier) en segundos de arco, longitud trópica geométrica:

| Año | Sol | Mercurio | Venus | Marte | Júpiter | Saturno | Urano | Neptuno |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| −100 | +4,1 | +1,8 | +3,7 | −4,8 | +5,3 | +0,7 | +3,1 | −14,4 |
| −500 | −0,4 | +1,4 | +0,4 | −0,7 | +6,6 | +0,2 | +2,9 | −16,3 |
| −1000 | −6,2 | −4,7 | −3,3 | −3,5 | +8,1 | +1,5 | +3,8 | −20,0 |
| −1500 | +1,4 | −0,3 | +10,9 | +2,0 | +8,4 | −0,2 | +4,9 | −23,5 |
| −2000 | +5,3 | +4,9 | +5,7 | **−132,6** | +7,8 | −0,1 | +6,2 | −27,2 |
| −2500 | −5,1 | −1,7 | −2,1 | **−574,9** | +8,3 | +0,6 | +8,8 | −30,9 |
| −2900 | −1,5 | −4,2 | −3,5 | **−410,8** | +9,9 | −0,1 | +9,0 | −35,1 |
| −2990 | +4,1 | +2,4 | +8,4 | **−390,4** | +9,9 | +0,5 | +9,8 | −35,1 |

- Sol, Mercurio, Venus, Júpiter, Saturno y Urano coinciden a **10″ o menos** en todo el intervalo (parte es el
  efecto del baricentro Tierra-Luna y parte la precisión de Moshier).
- Neptuno deriva lentamente (−14″ a −35″); quizá una pequeña diferencia de masas o condiciones iniciales.
- **Marte** coincide a menos de 5″ hasta −1500 y de pronto difiere −133″ en −2000 y hasta −575″ en −2500. El
  salto brusco seguido de oscilación sugiere un artefacto de ajuste en una de las fuentes.

**La discrepancia de Marte sigue abierta.** A favor de que el problema esté en Moshier: la integración coincide
con DE421 para Marte a 20 km; los demás planetas coinciden hasta el final; Moshier es una serie truncada
ajustada a un intervalo. Los asteroides no la explican (haría falta un error de movimiento medio de ~2,4·10⁻⁷).
Para zanjarlo hace falta una tercera referencia (DE441 de JPL, o Swiss con sus ficheros completos).

## 7.3 ΔT

La comparación con Swiss y los límites de su extrapolación están en el capítulo 5.

## 7.4 La configuración del artículo de Abhyankar

7 de febrero de 3104 a. C., 1 h 51 min UT (juliano): JD(UT) = 587 724,577; JD(TDB) = 587 725,474; ΔT = 77 531 s.

| Cuerpo | PyEphem | Sin convertir | Diferencia | Con UT → TDB | Diferencia |
|---|---:|---:|---:|---:|---:|
| Sol | 294,52 | 293,64 | −0,88 | 294,52 | −0,00 |
| Mercurio | 278,25 | 278,61 | +0,36 | 278,23 | −0,02 |
| Venus | 267,73 | 266,64 | −1,09 | 267,73 | +0,00 |
| Marte | 277,93 | 277,25 | −0,68 | 277,94 | +0,01 |
| Júpiter | 260,18 | 260,02 | −0,16 | 260,22 | +0,04 |
| Saturno | 253,00 | 252,86 | −0,14 | 252,96 | −0,04 |

Con la conversión, todas las diferencias son de 0,04° o menos; sin ella llegan a 1,09°. El acuerdo prueba
coherencia con VSOP87 en esa época, no que ambas sean exactas (y PyEphem usa su propio ΔT).

## 7.5 Las posiciones de un día actual

2026-11-03 11:51:48 UT; año TDB 2026,839 14; A = 24,2278°. Diferencias en segundos de arco:

| Cuerpo | propia − Swiss (geométricas) | Swiss aparente − geométrica |
|---|---:|---:|
| Sol | 6,2 | −12,4 |
| Mercurio | 8,6 | 26,4 |
| Venus | 17,7 | 10,8 |
| Marte | −0,8 | −6,3 |
| Júpiter | −0,3 | −4,8 |
| Saturno | −0,4 | 19,0 |
| Urano | −0,3 | 22,7 |
| Neptuno | 0,2 | 20,4 |

El ayanāṃśa de Lahiri del modelo es 24,2278° y el de Swiss 24,2320° (15″). Aberración, nutación y tiempo de luz
suman de 5″ a 26″: no explican discrepancias de grados.

### Ayanāṃśa según el criterio (Swiss Ephemeris, ese instante)

| Criterio | Ayanāṃśa | Diferencia con Lahiri |
|---|---:|---:|
| Lahiri (Chitrapaksha) | 24,2320° | 0 |
| Lahiri 1940 | 24,2173° | −0,015° |
| Chitrā verdadera | 24,2105° | −0,022° |
| Krishnamurti (KP) | 24,1352° | −0,097° |
| Yukteshwar | 22,8537° | −1,378° |
| Raman | 22,7857° | −1,446° |
| Fagan-Bradley | 25,1152° | +0,883° |
| Sūryasiddhānta | 21,2700° | −2,962° |
| Revatī verdadera | 20,4253° | −3,807° |
| J2000 (solo precesión) | 0,3749° | −23,857° |

### Cómo averiguar qué criterio usa una web

Para cada cuerpo, (longitud de la web − longitud trópica geométrica propia), módulo 360°. Si es **la misma
constante en todos**, es el negativo del ayanāṃśa de la web: ≈ 0° trópico; ≈ −24,23° Lahiri; ≈ −25,12°
Fagan-Bradley; ≈ −0,375° equinoccio fijo J2000… Si no es constante, la causa es otra: la hora (muchas efemérides
dan 0 h UT; la Luna recorre 0,5° por hora), la escala de tiempo, posiciones heliocéntricas, el marco J2000, los
nodos lunares medios o verdaderos. JPL Horizons es una buena referencia porque declara cuerpo, observador,
escala y marco.

## 7.6 Comprobaciones automáticas

El conjunto de pruebas (capítulo 13) incluye, con las tablas de efemérides presentes (marca `ephemeris`):

- `planet_positions` da las mismas longitudes sidéreas que el gráfico `plot_zodiac_with_planets`;
- `planet_positions_many` coincide con la versión instante a instante (a 10⁻⁹°) en fechas de −3101 a 2026 y da
  NaN fuera de las tablas;
- el disco del gráfico del cielo no cambia de tamaño al girar los ejes, y tiene la leyenda de los glifos.

## 7.7 Qué queda sin verificar

1. Marte antes de −2000: falta una tercera referencia.
2. Todo lo anterior a −3000: sin referencia independiente.
3. ΔT antes de −700: extrapolación incierta en horas.
4. La Luna: no se calcula.
