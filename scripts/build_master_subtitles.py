#!/usr/bin/env python3
"""
build_master_subtitles.py

Builds one master .srt for the whole final video by offsetting each
segment's own sidecar .srt by that segment's start time in the assembled
timeline. Reads .remotion/src/timeline-data.json (run
build_timeline_manifest.py first).

Do NOT burn subtitles in -- upload this file to YouTube instead, which is
searchable and translatable. See docs/remotion-video-guidelines.md.
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / ".remotion" / "src" / "timeline-data.json"
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


def offset_srt(srt_path, offset_sec):
    cues = []
    text = srt_path.read_text()
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 2:
            continue
        m = CUE_RE.search(lines[1]) if not CUE_RE.search(lines[0]) else CUE_RE.search(lines[0])
        # cue number is usually line 0, timestamp line 1 -- but tolerate either
        ts_line = next((l for l in lines if CUE_RE.search(l)), None)
        if not ts_line:
            continue
        m = CUE_RE.search(ts_line)
        start = to_seconds(*m.group(1, 2, 3, 4)) + offset_sec
        end = to_seconds(*m.group(5, 6, 7, 8)) + offset_sec
        body = lines[lines.index(ts_line) + 1:]
        cues.append((start, end, "\n".join(body)))
    return cues


def main():
    if not MANIFEST.is_file():
        sys.exit(f"Error: {MANIFEST} not found -- run build_timeline_manifest.py first")
    manifest = json.loads(MANIFEST.read_text())
    fps = manifest["fps"]

    cursor_frames = manifest["titleCardFrames"]
    all_cues = []
    for seg in manifest["segments"]:
        video_path = REPO_ROOT / seg["file"]
        srt_path = video_path.with_suffix(".srt")
        offset_sec = cursor_frames / fps
        if srt_path.is_file():
            all_cues.extend(offset_srt(srt_path, offset_sec))
        else:
            print(f"warn: no .srt for {seg['file']}", file=sys.stderr)
        cursor_frames += seg["durationInFrames"]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for i, (start, end, body) in enumerate(all_cues, 1):
            f.write(f"{i}\n{to_timestamp(start)} --> {to_timestamp(end)}\n{body}\n\n")

    total = cursor_frames / fps
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}: {len(all_cues)} cues, "
          f"last cue ends at {all_cues[-1][1]:.1f}s (timeline runs to {total:.1f}s)")


if __name__ == "__main__":
    main()
