import numpy as np
import matplotlib.pyplot as plt


def plot_sectors(
    ax,
    wedge_sizes: np.ndarray,
    radius: float,
    wedge_width: float,
    colors: np.ndarray | list,
    labels: list[str] | None = None,
    labeldistance: float | None = None,
):
    ax.pie(
        x = wedge_sizes,
        radius=radius,
        colors=colors,
        labels=labels,
        rotatelabels=True,
        labeldistance=labeldistance,
        wedgeprops=dict(width=wedge_width, edgecolor='k', linewidth=0.1),
        textprops={'fontsize': 6}
    )


def plot_partition_sectors(
    t1: float,
    t2: float,
    dt: float,
    part_durations: np.ndarray,
    part_colors: np.ndarray,
):
    fig, ax = plt.subplots()

    # Reference sectors

    nrefs = int((t2 - t1) / dt)
    ref_sizes = np.full((nrefs,), dt)
    ref_colors = ['lightblue'] * nrefs

    ref_radius = 1.0
    ref_width = 0.3
    labeldistance = 1.0 - 0.5 * ref_width / ref_radius

    radius = ref_radius + ref_width
    width = ref_width

    plot_sectors(
        ax,
        ref_sizes,
        ref_radius,
        ref_width,
        ref_colors
    )

    plot_sectors(
        ax,
        part_durations,
        radius,
        width,
        part_colors
    )

    ax.set_aspect(1)

    plt.show()