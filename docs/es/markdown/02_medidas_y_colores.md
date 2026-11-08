# 2. Medidas y colores

Cada subciclo recibe, a partir de su dirección, dos **medidas** escalares (dharma y pureza) y varios **colores**.
Ambos usan **pesos por posición**: el dígito del nivel $k$ pesa $b^{-k}$, de modo que los niveles exteriores
cuentan más que los interiores (`division.weights`):

$$
w(b, d) = \left(b^{-1},\ b^{-2},\ \dots,\ b^{-d}\right)
$$

Las bases son parámetros (`compute_level(d, bases, scales, colors)`):

| Parámetro | Valor por defecto | Uso |
|---|---|---|
| `bases[0]` | 4 | base de la división (número de edades); no se cambia |
| `bases[1]` | 2 | base de los pesos de los colores CMYK y del dharma |
| `bases[2]` | 2 | base de los pesos de la pureza |
| `scales[0]` | 1/2 | escala de `cmyk_scaled` |
| `scales[1]` | 2/3 | escala del negro de `cmyk_kscaled` |
| `scales[2]` | 1/2 | paso del coloreado del tetraedro |
| `colors` | amarillo, cian, magenta, negro | vértices del tetraedro de color (Satya, Treta, Dvapara, Kali) |

## 2.1 Dharma

Cada edad tiene una **virtud**: Satya 1, Treta 3/4, Dvapara 1/2, Kali 1/4 (es decir, $(4 - a)/4$). El **dharma**
de un subciclo es la media de las virtudes de sus dígitos, ponderada con los pesos de base `bases[1]`
(`measure.dharma_measure`):

$$
\operatorname{dharma}(a) = \frac{\sum_k w_k\, (4 - a_k)/4}{\sum_k w_k}
$$

Vale 1 para una dirección toda Satya y 1/4 para una toda Kali. Ejemplo, Kali › Treta › Dvapara › Satya con base
2: pesos normalizados (0,5333; 0,2667; 0,1333; 0,0667), virtudes (1/4; 3/4; 1/2; 1), aportaciones (0,1333;
0,2; 0,0667; 0,0667), dharma = **0,4667**.

Con la variante de color `cmyk_normalised` el dharma se puede leer del propio color
(`dharma_from_cmyk`): es el producto escalar de las tintas con (1, 3/4, 1/2, 1/4).

## 2.2 Pureza

La **pureza** mide cuánto domina una sola edad. Se calcula la **cuota** ponderada de cada edad (la suma de los
pesos, de base `bases[2]`, de sus dígitos, dividida por la suma de todos los pesos) y se toma la mayor menos la
menor:

$$
\operatorname{cuota}_e(a) = \frac{\sum_{k:\, a_k = e} w_k}{\sum_k w_k}, \qquad
\operatorname{pureza}(a) = \max_e \operatorname{cuota}_e - \min_e \operatorname{cuota}_e
$$

(`measure.purity_measure`).

Vale 1 si todos los dígitos son de la misma edad y 0 si las cuatro edades pesan lo mismo. En el ejemplo, las
cuotas son Satya 0,0667, Treta 0,2667, Dvapara 0,1333 y Kali 0,5333: pureza = Kali − Satya = **0,4667**.

## 2.3 Las medidas por nivel

El panel *Subcycle* del explorador desglosa ambas medidas nivel a nivel (`state.measure_breakdown`): el peso
de cada nivel, la virtud de su edad, lo que suma al dharma y su peso en la pureza. Muestra además el **rango**
de las dos medidas sobre las ordenaciones de la misma composición: el orden de los dígitos no cambia la
duración, pero sí las medidas, porque los niveles exteriores pesan más.

Para Kali › Treta › Dvapara › Satya, sus 24 ordenaciones tienen dharma entre 0,4333 y 0,8167, y todas la misma
pureza (con un dígito de cada edad, la pureza es siempre el mayor peso menos el menor). Con base 1 (todos los
niveles igual) ambas medidas serían iguales en toda la clase.

![Dharma y pureza de los 1 024 subciclos de profundidad 5, con el tamaño proporcional a la duración](figuras/dharma_pureza.png)

Rangos: el dharma va de 1/4 a 1 en todas las profundidades; la pureza mínima baja con la profundidad (4/7 ≈
0,571 a profundidad 3, 13/31 ≈ 0,419 a profundidad 5, con base 2). A profundidad 4 hay 46 valores distintos de
dharma y solo 9 de pureza.

## 2.4 Colores: las edades como tintas

Cada edad se asocia a una tinta de imprenta: **Satya → cian, Treta → magenta, Dvapara → amarillo, Kali →
negro**. Cada dígito añade su peso a la tinta de su edad, y de esas sumas salen las variantes CMYK
(`color.lcoords_to_cmyk`), convertidas a RGB con $\mathrm{RGB} = (1 - \mathrm{CMY})\,(1 - \mathrm{K})$:

| Variante | Definición |
|---|---|
| `cmyk` | sumas ponderadas de las tintas |
| `cmyk_normalised` | divididas por la suma de los pesos (la variante por defecto) |
| `cmyk_scaled` | normalizadas y multiplicadas por `scales[0]` (más claras) |
| `cmyk_kscaled` | normalizadas, con solo el negro multiplicado por `scales[1]` |
| `cmyk_composition` | recuentos de dígitos sin pesos, divididos por la profundidad: depende solo de la composición |
| `wcmy` | normalizadas y desplazadas una tinta: Satya → blanco, Treta → cian, Dvapara → magenta, Kali → amarillo, sin negro |

Además hay cuatro coloreados más (`division.level_colors`):

| Coloreado | Definición |
|---|---|
| `tetrahedron` | «juego del caos» en el espacio RGB (2.5) |
| `lrgb` | la tinta pura de la edad del último nivel |
| `dharma`, `purity` | gris con el valor de la medida |

En total, `COLOR_KEYS` tiene diez nombres. Ejemplo, Kali › Treta › Dvapara › Satya: `cmyk` = (0,0625; 0,25;
0,125; 0,5); `cmyk_normalised` = (0,0667; 0,2667; 0,1333; 0,5333); `cmyk_composition` = (¼, ¼, ¼, ¼).

![Las diez variantes de color de los 64 subciclos de profundidad 3](figuras/variantes_color.png)

## 2.5 El tetraedro de Sierpinski

El coloreado `tetrahedron` coloca las cuatro edades en cuatro colores-vértice (por defecto amarillo, cian,
magenta y negro, el mayor tetraedro que cabe en el cubo RGB, de volumen 1/3) y parte del centroide; cada
dígito acerca el punto una fracción `scales[2]` hacia el vértice de su edad:

$$
c_0 = \bar v = \tfrac14 \sum_e v_e, \qquad c_k = c_{k-1} + s\,\left(v_{a_k} - \bar v\right)
$$

(`color.lcoords_to_rgb_tetrahedron`, con $v_e$ los colores-vértice). Con $s = 1/2$, los colores de todas las
direcciones llenan un **tetraedro de Sierpinski**.

![Colores `tetrahedron` de los 4 096 subciclos de profundidad 6 en el cubo RGB: un tetraedro de Sierpinski](figuras/sierpinski_tetraedro.png)

## 2.6 Cuándo los colores no se repiten

Que cada subciclo de un nivel tenga un color distinto exige mantener los parámetros en ciertos rangos,
comprobados por `color.color_parameter_problems` (y por el diálogo de parámetros del explorador, que no aplica
valores fuera de ellos):

| Parámetro | Rango | Por qué |
|---|---|---|
| `bases[1]` | ≥ 2 | cada peso supera entonces la suma de todos los siguientes, y las sumas de tinta devuelven la dirección; por debajo de 2 hay repeticiones en bases aisladas (la razón áurea desde la profundidad 3; 1 desde la 2) |
| `scales[0]` | (0, 1] | la conversión CMYK → RGB de colores con tintas que suman *s* es entonces biyectiva |
| `scales[1]` | [0; 0,25] o [0,5; 1] | entre medias la conversión a RGB puede tener dos preimágenes (no se han encontrado repeticiones, pero no está garantizado) |
| `scales[2]` | [0,5; 1) | el último dígito pesa más que todos los anteriores; por debajo de 1/2 hay repeticiones en pasos aislados (0,382 desde la profundidad 3); con 1 solo cuenta el último |
| vértices | cuatro colores RGB no coplanarios | un color devuelve entonces sus coordenadas baricéntricas; conjuntos planos pueden repetir (cuatro alineados, desde la profundidad 2) |

`bases[2]` (pureza) no necesita cota: con 1 pesa igual todos los niveles. Dentro de los rangos, bases y pasos
mayores mantienen los colores distintos pero acercan los niveles profundos más de lo que una pantalla puede
separar: a profundidad 7, la base 2 da 15 764 colores distinguibles en pantalla de 16 384, y la base 3 solo
4 442.

Los efectos de cada parámetro sobre los coloreados están en `division.COLOR_PARAMETER_EFFECTS`: la base de
color cambia las variantes CMYK salvo `cmyk_composition` y también el dharma; la de pureza, solo la pureza; las
escalas, cada una su variante; paso y vértices, el tetraedro.

## 2.7 Resumen

- Pesos `b^−k`: los niveles exteriores cuentan más.
- Dharma: media ponderada de las virtudes (1 a 1/4). Pureza: cuota mayor menos cuota menor.
- Las medidas distinguen las ordenaciones de una composición, que tienen la misma duración.
- Diez coloreados; los CMYK asocian cada edad a una tinta, el del tetraedro dibuja un Sierpinski.
- Los parámetros tienen rangos que garantizan colores distintos dentro de cada nivel.
