from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import colorsys as csys
import itertools as itools
import sounddevice as sd
import pywt


# Conversion functions

def lcoords_to_int(lcoords: list[int]) -> int:
    return int(''.join(str(d) for d in lcoords), base=4)

def int_to_lcoords(x: int, base: int, depth: int) -> list[int]:
    padding = max(0, depth - len(np.base_repr(x, base=base)))
    if x == 0:
        padding += 1
    return [int(d) for d in np.base_repr(x, base=base, padding=padding)]

def fractional_to_lcoords(x: float, base: int, max_depth: int = 10) -> list[int]:
    g = [x]
    digits = []
    i = 0
    while len(np.unique(np.array(g))) == len(g) and i <= max_depth:
        digits.append(int(np.floor(base * g[-1])))
        g.append(base * g[-1] - digits[-1])
        i += 1
    return digits[:-1]

def lcoords_to_fractional(lcoords: np.ndarray, base: int) -> float:
    x = 0
    for k, lcoord in enumerate(lcoords, 1):
        x += lcoord * base**(-k)
    return x


# Color functions

def indicator_vector(i: int, lcoords: np.ndarray) -> np.ndarray:
    return np.array([int(i == c) for c in lcoords], dtype=int)

def lcoords_to_cmyk(lcoords: np.ndarray, weights: np.ndarray) -> np.ndarray:
    return np.array([np.dot(indicator_vector(i, lcoords), weights) for i in range(4)], dtype=float) / np.sum(weights)

# def lcoords_to_rgb(lcoords: np.ndarray, weights: np.ndarray, subtraction_factor: float):
#     return np.ones(3) - subtraction_factor * lcoords_to_cmyw(lcoords, weights)

def lcoords_to_rgb(lcoords: np.ndarray, weights: np.ndarray) -> np.ndarray:
    cmyk = lcoords_to_cmyk(lcoords, weights)
    return (np.ones(3) - cmyk[:3]) * (1 - cmyk[3])


# Cycle subdivision functions

proportions = np.array([0.4, 0.3, 0.2, 0.1], dtype=float)
offsets = np.insert(np.cumsum(proportions[:-1], dtype=float), 0, 0)

def weights(base: int, depth: int) -> np.ndarray:
    return np.array([base ** (-k) for k in range(1, depth + 1)])

def compute_duration(lcoords: list[int]) -> float:
    return np.prod(proportions[lcoords], dtype=float)

def compute_start(lcoords: list[int]) -> float:
    return np.dot(offsets[lcoords], np.insert(np.cumprod(proportions[lcoords][:-1]), 0, 1))

# def compute_level(depth: int, bases: list[int], subtraction_factor: float | None = None) -> tuple:
#     lcoords = np.array([int_to_lcoords(i, bases[0], depth) for i in range(bases[0]**depth)], dtype=int)
#
#     durations = np.array([compute_duration(lcoord) for lcoord in lcoords], dtype=float)
#     starts = np.array([compute_start(lcoord) for lcoord in lcoords], dtype=float)
#
#     weights = np.array([bases[1] ** (-k) for k in range(1, depth + 1)])
#     if subtraction_factor is None:
#         subtraction_factor = (bases[1] - 1) / (1 - bases[1]**(-depth))
#     colors = np.array([lcoords_to_color(lcoord, weights, subtraction_factor) for lcoord in lcoords], dtype=float)
#
#     return lcoords, durations, starts, colors

def compute_level(depth: int, bases: list[int], total_duration: float | None=None) -> tuple:
    lcoords = np.array([int_to_lcoords(i, bases[0], depth) for i in range(bases[0]**depth)], dtype=int)

    durations = np.array([compute_duration(lcoord) for lcoord in lcoords], dtype=float)
    starts = np.array([compute_start(lcoord) for lcoord in lcoords], dtype=float)
    rgb = np.array([lcoords_to_rgb(lcoord, weights(bases[1], depth)) for lcoord in lcoords], dtype=float)
    cmyk = np.array([lcoords_to_cmyk(lcoord, weights(bases[1], depth)) for lcoord in lcoords], dtype=float)

    if total_duration is not None:
        return lcoords, total_duration * durations, total_duration * starts, rgb, cmyk
    return lcoords, durations, starts, rgb, cmyk

def compute_deeper_subcycles(parent_coords: list[int], extra_depth: int, bases: list[int]) -> tuple:
    start_index = lcoords_to_int(parent_coords + [0] * extra_depth)
    end_index = start_index + bases[0]**extra_depth - 1
    print(start_index, end_index)

    depth = len(parent_coords) + extra_depth

    lcoords = np.array([int_to_lcoords(i, bases[0], depth) for i in range(start_index, end_index)], dtype=int)

    durations = np.array([compute_duration(lcoord) for lcoord in lcoords], dtype=float)
    starts = np.array([compute_start(lcoord) for lcoord in lcoords], dtype=float)
    colors = np.array([lcoords_to_rgb(lcoord, weights(bases[1], depth)) for lcoord in lcoords], dtype=float)

    return lcoords, durations, starts, colors

def select_subcycle(prefix_coords: list[int], level: tuple) -> tuple:
    depth = len(prefix_coords)
    if depth == 0:
        return level
    lcoords, durations, starts, colors = level
    sel_coords = [i for i, lcoord in enumerate(lcoords) if (lcoord[:depth] == prefix_coords).all()]
    return lcoords[sel_coords], durations[sel_coords], starts[sel_coords], colors[sel_coords]

def find_identical(a: np.ndarray, decimals: int) -> list:
    arounded = np.round(a, decimals)
    u, uidx, uinv = np.unique(arounded, axis=0, return_index=True, return_inverse=True)
    uu = uidx[uinv]
    return [(arounded[x], [i for i in range(len(uu)) if uu[i] == x]) for x in uidx]

def find_identical_colors(colors: list[list[float]], decimals: int) -> list:
    colors_rounded = np.round(colors, decimals)
    u, uidx, uinv = np.unique(colors_rounded, axis=0, return_index=True, return_inverse=True)
    uu = uidx[uinv]
    return [(colors_rounded[x], [i for i in range(len(uu)) if uu[i] == x]) for x in uidx]

def subdivision_map(i: int, u: float) -> float:
    return proportions[i] * u + offsets[i]

def find_lcoords(x: float, depth: int) -> np.ndarray:
    lcoords = []
    for d in range(depth):
        for coord, (x1, x2) in enumerate(zip(offsets, offsets + proportions)):
            if x1 <= x < x2:
                lcoords.append(coord)
                break
        x = (x - offsets[lcoords[-1]]) / proportions[lcoords[-1]]
    return np.array(lcoords)

def indentical_duration_lcoords(lcoords: list[int]):
    return set(itools.permutations(lcoords))

def partition_level(level: tuple, subdepth: int, base: int) -> list[tuple]:
    lcoords, durations, starts, rgb, cmyk = level

    depth = len(lcoords[0])
    if depth > subdepth:
        indices = np.arange(base**depth).reshape(base**subdepth, base**(depth - subdepth))
    else:
        return [level]
    return [(lcoords[index], durations[index], starts[index], rgb[index], cmyk[index]) for index in indices]


# Measure functions

def dharma_measure(cmyk: np.ndarray) -> float:
    return np.dot([1, 3/4, 1/2, 1/4], cmyk)

def purity_measure(cmyk: np.ndarray) -> float:
    return np.max(cmyk, axis=0) - np.min(cmyk, axis=0)


# Color plots

def plot_level_bar(ax, index: int, level: tuple):
    lcoords, durations, starts, rgb, cmyk = level

    ax.barh(
        y=index,
        width=durations,
        left=starts,
        height=1,
        align='center',
        color=rgb
    )
    ax.yaxis.set_visible(False)
    ax.xaxis.set_visible(False)
    ax.margins(x=0, y=0)

def plot_level_bars(levels: list[tuple]):
    fig, axs = plt.subplots(nrows=len(levels), ncols=1, sharex=True)
    for i, ax in enumerate(axs):
        plot_level_bar(ax, i, levels[i])
    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()
    fig.set_size_inches(16.5, 11.7)
    # fig.savefig("level_bars_v02.png", dpi=600)

def plot_cmyk_graph(level: tuple):
    lcoords, durations, starts, rgb, cmyk = level

    t = starts + durations / 2

    fig, ax = plt.subplots()
    for i, c in enumerate([(0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 0, 0)]):
        ax.plot(t, cmyk[:, i], color=c)

    plt.tight_layout()
    plt.show()

def plot_rgb_graph(level: tuple):
    lcoords, durations, starts, rgb, cmyk = level

    fig, ax = plt.subplots()
    ax.plot(starts + durations / 2, rgb[:, 0], color='red')
    ax.plot(starts + durations / 2, rgb[:, 1], color='green')
    ax.plot(starts + durations / 2, rgb[:, 2], color='blue')
    # ax.plot(starts + durations / 2, np.max(colors, axis=1) - np.min(colors, axis=1))

    plt.tight_layout()
    plt.show()

def plot_hsv_graph(level: tuple):
    lcoords, durations, starts, rgb, cmyk = level

    hsv = np.array([csys.rgb_to_hsv(c[0], c[1], c[2]) for c in rgb])

    fig, axs = plt.subplots(nrows=3, sharex='col')
    for i, title in enumerate(['Hue', 'Saturation', 'Value']):
        axs[i].plot(starts + durations / 2, hsv[:, i])
        axs[i].set_title(title)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()

def plot_hls_graph(level: tuple):
    lcoords, durations, starts, rgb, cmyk = level

    hls = np.array([csys.rgb_to_hls(c[0], c[1], c[2]) for c in rgb])

    fig, axs = plt.subplots(nrows=3, sharex='col')
    for i, title in enumerate(['Hue', 'Lightness', 'Saturation']):
        axs[i].plot(starts + durations / 2, hls[:, i])
        axs[i].set_title(title)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
    plt.show()

def plot_overlay(level: tuple, base: int):
    lcoords, durations, starts, rgb, cmyk = level

    # hsv = np.array([csys.rgb_to_hsv(rgb[0], rgb[1], rgb[2]) for rgb in colors])
    # hls = np.array([csys.rgb_to_hls(rgb[0], rgb[1], rgb[2]) for rgb in colors])
    dharma = np.array([dharma_measure(c) for c in cmyk])

    fig, ax = plt.subplots()
    ax.barh(
        y=0,
        width=durations,
        left=starts,
        height=dharma,
        align='edge',
        color=rgb
    )
    ax.margins(x=0, y=0)
    plt.tight_layout()
    plt.show()

def plot_purity_and_dharma(ax, level: tuple, base: int):
    lcoords, durations, starts, rgb, cmyk = level

    dharma = np.array([dharma_measure(c) for c in cmyk])
    purity = np.array([purity_measure(c) for c in cmyk])
    # max_duration = np.max(durations, axis=0)
    # sizes = 100 * durations / max_duration

    ax.scatter(
        x=dharma,
        y=purity,
        c=rgb,
        # s=sizes,
        s=10,
        alpha=0.3
    )
    ax.set_xlabel('Dharma')
    ax.set_ylabel('Purity')
    ax.label_outer()
    ax.grid(False)

def plot_quality_grid(levels: list[tuple], base: int):
    ncols = int(np.sqrt(len(levels)))
    nrows = int(len(levels) / ncols)

    w, h = 16.5, 11.7

    fig, axs = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        squeeze=False,
        sharex='all',
        sharey='all',
        subplot_kw=dict(aspect=h/w),
        gridspec_kw=dict(hspace=0, wspace=0)
    )
    fig.set_size_inches(w, h)
    k = 0
    for i in range(nrows):
        for j in range(ncols):
            plot_purity_and_dharma(axs[i, j], levels[k], base)
            # axs[i, j].text(1/4, 1, f"{k+1}", ha='left', va='top')
            axs[i, j].set_title(f"{k+1}")
            k += 1
    plt.tight_layout()
    plt.subplots_adjust(hspace=0, wspace=0)
    plt.show()
    fig.savefig("purity_dharma_grid_v01.png", dpi=600)

def plot_quality_scatter_3d(level: tuple):
    lcoords, durations, starts, rgb, cmyk = level

    dharma = np.array([dharma_measure(c) for c in cmyk])
    purity = np.array([purity_measure(c) for c in cmyk])
    angles = 2 * np.pi * (starts + durations / 2)

    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.scatter(
        xs=purity * np.cos(angles),
        ys=purity * np.sin(angles),
        zs=dharma,
        c=rgb,
        # s=durations,
        s=10,
        alpha=0.5
    )
    ax.set_xlabel('Dharma')
    ax.set_ylabel('Purity')
    ax.set_zlabel('Location')
    plt.margins(x=0, y=0)
    plt.tight_layout()
    plt.show()

def plot_rgb_scatter_3d(level: tuple, subdepth: int|None=None, base: int|None=None):
    lcoords, durations, starts, rgb, cmyk = level

    max_duration = np.max(durations, axis=0)
    sizes = 100 * durations / max_duration

    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.scatter(
        xs=rgb[:, 0],
        ys=rgb[:, 1],
        zs=rgb[:, 2],
        c=rgb,
        s=sizes,
        alpha=0.5
    )

    if subdepth is not None and base is not None:
        part_lcoords, part_durations, part_starts, part_rgb, part_cmyk = partition_level(level, subdepth, base)

        for rgb in part_rgb:
            for i in range(2, len(rgb) + 2):
                ax.plot(
                    xs=rgb[i-2:i, 0],
                    ys=rgb[i-2:i, 1],
                    zs=rgb[i-2:i, 2],
                    c=rgb[i-2]
                )

    ax.axis('off')
    # ax.set_xlabel('Red')
    # ax.set_ylabel('Green')
    # ax.set_zlabel('Blue')
    ax.set_aspect('equal')
    ax.set_proj_type('ortho')
    plt.tight_layout()
    plt.show()


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
        labels = ['' for i in range(len(lcoords))]

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


# Sound functions

def cmyk_to_tone(cmyk: np.ndarray, lcoords: np.ndarray, f0: float=440.0, duration: float=2.0, srate: int=44100, alpha: float=1.5) -> np.ndarray:
    t = np.linspace(0, duration, int(srate * duration), endpoint=False)
    s = np.zeros_like(t)
    nb = lcoords_to_fractional(lcoords, 4)
    for j, amp in enumerate(cmyk):
        for n in range(20):
            harmonic = 4 * n + j + 1
            phase = np.modf(n * nb)[0]
            s += amp * np.sin(2 * np.pi * (harmonic * f0 * t + phase)) / (n + 1)**alpha
    s *= (1 - cmyk[3])
    s /= np.max(np.abs(s) + 1e-9)
    return s

def cmyk_to_fractal_tone(cmyk: np.ndarray, lcoords: np.ndarray, f0: float=110.0, duration: float=2.0, srate: int=44100) -> np.ndarray:
    t = np.linspace(0, duration, int(srate * duration), endpoint=False)
    s = np.zeros_like(t)
    f = f0 * 2**(4 * dharma_measure(cmyk) - 1)
    nb = lcoords_to_fractional(lcoords, 4)
    for n in range(1, 33):
        digits = np.base_repr(n, base=4)
        amp = np.prod(cmyk[[int(d) for d in digits[:-1]]])
        phase = np.modf(n * nb)[0]
        s += amp * np.sin(2 * np.pi * (n * f * t + phase))
    s *= (1 - cmyk[3])
    s /= np.max(np.abs(s) + 1e-9)
    return s

def multilevel_fractal_wavelet_synthesis(levels: list[tuple], total_duration: float, f0: float=110.0, srate: int=44100) -> np.ndarray:
    beta = 0.5
    t = np.linspace(0, total_duration, int(srate * total_duration), endpoint=False)
    s = np.zeros_like(t)
    for depth, (lcoords, durations, starts, rgbs, cmyks) in enumerate(levels, start=1):
        psi = np.zeros_like(t)
        for lcoord, duration, start, cmyk in zip(lcoords, durations, starts, cmyks):
            f = f0 * 2**(4 * dharma_measure(cmyk) - 1)
            tmid = total_duration * (start + duration / 2)
            a2 = (total_duration * duration) ** 2
            for n in range(1, 17):
                digits = np.base_repr(n, base=4)
                amp = np.prod(cmyk[[int(d) for d in digits[:-1]]])
                psi += amp * np.real(np.exp(2 * np.pi * 1j * n * f * (t - tmid) - (t - tmid) ** 2 / (2 * a2)))
        s += beta ** depth * psi
        print(depth)
    s /= np.max(np.abs(s) + 1e-9)
    return s

def fractal_wavelet_synthesis_v01(level: tuple, total_duration: float, f0: float=110.0, srate: int=44100) -> np.ndarray:
    t = np.linspace(0, total_duration, int(srate * total_duration), endpoint=False)
    s = np.zeros_like(t)

    lcoords, durations, starts, rgbs, cmyks = level
    depth = len(lcoords[0])

    for lcoord, duration, start, cmyk in zip(lcoords, durations, starts, cmyks):
        f = f0 * 2**(4 * dharma_measure(cmyk) - 1)
        tmid = total_duration * (start + duration / 2)
        a = total_duration * duration
        gauss = np.exp(-0.5 * ((t - tmid) / a) ** 2)
        tone = np.zeros_like(t)
        for n in range(1, 9):
            amp = np.prod(cmyk[int_to_lcoords(n, 4, depth)])
            tone += amp * np.cos(2 * np.pi * n * f * (t - tmid))
        s += tone * gauss

    peak = np.max(np.abs(s))
    if peak > 0:
        s /= peak
    return s

def fractal_wavelet_synthesis_v02(level: tuple, T: float, f0: float=55.0, A: float=1.0, beta: float=0.4, srate: int=44100) -> tuple:
    t = np.linspace(0, T, int(srate * T), endpoint=False)
    s = np.zeros_like(t)

    lcoords, durations, starts, _, cmyks = level
    depth = len(lcoords[0])

    for i, (lcoord, duration, start, cmyk) in enumerate(zip(lcoords, durations, starts, cmyks)):
        tmid = T * (start + duration / 2)
        sigma = beta * duration * T
        gauss = np.exp(-0.5 * ((t - tmid) / sigma) ** 2)
        tone = np.zeros_like(t)
        for k, alpha in enumerate(lcoord):
            freq = f0 * (4 ** (depth - k)) * (4 - alpha)
            # tone += cmyk[alpha] * np.cos(2 * np.pi * freq * (t - tmid))
            tone += np.cos(2 * np.pi * freq * (t - tmid))
        tone /= depth
        s += A * tone * gauss
        if (i + 1) % 4**(depth-1) == 0:
            print(i + 1)

    peak = np.max(np.abs(s))
    if peak > 0:
        s /= peak
    return s, t


def compute_scalogram(signal, sr, wavelet='cmor1.5-1.0', num_scales=256, f_min=20.0, f_max=8000.0):
    """
    Compute and plot the scalogram of a signal.

    signal   : 1D numpy array, the audio signal
    sr       : int, sample rate in Hz
    wavelet  : str, complex Morlet wavelet specification
               'cmor{bandwidth}-{center_freq}'
    num_scales: int, number of frequency bins
    f_min    : float, minimum frequency in Hz
    f_max    : float, maximum frequency in Hz
    """
    # Build frequency array (logarithmically spaced)
    freqs = np.logspace(np.log10(f_min), np.log10(f_max), num_scales)

    # Convert frequencies to scales for the chosen wavelet
    # pywt.scale2frequency(wavelet, scale, precision) gives f = f_c / scale
    # so scale = f_c / freq (where f_c is the centre frequency of the wavelet)
    scales = pywt.central_frequency(wavelet) * sr / freqs

    # Compute CWT
    coefficients, cwt_freqs = pywt.cwt(signal, scales, wavelet, sampling_period=1.0/sr)
    # coefficients shape: (num_scales, len(signal))
    scalogram = np.abs(coefficients) ** 2

    return scalogram, cwt_freqs

def plot_scalogram(scalogram, freqs, sr, signal_duration, title='Scalogram of the Fractal of Ages'):
    """
    Plot the scalogram with time on the x-axis and
    frequency on the y-axis (log scale).
    """
    num_scales, num_time = scalogram.shape
    times = np.linspace(0, signal_duration, num_time)

    w, h = 16.5, 11.7
    fig, ax = plt.subplots(figsize=(w, h))

    # Use logarithmic colour scale for better dynamic range
    power = scalogram
    vmin  = np.percentile(power[power > 0], 5)
    vmax  = np.percentile(power, 99)
    norm  = mcolors.LogNorm(vmin=max(vmin, 1e-12), vmax=vmax)

    img = ax.pcolormesh(times, freqs, power, norm=norm, cmap='inferno', shading='auto')
    plt.colorbar(img, ax=ax, label='Power')

    ax.set_yscale('log')
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Frequency (Hz)', fontsize=12)
    ax.set_title(title, fontsize=14)

    # Mark the four top-level age boundaries
    props  = [0.4, 0.3, 0.2, 0.1]
    labels = ['Golden', 'Silver', 'Bronze', 'Iron']
    colors = ['gold', 'silver', '#cd7f32', '#8888aa']
    cum = 0.0
    for i, (p, label, col) in enumerate(zip(props, labels, colors)):
        ax.axvspan(cum * signal_duration,
                   (cum + p) * signal_duration,
                   alpha=0.08, color=col, label=label)
        ax.axvline(cum * signal_duration,
                   color='white', linewidth=0.5, alpha=0.6)
        ax.text((cum + p/2) * signal_duration,
                freqs[-1] * 0.7, label,
                ha='center', fontsize=9, color='white', alpha=0.8)
        cum += p

    # ax.legend(loc='upper right', fontsize=8, framealpha=0.4)
    ax.legend().set_visible(False)
    plt.tight_layout()
    plt.savefig('scalogram.png', dpi=600, bbox_inches='tight')
    plt.show()
    return fig, ax

if __name__ == "__main__":
    # Compute levels
    # manvantara = 64800
    bases = [4, 2]

    # nrows = 3
    # ncols = 3
    # num_levels = nrows * ncols
    # num_levels = 5
    # levels = [compute_level(depth, bases) for depth in range(1, num_levels+1)]
    # levels = [compute_level(depth, bases, manvantara) for depth in range(1, num_levels + 1)]

    # Uniqueness of colors
    # print([len(np.unique(level[3], axis=0)) == len(level[3]) for level in levels])
    # print([all([len(x[1]) == 1 for x in find_identical(level[3], 10)]) for level in levels])

    # Plot level bars
    # plot_level_bars(levels)

    # Plot quality grid
    # plot_quality_grid(levels, bases[1], nrows, ncols)

    # Plot color graphs
    # level = compute_level(6, bases)
    # plot_cmyk_graph(level)
    # plot_rgb_graph(level)
    # plot_hsv_graph(level)
    # plot_hls_graph(level)
    # plot_overlay(level, bases[1])
    # plot_rgb_scatter_3d(level)
    # plot_rgb_scatter_3d(level, 1, bases[0])
    # plot_quality_scatter_3d(level)

    # fig, ax = plt.subplots()
    # plot_purity_and_dharma(ax, level, bases[1])
    # plt.tight_layout()
    # plt.show()
    # fig.savefig("purity_dharma_v01.png", dpi=600)

    # part_level = partition_level(level, 2, bases[0])
    # plot_quality_grid(part_level, bases[1])


    # extra_depth = 6
    # parent_coords = [[0], [1], [2], [3]]
    # subcycles = [compute_deeper_subcycles(coords, extra_depth, bases) for coords in parent_coords]
    # side = int(np.sqrt(len(parent_coords)))
    # fig, axs = plt.subplots(
    #     ncols=side,
    #     nrows=side,
    #     sharex=True,
    #     sharey=True,
    #     subplot_kw=dict(aspect=1),
    #     gridspec_kw=dict(hspace=0, wspace=0)
    # )
    # for i in range(side):
    #     for j in range(side):
    #         plot_purity_and_dharma(axs[i, j], subcycles[j * side + i])
    # plt.show()


    # lcoords, durations, starts, colors = level
    # hsv = np.array([csys.rgb_to_hsv(*rgb) for rgb in colors])
    # xx = find_identical(hsv[:, 0] * (1.0 - hsv[:, 1]), 10)
    # xx = find_identical(colors[:, 2], 10)
    # xxx = np.array([[x[0], np.sum(durations[x[1]])] for x in xx])
    # fig, ax = plt.subplots()
    # ax.plot(xxx[:,0], xxx[:,1])
    # plt.show()

    # Subcycle comparison graphs
    # selectors = [([], levels[0])] + [([i], levels[1]) for i in range(4)]
    # subcycles = [select_subcycle(*sel) for sel in selectors]
    # plot_comparison_graph(subcycles)

    # Identical durations
    # xx = find_identical_durations(levels[2][1], 10)
    # for x in xx:
    #     print(x)

    # print(int_to_lcoords(41, 4, 3))
    # yy = indentical_duration_lcoords([0,3,1])
    # for y in yy:
    #     print(y, lcoords_to_int(list(y)), compute_duration(list(y)))

    # Relation between identical duration subcycles
    # fig, axs = plt.subplots(1, 2, figsize=(25, 50))
    # for i, ax in enumerate(axs, start=1):
    #     plot_identical_graph(ax, levels[i], find_identical_durations(levels[i][1], 10), ref_level=levels[0], one_to_many=True, show_labels=False)
    # plt.tight_layout()
    # plt.show()

    # Sound waves: Fourier
    # lcoords, durations, starts, rgb, cmyk = compute_level(3, bases, total_duration=60)
    # for c, l, d in zip(cmyk, lcoords, durations):
    #     signal = cmyk_to_fractal_tone(c, l, f0=110, duration=d)
    #     sd.play(signal, samplerate=44100)
    #     sd.wait()

    # Sound wave: multi-level wavelet
    # num_levels = 3
    # levels = [compute_level(depth, bases) for depth in range(1, num_levels+1)]
    # signal = multilevel_fractal_wavelet_synthesis(levels, 60)
    # sd.play(signal, samplerate=44100)
    # sd.wait()

    # Sound wave: single-level wavelet
    level = compute_level(4, bases)
    total_duration = 32.0
    srate = 44100
    signal, t_axis = fractal_wavelet_synthesis_v02(level, T=total_duration, srate=srate, beta=1.0/(2.0*np.sqrt(2*np.log(2))))
    sd.play(signal, samplerate=srate)
    sd.wait()

    scalogram, freqs = compute_scalogram(signal, srate, num_scales=256, f_min=30.0, f_max=srate/2)
    plot_scalogram(scalogram, freqs, srate, total_duration)

    """
    # Checks
    depth = 3
    bases = [4, 4]
    total_duration = 64800
    indices = [x for x in range(4**depth)]
    lcoords = [int_to_lcoords(index, bases[1], depth) for index in indices]
    fracs = [lcoords_to_fractional(coord, bases[0]) for coord in lcoords]
    ivectors = [[indicator_vector(i, coord) for i in range(1, 4)] for coord in lcoords]
    rgb = [lcoords_to_rgb(coord, bases[1]) for coord in lcoords]
    sfactor =  (bases[1] - 1) / (1 - bases[1]**(-depth))
    colours = [lcoords_to_colour(coord, sfactor, bases[1]) for coord in lcoords]
    rgb_check = [c[0] + 2 * c[1] + 3 * c[2] for c in rgb]
    tag_check = [fractional_to_lcoords(x, bases[1]) for x in rgb_check]
    durations = [compute_duration(lcoord, total_duration) for lcoord in lcoords]
    dur_check = np.sum(durations)
    starts = [compute_start(lcoord, total_duration) for lcoord in lcoords]
    end_check = starts[-1] + durations[-1]

    print(offsets)
    print([proportions[lcoords[1][:k]] for k in range(len(lcoords[1]))])
    print(dur_check)
    print(end_check)
    for i in range(len(indices)):
        print(indices[i],
              lcoords[i],
              fracs[i],
              ivectors[i],
              rgb[i],
              colours[i],
              rgb_check[i],
              tag_check[i],
              durations[i],
              starts[i])
    """