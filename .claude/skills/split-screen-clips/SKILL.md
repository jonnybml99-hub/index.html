---
name: split-screen-clips
description: Turn a YouTube video (stream, GTA gameplay, tips & tricks) into vertical 1080x1920 short-form clips for Instagram Reels, YouTube Shorts and TikTok, in the user's approved split-screen layout - streamer facecam on top, gameplay below, title hook at the top. Also a gameplay-only layout for tips/location videos. Use when the user says "make clips", "Clipping-Videos", "clip this video", "Shorts/Reels aus dem Video", or sends a YouTube link to clip.
---

# Split-Screen Clips

The user approved this exact look (Nov 2026). Keep it unless they ask for changes:

- **facecam layout** (default): title band (0-150px), facecam 1080x800 (150-950),
  white divider, gameplay 1080x740 (960-1700), blurred darkened gameplay behind
  everything. Gameplay crop shows ~70% of the width so the action is NOT cut in
  half; stream overlay (chat, logo, counters, HUD) is cropped away.
- **gameplay layout** (`LAYOUT=gameplay`, for tips/tricks/location clips with no
  facecam): title on top, large 1080x1080 gameplay in the middle, yellow caption
  line underneath (e.g. the location or the step).

Talk to the user in German.

## Workflow

1. **Metadata**: `vidiq_get_videos_by_ids` (title, duration, channel).
2. **Find moments**: `vidiq_video_watch` (25 credits) with a prompt asking for
   timestamped viral moments, or for tips videos: "list every tip/secret
   location with start/end timestamp, what is shown, and a one-line hook".
   `vidiq_video_transcript` (5 credits) is the cheap alternative.
3. **Cut the segments**: `vidiq_edit_media` op `trim_media` on the YouTube URL,
   1 credit each (much cheaper than `vidiq_generate_clips`, which is
   9 credits/minute and auto-crops badly - do NOT use it for the final clips).
   Poll `vidiq_job_poll`; the result `mediaUrl` is on
   `ai-internal-ffmpeg-output-prod.s3.amazonaws.com`, downloadable with curl.
   YouTube itself and `assets.vidiq.com` are blocked from the cloud container.
4. **Find the facecam**: grab a frame
   (`ffmpeg -ss 5 -i seg.mp4 -frames:v 1 f.png`), look at it, and set
   `CAM=w:h:x:y` if it is not at the default spot (bottom-left box of the
   Speed stream at 321:238:45:463). Pick `GAME` so it avoids overlays/HUD.
5. **Render**: `bash .claude/skills/split-screen-clips/scripts/split.sh in.mp4 out.mp4 "HOOK TITLE" ["caption"]`
   - Title: short, punchy English hook, no emoji (the font renders them as boxes).
   - Grab a preview frame of the output and check it before sending.
6. **Subtitles** (free, local): `bash scripts/setup.sh` once per container,
   then `python3 -I scripts/captions.py clip.mp4 clip_subs.mp4` - 3-word
   uppercase chunks, alternating white/yellow, centred on the divider
   (`--y 955`; use `--y 1500` for the gameplay layout, `--lang de` for German).
7. **Voiceover** (optional, free, local, for tips clips):
   `python3 -I scripts/voice.py "script text" vo.wav --voice am_michael`, then
   mix it in with the ffmpeg line in voice.py's docstring (English voices only).
8. **Deliver** with `SendUserFile` (display: render). Never publish to
   Instagram/YouTube without the user's explicit yes per post.

## Free tools (no vidIQ credits)

Everything after the cut is free and local: ffmpeg (layout), Whisper small via
sherpa-onnx (subtitles), Kokoro TTS (voice). `setup.sh` installs them from
PyPI and GitHub releases into `/opt/clip-models` (Hugging Face is blocked).
Only fetching a YouTube video needs vidIQ (`trim_media`, 1 credit), because
YouTube is blocked from the container. With 0 credits: ask the user to upload
their own recording (best for tips/tricks content) and skip step 3.

## Tips & tricks reels from a phone recording (the user's main workflow)

The user is often on their phone only. Chat uploads are capped at 30 MB, so
they screen-record the YouTube video and share a **Google Drive link**
("Jeder mit dem Link"). Drive hosts are allowed in the Default environment.
1. Download (gdown fails - it redirects to a blocked host):
   `curl -sSL -o source.mp4 "https://drive.usercontent.google.com/download?id=FILE_ID&export=download&confirm=t"`
2. iPhone recordings come in portrait with the landscape picture rotated.
   Check a frame; fix with
   `ffmpeg -i source.mp4 -vf "transpose=2,scale=1920:1080,fps=30" -crf 18 land.mp4`
   (transpose=1 if it is the other way round).
3. Watch it: contact sheet (`-vf "fps=1/10,scale=234:-1,tile=8x5"`) plus
   `captions.py land.mp4 --lang de --srt de.srt` for a timed transcript.
   Cut one reel per tip/topic (20-55 s), at sentence boundaries.
4. Render with `LAYOUT=tips` (whole 16:9 frame, so the video's own info boxes
   at the edges stay visible; 2-line German hook title with `$'Zeile 1\nZeile 2'`),
   then `captions.py ... --lang de --y 1330`.
   Run at most 3 renders in parallel and use a long background timeout.

## Notes

- Before spending credits, check `vidiq_balance`; tell the user what fits.
- Warn about copyright when clipping other creators' videos, and about
  platform rules for nudity/violence in GTA footage.
- The game's own subtitles stay visible under the burned-in captions.
