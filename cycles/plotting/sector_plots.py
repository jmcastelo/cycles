import numpy as np
import matplotlib.pyplot as plt

from cycles.conversion_functions import lcoords_to_int
from cycles.cycle_division_functions import partition_level

# Sector plots

def fix_pie_labels(wedges, texts, mode="radial"):
    """
    Correctly center-align rotated pie labels.
    mode: "radial"     — text points outward from center
          "tangential" — text runs along the arc
    """
    for text, wedge in zip(texts, wedges):
        mid = (wedge.theta1 + wedge.theta2) / 2

        if mode == "radial":
            rot = mid + (180 if 90 < mid < 270 else 0)
        else:
            rot = mid - 90 + (180 if 90 < mid < 270 else 0)

        text.set_rotation(rot)
        text.set_rotation_mode("anchor")
        text.set_ha("center")
        text.set_va("center")

def plot_comparison_graph(subcycles: list):
    fig, ax = plt.subplots(figsize=(25, 25))

    num_indices = len(subcycles)
    scale = 1.6
    width = scale / num_indices

    for i, (lcoords, durations, starts, colors) in enumerate(subcycles):
        labels = [f"{starts[j]:.1f} ({durations[j]:.2f}): {lcoords_to_int(lcoords[j]) + 1}" for j in range(len(lcoords))]

        radius = width * (i + 1.0)
        labeldistance = 1.0 - 0.6 * width / radius

        ax.pie(
            durations,
            radius=radius,
            colors=colors,
            labels=labels,
            rotatelabels=True,
            labeldistance=labeldistance,
            wedgeprops=dict(width=width, edgecolor='k', linewidth=0.1),
            textprops={'fontsize': 6}
        )

    ax.set_aspect(1)
    fig.tight_layout()
    plt.show()

def plot_identical_graph(ax, level: tuple, identical: list, ref_level: tuple|None=None, one_to_many: bool=False, show_labels=True):
    lcoords, durations, starts, rgb, cmyk = level

    if show_labels:
        labels = [f"{starts[j]:.1f} ({durations[j]:.2f}): {lcoords_to_int(lcoords[j]) + 1}" for j in range(len(lcoords))]
    else:
        labels = ['' for _ in range(len(lcoords))]

    explode = np.zeros(durations.size) - 0.025
    singletons = [idx for _, idx in identical if len(idx) == 1]
    explode[singletons] = 0

    radius = 1.6
    width = 0.3
    labeldistance = 1.0 - 0.5 * width / radius

    if ref_level is not None:
        ref_lcoords, ref_durations, ref_starts, ref_rgb, ref_cmyk = ref_level
        ref_labels = [f"{ref_starts[j]:.1f} ({ref_durations[j]:.2f}): {lcoords_to_int(ref_lcoords[j]) + 1}" for j in range(len(ref_lcoords))]

        ref_radius = radius + width
        ref_width = width
        ref_labeldistance = 1.0 - 0.5 * ref_width / ref_radius

        ref_wedges, ref_texts = ax.pie(
            ref_durations,
            radius=ref_radius,
            colors=ref_rgb,
            labels=ref_labels,
            rotatelabels=True,
            labeldistance=ref_labeldistance,
            wedgeprops=dict(width=ref_width, edgecolor='k', linewidth=0.1),
            textprops={'fontsize': 6}
        )

        fix_pie_labels(ref_wedges, ref_texts)

    wedges, texts = ax.pie(
        durations,
        radius=radius,
        colors=rgb,
        explode=explode,
        labels=labels,
        rotatelabels=False,
        labeldistance=labeldistance,
        wedgeprops=dict(width=width, edgecolor='k', linewidth=0.1),
        textprops={'fontsize': 6}
    )

    fix_pie_labels(wedges, texts)

    def wedge_midpoint(wedge, r: float):
        """Return (x, y) at the midpoint angle of a wedge."""
        theta = np.radians((wedge.theta1 + wedge.theta2) / 2)
        cx, cy = wedge.center
        return float(cx + r * np.cos(theta)), float(cy + r * np.sin(theta))

    # Connecting curves
    for _, indices in identical:
        if len(indices) > 1:
            for i in range(1, len(indices)):
                if one_to_many:
                    coords0 = wedge_midpoint(wedges[indices[0]], radius - width)
                    color = rgb[indices[0]]
                    arrowstyle = '<|-'
                    rad = 0.5 * (1 - (wedges[indices[i]].theta1 - wedges[indices[0]].theta1) / 180)
                else:
                    coords0 = wedge_midpoint(wedges[indices[i-1]], radius - width)
                    color = rgb[indices[i - 1]]
                    arrowstyle = '-'
                    rad = 0.5 * (1 - (wedges[indices[i]].theta1 - wedges[indices[i-1]].theta1) / 180)

                coords1 = wedge_midpoint(wedges[indices[i]], radius - width)

                for c, lw in [("black", 1.5), (color, 1.0)]:
                    ax.annotate(
                        text='',
                        xy=coords0,
                        xytext=coords1,
                        annotation_clip=False,
                        arrowprops=dict(
                            arrowstyle=arrowstyle,
                            color=c,
                            linewidth=lw,
                            connectionstyle=f"arc3,rad={rad}",
                            shrinkA=0,
                            shrinkB=0,
                            antialiased=True
                        )
                    )

    ax.set_aspect(1)
    # fig.tight_layout()
    # plt.show()

def plot_circle_diagram(levels: list[tuple], base: int):
    fig, ax = plt.subplots()

    circle = plt.Circle(
        xy=(0.0, 0.0),
        radius=1.0 / (2.0 * np.pi),
        color='lightgray'
    )
    ax.add_patch(circle)

    xy = [(0.0, 0.0)]
    r = [1.0 / (2.0 * np.pi)]
    s = [0.0]

    partitions = [partition_level(level, subdepth, base) for subdepth, level in enumerate(levels)]

    for depth, partition in enumerate(partitions, start=1):
        new_xy = []
        new_start = []
        new_radius = []
        for i, (lcoords, durations, starts, rgbs, cmyks) in enumerate(partition):
            j = int(np.modf(i)[1])
            base_xy = xy[j]
            base_start = s[j]
            base_radius = r[j]

            for duration, start, rgb in zip(durations, starts, rgbs):
                radius = duration / (2.0 * np.pi)
                angle = 2.0 * np.pi * (start - base_start)
                x = base_xy[0] + (base_radius + radius) * np.cos(angle)
                y = base_xy[1] + (base_radius + radius) * np.sin(angle)
                coords = (x, y)

                new_xy.append(coords)
                new_start.append(angle)
                new_radius.append(radius)

                circle = plt.Circle(
                    xy=coords,
                    radius=radius,
                    color=rgb
                )
                ax.add_patch(circle)

        xy = new_xy
        r = new_radius
        s = new_start

    ax.axis('off')
    ax.relim()
    ax.autoscale_view()
    ax.set_aspect(1)
    plt.show()
