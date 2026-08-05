#!/usr/bin/env python3
"""
process_recording.py

Turns a raw recording (raw/) into a podcast-ready clip (processed/):
  1. Detects silent gaps >= GAP_THRESHOLD seconds and cuts them out
     (video + audio stay in sync — both streams are trimmed with the
     same keep-segments).
  2. Cleans up the remaining audio: high-pass filter (rumble/hum),
     compressor (evens out loud/quiet parts), loudnorm (EBU R128 —
     consistent, "loud and clear" podcast loudness).
  3. Encodes video with NVIDIA NVENC (h264_nvenc), per project
     convention of preferring the GPU for video processing.

Usage:
  process_recording.py <input> [output] [--gap SECONDS] [--noise DB] [--pad SECONDS]

Defaults:
  output       processed/<input-basename> (same extension)
  --gap        1.0   (seconds of silence to treat as a cuttable gap)
  --noise      -30    (dBFS threshold below which audio counts as silence)
  --pad        0.15  (seconds kept on each side of a cut, so words aren't clipped)

Requires: ffmpeg, ffprobe (both on PATH).
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def ffprobe_duration(path):
    out = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    return float(out.stdout.strip())


def has_video_stream(path):
    out = run([
        "ffprobe", "-v", "error", "-select_streams", "v",
        "-show_entries", "stream=index", "-of", "csv=p=0", str(path),
    ])
    return bool(out.stdout.strip())


def detect_silences(path, noise_db, gap_secs):
    out = run([
        "ffmpeg", "-i", str(path),
        "-af", f"silencedetect=noise={noise_db}dB:d={gap_secs}",
        "-f", "null", "-",
    ])
    log = out.stderr
    starts = [float(m) for m in re.findall(r"silence_start:\s*([-\d.]+)", log)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([-\d.]+)", log)]
    # ffmpeg may report a trailing silence_start with no matching silence_end
    # (silence runs to EOF) — drop it, nothing to cut mid-stream for that case.
    return list(zip(starts, ends[: len(starts)]))


def keep_segments(duration, silences, pad):
    segments = []
    cursor = 0.0
    for start, end in silences:
        cut_start = start + pad
        cut_end = end - pad
        if cut_end <= cut_start:
            continue  # padding ate the whole gap, nothing to cut
        if cut_start > cursor:
            segments.append((cursor, cut_start))
        cursor = max(cursor, cut_end)
    if cursor < duration:
        segments.append((cursor, duration))
    return [(s, e) for s, e in segments if e - s > 0.01]


def build_select_expr(segments):
    return "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in segments)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output", nargs="?")
    ap.add_argument("--gap", type=float, default=1.0, help="silence duration (s) that counts as a cuttable gap")
    ap.add_argument("--noise", type=float, default=-30.0, help="silence threshold in dB")
    ap.add_argument("--pad", type=float, default=0.15, help="seconds kept on each side of a cut")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.is_file():
        sys.exit(f"Error: '{src}' not found.")

    if args.output:
        dst = Path(args.output)
    else:
        repo_root = Path(__file__).resolve().parent.parent
        dst = repo_root / "processed" / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)

    duration = ffprobe_duration(src)
    silences = detect_silences(src, args.noise, args.gap)
    segments = keep_segments(duration, silences, args.pad)

    if not segments:
        sys.exit("Error: silence detection removed the entire recording — check --noise/--gap.")

    kept = sum(e - s for s, e in segments)
    print(f"Duration: {duration:.1f}s, cutting {len(silences)} gap(s) >= {args.gap}s, keeping {kept:.1f}s")

    expr = build_select_expr(segments)
    video = has_video_stream(src)

    audio_chain = (
        f"aselect='{expr}',asetpts=N/SR/TB,"
        f"highpass=f=80,"
        f"acompressor=threshold=-18dB:ratio=3:attack=5:release=50,"
        f"loudnorm=I=-16:TP=-1.5:LRA=11"
    )

    if video:
        filter_complex = (
            f"[0:v]select='{expr}',setpts=N/FRAME_RATE/TB[v];"
            f"[0:a]{audio_chain}[a]"
        )
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "[a]",
            "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19", "-b:v", "0",
            "-c:a", "aac", "-b:a", "192k",
            str(dst),
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-af", audio_chain,
            "-c:a", "aac", "-b:a", "192k",
            str(dst),
        ]

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)
    print(f"Done. Output written to '{dst}'")


if __name__ == "__main__":
    main()
