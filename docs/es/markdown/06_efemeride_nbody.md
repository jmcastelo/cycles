# 6. Efeméride propia por integración numérica de N cuerpos

*Revisión del documento homónimo de `efemerides_precesion_tiempo`, con las tablas actuales y las consultas
vectorizadas.*

## 6.1 Para qué

Las efemérides de referencia cubren intervalos limitados: las series de Moshier unos ±3000 años; DE421, de 1900
a 2050 aproximadamente. Un ciclo de 2,5 vueltas de precesión dura unos 64 500 años (de −61 146 a 3394 en el
modelo por defecto), así que se construyó una efeméride **propia**: se integra el sistema solar una vez, se guarda
la solución en tablas compactas y se consultan para cualquier instante. Es `cycles.functions.nbody_ephemeris`:
NumPy para consultar, REBOUND y REBOUNDx (extra `astro`) para construir.

## 6.2 Modelo físico

- **Cuerpos (11):** Sol, Mercurio, Venus, Tierra, Luna, Marte, Júpiter, Saturno, Urano, Neptuno y Plutón. Tierra
  y Luna se integran por separado (tratar su baricentro como una masa puntual lo haría derivar unos 117 km por
  año).
- **Condiciones iniciales:** posiciones, velocidades y masas de **JPL DE421** (Folkner, Williams y Boggs 2009) en
  J2000.0, baricéntricas en el ICRF, incrustadas en el código.
- **Fuerzas:** gravitación newtoniana más **relatividad general de primer orden post-newtoniano** (`gr_full` de
  REBOUNDx).
- **Integrador IAS15** (Rein y Spiegel 2015), adaptativo de orden 15; con la tolerancia por defecto
  (`epsilon = 1e-6`) da pasos de unos 3,4 días.

## 6.3 Lo que no se modela

| Efecto omitido | Consecuencia |
|---|---|
| Asteroides | se supone pequeño frente a otras incertidumbres; no cuantificado |
| Achatamiento del Sol | no se modela |
| Pérdida de masa del Sol | ~10⁻¹³ por año; estimación de orden de magnitud: unos 0,2° en la longitud media de la Tierra tras 61 000 años |
| Achatamiento y mareas de la Tierra | no se modelan |

**La Luna no es fiable** más allá de unas décadas (falta la aceleración de marea), así que la tabla **no la
guarda**: solo el baricentro Tierra-Luna (EMB), a hasta 4700 km de la Tierra. Mirar desde el EMB introduce unos
6,5″ divididos por la distancia al planeta en UA. Las posiciones son **geométricas**.

## 6.4 Almacenamiento

Cada cuerpo se muestrea una vez cada `stride` pasos del integrador (Mercurio 1, Venus 2, EMB 3, Marte 5, Júpiter
24, Saturno 48, Urano 120, Neptuno y Plutón 240): unas 25–65 muestras por órbita. Por cuerpo hay dos ficheros:

- `<cuerpo>.t.f64`: tiempos (días a lo largo de la dirección de integración);
- `<cuerpo>.f64`: filas de 9 dobles: posición (UA), velocidad (UA/día) y aceleración (UA/día²), baricéntricas
  en el ICRF.

El **Sol no se guarda**: se recupera de los demás, porque el baricentro del sistema está en el origen. Las
consultas usan **interpolación de Hermite quíntica** con posición, velocidad y aceleración en los extremos de
cada intervalo. `load_ephemeris` abre las tablas con proyección en memoria (solo lectura); el estado del
integrador se guarda como punto de control (`state.bin`), así que una corrida puede interrumpirse, reanudarse o
ampliarse, con un resultado idéntico bit a bit. `meta.json` guarda dirección, tolerancia, strides, pasos hechos,
JD de partida y descripción del modelo.

## 6.5 Las tablas del proyecto

| Tabla | Contenido | Disco |
|---|---|---|
| `sandbox/data/tabla70k70k` | `back/` y `forward/`, unos 70 000 años en cada dirección desde J2000, `epsilon = 1e-6` | ~2,4 GB |
| `sandbox/data/tabla70k70kp` | lo mismo con `epsilon = 1e-9` (más precisa y lenta) | ~6,4 GB |

```bash
python -m cycles.functions.nbody_ephemeris build sandbox/data/tabla70k70k 70000 \
    --direction both --forward-years 70000 --workers 2
python -m cycles.functions.nbody_ephemeris build sandbox/data/tabla70k70kp 70000 \
    --direction both --forward-years 70000 --workers 2 --epsilon 1e-9
```

`years` se cuenta **desde J2000**: 70 000 años hacia atrás llegan al año −68 000, de sobra para el inicio del
Satya del modelo por defecto (−61 146). En el lapso del estudio, las dos tolerancias coinciden a una décima de
segundo de arco: la incertidumbre mayor viene de lo que el modelo omite, no del integrador. Coste: unos 0,10–
0,12 s por año simulado en un núcleo; `--workers 2` integra las dos direcciones a la vez.

El explorador busca la tabla en `$CYCLES_EPHEMERIS`, luego en la última carpeta elegida con *Ephemeris…* y, por
último, en `sandbox/data/tabla70k70k` (`sky.ephemeris_parts` reconoce una carpeta con `back/` y `forward/`, o una
sola tabla con `meta.json`).

## 6.6 Consultas

```python
import cycles.functions.nbody_ephemeris as nbe

eph = nbe.load_ephemeris("sandbox/data/tabla70k70k/back")
jd = nbe.year_to_jd(-3100.83)                           # JD = 2451545 + (año − 2000) × 365,25 (TDB)
pos, vel = nbe.body_state(eph, "jupiter", jd)           # baricéntrico, ICRF (UA, UA/día)
u = nbe.geocentric_direction(eph, "jupiter", jd)        # vector unitario desde el EMB
```

### Consultas vectorizadas

Para muchos instantes a la vez (el panel *Sky comparison* calcula el cielo de niveles enteros):

- `body_states(eph, cuerpo, jd)`: con `jd` de forma (N,), posiciones y velocidades (N, 3). Busca los
  intervalos con `searchsorted` y evalúa el polinomio de Hermite con matrices; `body_state` (un instante) es
  ahora un envoltorio suyo, así que hay una sola implementación.
- `geocentric_directions(eph, cuerpos, jd)`: direcciones unitarias (N, 3) de varios cuerpos, interpolando el
  origen una sola vez.
- `equinoctial_precession.planet_positions_many(años_tdb, tablas, cuerpos)`: longitudes sidérea y trópica y
  latitud (N,) de cada cuerpo, repartiendo los instantes entre la tabla hacia atrás y la hacia delante; fuera
  de ambas, NaN.

Rendimiento medido: 16 384 instantes con nueve cuerpos, **0,32 s** frente a unos 13 s instante a instante (unas
40 veces más rápido), con una diferencia máxima con la versión escalar de 2·10⁻¹³°. `planet_positions(año,
tablas, cuerpos)` da el mismo resultado para un solo instante, sin dibujar (lo usa el gráfico del cielo).

### Del vector a la longitud

```python
from cycles.plotting.equinoctial_precession import ecliptic_coordinates_of_date
lon, lat = ecliptic_coordinates_of_date(u, year, sidereal=True)
```

## 6.7 Exactitud medida

Frente a DE421, ±30 años (el peor de 300 consultas por dirección):

| Cuerpo | Error máximo |
|---|---|
| Mercurio | 37 km (0,16″ vistos desde el Sol) |
| Venus | 1 km |
| Baricentro Tierra-Luna | 3 km |
| Marte | 20 km |
| Júpiter | 9 km |
| Saturno | 6 km |

Pasar de `epsilon` 10⁻⁹ a 10⁻⁶ cambia el resultado en menos de 0,001 km por siglo y acelera 1,65 veces. Las
comparaciones con otras fuentes en épocas lejanas están en el capítulo 7. **Más allá del año −3000 no hay
referencia independiente**: lo que da la integración es una predicción del modelo.

## 6.8 Intentos de acelerar la construcción

| Intento | Resultado |
|---|---|
| Relajar `epsilon` | 1,65× sin pérdida apreciable (adoptado) |
| Hermite quíntico sin guardar el Sol | menos disco y consultas rápidas (adoptado) |
| Paralelizar una integración | imposible: cada paso necesita el anterior |
| Parareal (paralelo en el tiempo) | no converge antes que la serie: los errores de fase de Mercurio se amplifican |
| WHFast con relatividad | no fue más rápido |
| Integraciones independientes a la vez (`build_many`) | funciona (ambas direcciones, variantes) |

## 6.9 Incertidumbre: lo propuesto y no hecho

Integrar **variantes** (tolerancias, condiciones iniciales perturbadas) con `build_many` daría una medida de la
sensibilidad; no se ha hecho. El sistema solar es caótico, pero con un tiempo de Lyapunov de millones de años: a
60 000 años los errores de modelo pesan más que el caos.

## 6.10 Límites

1. Sin Luna; solo el baricentro Tierra-Luna. 2. Posiciones geométricas. 3. Sin asteroides, achatamiento ni
pérdida de masa solar, ni mareas. 4. Sin referencia independiente antes de −3000. 5. Discrepancia abierta de
Marte con Moshier desde −2000 (capítulo 7).
