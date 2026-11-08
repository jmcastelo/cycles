"""
Convierte los capítulos Markdown de ../markdown en un documento LaTeX (LuaLaTeX) con panel de selección.

    python md_a_tex.py          # escribe cycles_documentacion.tex (las figuras se leen de ../markdown/figuras)
    python md_a_tex.py --forzar # aunque la versión documentada no sea la del programa

Comprueba que la versión que declara 00_indice_y_glosario.md es la de cycles/__init__.py.

Solo entiende el subconjunto de Markdown que usan estos documentos: títulos #, ## y ###, párrafos, listas con
«- » y «1. », tablas con barras, bloques de código con ```, figuras ![pie](figuras/x.png) en su propia línea,
**negrita**, *cursiva*, `código`, ~~tachado~~, enlaces, superíndices a^b o a^(…), y fórmulas en LaTeX: $…$ en línea
y $$…$$ en sus propias líneas (como las muestra GitHub).
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARKDOWN = HERE.parent / 'markdown'
OUT = HERE / 'cycles_documentacion.tex'
# la raíz del proyecto: la carpeta con pyproject.toml, subiendo desde aquí
ROOT = next(parent for parent in HERE.parents if (parent / 'pyproject.toml').exists())

# Archivo -> (identificador del bloque, título del capítulo en el documento LaTeX o None para el del Markdown)
CHAPTERS = {
    '00': ('Intro', 'Introducción, índice y glosario'),
    '01': ('Division', None), '02': ('Medidas', None), '03': ('Permutaciones', None),
    '04': ('Precesion', None), '05': ('Fechas', None), '06': ('Nbody', None), '07': ('Validacion', None),
    '08': ('Modelo', None), '09': ('Hindu', None), '10': ('Modulos', None), '11': ('Estudios', None),
    '12': ('Aplicacion', None), '13': ('Pruebas', None), '14': ('Resultados', None),
    '15': ('Eventos', None),
}
PARTS = {'01': 'La estructura', '04': 'Astronomía y tiempo', '10': 'El software', '15': 'Contrastes'}
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
_KEPT: list[str] = []      # trozos ya convertidos, sustituidos por marcas mientras se procesa el resto

SPECIAL = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_',
           '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}


def escape(text: str) -> str:
    return ''.join(SPECIAL.get(c, c) for c in text)


def code(text: str) -> str:
    """Código en línea, con cortes de línea permitidos tras _ . , ( / y espacios (no dentro de un número: 0.3)."""
    out = []
    for k, c in enumerate(text):
        out.append(SPECIAL.get(c, c))
        decimal = c == '.' and k + 1 < len(text) and text[k + 1].isdigit()
        if c in '_.,(/=' and not decimal:
            out.append(r'\allowbreak{}')
    return r'\texttt{' + ''.join(out) + '}'


def inline(text: str) -> str:
    """Formato en línea de Markdown a LaTeX."""
    keep = _KEPT          # compartido entre llamadas anidadas (un enlace con código dentro)

    def hold(latex: str) -> str:
        keep.append(latex)
        return f"\x00{len(keep) - 1}\x00"

    text = re.sub(r'`([^`]+)`', lambda m: hold(code(m.group(1))), text)
    # maths in $…$ goes to LaTeX as it is (as GitHub renders it)
    text = re.sub(r'(?<![\\$\w])\$([^\s$](?:[^$\n]*?[^\s$])?)\$(?![\w$])', lambda m: hold('$' + m.group(1) + '$'),
                  text)

    def link(m):
        label, url = m.group(1), m.group(2)
        if url.startswith('http'):
            return hold(r'\href{' + url + '}{' + inline(label) + '}')
        return hold(inline(label))
    text = re.sub(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)', link, text)

    # superíndices: a^b y a^(…), con paréntesis anidados
    result, i = [], 0
    while i < len(text):
        if text[i] == '^' and i > 0 and i + 1 < len(text):
            if text[i + 1] == '(':
                depth, j = 0, i + 1
                while j < len(text):
                    depth += {'(': 1, ')': -1}.get(text[j], 0)
                    if depth == 0:
                        break
                    j += 1
                content, i = text[i + 2:j], j + 1
            else:
                m = re.match(r'[\w\u2212\-]+', text[i + 1:])
                if not m:
                    result.append(text[i])
                    i += 1
                    continue
                content, i = m.group(0), i + 1 + len(m.group(0))
            result.append(hold(r'\textsuperscript{' + inline(content) + '}'))
            continue
        result.append(text[i])
        i += 1
    text = escape(''.join(result))
    # miles separados por espacio (64 540,1; −16 268,2): espacio fino que no se parte
    text = re.sub(r'(?<=\d) (?=\d{3}(?!\d))', r'\\,', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)
    text = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'\\emph{\1}', text)
    text = re.sub(r'\\textasciitilde\{\}\\textasciitilde\{\}(.+?)\\textasciitilde\{\}\\textasciitilde\{\}',
                  r'\\sout{\1}', text)
    while '\x00' in text:
        text = re.sub('\x00(\\d+)\x00', lambda m: keep[int(m.group(1))], text)
    return text


def table(rows: list[str]) -> str:
    cells = [[c.strip() for c in row.strip().strip('|').split('|')] for row in rows]
    header, align, body = cells[0], cells[1], cells[2:]
    n = len(header)
    def words(text):
        return [len(w) for w in re.sub(r'[*`]', '', text).split()] or [0]
    # ancho de cada columna: según lo que contiene, y al menos su palabra más larga (que no se puede partir)
    weights = [min(90, max(6, max(len(r[k]) if k < len(r) else 0 for r in [header] + body))) for k in range(n)]
    minimum = [max(max(words(r[k])) if k < len(r) else 0 for r in [header] + body) + 2 for k in range(n)]
    total = sum(weights)
    letters = 70.0                     # caracteres de código que caben, más o menos, en el ancho de línea
    widths = [max(0.97 * weights[k] / total, minimum[k] / letters) for k in range(n)]
    scale = min(1.0, 0.97 / sum(widths))
    spec = []
    for k in range(n):
        width = max(0.07, widths[k] * scale)
        side = r'\raggedleft' if align[k].endswith(':') and not align[k].startswith(':') else r'\raggedright'
        spec.append(rf'>{{{side}\arraybackslash}}p{{{width:.3f}\linewidth-2\tabcolsep}}')
    head = ' & '.join(r'\textbf{' + inline(h) + '}' if h else '' for h in header)
    lines = [r'{\small', r'\begin{longtable}{@{}' + ''.join(spec) + '@{}}', r'\toprule', head + r' \\',
             r'\midrule', r'\endhead']
    for row in body:
        row = row + [''] * (n - len(row))
        lines.append(' & '.join(inline(c) for c in row[:n]) + r' \\')
    lines += [r'\bottomrule', r'\end{longtable}}']
    return '\n'.join(lines)


def figure(line: str) -> str:
    m = re.match(r'!\[(.*)\]\((?:figuras/)?([^)]+)\)\s*$', line.strip())
    caption, name = m.group(1), m.group(2)
    return r'\figura{' + name + '}{' + inline(caption) + '}'


def convert_body(lines: list[str]) -> list[str]:
    """Bloques de un trozo de Markdown (sin títulos) a LaTeX."""
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.strip().startswith('$$'):
            # display maths: $$ … $$ on its own line(s)
            j = i
            body = line.strip()[2:]
            while not body.rstrip().endswith('$$') or (j == i and len(line.strip()) == 2):
                j += 1
                body += '\n' + lines[j].strip()
            out.append('\\[\n' + body.rstrip()[:-2].strip() + '\n\\]')
            i = j + 1
            continue
        if line.startswith('```'):
            j = i + 1
            while j < len(lines) and not lines[j].startswith('```'):
                j += 1
            longest = max((len(l) for l in lines[i + 1:j]), default=0)
            size = r'\small' if longest <= 82 else r'\footnotesize' if longest <= 95 else r'\scriptsize'
            out.append('\n'.join([rf'\begin{{Verbatim}}[fontsize={size},frame=single,framesep=2mm,'
                                   r'rulecolor=\color{black!25}]', *lines[i + 1:j], r'\end{Verbatim}']))
            i = j + 1
            continue
        if line.startswith('|'):
            j = i
            while j < len(lines) and lines[j].startswith('|'):
                j += 1
            out.append(table(lines[i:j]))
            i = j
            continue
        if line.startswith('!['):
            out.append(figure(line))
            i += 1
            continue
        bullet = re.match(r'^(\s*)(- |\d+\. )', line)
        if bullet:
            kind = 'itemize' if bullet.group(2) == '- ' else 'enumerate'
            items = []
            while i < len(lines) and lines[i].strip():
                m = re.match(r'^(\s*)(- |\d+\. )(.*)', lines[i])
                if m and len(m.group(1)) == 0:
                    items.append(m.group(3))
                else:
                    items[-1] += ' ' + lines[i].strip()
                i += 1
            out.append('\n'.join([rf'\begin{{{kind}}}', *(r'\item ' + inline(item) for item in items),
                                   rf'\end{{{kind}}}']))
            continue
        paragraph = []
        while i < len(lines) and lines[i].strip() and not re.match(r'^(```|\||!\[|- |\d+\. |\$\$)', lines[i]):
            paragraph.append(lines[i].strip())
            i += 1
        out.append(inline(' '.join(paragraph)))
    return out


def convert_chapter(path: Path, number: str) -> tuple[str, list[str]]:
    """Un capítulo con sus secciones como bloques; devuelve el LaTeX y los identificadores de los bloques."""
    slug, title_override = CHAPTERS[number]
    lines = path.read_text(encoding='utf-8').splitlines()
    chapter_id = 'cap' + slug
    ids = [chapter_id]
    title = re.sub(r'^\d+\.\s*', '', lines[0].lstrip('# ').strip())
    if number == '00':
        head = [rf'\chapter*{{{title_override}}}', rf'\addcontentsline{{toc}}{{chapter}}{{{title_override}}}',
                rf'\markboth{{{title_override}}}{{{title_override}}}']
    else:
        head = [rf'\numCap{{{int(number)}}}', rf'\chapter{{{inline(title)}}}']
    out = [rf'\begin{{{chapter_id}}}'] + head
    chunks, current, heading = [], [], None
    for line in lines[1:]:
        if line.startswith('## '):
            chunks.append((heading, current))
            heading, current = line[3:].strip(), []
        else:
            current.append(line)
    chunks.append((heading, current))
    sections = 0
    for heading, body in chunks:
        if heading is None:
            out += convert_body(body)
            continue
        section_id = f"sec{slug}{LETTERS[sections]}"
        ids.append(section_id)
        sections += 1
        numbered = re.match(r'^(\d+)\.(\d+)\s+(.*)', heading)
        out.append(rf'\begin{{{section_id}}}')
        if numbered:
            out += [r'\needspace{8\baselineskip}', rf'\numSec{{{int(numbered.group(2))}}}',
                    rf'\section{{{inline(numbered.group(3))}}}']
        else:
            out.append(rf'\section*{{{inline(heading)}}}')
        sub = []
        for line in body:
            if line.startswith('### '):
                out += convert_body(sub)
                sub = []
                out.append(r'\needspace{8\baselineskip}\subsection*{' + inline(line[4:].strip()) + '}')
            else:
                sub.append(line)
        out += convert_body(sub)
        out.append(rf'\end{{{section_id}}}')
    out.append(rf'\end{{{chapter_id}}}')
    return '\n\n'.join(out), ids          # una línea en blanco entre bloques: los párrafos no se juntan


PREAMBLE = r"""% !TEX program = lualatex
% =====================================================================================
%  CICLOS: LA DIVISIÓN 4:3:2:1, LA PRECESIÓN Y EL EXPLORADOR
%  Documentación del proyecto (versión LaTeX modular), generada desde ../markdown con md_a_tex.py
%
%  Compilar con LuaLaTeX (dos pasadas):  lualatex cycles_documentacion.tex
%  Las figuras se leen de \figdir. Para elegir qué contenidos aparecen, ver el PANEL DE SELECCIÓN
%  y el apéndice «Cómo seleccionar contenidos».
% =====================================================================================
\documentclass[11pt,a4paper]{report}

% ----------------------------- Fuentes e idioma ------------------------------------
% Fuente principal y de código; los símbolos que les faltan (signos del zodiaco, planetas, subíndices,
% operadores) se toman de DejaVu y Noto, por este orden.
\usepackage{fontspec}
\directlua{luaotfload.add_fallback("simbolos", {"DejaVu Sans:mode=harf;", "Noto Sans Math:mode=harf;",
  "Noto Sans Symbols:mode=harf;", "Noto Sans Symbols 2:mode=harf;"})}
\IfFontExistsTF{Libertinus Serif}{\setmainfont{Libertinus Serif}[RawFeature={fallback=simbolos}]}{%
  \setmainfont{Noto Serif}[RawFeature={fallback=simbolos}]}
\IfFontExistsTF{DejaVu Sans Mono}{\setmonofont{DejaVu Sans Mono}[Scale=MatchLowercase,RawFeature={fallback=simbolos}]}{%
  \setmonofont{JetBrains Mono}[Scale=MatchLowercase,RawFeature={fallback=simbolos}]}
\usepackage{amsmath}
\usepackage{unicode-math}           % fórmulas: la fuente matemática de Libertinus, con los símbolos Unicode
\IfFontExistsTF{Libertinus Math}{\setmathfont{Libertinus Math}}{}
\IfFileExists{spanish.ldf}{%
  \usepackage[spanish,es-noshorthands,es-nodecimaldot,es-tabla,es-nolists]{babel}}{%
  \usepackage[main=spanish,provide=*]{babel}}

% ----------------------------- Paquetes --------------------------------------------
\usepackage[a4paper,margin=2.5cm]{geometry}
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{caption}
\usepackage{booktabs,longtable,array,calc}
\usepackage{etoolbox}
\usepackage{enumitem}
\usepackage{fancyvrb}
\usepackage{comment}
\usepackage{needspace}          % un título no se queda solo al pie de una página
\IfFileExists{ulem.sty}{\usepackage[normalem]{ulem}}{\newcommand{\sout}[1]{##1}}   % tachado
\usepackage{fancyhdr}
\usepackage{microtype}
\usepackage[colorlinks=true,linkcolor=blue!45!black,urlcolor=blue!45!black,
            pdftitle={Ciclos: la división 4:3:2:1, la precesión y el explorador},
            pdfauthor={},pdflang={es}]{hyperref}
\usepackage{bookmark}

\sloppy
\emergencystretch=3em
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.55em plus 0.15em}
\setlist{itemsep=0.15em,topsep=0.3em,labelsep=0.6em}
\setlist[itemize]{label=\textbullet,leftmargin=1.6em}
\setlist[enumerate]{leftmargin=1.9em}
% más sitio para los números de sección de dos cifras en el índice (12.10)
\makeatletter
\renewcommand*\l@section{\@dottedtocline{1}{1.5em}{2.9em}}
\makeatother
\setcounter{tocdepth}{1}
\captionsetup{font=small,labelfont=bf,skip=4pt,hypcap=false}
\setlength{\LTpre}{0.4em}
\setlength{\LTpost}{0.6em}

% ----------------------------- Cabeceras -------------------------------------------
\setlength{\headheight}{14pt}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\nouppercase{\leftmark}}
\fancyhead[R]{\small\thepage}
\renewcommand{\headrulewidth}{0.3pt}
\fancypagestyle{plain}{\fancyhf{}\fancyfoot[C]{\small\thepage}\renewcommand{\headrulewidth}{0pt}}

% ----------------------------- Figuras ---------------------------------------------
% Carpeta de las figuras (cámbiese si las imágenes están en otro sitio).
\newcommand{\figdir}{../markdown/figuras/}
% \figura{archivo}{pie}: figura no flotante, a lo ancho y como mucho a 0,6 de la altura de la página;
% si falta el archivo, muestra un marco con su nombre.
\newcommand{\figura}[2]{%
  \begin{center}\begin{minipage}{\linewidth}\centering   % la imagen y su pie, siempre juntos
    \IfFileExists{\figdir#1}{\includegraphics[width=\linewidth,height=0.6\textheight,keepaspectratio]{\figdir#1}}{%
      \fbox{\parbox{0.7\linewidth}{\centering\small Figura no encontrada:\\ \texttt{\figdir#1}}}}
    \captionof{figure}{#2}
  \end{minipage}\end{center}}

% Numeración: se conserva la de los documentos Markdown (capítulo N, sección N.M) aunque se omitan bloques.
\newbool{numeracionOriginal}
\booltrue{numeracionOriginal}
\newcommand{\renumerar}{\boolfalse{numeracionOriginal}}
\newcommand{\numCap}[1]{\ifbool{numeracionOriginal}{\setcounter{chapter}{\numexpr#1-1\relax}}{}}
\newcommand{\numSec}[1]{\ifbool{numeracionOriginal}{\setcounter{section}{\numexpr#1-1\relax}}{}}

% =====================================================================================
%  PANEL DE SELECCIÓN DE CONTENIDOS
%  \incluir{id}  activa un bloque;  \excluir{id}  lo desactiva.
%  \incluirTodo / \excluirTodo  parten de un extremo (después se afina bloque a bloque).
%  Los capítulos (capXxx) contienen a sus secciones (secXxxA, secXxxB, …): para que una sección
%  aparezca, su capítulo debe estar activo. El apéndice lista qué es cada bloque.
% =====================================================================================
\newcommand{\incluir}[1]{\expandafter\def\csname #1\endcsname{}\expandafter\def\csname end#1\endcsname{}}
\newcommand{\excluir}[1]{\excludecomment{#1}}
\newcommand{\listaDeBloques}{%
<<BLOQUES>>}
\newcommand{\incluirTodo}{\expandafter\forcsvlist\expandafter\incluir\expandafter{\listaDeBloques}}
\newcommand{\excluirTodo}{\expandafter\forcsvlist\expandafter\excluir\expandafter{\listaDeBloques}}

\incluirTodo                        % valor por defecto: todo el contenido
% \excluirTodo                      % <- alternativa: empezar vacío y activar solo lo deseado

% ---- Ajustes individuales (quítese el % de la línea que se quiera aplicar) --------
<<AJUSTES>>

% ---- Numeración -------------------------------------------------------------------
% \renumerar                        % numeración consecutiva en lugar de la de los capítulos Markdown

% =====================================================================================
\title{{\Huge Ciclos}\\[0.8em]\Large La división 4:3:2:1, la precesión de los equinoccios\\y el explorador gráfico}
\author{Documentación del proyecto\\[0.4em]\normalsize Versión <<VERSION>> del programa}
\hypersetup{pdfsubject={Documentación de la versión <<VERSION>>}}
\date{\today}

\begin{document}
\maketitle
\tableofcontents
"""

APPENDIX = r"""
\begin{capGuiaUso}
\chapter*{Apéndice: cómo seleccionar contenidos}
\addcontentsline{toc}{chapter}{Apéndice: cómo seleccionar contenidos}
\markboth{Cómo seleccionar contenidos}{Cómo seleccionar contenidos}
Este documento se genera a partir de los capítulos Markdown de \texttt{../markdown} con
\texttt{md\_a\_tex.py} (en esta misma carpeta): tras cambiar un capítulo, basta volver a ejecutarlo y a
compilar. El contenido está dividido en \emph{bloques}: cada capítulo y cada sección es un entorno con nombre
(por ejemplo \texttt{capModelo} o \texttt{secModeloE}) que se activa o se desactiva desde el \textbf{panel de
selección} del preámbulo.

\begin{itemize}
\item \verb|\incluirTodo| (por defecto) activa todos los bloques; \verb|\excluirTodo| los desactiva todos, para
  después activar solo los deseados con \verb|\incluir{...}|.
\item \verb|\excluir{secModeloH}| quita una sección; \verb|\excluir{capAplicacion}| quita un capítulo entero (con sus
  secciones).
\item Por defecto se conserva la numeración de los capítulos Markdown (capítulo 8, sección 8.5…) aunque se omitan
  bloques; \verb|\renumerar| numera de forma consecutiva.
\item \verb|\figdir| indica la carpeta de las figuras; si falta una imagen, se dibuja un marco con su nombre.
\item Las fórmulas se escriben en LaTeX en los propios Markdown (\verb|$…$| en línea y \verb|$$…$$| en sus propias
  líneas, como las muestra GitHub) y pasan tal cual; se componen con \texttt{unicode-math} y la fuente
  matemática Libertinus Math. En las fórmulas, la coma decimal se escribe \verb|{,}|.
\item Compilar con \texttt{lualatex} (dos pasadas, para el índice). Los símbolos que no tiene la fuente
  principal (signos del zodiaco, planetas, subíndices) se toman de las fuentes DejaVu y Noto.
\end{itemize}

Bloques:

<<TABLA>>
\end{capGuiaUso}
\end{document}
"""


VERSION_LINE = re.compile(r'Versión del programa documentada: \*\*(\d+\.\d+\.\d+)\*\*')


def versions() -> tuple[str, str]:
    """(versión que declaran los documentos, versión del programa en cycles/__init__.py)."""
    index = (MARKDOWN / '00_indice_y_glosario.md').read_text(encoding='utf-8')
    found = VERSION_LINE.search(index)
    if found is None:
        sys.exit('00_indice_y_glosario.md no dice qué versión documenta («Versión del programa documentada: **X.Y.Z**»)')
    source = (ROOT / 'cycles' / '__init__.py').read_text(encoding='utf-8')
    program = re.search(r'__version__\s*=\s*"([^"]+)"', source).group(1)
    return found.group(1), program


def main() -> None:
    documented, program = versions()
    if documented != program and '--forzar' not in sys.argv:
        sys.exit(f"Los documentos describen la versión {documented} y el programa es la {program}: actualícense "
                 f"(y su línea de versión en 00_indice_y_glosario.md), o úsese --forzar.")
    files = sorted(MARKDOWN.glob('[0-9][0-9]_*.md'))
    bodies, all_ids, descriptions = [], [], []
    for path in files:
        number = path.name[:2]
        if number in PARTS:
            bodies.append(r'\part{' + PARTS[number] + '}')
        body, ids = convert_chapter(path, number)
        bodies.append(body)
        all_ids += ids
        lines = path.read_text(encoding='utf-8').splitlines()
        chapter_title = CHAPTERS[number][1] or re.sub(r'^#\s*\d+\.\s*', '', lines[0])
        descriptions.append((ids[0], '', chapter_title))
        sections = [l[3:].strip() for l in lines if l.startswith('## ')]
        descriptions += [(sid, '', title) for sid, title in zip(ids[1:], sections)]
    all_ids.append('capGuiaUso')
    blocks = ',%\n'.join('    ' + ','.join(all_ids[k:k + 6]) for k in range(0, len(all_ids), 6))
    settings = '\n'.join(rf'% \excluir{{{block}}}' for block in all_ids)
    rows = [r'{\small', r'\begin{longtable}{@{}>{\raggedright\arraybackslash}p{0.25\linewidth}'
                        r'>{\raggedright\arraybackslash}p{0.7\linewidth}@{}}',
            r'\toprule \textbf{Bloque} & \textbf{Contenido} \\ \midrule \endhead']
    for block, _, title in descriptions:
        rows.append(r'\texttt{' + block + '} & ' + inline(title) + r' \\')
    rows += [r'\texttt{capGuiaUso} & Este apéndice \\', r'\bottomrule', r'\end{longtable}}']
    text = (PREAMBLE.replace('<<BLOQUES>>', blocks).replace('<<AJUSTES>>', settings).replace('<<VERSION>>', documented)
            + '\n\n'.join(bodies) + APPENDIX.replace('<<TABLA>>', '\n'.join(rows)))
    OUT.write_text(text, encoding='utf-8')
    print(f"{OUT.name}: {len(files)} capítulos, {len(all_ids)} bloques")


if __name__ == '__main__':
    main()
