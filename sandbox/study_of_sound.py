"""
Study of sounds synthesised from subcycles.

With --save the sounds are written as WAV files to sandbox/sounds; without
--no-show they are played (needs the sounddevice package).
"""

import wave

import numpy as np

from cycles.functions.sound import (
    cmyk_to_fractal_tone,
    multilevel_fractal_wavelet_synthesis,
    fractal_wavelet_synthesis_v01,
    fractal_wavelet_synthesis_v02,
    compute_scalogram,
    plot_scalogram,
)
from common import PLOTS_DIR, SOUNDS_DIR, compute_levels
from runner import study, run

SAMPLE_RATE = 44100


def setup():
    return dict(
        levels=compute_levels(4),
        f0=110.0,
        seconds=60.0,           # length of the tone sequence and of the wavelet syntheses
        wavelet_seconds=32.0,   # length of the single-level wavelet synthesis (v02)
    )


def _output(signal: np.ndarray, name: str, opts) -> None:
    """Save the signal as a 16-bit WAV file and/or play it."""
    if opts.save:
        SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
        path = SOUNDS_DIR / f"{name}.wav"
        with wave.open(str(path), 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(SAMPLE_RATE)
            f.writeframes((np.clip(signal, -1, 1) * 32767).astype('<i2').tobytes())
        print(f"Saved {path}")
    if opts.show:
        import sounddevice as sd
        sd.play(signal, samplerate=SAMPLE_RATE)
        sd.wait()


@study
def fractal_tones(ctx, opts):
    """Sequence of the tones of the depth-3 subcycles, each lasting its share of the total."""
    level = ctx.levels[2]
    tones = [cmyk_to_fractal_tone(cmyk, lcoords, f0=ctx.f0, duration=ctx.seconds * duration, srate=SAMPLE_RATE)
             for cmyk, lcoords, duration in zip(level.cmyk(), level.lcoords, level.durations)]
    _output(np.concatenate(tones), 'fractal_tones_depth_3', opts)


@study(default=False)
def multilevel_wavelets(ctx, opts):
    """Wavelet synthesis of depths 1 to 3 together (slow)."""
    signal = multilevel_fractal_wavelet_synthesis(ctx.levels[:3], ctx.seconds, f0=ctx.f0, srate=SAMPLE_RATE)
    _output(signal, 'multilevel_wavelets_depths_1_3', opts)


@study(default=False)
def wavelets_v01(ctx, opts):
    """Wavelet synthesis of depth 3, each subcycle a tone with 8 color-weighted partials."""
    signal = fractal_wavelet_synthesis_v01(ctx.levels[2], ctx.seconds, f0=ctx.f0, srate=SAMPLE_RATE)
    _output(signal, 'wavelets_v01_depth_3', opts)


@study(default=False)
def wavelets_v02_scalogram(ctx, opts):
    """Wavelet synthesis of depth 4 (each subcycle a chord of its digits) and its scalogram (memory hungry)."""
    seconds = ctx.wavelet_seconds
    beta = 1.0 / (2.0 * np.sqrt(2 * np.log(2)))  # Gaussian with full width at half maximum = duration
    signal, _ = fractal_wavelet_synthesis_v02(ctx.levels[3], T=seconds, srate=SAMPLE_RATE, beta=beta)
    _output(signal, 'wavelets_v02_depth_4', opts)
    scalogram, freqs = compute_scalogram(signal, SAMPLE_RATE, num_scales=256, f_min=30.0, f_max=SAMPLE_RATE / 2)
    plot_scalogram(scalogram, freqs, SAMPLE_RATE, seconds,
                   save_path=PLOTS_DIR / 'study_of_sound' / 'scalogram_v02_depth_4.png' if opts.save else None)


if __name__ == "__main__":
    run(setup)
