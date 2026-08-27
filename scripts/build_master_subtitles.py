#!/usr/bin/env python3
"""
build_master_subtitles.py

Builds one master .srt for the whole delivered video by offsetting every
segment's own sidecar .srt into the assembled timeline. Reads
.remotion/src/hook-data.json (if present) and .remotion/src/timeline-data.json,
so run build_hook_manifest.py / build_timeline_manifest.py first.

The delivered video is hook + body, in that order (see the combine-all skill),
so the body's cues are offset by the hook's real duration. Get that wrong and
every subtitle in the video is late by ~30 seconds -- which is why the offset is
read from the hook manifest rather than typed.

Do NOT burn subtitles in -- upload this file to YouTube instead, which is
searchable and translatable. See docs/remotion-video-guidelines.md.

Usage:
  build_master_subtitles.py [--no-hook]

  --no-hook   ignore hook-data.json; emit the body only, starting at 0.
              Use when delivering the body on its own.
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / ".remotion" / "src" / "timeline-data.json"
HOOK_MANIFEST = REPO_ROOT / ".remotion" / "src" / "hook-data.json"
OUT = REPO_ROOT / ".remotion" / "out" / "final.srt"

CUE_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})"
)


def to_seconds(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def to_timestamp(seconds):
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = round((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def read_srt(srt_path):
    """(start, end, text) per cue, in the file's own timeline."""
    cues = []
    blocks = re.split(r"\n\s*\n", srt_path.read_text().strip())
    for block in blocks:
        lines = block.splitlines()
        # The cue number is usually line 0 and the timestamp line 1, but
        # tolerate either -- some tools omit the number.
        ts_line = next((l for l in lines if CUE_RE.search(l)), None)
        if not ts_line:
            continue
        m = CUE_RE.search(ts_line)
        body = "\n".join(lines[lines.index(ts_line) + 1:]).strip()
        if not body:
            continue
        cues.append((
            to_seconds(*m.group(1, 2, 3, 4)),
            to_seconds(*m.group(5, 6, 7, 8)),
            body,
        ))
    return cues


def place(cues, offset_sec, trim_sec=0.0, window_sec=None):
    """Shift cues into the master timeline, clipping to the visible window.

    `trim_sec` is how much of the head of the source was skipped (a hook beat's
    startFromFrame), so a cue's time in the source is `t - trim_sec` in the
    beat. `window_sec` is the beat's length; cues wholly outside it are dropped
    rather than emitted at a time where the picture is no longer on screen.
    """
    out = []
    for start, end, body in cues:
        s = start - trim_sec
        e = end - trim_sec
        if window_sec is not None:
            if e <= 0 or s >= window_sec:
                continue
            s = max(s, 0.0)
            e = min(e, window_sec)
        if e <= s:
            continue
        out.append((s + offset_sec, e + offset_sec, body))
    return out


def sidecar(rel_path):
    p = (REPO_ROOT / rel_path).with_suffix(".srt")
    return p if p.is_file() else None


def hook_cues(fps):
    """Cues from the hook, plus the hook's total duration in seconds.

    A hook beat may have no source at all (a title card), in which case it
    contributes silence -- it still advances the cursor, because it occupies
    real time in the delivered video.
    """
    if not HOOK_MANIFEST.is_file():
        return [], 0.0

    hook = json.loads(HOOK_MANIFEST.read_text())
    cues, cursor_frames = [], 0
    for beat in hook["beats"]:
        dur_frames = beat["durationInFrames"]
        src = beat.get("source")
        if src:
            srt = sidecar(src["src"])
            if srt:
                cues.extend(place(
                    read_srt(srt),
                    offset_sec=cursor_frames / fps,
                    trim_sec=src.get("startFromFrame", 0) / fps,
                    window_sec=dur_frames / fps,
                ))
            else:
                print(f"warn: hook beat {beat['id']}: no .srt for {src['src']}",
                      file=sys.stderr)
        cursor_frames += dur_frames

    return cues, cursor_frames / fps


def main():
    use_hook = "--no-hook" not in sys.argv

    if not MANIFEST.is_file():
        sys.exit(f"Error: {MANIFEST} not found -- run build_timeline_manifest.py first")
    manifest = json.loads(MANIFEST.read_text())
    fps = manifest["fps"]

    all_cues = []
    hook_sec = 0.0
    if use_hook:
        all_cues, hook_sec = hook_cues(fps)
        if HOOK_MANIFEST.is_file():
            print(f"Hook: {len(all_cues)} cue(s), {hook_sec:.1f}s -- "
                  f"body offset by that much.")
        else:
            print("No hook-data.json; body starts at 0.")
    else:
        print("--no-hook: body only, starting at 0.")

    # No title card and no silent pre-roll in the body: segment 0's own
    # audio+picture start at the body's frame 0. The only thing ahead of it in
    # the delivered video is the hook.
    cursor_frames = round(hook_sec * fps)

    for seg in manifest["segments"]:
        srt = sidecar(seg["file"])
        if srt:
            all_cues.extend(place(read_srt(srt), offset_sec=cursor_frames / fps))
        else:
            print(f"warn: no .srt for {seg['file']}", file=sys.stderr)
        cursor_frames += seg["durationInFrames"]

    if not all_cues:
        sys.exit("Error: no cues found -- are the sidecar .srt files present?")

    all_cues.sort(key=lambda c: c[0])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for i, (start, end, body) in enumerate(all_cues, 1):
            f.write(f"{i}\n{to_timestamp(start)} --> {to_timestamp(end)}\n{body}\n\n")

    total = cursor_frames / fps
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}: {len(all_cues)} cues, "
          f"last cue ends at {all_cues[-1][1]:.1f}s (timeline runs to {total:.1f}s)")
    if all_cues[-1][1] > total + 1.0:
        print(f"warn: last cue ends {all_cues[-1][1] - total:.1f}s past the end of "
              f"the timeline -- a sidecar .srt is probably stale.", file=sys.stderr)


if __name__ == "__main__":
    main()
