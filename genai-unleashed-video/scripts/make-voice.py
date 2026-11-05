"""Generates the voiceover lines and post-processes them so they sit like a mic recording.

Usage: make-voice.py <output directory>
Prints the pauses in each line so src/Composition.tsx can sync its text to the words.
"""
import asyncio
import subprocess
import sys
from pathlib import Path

import edge_tts
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
VOICE = "en-US-BrianMultilingualNeural"
# Commas and ellipses are the pauses: the voice phrases a single sentence better than joined clips.
LINES = {
    "vo-open": ("This is Gopinath... the speaker, explaining Gen A.I.", "-6%", "-2Hz"),
    "vo-close": (
        "Thank you, to everyone who showed up... This was, Gen A.I. Unleashed.",
        "-8%",
        "-3Hz",
    ),
}

rng = np.random.default_rng(7)


def decode(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(float) / 32768


def drift(voice):
    """Slowly wanders pitch and pace by about half a percent, as a person never holds either still."""
    n = len(voice)
    knots = np.interp(np.arange(n), np.linspace(0, n, n // (SR // 3) + 2), rng.normal(0, 0.005, n // (SR // 3) + 2))
    return np.interp(np.cumsum(1 + knots), np.arange(n), voice, right=0)


def tone(voice):
    """Rolls off rumble, warms the chest, and tames the 2-4 kHz edge synthetic voices tend to have."""
    voice = sosfilt(butter(2, 80, "highpass", fs=SR, output="sos"), voice)
    edge = sosfilt(butter(2, [2000, 4000], "bandpass", fs=SR, output="sos"), voice)
    chest = sosfilt(butter(2, [120, 300], "bandpass", fs=SR, output="sos"), voice)
    return voice - 0.25 * edge + 0.18 * chest


def compress(voice, threshold=0.18, ratio=2.5):
    """Soft compression with a 60 ms detector, enough to level words without pumping."""
    size = int(0.06 * SR)
    level = np.sqrt(np.convolve(voice**2, np.ones(size) / size, mode="same")) + 1e-6
    over = np.maximum(level / threshold, 1)
    return voice * over ** (1 / ratio - 1)


def room(voice):
    """A small, quiet room: a short decaying tail plus tone under everything so silence is not digital."""
    t = np.arange(int(0.22 * SR)) / SR
    tail = rng.standard_normal(len(t)) * np.exp(-t / 0.05)
    tail = sosfilt(butter(2, [300, 5000], "bandpass", fs=SR, output="sos"), tail)
    wet = fftconvolve(voice, tail)[: len(voice)]
    wet *= 0.07 * np.max(np.abs(voice)) / np.max(np.abs(wet))
    bed = sosfilt(butter(1, 1500, "lowpass", fs=SR, output="sos"), rng.standard_normal(len(voice)))
    bed *= 10 ** (-58 / 20) / np.sqrt(np.mean(bed**2))
    return voice + wet + bed


def pauses(voice):
    """Returns (start, end) of each gap in the speech, measured on a 20 ms loudness window."""
    hop = int(0.02 * SR)
    n = len(voice) // hop
    rms = np.sqrt((voice[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
    quiet = rms < 0.02 * rms.max()
    gaps, start = [], None
    for i, q in enumerate(quiet):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if (i - start) * 0.02 >= 0.12:
                gaps.append((round(start * 0.02, 2), round(i * 0.02, 2)))
            start = None
    return gaps


async def main(out):
    out.mkdir(exist_ok=True)
    for name, (text, rate, pitch) in LINES.items():
        raw = out / f"{name}-raw.mp3"
        await edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch).save(str(raw))
        voice = decode(raw)
        voice = room(compress(tone(drift(voice))))
        voice *= 10 ** (-3 / 20) / np.max(np.abs(voice))
        wavfile.write(out / f"{name}.wav", SR, (voice * 32767).astype(np.int16))
        print(f"{name}: {len(voice) / SR:.2f}s gaps={pauses(voice)}")


asyncio.run(main(Path(sys.argv[1])))
