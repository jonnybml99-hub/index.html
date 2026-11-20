#!/bin/bash
# One-time setup per cloud container (idempotent): free local tools for
# subtitles (Whisper small via sherpa-onnx) and voiceovers (Kokoro TTS).
# Models come from GitHub releases (Hugging Face is blocked in this environment).
set -e
M="${CLIP_MODELS:-/opt/clip-models}"; mkdir -p "$M"; cd "$M"
python3 -c "import sherpa_onnx, kokoro_onnx, soundfile" 2>/dev/null || \
  pip install -q sherpa-onnx kokoro-onnx soundfile yt-dlp
R=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models
if [ ! -f sherpa-onnx-whisper-small/small-encoder.int8.onnx ]; then
  curl -sSfL "$R/sherpa-onnx-whisper-small.tar.bz2" | tar xj
  rm -f sherpa-onnx-whisper-small/small-encoder.onnx sherpa-onnx-whisper-small/small-decoder.onnx
fi
[ -f silero_vad.onnx ] || curl -sSfLO "$R/silero_vad.onnx"
K=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -f kokoro-v1.0.onnx ] || curl -sSfLO "$K/kokoro-v1.0.onnx"
[ -f voices-v1.0.bin ] || curl -sSfLO "$K/voices-v1.0.bin"
echo "clip tools ready in $M"
