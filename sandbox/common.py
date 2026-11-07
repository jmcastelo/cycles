"""Paths, default parameters and helpers shared by the sandbox studies."""

from pathlib import Path

from cycles.functions.division import (
    COLOR_KEYS, DEFAULT_BASES, DEFAULT_SCALES, TETRAHEDRON_COLORS, Level, compute_level, level_colors,
)

SANDBOX_DIR = Path(__file__).resolve().parent
PLOTS_DIR = SANDBOX_DIR / "plots"
DATA_DIR = SANDBOX_DIR / "data"
SOUNDS_DIR = SANDBOX_DIR / "sounds"

# Default parameters (see cycles.functions.division); a session given to the runner (--session) replaces them
BASES = DEFAULT_BASES
SCALES = DEFAULT_SCALES
MODEL = None        # the cycle model of a session, if one was given (else each study chooses its own)
SESSION = None      # the whole session (a dict), if one was given

__all__ = ['SANDBOX_DIR', 'PLOTS_DIR', 'DATA_DIR', 'SOUNDS_DIR', 'BASES', 'SCALES', 'TETRAHEDRON_COLORS',
           'COLOR_KEYS', 'MODEL', 'SESSION', 'compute_levels', 'level_colors', 'save_figure', 'fig_data',
           'apply_session']


def compute_levels(max_depth: int, bases=None, scales=None, colors=None) -> list[Level]:
    """Levels of depth 1 to ``max_depth`` (with the current parameters unless given)."""
    bases = BASES if bases is None else bases
    scales = SCALES if scales is None else scales
    colors = TETRAHEDRON_COLORS if colors is None else colors
    return [compute_level(depth, bases, scales, colors) for depth in range(1, max_depth + 1)]


def apply_session(data: dict, module=None) -> str:
    """
    Use the cycle model and the color parameters of a session saved by the
    explorer: here, and in ``module`` (the running study script, which
    imported them by name). Returns a one-line description.
    """
    import numpy as np
    from cycles.functions.cycle_model import CycleModel
    global BASES, SCALES, TETRAHEDRON_COLORS, MODEL, SESSION
    if not isinstance(data, dict) or data.get('format') != 'cycles-session':
        raise ValueError('not a cycles session file')
    state = data.get('state', {})
    values = {}
    parameters = state.get('color_parameters')
    if parameters:
        values['BASES'] = [float(b) if float(b) % 1 else int(b) for b in parameters['bases']]
        values['SCALES'] = [float(x) for x in parameters['scales']]
        values['TETRAHEDRON_COLORS'] = np.asarray(parameters['colors'], dtype=float)
    values['MODEL'] = CycleModel.from_dict(state['model']) if state.get('model') else None
    values['SESSION'] = data
    for name, value in values.items():
        globals()[name] = value
        if module is not None and hasattr(module, name):
            setattr(module, name, value)
    model = values['MODEL']
    return (f"cycle model {model.name!r}" if model else 'normalized time') + \
        (f", color bases {values['BASES']} and scales {values['SCALES']}" if parameters else '')


def save_figure(fig, path, dpi: int = 300) -> None:
    """Save ``fig`` to ``path``, creating missing folders."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi)


def fig_data(path, paper: str = 'a4', dpi: int = 300, tight_layout: bool = False,
             orientation: str = 'landscape') -> tuple:
    """``fig_data`` tuple for the plotting functions (see ``format_plot``)."""
    return paper, orientation, str(path), dpi, tight_layout
