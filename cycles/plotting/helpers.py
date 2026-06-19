import matplotlib.pyplot as plt
import papersize as ps
from pathlib import Path


def save_plot(fig: plt.Figure, fig_data: tuple[str, str, str, int]):
    paper_type, orientation_type, fig_path, dpi = fig_data

    orientation = ps.LANDSCAPE
    if orientation_type.lower() == 'portrait':
        orientation = ps.PORTRAIT

    psize = ps.rotate(ps.parse_papersize(paper_type, 'in'), orientation)
    figsize = (float(psize[0]), float(psize[1]))

    Path(fig_path).parent.mkdir(parents=True, exist_ok=True)

    fig.set_size_inches(figsize)
    fig.savefig(fig_path, dpi=dpi)