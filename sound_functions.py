import numpy as np
import pywt
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from conversion_functions import lcoords_to_fractional, int_to_lcoords
from measure_functions import dharma_measure

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
    plt.savefig('./PNGs/scalogram.png', dpi=600, bbox_inches='tight')
    plt.show()
    return fig, ax