# 14. Resultados y preguntas abiertas

## 14.1 La estructura

1. **Duraciones.** A profundidad *d* hay 4^d subciclos, C(*d* + 3, 3) composiciones y exactamente
   **(*d* + 1)² duraciones distintas**: la duración es 2^(2n₀ + n₂) · 3^n₁ / 10^d y solo depende de
   (n₁, 2n₀ + n₂). Las composiciones de igual duración difieren en múltiplos de (1, 0, −2, 1), porque
   0,4 · 0,1 = 0,2². Subciclos de profundidades distintas nunca comparten duración (`unique_across_depths`).
2. **Las clases crecen** con la profundidad: la mayor tiene 9 subciclos a profundidad 3, 28 a la 4 y 95 a la 5.
3. **Permutaciones.** Toda permutación de posiciones conserva duraciones y composiciones; ⟨σ⟩ fija 4^(ciclos) y
   tiene la media de los fijos de sus potencias como número de órbitas; todo S_m tiene C(*m* + 3, 3) órbitas (las
   composiciones).
4. **Medidas.** El orden de los dígitos no cambia la duración pero sí el dharma (los niveles exteriores pesan
   más): las 24 ordenaciones de Kali › Treta › Dvapara › Satya van de 0,4333 a 0,8167, todas con la misma pureza.
5. **Colores.** Dentro de los rangos de los parámetros los colores de cada nivel son únicos; el coloreado del
   tetraedro llena un tetraedro de Sierpinski.

## 14.2 El modelo de ciclo y la precesión

1. **Cuotas de tiempo.** Dividiendo el arco (2,5 vueltas, modelo de largo plazo), los yugas ocupan 0,4039,
   0,2915, 0,2040 y 0,1006 del tiempo. La identidad de las tasas medias lo explica exactamente.
2. **Los dos criterios** ponen las fronteras de los yugas a hasta unos **300 años** (289 en el inicio del Treta);
   dentro del Kali, a años o menos (Kali › Dvapara, 6,4 años).
3. **El ancla tradicional está cerca de una de las peores** colocaciones para 2,5 vueltas (desviación 0,0085
   frente a unos 0,002 en las mejores): el Treta cubre el máximo de la tasa y el Dvapara su mínimo. Con el arco
   libre, el ajuste tiende al arco más largo permitido.
4. **El periodo de ~20 000 años del paisaje** es la variación de ~41 000 años de la tasa (la oblicuidad),
   rectificada: viene del modelo de precesión, no de la división.

## 14.3 El cielo

**Clases de subciclos.** Para la clase de composición de Kali › Treta › Dvapara › Satya (24 subciclos), la
concentración de los planetas en los inicios está cerca del azar (por ejemplo, Júpiter 0,27 frente a 0,18): la
clase no comparte una configuración del cielo.

**Parecido con la selección.** Comparando el cielo de los inicios de todos los subciclos de una profundidad con
el de Kali › Treta › Dvapara › Satya (cuerpos lentos):

| Profundidad | Subciclos | Δ más cercana | Δ más cercana esperada al azar | Bajo la línea del 5 % |
|---|---:|---:|---:|---:|
| 4 | 256 | 23,7° | ~17,9° | 5,1 % |
| 7 | 16 384 | 5,1° | ~3,8° | 5,3 % |
| 8 | 65 536 | 3,1° | ~2,9° | 5,3 % |

Los inicios de los subciclos **no se acercan más que instantes al azar**: los parecidos que aparecen vienen de los
periodos propios de los planetas, no de la división.

**Configuraciones notables** (Abhyankar, conjunciones en Puṣya): son frecuentes; sin un modelo de azar no tienen
valor probatorio (capítulo 9).

**Acontecimientos planetarios** (capítulo 15). Ninguna de las 29 pruebas (el Sūrya Siddhānta en 0° de Aries, las
grandes conjunciones y sus cambios de trígono, las conjunciones de Urano–Neptuno y Neptuno–Plutón; profundidades 1
a 5; zodiacos sidéreo y trópico) es significativa tras la corrección de Holm. Los planetas sí se reúnen cerca de 0°
de Aries sidéreo al inicio del Kali (ángulo medio 15°, arco 41°), pero es el ancla del modelo; sin ella, p = 0,19.

## 14.4 Preguntas abiertas y trabajo pendiente

| Tema | Estado |
|---|---|
| **Eventos y significación** (idea 4) | hecho para tres hipótesis astronómicas (capítulo 15); pendientes: otras familias de acontecimientos, el mapa de significación sobre el paisaje del modelo, el nulo de las permutaciones de dígitos, los acontecimientos históricos con fecha (falta un conjunto de datos) y el panel *Events* del explorador |
| **Sonido en el explorador** (idea 7) | reproducir el tramo ampliado con un cursor ligado al momento del cielo, y oír el efecto de σ |
| **Animación de permutaciones** | reproducir el panel de permutaciones a través de σ⁰, σ¹, σ², … |
| **Acoplamiento con QtAds** (opcional) | destinos de soltado al arrastrar paneles y paneles que se ocultan en un borde, si los menús de colocación se quedan cortos |
| **Dosier** | el resumen pasa a una segunda página A4 vertical cuando el subciclo tiene marcadores |
| **Marte antes de −2000** | discrepancia con Moshier; falta una tercera referencia (DE441) |
| **Incertidumbre numérica de la efeméride** | integrar variantes con `build_many` |
| **ΔT antes de −700** | extrapolación incierta en horas; afecta al Sol y a los planetas interiores en fechas antiguas |
| **El ancla del ciclo** | es una hipótesis de investigación: ninguna fuente textual ni astronómica fija las fronteras anteriores al Kali |
