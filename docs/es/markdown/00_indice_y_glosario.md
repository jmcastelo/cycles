# Ciclos: documentación del proyecto

Versión del programa documentada: **0.2.0** (ver `CHANGELOG.md` en la raíz del proyecto y el capítulo 10, «Versiones»).

Este conjunto de documentos describe con detalle el proyecto **cycles**: el análisis matemático de un ciclo
dividido fractalmente en cuatro edades en razón 4 : 3 : 2 : 1 (Satya, Treta, Dvapara y Kali), su colocación en la
historia mediante la precesión de los equinoccios, el cielo calculado con una efeméride propia, el código y el
explorador gráfico. Incorpora, revisados y actualizados, los documentos de `efemerides_precesion_tiempo`
(capítulos 4 a 7 y 9).

## Cómo están organizados

| Documento | Contenido |
|---|---|
| **I. La estructura** | |
| [`01_division_fractal.md`](01_division_fractal.md) | la regla 4:3:2:1, direcciones e índices, duración e inicio, niveles, composiciones, la regla (1, 0, −2, 1) y las (*d* + 1)² duraciones |
| [`02_medidas_y_colores.md`](02_medidas_y_colores.md) | pesos por posición, dharma, pureza, medidas por nivel, los diez coloreados, el tetraedro de Sierpinski y los rangos de los parámetros |
| [`03_permutaciones.md`](03_permutaciones.md) | la acción de una permutación de las posiciones, su alcance, órbitas, puntos fijos y el lema de Burnside |
| **II. Astronomía y tiempo** | |
| [`04_precesion_y_ayanamsa.md`](04_precesion_y_ayanamsa.md) | precesión, zodiaco trópico y sidéreo, ayanāṃśa de Lahiri, modelos lineal y de largo plazo, la tasa variable, la inversa, el esquema |
| [`05_calendarios_y_escalas_de_tiempo.md`](05_calendarios_y_escalas_de_tiempo.md) | numeración astronómica, calendarios, día juliano, año decimal, UT / TT / TDB, ΔT, hora local |
| [`06_efemeride_nbody.md`](06_efemeride_nbody.md) | la efeméride por integración de N cuerpos: modelo, almacenamiento, tablas, consultas vectorizadas, exactitud |
| [`07_validacion.md`](07_validacion.md) | comparaciones con DE421, Moshier, PyEphem y Swiss Ephemeris; el caso de Marte; comprobaciones automáticas |
| [`08_modelo_de_ciclo.md`](08_modelo_de_ciclo.md) | mapas de tiempo, el modelo de ciclo y sus presets, el arco en vueltas, los dos criterios, el desajuste, el ajuste y el paisaje |
| [`09_division_hindu_del_tiempo.md`](09_division_hindu_del_tiempo.md) | lo canónico y lo que no, la relación con la precesión, Abhyankar (1993), los pasajes puránicos, el fin del Kali |
| **III. El software** | |
| [`10_arquitectura_y_modulos.md`](10_arquitectura_y_modulos.md) | organización del código, instalación, guía de los módulos de cálculo, figuras y explorador, y versiones |
| [`11_estudios_del_sandbox.md`](11_estudios_del_sandbox.md) | el ejecutor de estudios, sus opciones (`--session`) y cada estudio |
| [`12_aplicacion_grafica.md`](12_aplicacion_grafica.md) | el explorador: navegador, paneles, modelo, colores, gráficos, sesiones, dosier, disposición, atajos |
| [`13_pruebas.md`](13_pruebas.md) | cómo se ejecutan las pruebas y qué comprueban |
| [`14_resultados_y_preguntas_abiertas.md`](14_resultados_y_preguntas_abiertas.md) | resultados obtenidos y trabajo pendiente |

Estos documentos están en `docs/es/` del repositorio: los capítulos en `markdown/`, con sus figuras en
`markdown/figuras/`; la versión LaTeX, que reúne todos los capítulos en un solo documento, se genera en `tex/` con
`md_a_tex.py` (el `.tex` y el PDF no se versionan; el PDF se adjunta a cada versión publicada); y los guiones que
regeneran las figuras, en `generar_figuras/`.

## Resultados principales

1. **Hay (*d* + 1)² duraciones distintas a profundidad *d***, y las composiciones de igual duración difieren en
   múltiplos de (1, 0, −2, 1), porque 0,4 · 0,1 = 0,2².
2. **Las permutaciones de las posiciones conservan las duraciones**; las órbitas de todo el grupo simétrico son las
   composiciones (lema de Burnside).
3. **Con 2,5 vueltas de precesión**, el Satya es una vuelta y los yugas ocupan 1, ¾, ½ y ¼ de vuelta. Con la tasa
   de precesión variable, sus cuotas de tiempo son 0,4039, 0,2915, 0,2040 y 0,1006, y los dos criterios (4:3:2:1 del
   arco y de los años) ponen las fronteras de los yugas a hasta unos 300 años.
4. **El ancla tradicional del Kali** (3102 a. C.) está cerca de una de las peores colocaciones para que ambos
   criterios coincidan; el acuerdo sube y baja cada unos 20 000 años, la variación de 41 000 años de la tasa
   rectificada.
5. **El cielo en los inicios de los subciclos** no se parece al de la selección más que el de instantes al azar: los
   parecidos vienen de los periodos de los planetas.
6. **La efeméride propia** cubre ±70 000 años; coincide con DE421 a decenas de km y con Moshier a 10″ o menos hasta
   −3000, salvo Marte (discrepancia abierta). Más allá de −3000 no hay referencia independiente.

## Convenciones

- Código e interfaz en inglés; estos documentos en español, con los nombres que se ven en pantalla.
- Años en **numeración astronómica** (1 a. C. = 0; 3102 a. C. = −3101), decimales permitidos (años julianos de
  J2000).
- Edades numeradas 0 a 3: Satya, Treta, Dvapara, Kali.
- Tiempo normalizado en [0, 1); los años de los modelos de ciclo están en UT.
- Decimales con coma y miles con espacio en el texto; con punto en el código.

## Glosario

**Edad / yuga.** Cada una de las cuatro partes de un ciclo: Satya (o Krita), Treta, Dvapara y Kali, con 0,4, 0,3,
0,2 y 0,1 de su longitud; también Oro, Plata, Bronce y Hierro.

**Subciclo.** Una parte de una parte… del ciclo, a cualquier profundidad.

**Dirección (`lcoords`).** Los dígitos (0–3) que nombran la edad elegida en cada nivel, de fuera hacia dentro.

**Índice (`tcoord`).** La dirección leída en base 4: la posición del subciclo en el tiempo entre los de su
profundidad.

**Nivel.** Todos los 4^d subciclos de una profundidad (`Level`).

**Composición.** Cuántos dígitos de cada edad tiene una dirección, (n₀, n₁, n₂, n₃); determina la duración.

**Clase de igual duración.** Las composiciones (y sus subciclos) con la misma duración: difieren en múltiplos de
(1, 0, −2, 1).

**Dharma.** Media ponderada de las virtudes de las edades de una dirección (Satya 1, Treta ¾, Dvapara ½, Kali ¼).

**Pureza.** Cuota ponderada de la edad más presente menos la de la menos presente.

**Coloreado.** Regla que da un color a cada subciclo a partir de su dirección (las edades como tintas: cian,
magenta, amarillo y negro).

**σ, órbita.** Una permutación de las posiciones de los dígitos; la órbita de un subciclo es el conjunto de lugares
por los que lo llevan las potencias de σ.

**Mapa de tiempo.** La correspondencia entre el tiempo normalizado y los años (`TimeMap`).

**Modelo de ciclo.** Ancla, escala, división y precesión que colocan el ciclo en la historia (`CycleModel`).

**Ancla.** El instante (fecha y hora, o ayanāṃśa) al que se fija un punto del ciclo (por defecto, el inicio del
Kali).

**Criterios de división.** 4:3:2:1 del arco de precesión o de los años; con tasa variable no coinciden.

**Desajuste.** Cuánto se apartan de 0,4, 0,3, 0,2 y 0,1 las cuotas de tiempo al dividir el arco.

**Ayanāṃśa.** Ángulo entre el equinoccio de la fecha y el origen del zodiaco sidéreo; positivo cuando el punto
vernal ha retrocedido; sin reducir módulo 360°.

**Zodiaco trópico / sidéreo.** El trópico se mide desde el equinoccio de la fecha; el sidéreo, fijo respecto a las
estrellas.

**Precesión de los equinoccios.** Giro lento del eje terrestre (lunisolar) más el movimiento del plano de la
eclíptica (planetaria): unos 50″ por año.

**Geométrico / aparente.** La posición geométrica es la dirección real en el instante; la aparente añade tiempo
de luz, aberración y nutación.

**J2000.0.** 2000-01-01 12:00 TT, día juliano 2 451 545,0.

**Día juliano (JD).** Cuenta continua de días desde el mediodía del 1 de enero de 4713 a. C. juliano.

**UT, TT, TDB, ΔT.** Tiempo universal (rotación terrestre), tiempo terrestre (uniforme), tiempo dinámico
baricéntrico (el de las efemérides); ΔT = TT − UT.

**ICRF.** Sistema de referencia celeste con los ejes del ecuador y equinoccio medios de J2000.0.

**Baricentro Tierra-Luna (EMB).** Centro de masas del par; dista de la Tierra hasta ~4700 km. Es el cuerpo que
guardan las tablas.

**IAS15.** Integrador adaptativo de orden 15 (Rein y Spiegel 2015).

**Nakṣatra.** Cada una de las 27 divisiones de 13°20′ del zodiaco sidéreo, desde 0° de Aries sidéreo; Puṣya
(Tiṣya) va de 93°20′ a 106°40′.

**Lahiri (Chitrapaksha).** Ayanāṃśa oficial de la India: 23,853° en J2000.0.

**Concentración R.** Longitud del vector unitario medio de unas longitudes: 1 si coinciden, unos √(π/4n) para *n*
al azar.

**Sesión.** Todo lo que muestra el explorador, guardado en un fichero `*.cycles.json`.

**Dosier.** PDF con todo lo que se sabe de un subciclo.

## Referencias

- Vondrák, J., Capitaine, N., Wallace, P. (2011). *New precession expressions, valid for long time intervals.*
  A&A 534, A22; corrigendum A&A 541, C1 (2012).
- Folkner, W. M., Williams, J. G., Boggs, D. H. (2009). *The Planetary and Lunar Ephemeris DE 421.* IPN Progress
  Report 42-178.
- Rein, H., Spiegel, D. S. (2015). *IAS15: a fast, adaptive, high-order integrator for gravitational dynamics.*
  MNRAS 446, 1424.
- Espenak, F., Meeus, J. *Polynomial expressions for Delta T.* NASA Eclipse Web Site.
- Abhyankar, K. D. (1993). Artículo sobre dos sellos de Mohenjo-daro. Bull. Astr. Soc. India 21, 475–479 (copia en
  `sandbox/docs/papers/`).
- ERFA (Essential Routines for Fundamental Astronomy), derivada de SOFA (IAU).
- Guénon, R. *Formes traditionnelles et cycles cosmiques*; Hani, J. (sobre la subdivisión de los ciclos).
