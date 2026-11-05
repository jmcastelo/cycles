"""Paths, default parameters and helpers shared by the sandbox studies."""

from pathlib import Path

from cycles.functions.division import (
    COLOR_KEYS, DEFAULT_BASES, DEFAULT_SCALES, TETRAHEDRON_COLORS, Level, compute_level, level_colors,
)

SANDBOX_DIR = Path(__file__).resolve().parent
PLOTS_DIR = SANDBOX_DIR / "plots"
DATA_DIR = SANDBOX_DIR / "data"
SOUNDS_DIR = SANDBOX_DIR / "sounds"

# Default parameters (see cycles.functions.division)
BASES = DEFAULT_BASES
SCALES = DEFAULT_SCALES

__all__ = ['SANDBOX_DIR', 'PLOTS_DIR', 'DATA_DIR', 'SOUNDS_DIR', 'BASES', 'SCALES', 'TETRAHEDRON_COLORS',
           'COLOR_KEYS', 'compute_levels', 'level_colors', 'save_figure', 'fig_data']


def compute_levels(max_depth: int, bases=BASES, scales=SCALES, colors=TETRAHEDRON_COLORS) -> list[Level]:
    """Levels of depth 1 to ``max_depth``."""
    return [compute_level(depth, bases, scales, colors) for depth in range(1, max_depth + 1)]


def save_figure(fig, path, dpi: int = 300) -> None:
    """Save ``fig`` to ``path``, creating missing folders."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi)


def fig_data(path, paper: str = 'a4', dpi: int = 300, tight_layout: bool = False,
             orientation: str = 'landscape') -> tuple:
    """``fig_data`` tuple for the plotting functions (see ``format_plot``)."""
    return paper, orientation, str(path), dpi, tight_layout
