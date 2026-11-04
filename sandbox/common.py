"""Paths, default parameters and helpers shared by the sandbox studies."""

from pathlib import Path

import numpy as np

from cycles.functions.color import lcoords_to_lrgb
from cycles.functions.division import Level, RGB_KEYS, compute_level

SANDBOX_DIR = Path(__file__).resolve().parent
PLOTS_DIR = SANDBOX_DIR / "plots"
DATA_DIR = SANDBOX_DIR / "data"
SOUNDS_DIR = SANDBOX_DIR / "sounds"

# [division base, color weight base, purity weight base]
BASES = [4, 2, 2]
# [cmyk scale, black scale, tetrahedron step] (see compute_level)
SCALES = [1 / 2, 2 / 3, 0.5]
# Vertex colors of the tetrahedron coloring: Golden, Silver, Bronze, Iron
TETRAHEDRON_COLORS = np.array([[1, 1, 0], [0, 1, 1], [1, 0, 1], [0, 0, 0]])

# Names accepted by level_colors: the RGB variants of a Level, plus three more
COLOR_KEYS = RGB_KEYS + ('lrgb', 'dharma', 'purity')


def compute_levels(max_depth: int, bases=BASES, scales=SCALES, colors=TETRAHEDRON_COLORS) -> list[Level]:
    """Levels of depth 1 to ``max_depth``."""
    return [compute_level(depth, bases, scales, colors) for depth in range(1, max_depth + 1)]


def level_colors(level: Level) -> dict[str, np.ndarray]:
    """
    RGB color of every subcycle of ``level`` for each name in ``COLOR_KEYS``:
    the Level's RGB variants, ``lrgb`` (pure ink of the innermost age), and
    ``dharma`` / ``purity`` as gray levels.
    """
    colors = {key: level.rgb(key) for key in RGB_KEYS}
    colors['lrgb'] = np.array([lcoords_to_lrgb(lcoords)[-1] for lcoords in level.lcoords])
    colors['dharma'] = np.repeat(level.dharmas[:, None], 3, axis=1)
    colors['purity'] = np.repeat(level.purities[:, None], 3, axis=1)
    return colors


def save_figure(fig, path, dpi: int = 300) -> None:
    """Save ``fig`` to ``path``, creating missing folders."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi)


def fig_data(path, paper: str = 'a4', dpi: int = 300, tight_layout: bool = False,
             orientation: str = 'landscape') -> tuple:
    """``fig_data`` tuple for the plotting functions (see ``format_plot``)."""
    return paper, orientation, str(path), dpi, tight_layout
