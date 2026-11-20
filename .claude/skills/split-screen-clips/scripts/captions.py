#!/usr/bin/env python3
"""Transcribe a clip locally (Whisper small via sherpa-onnx, free, offline) and
write TikTok-style word-chunk captions as an .ass file, or burn them in.

Usage:
  captions.py INPUT.mp4 OUTPUT.mp4 [--y 955] [--lang en] [--words 3]
  captions.py INPUT.mp4 --srt out.srt         (transcript only)

--y is the vertical centre of the caption line on the 1080x1920 frame
(955 = the divider between facecam and gameplay in the facecam layout,
1500 = under the gameplay in the gameplay layout).
"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
import sherpa_onnx

MODELS = os.environ.get("CLIP_MODELS", "/opt/clip-models")
SR = 16000


def load_audio(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def transcribe(samples, lang):
    d = f"{MODELS}/sherpa-onnx-whisper-small"
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=f"{d}/small-encoder.int8.onnx", decoder=f"{d}/small-decoder.int8.onnx",
        tokens=f"{d}/small-tokens.txt", language=lang, task="transcribe", num_threads=4)
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = f"{MODELS}/silero_vad.onnx"
    cfg.silero_vad.min_silence_duration = 0.25
    cfg.silero_vad.max_speech_duration = 5
    cfg.sample_rate = SR
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=120)
    segs = []
    win = cfg.silero_vad.window_size
    for i in range(0, len(samples), win):
        vad.accept_waveform(samples[i:i + win])
        while not vad.empty():
            segs.append((vad.front.start, np.array(vad.front.samples))); vad.pop()
    vad.flush()
    while not vad.empty():
        segs.append((vad.front.start, np.array(vad.front.samples))); vad.pop()
    # VAD keeps music/game audio as one long block; whisper then drops most
    # words. Re-split anything longer than 6 s into ~5 s windows.
    split = []
    for start, s in segs:
        step = 5 * SR
        if len(s) <= 6 * SR:
            split.append((start, s)); continue
        for o in range(0, len(s), step):
            if len(s) - o > SR // 2:
                split.append((start + o, s[o:o + step]))
    out = []
    for start, s in split:
        st = rec.create_stream(); st.accept_waveform(SR, s); rec.decode_stream(st)
        text = st.result.text.strip()
        if text:
            out.append((start / SR, (start + len(s)) / SR, text))
    return out


def chunk(segments, n):
    """Split each segment into n-word chunks, timed by character share."""
    res = []
    for a, b, text in segments:
        words = text.split()
        groups = [" ".join(words[i:i + n]) for i in range(0, len(words), n)]
        total = sum(len(g) for g in groups) or 1
        t = a
        for g in groups:
            d = (b - a) * len(g) / total
            show = min(d, 0.45 * len(g.split()) + 0.4)  # never linger on screen
            res.append((t, t + show, g)); t += d
    return res


def ts(t, ass=True):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}" if ass else \
        f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"


def write_ass(chunks, path, y):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter Display,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,3,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(path, "w") as f:
        f.write(head)
        for i, (a, b, g) in enumerate(chunks):
            col = r"{\c&H00FFFF&}" if i % 2 else ""   # alternate white / yellow
            f.write(f"Dialogue: 0,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\pos(540,{y})}}{col}{g.upper()}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input"); p.add_argument("output", nargs="?")
    p.add_argument("--y", type=int, default=955)
    p.add_argument("--lang", default="en")
    p.add_argument("--words", type=int, default=3)
    p.add_argument("--srt")
    a = p.parse_args()
    segs = transcribe(load_audio(a.input), a.lang)
    for s, e, t in segs:
        print(f"[{s:6.2f}-{e:6.2f}] {t}", file=sys.stderr)
    if a.srt:
        with open(a.srt, "w") as f:
            for i, (s, e, t) in enumerate(segs, 1):
                f.write(f"{i}\n{ts(s, False)} --> {ts(e, False)}\n{t}\n\n")
    if a.output:
        ass = tempfile.mktemp(suffix=".ass")
        write_ass(chunk(segs, a.words), ass, a.y)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.input, "-vf", f"ass={ass}",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "copy",
                        "-movflags", "+faststart", a.output], check=True)
        os.remove(ass)
        print("wrote", a.output)


if __name__ == "__main__":
    main()
