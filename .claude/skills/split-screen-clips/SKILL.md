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
6. **Deliver** with `SendUserFile` (display: render). Never publish to
   Instagram/YouTube without the user's explicit yes per post.

## Notes

- Before spending credits, check `vidiq_balance`; tell the user what fits.
- Warn about copyright when clipping other creators' videos, and about
  platform rules for nudity/violence in GTA footage.
- Burned-in subtitles of the streamer's speech are not done yet (no
  transcription tool in the container); the game's own subtitles stay visible.
