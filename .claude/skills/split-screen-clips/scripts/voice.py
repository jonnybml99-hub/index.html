#!/usr/bin/env python3
"""Generate a voiceover locally with Kokoro TTS (free, offline).

Usage:
  voice.py "Text to speak" out.wav [--voice am_michael] [--speed 1.1] [--lang en-us]
  voice.py --list                       (list voices)

Good voices: am_michael, am_adam, am_puck (male US), af_heart, af_bella (female US),
bm_george (male UK). German is not supported by Kokoro; write scripts in English.

Mix onto a clip (ducks game audio to 25%):
  ffmpeg -i clip.mp4 -i out.wav -filter_complex \
    "[0:a]volume=0.25[g];[g][1:a]amix=inputs=2:duration=first[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac out.mp4
"""
import argparse, os, sys
import soundfile as sf
from kokoro_onnx import Kokoro

MODELS = os.environ.get("CLIP_MODELS", "/opt/clip-models")

p = argparse.ArgumentParser()
p.add_argument("text", nargs="?"); p.add_argument("out", nargs="?")
p.add_argument("--voice", default="am_michael")
p.add_argument("--speed", type=float, default=1.1)
p.add_argument("--lang", default="en-us")
p.add_argument("--list", action="store_true")
a = p.parse_args()
k = Kokoro(f"{MODELS}/kokoro-v1.0.onnx", f"{MODELS}/voices-v1.0.bin")
if a.list:
    print("\n".join(sorted(k.get_voices()))); sys.exit()
if not (a.text and a.out):
    p.error("text and out are required")
samples, sr = k.create(a.text, voice=a.voice, speed=a.speed, lang=a.lang)
sf.write(a.out, samples, sr)
print(f"wrote {a.out} ({len(samples)/sr:.1f}s)")
