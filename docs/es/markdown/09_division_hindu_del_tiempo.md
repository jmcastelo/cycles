# 9. La división hindú del tiempo, la precesión y los contrastes astronómicos

*Revisión del documento homónimo de `efemerides_precesion_tiempo`, actualizada con el modelo de ciclo. Se
distinguen en todo momento **lo canónico**, **lo calculado** y **lo que no puede concluirse**.*

## 9.1 La estructura aritmética

### Lo canónico

- **1 año divino = 360 años humanos.**
- Un **Mahāyuga** (Caturyuga, el ciclo de cuatro yugas) dura **12 000 años divinos = 4 320 000 años humanos**.
- Sus cuatro yugas guardan la proporción **4 : 3 : 2 : 1**: periodos «puros» de 4000 (Kṛta o Satya), 3000
  (Tretā), 2000 (Dvāpara) y 1000 (Kali) años divinos; con los crepúsculos (*sandhyā* y *sandhyāṃśa*, una
  décima del periodo puro a cada lado), 4800, 3600, 2400 y 1200, que suman 12 000. Las proporciones 0,4 / 0,3 /
  0,2 / 0,1 se cumplen en ambos casos.
- Un **Manvantara** agrupa **71 Mahāyugas**; un **Kalpa**, **1000 Mahāyugas**.

*Terminología:* en este proyecto se ha llamado a veces «Manvantara» al ciclo de cuatro yugas; en el canon, ese
ciclo es el Mahāyuga.

### Lo que no es canónico

La **subdivisión indefinida 4 : 3 : 2 : 1** (cada yuga dividido a su vez del mismo modo, capítulo 1) es una
**extensión analógica de la tradición esotérica occidental (Guénon, Hani)**, no una división atestiguada en los
textos. Es el objeto de estudio del proyecto, no una afirmación sobre las fuentes.

## 9.2 ¿Es fractal?

En sentido estricto, **no**: el intervalo se divide en piezas cuyas razones de semejanza suman 1, y la dimensión
de similitud $s$ de la **ecuación de Moran**, $\sum_i r_i^{\,s} = 1$, es exactamente **1**: la estructura rellena el
intervalo. Aparecen fractales al retener solo algunas piezas en cada nivel, o al usar una medida distinta de la
longitud:

| Piezas retenidas en cada nivel | Dimensión $s$ |
|---|---:|
| las cuatro | 1,0000 |
| sin el Kali (0,4; 0,3; 0,2) | 0,9099 |
| Satya, Tretā y Kali | 0,8165 |
| Tretā y Dvāpara | 0,4963 |
| Satya y Kali | 0,4620 |

Los coloreados del capítulo 2 son otro ejemplo: el del tetraedro llena un tetraedro de Sierpinski, de dimensión
2 en el espacio de color.

## 9.3 La relación con la precesión

La observación de partida: el ciclo de cuatro yugas equivale a **2,5 vueltas de precesión**, con 1, ¾, ½ y ¼ de
vuelta por yuga (exactamente 4 : 3 : 2 : 1; capítulo 8).

- **Con precesión lineal encaja exactamente**: a 50,29″/año, 2,5 vueltas son 64 426,3 años; la cifra de 64 430
  años equivale a 2,5 × 25 772 (el preset de tasa constante).
- **Con precesión de largo plazo**, dividir el arco da cuotas de tiempo de 0,4039, 0,2915, 0,2040 y 0,1006.

**Cadena del modelo por defecto** (Kali a medianoche en Ujjain, 17 feb 3102 a. C., 18:57 UT):

| Frontera | Año | Duración del yuga (años) | Cuota | Ideal |
|---|---:|---:|---:|---:|
| inicio del Satya | −61 146,5 | 26 065,1 | 0,4039 | 0,4 |
| inicio del Tretā | −35 081,4 | 18 813,2 | 0,2915 | 0,3 |
| inicio del Dvāpara | −16 268,2 | 13 167,4 | 0,2040 | 0,2 |
| inicio del Kali | −3 100,8 | 6 494,4 | 0,1006 | 0,1 |
| fin del Kali | 3 393,6 | — | — | — |

Duración total: 64 540,1 años; mayor desvío de las cuotas, 0,0085. Variando el ancla con el arco fijo, ningún
ancla deja las cuotas dentro de 0,001 (la mejor ronda 0,002); el periodo con que sube y baja el acuerdo, unos
20 000 años, viene de la variación de la tasa (capítulo 8). **Conclusión: con precesión no lineal, 4:3:2:1 puede
cumplirse en ángulo, pero no exactamente en tiempo; la discrepancia es menor de 0,01.**

## 9.4 El artículo de Abhyankar (1993)

K. D. Abhyankar, *Bulletin of the Astronomical Society of India* 21, 475–479 (1993), sobre dos sellos de
Mohenjo-daro (copia en `sandbox/docs/papers/`).

**Afirmaciones:** el **sello 420** mostraría las cuatro estrellas cardinales hacia 3000 a. C. (Aldebarán,
δ Leonis, Antares y Fomalhaut); el **sello 430**, la configuración del **7 de febrero de 3104 a. C.** (la Luna y
cinco planetas dentro de 25°), que el autor propone como **origen** de la fecha tradicional del Kali; no afirma
que el Kali empezara en 3104 a. C. Es uno de los presets del modelo de ciclo.

**Comprobaciones:**

- Los días julianos del artículo son coherentes, salvo una errata (587 698,573 en el texto, 587 695,573 en la
  figura).
- Con PyEphem la Luna y los cinco planetas ocupan 25,2°, como dice el artículo; con la efeméride propia y la
  conversión UT → TDB se obtiene lo mismo (capítulo 7).
- En la fecha tradicional (18 feb 3102 a. C.) los planetas ocupan 41°, no 25°.
- Las estrellas alcanzan sus posiciones cardinales en años distintos (Aldebarán −3047, Antares −3049, δ Leonis
  −3149, Fomalhaut −2602): no son simultáneas.

**Cuánto significa la coincidencia:** en ±200 años hay 11 episodios con la Luna y cinco planetas dentro de 30°
(uno cada ~36 años), algunos más cerrados (16 de mayo de 3064 a. C., 14,3°). Con un menú de siete tipos de patrón
(conjunciones, oposiciones, trígonos…) hay un evento aproximadamente **cada 0,6 años**: encontrar *alguna*
configuración notable en una fecha dada no tiene valor probatorio. El panel *Sky comparison* del explorador
(capítulo 12) hace este tipo de contraste de forma sistemática, comparando con instantes al azar.

**Los planetas medios del propio texto** (capítulo 15.5): el Sūrya Siddhānta pone sus planetas medios en 0° de
Aries al inicio del Kali. Los planetas medios reales estaban entonces a 22° de media de ese punto (todos dentro de
64°): una reunión, pero no la conjunción exacta. Los movimientos medios del texto coinciden con el cielo hacia el
año 1172 y se alejan más de 20° en su propia época, de modo que la conjunción del Kali es un cálculo hacia atrás con
parámetros muy posteriores; y la otra conjunción que implican (al inicio del Treta, porque todas sus revoluciones
por Mahāyuga son pares) no está en el cielo real.

## 9.5 Pasajes puránicos sobre el cambio de yuga

Resumen de los pasajes (en IAST, del corpus GRETIL, con traducciones provisionales; el fichero
`pasajes_cambio_de_yuga.md` de la sesión original no está en el repositorio):

- **Retorno del Kṛta (fin del Kali):** *Bhāgavata* 12.2.24, *Viṣṇu* 4.24.102 y *Brahmāṇḍa* 2.74.225: el Kṛta
  volverá cuando la **Luna, el Sol, Tiṣya (Puṣya) y Júpiter** estén en un mismo signo. Es una condición del **fin**
  del Kali.
- **Los Siete Sabios (Saptarṣi) en Maghā:** *Bhāgavata* 12.2.22–37 y *Viṣṇu* 4.24.102–113 los sitúan en Maghā en
  tiempos de Parīkṣit y del inicio del Kali.
- **Tiṣya como nombre del cuarto yuga:** *Brahmāṇḍa* 1.7.21, *Liṅga* 1.39.5.

### La prueba de los Saptarṣi

Con la línea Kratu–Pulaha leída por el círculo horario, el nakṣatra resulta **Puṣya entre −3230 y −1930** y
**Maghā entre −850 y +470**: **no Maghā en −3101**. La lectura astronómica no apoya la fecha tradicional. Se
adoptó la lectura por nakṣatras (Puṣya entre 93°20′ y 106°40′ sidéreos con Lahiri); la elección de ayanāṃśa no
cambia los candidatos.

## 9.6 El criterio para el fin del Kali

Regla fijada en la sesión original: el **fin del Kali** es la **triple conjunción en Puṣya del Sol, la Luna y
Júpiter** más próxima al fin que dan los ángulos de precesión.

| Candidata | Comentario |
|---|---|
| **21 de agosto de 3402** (3402,61) | arco de 1,4°; la más próxima |
| 15 de agosto de 3378 | en Puṣya |
| 30 de agosto de 3355 | solo en el signo de Cáncer |

Con el modelo de ciclo, esta cadena es un ancla en el **punto final** (`anchor_point='end'`, 21 ago 3402):

| Frontera | Año |
|---|---:|
| inicio del Satya | −61 137,6 |
| inicio del Tretā | −35 072,5 |
| inicio del Dvāpara | −16 259,1 |
| inicio del Kali | −3 091,6 (3093 a. C.) |
| fin del Kali | 3 402,6 |

Las cuotas no cambian; el inicio del Kali queda unos 9 años después de la fecha tradicional.

**Qué no prueba:** los sucesos con Sol, Luna y Júpiter en Puṣya ocurren cada ~36 años (en Cáncer, cada ~8): que
uno caiga cerca de 3393 no es evidencia, y no tiene sentido buscar otras fechas para ajustar el resultado.

## 9.7 Qué se puede y qué no se puede concluir

| Afirmación | Estado |
|---|---|
| El ciclo de cuatro yugas son 2,5 vueltas de precesión con 1 : ¾ : ½ : ¼ | **aritmética**, exacta con tasa constante |
| Con precesión no lineal las cuotas de tiempo se desvían menos de 0,01 | **calculado** |
| El periodo de ~20 000 años del acuerdo viene de la tasa de precesión | **calculado** (capítulo 8) |
| La estructura 4:3:2:1 tiene dimensión de similitud 1 | **demostrado** |
| La subdivisión indefinida es canónica | **no** |
| El sello 430 muestra la configuración del 7 feb 3104 a. C. | **afirmación del autor**; esos eventos son frecuentes |
| Una triple conjunción en Puṣya cerca de 3393 es el fin del Kali | **lectura posible**, sin valor probatorio |
| Los Saptarṣi estaban en Maghā en 3102 a. C. | **no** con la lectura astronómica |
| Fechas de las fronteras anteriores al Kali | **sin criterio** independiente de la hipótesis del arco |

## 9.8 Estado de las continuaciones propuestas

1. ~~Corrida larga de la efeméride~~: hecha (tablas de ±70 000 años, capítulo 6); el cielo de cualquier frontera
   se ve en el explorador.
2. Incertidumbre numérica con variantes de la integración: **pendiente**.
3. Discrepancia de Marte con una tercera efeméride: **pendiente**.
4. ~~Fronteras a partir del fin del Kali~~: es un ancla en el punto final del modelo de ciclo.
