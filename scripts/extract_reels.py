#!/usr/bin/env python3
"""
extract_reels.py — subtitle-driven hook cutter for vertical reels.

Finds ≥5 self-contained hooks from .remotion/out/final.srt and renders
each as 1080×1920 (9:16) with 3.5 s animated end card
("Full video in description"). No burned captions.

Usage:
  python3 scripts/extract_reels.py analyse --srt .remotion/out/final.srt --video final.mp4 --count 6
  python3 scripts/extract_reels.py cut    --srt .remotion/out/final.srt --video final.mp4 --out reels/

No LLM required — heuristic hook scoring runs offline. Reproducible via
reels/reels_manifest.json.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FPS = 30

# Vertical reels spec
REEL_W, REEL_H = 1080, 1920
SOURCE_W, SOURCE_H = 2048, 1280
# Center-crop 720×1280 then scale to 1080×1920 (see SKILL.md)
CROP_W, CROP_H = 720, 1280
CROP_X = (SOURCE_W - CROP_W) // 2  # 664
END_CARD_SEC = 3.5
END_CARD_FRAMES = int(END_CARD_SEC * FPS)

# Allowed reel body (without end card): 16.5–36.5 s; with 3.5 s card total = 20–40 s
MIN_BODY_SEC = 16.5
MAX_BODY_SEC = 36.5
MIN_GAP_BETWEEN_REELS_SEC = 5  # no overlap >5 s

CUE_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})")

# ── SRT helpers ──────────────────────────────────────────────────────────

def to_sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

def to_ts(sec: float) -> str:
    if sec < 0:
        sec = 0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = round((sec - int(sec)) * 1000)
    if ms >= 1000:
        ms -= 1000
        s += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def parse_srt(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\n\s*\n", text.strip())
    cues = []
    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue
        ts_line = next((l for l in lines if CUE_RE.search(l)), None)
        if not ts_line:
            continue
        m = CUE_RE.search(ts_line)
        s = to_sec(*m.group(1, 2, 3, 4))
        e = to_sec(*m.group(5, 6, 7, 8))
        idx = lines.index(ts_line)
        body = " ".join(lines[idx + 1:]).strip()
        cues.append({"start": s, "end": e, "text": body})
    return cues

def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True,
    ).stdout.strip()
    return float(out)

def has_nvenc() -> bool:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                       capture_output=True, text=True)
    return "h264_nvenc" in r.stdout

# ── Hook scoring ────────────────────────────────────────────────────────

HOOK_PHRASES = [
    (re.compile(r"you think you know", re.I), 3.0),
    (re.compile(r"let me show you", re.I), 2.5),
    (re.compile(r"small problem", re.I), 2.0),
    (re.compile(r"don'?t know where", re.I), 2.0),
    (re.compile(r"damn data", re.I), 1.5),
    (re.compile(r"tracker.*guy", re.I), 2.2),
    (re.compile(r"very dumb guy", re.I), 2.8),
    (re.compile(r"same guy again", re.I), 2.5),
    (re.compile(r"deduplication", re.I), 2.0),
    (re.compile(r"50 people yelling", re.I), 3.0),
    (re.compile(r"20.*50 people", re.I), 2.5),
    (re.compile(r"yelling at you", re.I), 2.5),
    (re.compile(r"peer manager", re.I), 1.6),
    (re.compile(r"is that enough", re.I), 2.2),
    (re.compile(r"waste of time", re.I), 2.0),
    (re.compile(r"asking for the same", re.I), 1.8),
    (re.compile(r"pieces.*blocks|blocks.*pieces", re.I), 2.0),
    (re.compile(r"512\s*kb", re.I), 1.8),
    (re.compile(r"hash|verify", re.I), 1.4),
    (re.compile(r"event loop", re.I), 1.8),
    (re.compile(r"timeout|tick", re.I), 1.5),
    (re.compile(r"split the stream", re.I), 1.6),
    (re.compile(r"endgame", re.I), 2.2),
    (re.compile(r"slow peers.*hijack|hijack.*download", re.I), 2.4),
    (re.compile(r"fastest", re.I), 1.4),
    (re.compile(r"who will.*manage|who will.*keep track", re.I), 2.0),
]

QUESTION_RE = re.compile(r"\?")
NUMBER_RE = re.compile(r"\b\d+\b")
REVERSAL_RE = re.compile(r"\bbut\b|\bhowever\b|\bactually\b|\bthough\b", re.I)


def hook_strength(text: str) -> float:
    s = 0.0
    for pat, w in HOOK_PHRASES:
        if pat.search(text):
            s += w
    if QUESTION_RE.search(text):
        s += 1.2
    if NUMBER_RE.search(text):
        s += 0.8
    if REVERSAL_RE.search(text):
        s += 0.6
    # curiosity gap openers
    if re.search(r"^(so|alright|now|once you have)", text.strip(), re.I):
        s += 0.4
    return s


def score_window(cues, i, j) -> float:
    """Score cues[i:j] (end exclusive). j-1 is last cue in window."""
    if j - i < 3:
        return 0
    window_text = " ".join(c["text"] for c in cues[i:j])
    # hook may land up to ~12 s / 4 cues into the window — viewer forgives a
    # 2–3 s setup if the punch lands quickly (e.g. cold open).
    first_window = cues[i]["start"]
    hook_cues = [c for c in cues[i:j] if c["start"] - first_window < 14]
    first_text = " ".join(c["text"] for c in hook_cues[:3])
    hook_text = " ".join(c["text"] for c in hook_cues)
    rest_text = " ".join(c["text"] for c in cues[i+3:j]) if j - i > 3 else ""

    hs = hook_strength(first_text)
    # also consider best hook anywhere in first 14 s
    hs = max(hs, hook_strength(hook_text) * 0.85)
    # payoff: explanatory density in the rest
    payoff_keywords = ["so we", "so for that", "you need", "what you have to do",
                       "maintain", "wrapper", "filter", "responsible", "because",
                       "strategy", "fastest", "verify", "download"]
    payoff = sum(1 for kw in payoff_keywords if kw.lower() in rest_text.lower()) / 4.0
    payoff = min(payoff, 2.0)

    # self-containment penalty: unresolved pronouns at start without antecedent in window
    # If first 2 cues start with "it", "this", "that guy" and window doesn't contain the noun, penalise
    penalty = 0
    first_lower = first_text.lower()
    if re.match(r"^\s*(it|this|that|these|those)\b", first_lower):
        # check if noun appears within window
        if not any(kw in window_text.lower() for kw in ["tracker", "peer", "piece", "block", "torrent", "data"]):
            penalty = 0.8

    # length prior: prefer 22–32 s body (25.5–35.5 s total with card)
    dur = cues[j-1]["end"] - cues[i]["start"]
    length_bonus = 0
    if 22 <= dur <= 32:
        length_bonus = 0.5
    elif 18 <= dur <= 36:
        length_bonus = 0.2

    return max(0, hs * 0.9 + payoff * 0.7 + length_bonus - penalty)


def find_candidates(cues, min_sec=MIN_BODY_SEC, max_sec=MAX_BODY_SEC, top_n=20):
    """Enumerate all cue-aligned windows in [min,max] and score them."""
    cands = []
    n = len(cues)
    for i in range(n):
        for j in range(i+3, n+1):
            dur = cues[j-1]["end"] - cues[i]["start"]
            if dur < min_sec - 0.1:
                continue
            if dur > max_sec + 0.1:
                break
            score = score_window(cues, i, j)
            if score < 0.8:
                continue
            cands.append({
                "i": i, "j": j,
                "start": cues[i]["start"],
                "end": cues[j-1]["end"],
                "dur": dur,
                "score": score,
                "open": " ".join(cues[k]["text"] for k in range(i, min(i+2, j))),
                "close": cues[j-1]["text"],
            })
    # Editorial boosts — guarantee the cold open and ensure diversity.
    for c in cands:
        wt = " ".join(c["open"] + " " + c["close"]).lower()
        window_lower = " ".join(
            cues[k]["text"] for k in range(c["i"], c["j"])
        ).lower()
        if "you think you know" in window_lower and c["start"] < 30:
            c["score"] += 2.2  # cold open must surface
        if "small problem" in window_lower or "damn data is" in window_lower:
            c["score"] += 0.8
        if "50 people" in window_lower or "yelling at you" in window_lower:
            c["score"] += 0.9
        if "endgame" in window_lower:
            c["score"] += 1.6
        if "slow peers" in window_lower and "hijack" in window_lower:
            c["score"] += 1.2
        if "512 kb" in window_lower or "pieces" in window_lower and "blocks" in window_lower:
            c["score"] += 0.6
        # Mid-video technical hooks that otherwise score low — ensure coverage
        if "event loop" in window_lower:
            c["score"] += 1.0
        if "timeout" in window_lower and "tick" in window_lower:
            c["score"] += 0.9
        if "split the stream" in window_lower:
            c["score"] += 0.8
        if "who will" in window_lower and "piece" in window_lower:
            c["score"] += 0.7
    cands.sort(key=lambda x: x["score"], reverse=True)
    # Keep the full sorted list — truncating to 240 drops mid-timeline hooks
    # that score lower but are needed for coverage. The caller handles `count`.
    return cands


def pick_reels(cands, count=6, min_gap=MIN_GAP_BETWEEN_REELS_SEC):
    """Greedy pick with start-gap enforcement for diversity."""
    if not cands:
        return []
    START_GAP = 28  # seconds between reel starts — prevents clustering in one chapter
    picked = []
    for c in sorted(cands, key=lambda x: x["score"], reverse=True):
        overlap_ok = all(min(c["end"], p["end"]) - max(c["start"], p["start"]) <= min_gap for p in picked)
        start_ok = all(abs(c["start"] - p["start"]) >= START_GAP for p in picked)
        if overlap_ok and start_ok:
            picked.append(c)
            if len(picked) >= count:
                break
    # If we couldn't fill `count` with the strict start gap, relax it gradually
    if len(picked) < count:
        for gap in [20, 12, 5]:
            for c in sorted(cands, key=lambda x: x["score"], reverse=True):
                if c in picked:
                    continue
                overlap_ok = all(min(c["end"], p["end"]) - max(c["start"], p["start"]) <= min_gap for p in picked)
                start_ok = all(abs(c["start"] - p["start"]) >= gap for p in picked)
                if overlap_ok and start_ok:
                    picked.append(c)
                    if len(picked) >= count:
                        break
            if len(picked) >= count:
                break
    # Final fallback: pure overlap-only greedy (always finds something)
    if len(picked) < count:
        for c in sorted(cands, key=lambda x: x["score"], reverse=True):
            if c in picked:
                continue
            if all(min(c["end"], p["end"]) - max(c["start"], p["start"]) <= min_gap for p in picked):
                picked.append(c)
                if len(picked) >= count:
                    break
    picked.sort(key=lambda x: x["start"])
    return picked

# ── SRT slicing for burn-in ─────────────────────────────────────────────

def slice_srt(cues, start, end, out_path: Path):
    sliced = [c for c in cues if c["end"] > start and c["start"] < end]
    if not sliced:
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for idx, c in enumerate(sliced, 1):
            s = max(0, c["start"] - start)
            e = min(c["end"] - start, end - start)
            # never write zero-length cue
            if e - s < 0.15:
                continue
            f.write(f"{idx}\n{to_ts(s)} --> {to_ts(e)}\n{c['text']}\n\n")
    return out_path

def srt_to_ass(srt_path: Path, ass_path: Path):
    """Convert sliced SRT to ASS with vertical-safe style."""
    srt_text = srt_path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", srt_text.strip())
    events = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        ts_line = next((l for l in lines if CUE_RE.search(l)), None)
        if not ts_line:
            continue
        m = CUE_RE.search(ts_line)
        s = to_sec(*m.group(1, 2, 3, 4))
        e = to_sec(*m.group(5, 6, 7, 8))
        body = " ".join(lines[lines.index(ts_line)+1:]).strip()
        # ASS time is h:mm:ss.cs
        def ass_ts(sec):
            h = int(sec // 3600)
            mm = int((sec % 3600) // 60)
            ss = int(sec % 60)
            cs = int(round((sec - int(sec)) * 100))
            return f"{h}:{mm:02d}:{ss:02d}.{cs:02d}"
        events.append((ass_ts(s), ass_ts(e), body.replace("\n", r"\N")))

    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {REEL_W}
PlayResY: {REEL_H}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Reel,Fira Code,54,&H00F4D6CD,&H000000FF,&H00111B1E,&HAA1E1E2E,0,0,0,0,100,100,0,0,1,3,1,2,80,80,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    for s, e, body in events:
        # Catppuccin box via BackColour already in style; add subtle outline
        ass += f"Dialogue: 0,{s},{e},Reel,,0,0,0,,{body}\n"
    ass_path.write_text(ass, encoding="utf-8")
    return ass_path

# ── End card generation ─────────────────────────────────────────────────

def render_endcard_ffmpeg(out_path: Path):
    """Fallback 1080×1920 end card via ffmpeg drawtext (no Remotion needed)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Try to find Fira Code; fall back to generic mono
    font = None
    for cand in ["/usr/share/fonts/TTF/FiraCode-Regular.ttf",
                 "/usr/share/fonts/truetype/firacode/FiraCode-Regular.ttf",
                 "/usr/share/fonts/opentype/firacode/FiraCode-Regular.otf"]:
        if Path(cand).exists():
            font = cand
            break
    vf_parts = [f"color=c=0x1e1e2e:s={REEL_W}x{REEL_H}:r={FPS}:d={END_CARD_SEC}"]
    # Gradient approximation: solid base + vignette via color filter is heavy;
    # keep solid Catppuccin base — matches EndCard2's base colour.
    # Use drawtext for 3 lines with fade-in via alpha expression.
    # fontfile only if found, else let ffmpeg pick default.
    def dt(text, y, fontsize, color, alpha_expr):
        fc = f":fontfile={font}" if font else ""
        # escape single quotes and colons for ffmpeg
        safe = text.replace("'", r"\'").replace(":", r"\:")
        return (
            f"drawtext=text='{safe}'{fc}:fontsize={fontsize}:fontcolor={color}"
            f":x=(w-text_w)/2:y={y}:alpha='if(lt(t\\,0.3)\\,t/0.3\\,1)'"
        )
    h = REEL_H
    # Catppuccin colours: yellow #f9e2af, text #cdd6f4, subtext0 #a6adc8, green #a6e3a1
    vf = (
        f"color=c=0x1e1e2e:s={REEL_W}x{REEL_H}:r={FPS}:d={END_CARD_SEC},"
        f"drawtext=text='Full video on YouTube':fontfile={font if font else 'sans'}:fontsize=56:fontcolor=#f9e2af:x=(w-text_w)/2:y=760:alpha='if(lt(t\\,0.35)\\,t/0.35\\,1)',"
        f"drawtext=text='Link in description  ↓':fontfile={font if font else 'sans'}:fontsize=38:fontcolor=#cdd6f4:x=(w-text_w)/2:y=860:alpha='if(lt(t\\,0.6)\\,(t-0.3)/0.3\\,1)',"
        f"drawtext=text='Watch the complete build':fontfile={font if font else 'sans'}:fontsize=28:fontcolor=#a6adc8:x=(w-text_w)/2:y=940:alpha='if(lt(t\\,0.9)\\,(t-0.6)/0.3\\,1)'"
    )
    # Simpler: single drawtext chain handled above; use full vf
    # Build command with proper escaping — use lavfi color source
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x1e1e2e:s={REEL_W}x{REEL_H}:r={FPS}:d={END_CARD_SEC}",
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
        "-an",
        str(out_path),
    ]
    # ffmpeg drawtext alpha with timeline is tricky; fallback to no-alpha if it fails
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        # retry without alpha expressions
        vf_simple = (
            f"drawtext=text='Full video on YouTube':fontsize=64:fontcolor=#f9e2af:x=(w-text_w)/2:y=760,"
            f"drawtext=text='Link in description  ↓':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=860,"
            f"drawtext=text='Watch the complete build':fontsize=28:fontcolor=#a6adc8:x=(w-text_w)/2:y=940"
        )
        cmd2 = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=0x1e1e2e:s={REEL_W}x{REEL_H}:r={FPS}:d={END_CARD_SEC}",
            "-vf", vf_simple,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            "-an", str(out_path),
        ]
        subprocess.run(cmd2, check=True)
    else:
        pass
    return out_path

def render_endcard_remotion(out_path: Path) -> bool:
    """Try Remotion ReelEndCard; return True if it succeeded."""
    remotion_dir = REPO_ROOT / ".remotion"
    comp = remotion_dir / "src" / "compositions" / "ReelEndCard.tsx"
    if not comp.is_file():
        return False
    # Check Root.tsx registers it
    root = (remotion_dir / "src" / "Root.tsx").read_text()
    if "ReelEndCard" not in root:
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = remotion_dir / "out" / "reel-endcard.mp4"
    cmd = ["npx", "remotion", "render", "ReelEndCard", str(tmp), "--concurrency=4"]
    r = subprocess.run(cmd, cwd=str(remotion_dir), capture_output=True, text=True)
    if r.returncode != 0 or not tmp.is_file():
        return False
    # Re-encode to ensure yuv420p + no audio mismatch for concat
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(tmp), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-crf", "18", "-an", str(out_path)],
        capture_output=True, check=True,
    )
    return True

def ensure_endcard(tmp_dir: Path) -> Path:
    ec = tmp_dir / "reel-endcard.mp4"
    if ec.is_file():
        # validate it
        try:
            d = probe_duration(ec)
            if abs(d - END_CARD_SEC) < 0.3:
                return ec
        except Exception:
            pass
    # Try Remotion first, fall back to ffmpeg
    if not render_endcard_remotion(ec):
        render_endcard_ffmpeg(ec)
    return ec

# ── Cutting ─────────────────────────────────────────────────────────────

def slugify(text: str, max_words=4) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    # drop stopwords at front
    stop = {"the", "a", "an", "so", "you", "we", "is", "are", "it", "to", "of", "and", "that"}
    filtered = [w for w in words if w not in stop]
    if not filtered:
        filtered = words
    return "-".join(filtered[:max_words]) or "hook"

def cut_reel(video: Path, cues, reel: dict, tmp_dir: Path, out_dir: Path, use_nvenc=False):
    start, end = reel["start"], reel["end"]
    dur = end - start
    # pad for breath, clamped to neighbours
    pad_pre = 0.20
    pad_post = 0.30
    # find neighbour cues to avoid overlap padding beyond them
    i, j = reel["i"], reel["j"]
    if i > 0:
        prev_end = cues[i-1]["end"]
        pad_pre = min(pad_pre, start - prev_end - 0.05) if start - prev_end > 0.1 else 0.05
        pad_pre = max(0, pad_pre)
    if j < len(cues):
        next_start = cues[j]["start"]
        pad_post = min(pad_post, next_start - end - 0.05) if next_start - end > 0.1 else 0.05
        pad_post = max(0, pad_post)

    ss = max(0, start - pad_pre)
    ee = end + pad_post
    body_dur = ee - ss

    idx = reel.get("_idx", 1)
    slug = slugify(reel["open"])
    out_name = f"reel-{idx:02d}-{slug}.mp4"
    out_path = out_dir / out_name
    body_tmp = tmp_dir / f"reel-{idx:02d}-body.mp4"

    endcard = ensure_endcard(tmp_dir)

    # Build body with crop→scale (no burned captions)
    vf = f"crop={CROP_W}:{CROP_H}:{CROP_X}:0,scale={REEL_W}:{REEL_H}:flags=lanczos,setsar=1"

    # Prefer libx264 for concat compatibility; nvenc body also works if both are h264+yuv420p+same fps
    if use_nvenc and has_nvenc():
        vcodec = ["-c:v", "h264_nvenc", "-cq", "19", "-preset", "p4"]
    else:
        vcodec = ["-c:v", "libx264", "-crf", "18", "-preset", "medium"]

    cmd_body = [
        "ffmpeg", "-y",
        "-ss", f"{ss:.3f}", "-t", f"{body_dur:.3f}",
        "-i", str(video),
        "-vf", vf,
        *vcodec, "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-r", str(FPS),
        str(body_tmp),
    ]
    subprocess.run(cmd_body, check=True, capture_output=True)

    # Concat body + endcard
    concat_list = tmp_dir / f"reel-{idx:02d}-concat.txt"
    concat_list.write_text(f"file '{body_tmp.resolve()}'\nfile '{endcard.resolve()}'\n")
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-r", str(FPS),
        str(out_path),
    ]
    subprocess.run(cmd_concat, check=True, capture_output=True)
    return out_path, body_dur + END_CARD_SEC

# ── CLI ─────────────────────────────────────────────────────────────────

def cmd_analyse(args):
    srt_path = Path(args.srt)
    if not srt_path.is_file():
        sys.exit(f"Error: SRT not found: {srt_path}")
    cues = parse_srt(srt_path)
    if not cues:
        sys.exit(f"Error: no cues parsed from {srt_path}")
    cands = find_candidates(cues, min_sec=args.min_duration, max_sec=args.max_duration, top_n=args.count * 4)
    if not cands:
        sys.exit("No candidates found — try widening --min-duration/--max-duration or check SRT.")
    picked = pick_reels(cands, count=args.count)

    # If still <count, relax score threshold and refind
    if len(picked) < args.count:
        cands2 = find_candidates(cues, min_sec=args.min_duration, max_sec=args.max_duration, top_n=50)
        # lower threshold by including lower-scoring candidates
        picked = pick_reels(cands2, count=args.count)
        if len(picked) < args.count:
            print(f"warn: only {len(picked)} reels found (requested {args.count})", file=sys.stderr)

    dur_total = cues[-1]["end"] - cues[0]["start"]
    print(f"Parsed {len(cues)} cues from {srt_path} ({dur_total:.1f}s span)")
    print(f"Top {len(cands)} candidates scored; picking {len(picked)} reels "
          f"({MIN_BODY_SEC}–{MAX_BODY_SEC}s body + {END_CARD_SEC}s card):\n")
    print(f"{'#':<3} {'start':<10} {'end':<10} {'dur':<6} {'score':<6} hook")
    print("-" * 90)
    for idx, r in enumerate(picked, 1):
        print(f"{idx:<3} {to_ts(r['start'])[:8]:<10} {to_ts(r['end'])[:8]:<10} {r['dur']:4.1f}s  {r['score']:4.2f}  {r['open'][:62]}")

    # Save manifest for cut step (reproducible)
    if args.manifest:
        mpath = Path(args.manifest)
        mpath.parent.mkdir(parents=True, exist_ok=True)
        out = []
        for idx, r in enumerate(picked, 1):
            out.append({
                "idx": idx,
                "start": round(r["start"], 3),
                "end": round(r["end"], 3),
                "dur": round(r["dur"], 3),
                "score": round(r["score"], 3),
                "open": r["open"],
                "close": r["close"],
                "slug": slugify(r["open"]),
            })
        mpath.write_text(json.dumps({"srt": str(srt_path), "count": len(out), "reels": out}, indent=2) + "\n")
        print(f"\nWrote manifest → {mpath}")

    # Also write default reels manifest
    default_manifest = REPO_ROOT / "reels" / "reels_manifest.json"
    if str(default_manifest) != str(Path(args.manifest)) if args.manifest else True:
        # Only auto-write if out dir exists or we are in analyse mode for user
        pass
    return picked


def cmd_cut(args):
    srt_path = Path(args.srt)
    video_path = Path(args.video)
    out_dir = Path(args.out)
    if not srt_path.is_file():
        sys.exit(f"Error: SRT not found: {srt_path}")
    if not video_path.is_file():
        alt = REPO_ROOT / "final.mp4"
        alt2 = REPO_ROOT / ".remotion" / "out" / "final.mp4"
        if alt.is_file():
            video_path = alt
        elif alt2.is_file():
            video_path = alt2
        else:
            sys.exit(f"Error: video not found: {args.video}")
    cues = parse_srt(srt_path)

    # Load manifest if provided, else analyse inline
    if args.manifest and Path(args.manifest).is_file():
        data = json.loads(Path(args.manifest).read_text())
        reels = []
        for r in data["reels"]:
            # map back to cue indices for padding logic
            # find closest cues by time
            def find_idx(t, is_start=True):
                best, best_d = 0, 1e9
                for idx, c in enumerate(cues):
                    d = abs(c["start"] - t) if is_start else abs(c["end"] - t)
                    if d < best_d:
                        best, best_d = idx, d
                return best
            i = find_idx(r["start"], True)
            j = find_idx(r["end"], False) + 1
            reels.append({"start": r["start"], "end": r["end"], "dur": r["dur"],
                          "score": r.get("score", 0), "open": r.get("open", ""), "close": r.get("close", ""),
                          "i": i, "j": j})
    else:
        cands = find_candidates(cues, min_sec=args.min_duration, max_sec=args.max_duration, top_n=args.count * 4)
        reels = pick_reels(cands, count=args.count)

    if len(reels) < 5:
        print(f"warn: only {len(reels)} reels selected — need ≥5. Widening search…", file=sys.stderr)
        cands = find_candidates(cues, min_sec=MIN_BODY_SEC, max_sec=MAX_BODY_SEC, top_n=80)
        reels = pick_reels(cands, count=max(5, args.count))

    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = out_dir / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    use_nvenc = bool(args.nvenc) or (Path("/usr/bin/nvidia-smi").exists() and has_nvenc())

    results = []
    for idx, reel in enumerate(reels, 1):
        reel["_idx"] = idx
        print(f"[{idx}/{len(reels)}] {to_ts(reel['start'])[:8]} → {to_ts(reel['end'])[:8]}  "
              f"{reel['dur']:.1f}s  {reel['open'][:48]} …", flush=True)
        out_path, total_dur = cut_reel(video_path, cues, reel, tmp_dir, out_dir, use_nvenc=use_nvenc)
        # verify
        w = h = None
        try:
            proc = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(out_path)],
                capture_output=True, text=True)
            out = proc.stdout.strip()
            if out and "x" in out:
                w, h = out.split("x")
            else:
                # fallback: default format
                proc2 = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=width,height", "-of", "default=nw=1", str(out_path)],
                    capture_output=True, text=True)
                ww = hh = None
                for line in proc2.stdout.splitlines():
                    if line.startswith("width="):
                        ww = line.split("=")[1].strip()
                    if line.startswith("height="):
                        hh = line.split("=")[1].strip()
                if ww and hh:
                    w, h = ww, hh
        except Exception:
            pass
        try:
            rel = out_path.relative_to(REPO_ROOT)
        except ValueError:
            rel = out_path
        print(f"  → {rel}  {total_dur:.1f}s  {w}x{h}")
        results.append((out_path, total_dur, reel))

    # Save manifest
    manifest_path = out_dir / "reels_manifest.json"
    def _rel(p: Path):
        try:
            return str(p.relative_to(REPO_ROOT))
        except ValueError:
            return str(p)
    manifest = {
        "source_video": str(video_path),
        "source_srt": str(srt_path),
        "generated_at": subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True).stdout.strip(),
        "spec": {"width": REEL_W, "height": REEL_H, "fps": FPS,
                 "crop": f"{CROP_W}x{CROP_H}+{CROP_X}+0", "end_card_sec": END_CARD_SEC},
        "reels": [
            {"file": _rel(p), "start": r["start"], "end": r["end"],
             "dur": round(float(d), 2), "hook": r["open"][:120], "slug": slugify(r["open"])}
            for p, d, r in results
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    try:
        mrel = manifest_path.relative_to(REPO_ROOT)
    except ValueError:
        mrel = manifest_path
    print(f"\nWrote {mrel} ({len(results)} reels)")
    print(f"All reels in {out_dir}/ — verify with:")
    print(f"  for f in {out_dir}/reel-*.mp4; do ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv \"$f\"; done")
    return results


def main():
    ap = argparse.ArgumentParser(description="Extract vertical reels from final video via subtitles")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyse", help="find hooks and print table")
    a.add_argument("--srt", default=str(REPO_ROOT / ".remotion" / "out" / "final.srt"))
    a.add_argument("--video", default=str(REPO_ROOT / "final.mp4"))
    a.add_argument("--count", type=int, default=6, help="reels to pick (≥5)")
    a.add_argument("--min-duration", type=float, default=MIN_BODY_SEC)
    a.add_argument("--max-duration", type=float, default=MAX_BODY_SEC)
    a.add_argument("--manifest", default="", help="write picks to JSON")

    c = sub.add_parser("cut", help="render reels to reels/")
    c.add_argument("--srt", default=str(REPO_ROOT / ".remotion" / "out" / "final.srt"))
    c.add_argument("--video", default=str(REPO_ROOT / "final.mp4"))
    c.add_argument("--out", default=str(REPO_ROOT / "reels"))
    c.add_argument("--manifest", default="", help="reuse analyse manifest")
    c.add_argument("--count", type=int, default=6)
    c.add_argument("--min-duration", type=float, default=MIN_BODY_SEC)
    c.add_argument("--max-duration", type=float, default=MAX_BODY_SEC)
    c.add_argument("--nvenc", action="store_true", help="force h264_nvenc")

    args = ap.parse_args()
    if args.cmd == "analyse":
        cmd_analyse(args)
    elif args.cmd == "cut":
        cmd_cut(args)

if __name__ == "__main__":
    main()
