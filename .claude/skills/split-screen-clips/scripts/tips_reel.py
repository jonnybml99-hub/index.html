#!/usr/bin/env python3
"""Premium tips reel (1080x1920) from a 16:9 segment, in one ffmpeg pass.

  tips_reel.py SEG.mp4 OUT.mp4 --line1 "2 TRICKS FÜR" --line2 "JEDEN ÜBERFALL" \
      [--badge "GTA 6 TIPP"] [--cta "FOLGEN FÜR MEHR TIPPS"] [--lang de] [--no-sfx]

Effects: white flash + bass hit/whoosh at the start, badge slide-in, title
slam-in (scale + fade) with a recurring pulse on line 2, slow push-in zoom and
colour grade on the gameplay, glowing yellow frame, word-pop captions
(auto-transcribed with Whisper), progress bar, CTA pop-up in the last seconds,
loudness normalised to -14 LUFS for Reels/Shorts.
"""
import argparse, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from captions import load_audio, transcribe, chunk, ts  # noqa: E402

W, H = 1080, 1920
GY, GH = 560, 608          # gameplay box position / height
YEL = "&H0000D4FF&"        # ASS BGR: #FFD400
RED = "&H003C2DE8&"        # #E82D3C


def dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", path], capture_output=True, text=True).stdout)


def esc(s):
    return s.replace("{", "(").replace("}", ")")


def build_ass(path, a, D, caps):
    L = []
    L.append(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: T1,Inter Display Black,98,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,0,1,0,0,100,100,1,0,1,8,6,5,20,20,0,1
Style: T2,Inter Display Black,112,{YEL},{YEL},&H00000000,&HA0000000,0,1,0,0,100,100,1,0,1,9,7,5,20,20,0,1
Style: Badge,Inter Display Black,44,&H00FFFFFF,&H00FFFFFF,{RED},{RED},0,0,0,0,100,100,4,0,3,14,0,5,20,20,0,1
Style: Cap,Inter Display Black,80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,1,0,1,8,4,5,40,40,0,1
Style: CTA,Inter Display Black,62,&H00000000,&H00000000,{YEL},{YEL},0,0,0,0,100,100,2,0,3,20,0,5,20,20,0,1
Style: Hook,Inter Display Black,92,&H00FFFFFF,&H00FFFFFF,{RED},&H00000000,0,1,0,0,100,100,1,0,3,18,0,5,20,20,0,1
Style: Pill,Inter Display Black,44,&H00FFFFFF,&H00FFFFFF,{RED},{RED},0,0,0,0,100,100,1,0,3,16,0,5,20,20,0,1
Style: Box,Inter Display Black,10,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Q,Inter Display Black,82,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,0,1,0,0,100,100,1,0,1,8,5,5,30,30,0,1
Style: Small,Inter Display Black,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,0,0,0,0,100,100,2,0,1,5,2,5,20,20,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")
    end = ts(D)
    # badge slides in from the left
    L.append(f"Dialogue: 2,{ts(0.15)},{end},Badge,,0,0,0,,"
             f"{{\\move(-300,190,540,190,0,260)}}{esc(a.badge)}")
    # title slam-in
    slam = "\\fscx180\\fscy180\\alpha&HFF&\\t(0,170,\\fscx92\\fscy92\\alpha&H00&)\\t(170,280,\\fscx100\\fscy100)"
    L.append(f"Dialogue: 3,{ts(0.25)},{end},T1,,0,0,0,,{{\\pos(540,300){slam}}}{esc(a.line1)}")
    pulse = "".join(f"\\t({int(k*1000)},{int(k*1000+180)},\\fscx108\\fscy108)"
                    f"\\t({int(k*1000+180)},{int(k*1000+420)},\\fscx100\\fscy100)"
                    for k in [x * 2.5 + 2.0 for x in range(int(D / 2.5))])
    L.append(f"Dialogue: 3,{ts(0.42)},{end},T2,,0,0,0,,{{\\pos(540,420){slam}{pulse}}}{esc(a.line2)}")
    # strong start: shaking hook line over the gameplay
    if a.hook:
        shake = "".join(f"\\t({k*70},{k*70+70},\\frz{3 if k % 2 else -3})" for k in range(5)) + \
                "\\t(350,420,\\frz0)"
        L.append(f"Dialogue: 5,{ts(0.1)},{ts(1.9)},Hook,,0,0,0,,"
                 f"{{\\pos(540,{GY + GH // 2})\\fscx200\\fscy200\\t(0,150,\\fscx100\\fscy100){shake}"
                 f"\\fad(0,250)}}{esc(a.hook)}")
    # mid-video comment trigger, slides in from the right
    if a.mid and D > 14:
        m = D * 0.45
        L.append(f"Dialogue: 4,{ts(m)},{ts(m + 3.2)},Pill,,0,0,0,,"
                 f"{{\\move(1500,1520,540,1520,0,250)\\fad(0,200)}}{esc(a.mid)}")
    # satisfying end card (last 3 s): dim gameplay, question pops, comment prompt bounces
    if a.question and D > 6:
        e0 = D - 3
        L.append(f"Dialogue: 6,{ts(e0)},{end},Box,,0,0,0,,"
                 f"{{\\pos(0,{GY})\\p1\\1c&H000000&\\alpha&HFF&\\t(0,300,\\alpha&H50&)}}"
                 f"m 0 0 l {W} 0 {W} {GH} 0 {GH}{{\\p0}}")
        q = esc(a.question).replace("|", "\\N")
        L.append(f"Dialogue: 7,{ts(e0 + 0.15)},{end},Q,,0,0,0,,"
                 f"{{\\pos(540,{GY + GH // 2})\\fscx0\\fscy0\\t(0,220,\\fscx110\\fscy110)\\t(220,340,\\fscx100\\fscy100)}}{q}")
        bounce = "".join(f"\\t({k},{k+200},\\fscx112\\fscy112)\\t({k+200},{k+400},\\fscx100\\fscy100)"
                         for k in range(400, 3000, 600))
        L.append(f"Dialogue: 7,{ts(e0 + 0.4)},{end},CTA,,0,0,0,,"
                 f"{{\\pos(540,1330)\\fad(150,0){bounce}}}↓ KOMMENTIERE ↓")
        if a.cta:
            L.append(f"Dialogue: 7,{ts(e0 + 0.8)},{end},Small,,0,0,0,,{{\\pos(540,1440)\\fad(200,0)}}{esc(a.cta)}")
    # captions: pop each chunk, alternate white / yellow (none on the end card)
    caps = [c for c in caps if not (a.question and c[0] >= D - 3)]
    caps = [(s, min(e, D - 3) if a.question else e, g) for s, e, g in caps]
    for i, (s, e, g) in enumerate(caps):
        col = f"\\c{YEL}" if i % 2 else ""
        L.append(f"Dialogue: 1,{ts(s)},{ts(e)},Cap,,0,0,0,,"
                 f"{{\\pos(540,1330){col}\\fscx125\\fscy125\\t(0,90,\\fscx100\\fscy100)}}{esc(g.upper())}")
    open(path, "w").write("\n".join(L) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("seg"); p.add_argument("out")
    p.add_argument("--line1", required=True); p.add_argument("--line2", required=True)
    p.add_argument("--badge", default="GTA 6 TIPP")
    p.add_argument("--cta", default="FOLGEN FÜR MEHR TIPPS")
    p.add_argument("--hook", default="99% KENNEN DAS NICHT",
                   help="big shaking line over the gameplay for the first 1.8 s ('' = off)")
    p.add_argument("--question", default="WELCHEN TRICK|KANNTEST DU NICHT?",
                   help="end-card question, | = line break ('' = no end card)")
    p.add_argument("--mid", default="SCHREIB „TEIL 2“ IN DIE KOMMENTARE",
                   help="mid-video comment trigger ('' = off)")
    p.add_argument("--lang", default="de")
    p.add_argument("--words", type=int, default=3)
    p.add_argument("--no-sfx", action="store_true")
    a = p.parse_args()

    D = dur(a.seg)
    caps = chunk(transcribe(load_audio(a.seg), a.lang), a.words)
    ass = tempfile.mktemp(suffix=".ass")
    build_ass(ass, a, D, caps)
    N = int(D * 30) + 1

    vf = (
        f"[0:v]fps=30,scale=1920:1080,split=2[a][c];"
        # background: blurred, darkened, vignetted
        f"[a]crop=1080:1080:420:0,scale=1920:1920,crop={W}:{H}:420:0,boxblur=40:3,"
        f"eq=brightness=-0.16:saturation=1.4,vignette=PI/4[bg];"
        # gameplay: slow push-in + punchier grade
        f"[c]zoompan=z='if(lt(on,12),1.22-0.22*on/12,1)+0.07*on/{N}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x{GH}:fps=30,"
        f"eq=contrast=1.08:saturation=1.22,unsharp=5:5:0.5[game];"
        # glow frame behind gameplay
        f"[bg]drawbox=x=0:y={GY-14}:w={W}:h={GH+28}:color=0xFFD400@0.25:t=fill,"
        f"drawbox=x=0:y={GY-8}:w={W}:h={GH+16}:color=0xFFD400:t=fill[bg2];"
        f"[bg2][game]overlay=0:{GY},"
        # progress bar
        f"drawbox=x=0:y={H-22}:w={W}:h=22:color=black@0.6:t=fill,"
        f"drawbox=x=0:y={H-22}:w='{W}*t/{D:.3f}':h=22:color=0xFFD400:t=fill,"
        f"ass={ass},fade=in:st=0:d=0.35:color=white[v]"
    )
    if a.no_sfx:
        af = "[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
        inputs = ["-i", a.seg]
    else:
        # bass hit + whoosh, generated (no external assets)
        inputs = ["-i", a.seg,
                  "-f", "lavfi", "-t", "1.2", "-i",
                  "aevalsrc='0.9*sin(2*PI*(38+70*exp(-8*t))*t)*exp(-4*t)':s=48000:c=stereo",
                  "-f", "lavfi", "-t", "0.6", "-i", "anoisesrc=c=pink:a=0.5:r=48000",
                  # end chime: two bright tones (E6 + B6) ringing out
                  "-f", "lavfi", "-t", "2.5", "-i",
                  "aevalsrc='0.35*(sin(2*PI*1318*t)+0.6*sin(2*PI*1976*t))*exp(-2.2*t)':s=48000:c=stereo"]
        dly = int(max(D - 3, 0) * 1000)
        af = ("[2:a]highpass=f=800,lowpass=f=6000,afade=t=in:d=0.35,afade=t=out:st=0.35:d=0.25,"
              "aformat=channel_layouts=stereo,volume=0.6[wh];"
              f"[3:a]adelay={dly}|{dly}[ch];"
              "[0:a]aformat=sample_rates=48000:channel_layouts=stereo[g];"
              "[g][1:a][wh][ch]amix=inputs=4:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs,
                    "-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[aout]",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", a.out],
                   check=True)
    os.remove(ass)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
