import matplotlib.pyplot as plt
import papersize as ps
from pathlib import Path


def format_plot(fig: plt.Figure, fig_data: tuple[str, str, str, int, bool], save_fig: bool=False):
    paper_type, orientation_type, fig_path, dpi, tight_layout = fig_data

    orientation = ps.LANDSCAPE
    if orientation_type.lower() == 'portrait':
        orientation = ps.PORTRAIT

    psize = ps.rotate(ps.parse_papersize(paper_type, 'in'), orientation)
    figsize = (float(psize[0]), float(psize[1]))

    fig.set_size_inches(figsize)
    if tight_layout:
        fig.tight_layout()

    if save_fig:
        Path(fig_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(fig_path, dpi=dpi)