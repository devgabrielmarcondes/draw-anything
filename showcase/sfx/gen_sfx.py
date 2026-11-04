"""Make the sound effects of the showcase video from code (no recorded samples).
Usage: python sfx/gen_sfx.py   (writes sfx/*.wav, 48 kHz mono)"""
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
OUT = Path(__file__).resolve().parent
rng = np.random.default_rng(7)


def t(sec):
    return np.arange(int(SR * sec)) / SR


def band(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def env(n, attack, decay):
    """Fast attack, exponential decay (seconds)."""
    x = np.arange(n) / SR
    return np.minimum(1, x / max(attack, 1e-4)) * np.exp(-x / decay)


def save(name, x, peak=0.9):
    x = x / (np.abs(x).max() + 1e-9) * peak
    wavfile.write(OUT / f"{name}.wav", SR, (x * 32767).astype(np.int16))


def key(seed):
    r = np.random.default_rng(seed)
    n = int(SR * 0.05)
    x = band(r.standard_normal(n), 1800 + 600 * r.random(), 6000) * env(n, 0.0005, 0.006)
    x += 0.3 * np.sin(2 * np.pi * (250 + 60 * r.random()) * t(0.05)) * env(n, 0.001, 0.01)
    return x


for i in range(4):                                      # typing: four slightly different keys
    save(f"key{i}", key(i), 0.6)

n = int(SR * 0.12)                                      # enter: lower, longer key
save("enter", band(rng.standard_normal(n), 400, 3000) * env(n, 0.0005, 0.02)
     + 0.6 * np.sin(2 * np.pi * 140 * t(0.12)) * env(n, 0.001, 0.03), 0.8)

n = int(SR * 0.06)                                      # click: UI click
save("click", band(rng.standard_normal(n), 2500, 9000) * env(n, 0.0003, 0.004)
     + 0.5 * np.sin(2 * np.pi * 1800 * t(0.06)) * env(n, 0.0005, 0.008), 0.7)

x = t(0.14)                                             # pop: a card lands, a chip attaches
f = 520 + 600 * np.exp(-x / 0.02)
save("pop", np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(x), 0.002, 0.04), 0.7)

x = t(0.09)                                             # blip: a new line in the terminal
save("blip", (np.sin(2 * np.pi * 1320 * x) + 0.3 * np.sin(2 * np.pi * 2640 * x)) * env(len(x), 0.003, 0.025), 0.5)

x = t(0.04)                                             # tick: agent name changes
save("tick", np.sin(2 * np.pi * 2200 * x) * env(len(x), 0.0005, 0.007), 0.5)


def chime(notes, sec=1.6, gap=0.07):
    x = t(sec); y = np.zeros_like(x)
    for i, hz in enumerate(notes):
        d = int(SR * gap * i); n = len(x) - d
        part = sum(a * np.sin(2 * np.pi * hz * m * x[:n]) for m, a in ((1, 1), (2, 0.25), (3, 0.08)))
        y[d:] += part * env(n, 0.004, 0.45)
    return y


save("chime", chime([1318.5, 1975.5]), 0.55)            # done: E6, B6
save("shimmer", chime([880, 1318.5, 1760, 2637], 2.0, 0.05), 0.5)


def whoosh(sec, lo, hi):
    """Noise through a band that sweeps up and back down; loudest in the middle."""
    x = t(sec); n = len(x)
    noise = rng.standard_normal(n); y = np.zeros(n)
    k = 32
    for i in range(k):                                  # piecewise filter sweep
        a, b = i * n // k, (i + 1) * n // k
        c = lo + (hi - lo) * np.sin(np.pi * (a + b) / 2 / n)
        y[a:b] = band(noise[max(0, a - 2000):b], c * 0.6, c * 1.6)[-(b - a):]
    return y * np.sin(np.pi * x / sec) ** 2


save("whoosh", whoosh(0.6, 400, 2400), 0.7)
save("swish", whoosh(0.35, 900, 3500), 0.5)             # drag

n = int(SR * 0.35)                                      # drop: soft low thud
x = t(0.35)
save("drop", np.sin(2 * np.pi * np.cumsum(90 + 80 * np.exp(-x / 0.03)) / SR) * env(n, 0.002, 0.08)
     + 0.15 * band(rng.standard_normal(n), 200, 1500) * env(n, 0.001, 0.02), 0.8)
