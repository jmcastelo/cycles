# Generar las figuras

Desde la raíz del proyecto, con el entorno virtual activo (las de la efeméride necesitan `sandbox/data/tabla70k70k`):

```bash
D=docs/es/markdown/figuras
python docs/es/generar_figuras/figuras_estructura.py $D          # capítulos 1 y 2
python docs/es/generar_figuras/figuras_precesion.py $D           # capítulo 4
python docs/es/generar_figuras/figuras_zodiaco.py $D             # capítulo 10
python docs/es/generar_figuras/figuras_explorador.py $D part1 part2 shots model   # explorador (sin pantalla)
cd docs/es/tex && python md_a_tex.py && lualatex cycles_documentacion.tex && lualatex cycles_documentacion.tex
```

`figuras_explorador.py` abre el explorador sin pantalla, con ajustes temporales: `part1` (tetraedro, Sierpinski,
permutaciones), `part2` (paisaje), `shots` (capturas de la ventana, los paneles y los diálogos), `model` (los
diálogos del modelo y de los colores, que esperan a sus temporizadores). El documento LaTeX lee las figuras directamente de `markdown/figuras/`.
