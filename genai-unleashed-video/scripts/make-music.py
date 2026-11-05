"""Shapes the licensed track around the edit: filtered builds, open drops, impact hits.

Usage: make-music.py <source audio> <output wav> <opening voiceover> <closing voiceover>
Prints the tempo that src/Composition.tsx needs for its BPM constant.
"""
import subprocess
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 44100
FPS = 30
TOTAL_BEATS = 116
WORD_HITS = [16, 17, 18, 19, 21]
IMPACTS = [0, 6, 24, 64, 94]
WHOOSHES = [4, 16, 28, 32, 36, 38, 40, 44, 48, 52, 56, 68, 72, 76, 84]
# (beat the riser lands on, seconds it takes to climb)
RISERS = [(16, 1.5), (24, 1.2), (64, 1.5)]
FINALE_BEAT = 94
# (beat, delay in frames, music level under the voice)
VOICES = [(0, 10, 0.4), (94, 20, 0.25)]
# (start beat, end beat, cutoff at start, cutoff at end): the track opens up across each range.
BUILDS = [(0, 16, 700, 1600), (16, 24, 900, 9000), (56, 64, 500, 9000)]

rng = np.random.default_rng(150)


def load(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(SR), "-f", "s16le", "-"],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.int16).reshape(-1, 2).astype(float) / 32768


def find_grid(audio):
    """Returns (bpm, first downbeat in seconds) by scoring a click grid against onsets."""
    mono = audio[: SR * 90].mean(axis=1)
    low = sosfilt(butter(2, 180, "lowpass", fs=SR, output="sos"), mono)
    hop = 256
    n = len(mono) // hop
    rms = np.sqrt(np.add.reduce((low[: n * hop].reshape(n, hop)) ** 2, axis=1) / hop)
    onset = np.maximum(0, np.diff(np.log(rms + 1e-3)))
    rate = SR / hop
    best = (0.0, 150.0, 0.0)
    for bpm in np.arange(150, 170, 0.02):
        period = 60 * rate / bpm
        idx = np.arange(0, len(onset) - period, period)
        for phase in np.arange(0, period, 1.0):
            score = onset[(idx + phase).astype(int)].mean()
            if score > best[0]:
                best = (score, bpm, phase / rate)
    _, bpm, phase = best
    beat = 60 / bpm
    bars = [onset[(np.arange(phase + i * beat, 80, 4 * beat) * rate).astype(int)].mean() for i in range(4)]
    return bpm, phase + int(np.argmax(bars)) * beat


def impact(length):
    t = np.arange(int(length * SR)) / SR
    boom = np.sin(2 * np.pi * np.cumsum(32 + 90 * np.exp(-t / 0.09)) / SR) * np.exp(-t / 0.6)
    crash = sosfilt(butter(2, 2500, "highpass", fs=SR, output="sos"), rng.standard_normal(len(t)))
    return np.tanh(1.6 * boom) + crash * np.exp(-t / 0.4) * 0.22


def whoosh(length=0.28):
    n = int(length * SR)
    noise = sosfilt(butter(2, [700, 7000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n))
    return noise * np.linspace(0, 1, n) ** 3


def riser(length):
    n = int(length * SR)
    noise = sosfilt(butter(2, 1200, "highpass", fs=SR, output="sos"), rng.standard_normal(n))
    return noise * np.linspace(0, 1, n) ** 2.5


def add(track, at, sig, gain):
    start = max(0, int(at * SR))
    end = min(len(track), start + len(sig))
    if end > start:
        track[start:end] += (sig[: end - start] * gain)[:, None]


def filtered_build(mix, beat):
    """Crossfades short lowpassed blocks so the cutoff sweeps without clicks."""
    out = mix.copy()
    block = int(0.05 * SR)
    for start_beat, end_beat, low, high in BUILDS:
        start, end = int(start_beat * beat * SR), int(end_beat * beat * SR)
        pos = start
        while pos < end:
            progress = (pos - start) / (end - start)
            cutoff = low * (high / low) ** progress
            sos = butter(2, cutoff, "lowpass", fs=SR, output="sos")
            pad = int(0.1 * SR)
            a, b = max(0, pos - pad), min(len(mix), pos + block + block // 4)
            piece = sosfilt(sos, mix[a:b], axis=0)[pos - a :]
            out[pos : pos + len(piece)] = piece * (0.55 + 0.35 * progress)
            pos += block
    return out


source, target = sys.argv[1], sys.argv[2]
audio = load(source)
bpm, start = find_grid(audio)
beat = 60 / bpm
frames = round(TOTAL_BEATS * beat * FPS)
length = int(frames / FPS * SR)
mix = filtered_build(audio[int(start * SR) : int(start * SR) + length].copy(), beat)

fx = np.zeros_like(mix)
for hit in WORD_HITS:
    add(fx, hit * beat, impact(0.9), 0.55)
for hit in IMPACTS:
    add(fx, hit * beat, impact(2.2), 0.75)
for hit in WHOOSHES:
    w = whoosh()
    add(fx, hit * beat - len(w) / SR, w, 0.22)
for hit, length in RISERS:
    add(fx, hit * beat - length, riser(length), 0.1)

# The track settles under the closing voiceover instead of playing at full energy.
soft = sosfilt(butter(2, 900, "lowpass", fs=SR, output="sos"), mix, axis=0)
turn = int(FINALE_BEAT * beat * SR)
blend = np.clip((np.arange(len(mix)) - turn) / (0.4 * SR), 0, 1)[:, None]
mix = mix * (1 - blend) + soft * 0.55 * blend

stereo = mix * 0.85 + fx
stereo = np.tanh(stereo)
stereo *= 10 ** (-3 / 20) / np.max(np.abs(stereo))
fade = len(mix) - turn - int(0.5 * SR)
stereo[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5

# Music ducks under each voiceover, which sits on top at a fixed level.
ramp = int(0.35 * SR)
duck = np.ones(len(stereo))
voices = []
for path, (voice_beat, delay, level) in zip(sys.argv[3:5], VOICES):
    voice = load(path)
    voice *= 10 ** (-2 / 20) / np.max(np.abs(voice))
    at = int((voice_beat * beat + delay / FPS) * SR)
    voices.append((at, voice))
    duck[max(0, at - ramp) : at] = np.linspace(1, level, at - max(0, at - ramp))
    duck[at : at + len(voice)] = level
    duck[at + len(voice) : at + len(voice) + ramp] = np.linspace(level, 1, ramp)
stereo = stereo * duck[:, None]
for at, voice in voices:
    stereo[at : at + len(voice)] += voice
stereo = np.clip(stereo, -0.98, 0.98)
wavfile.write(target, SR, (stereo * 32767).astype(np.int16))
print(f"bpm={bpm:.2f} start={start:.3f}s frames={frames}")
