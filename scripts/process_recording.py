#!/usr/bin/env python3
"""
process_recording.py

Turns a raw recording (raw/) into a podcast-ready clip (processed/):
  1. Detects silent gaps >= GAP_THRESHOLD seconds and shortens them
     (video + audio stay in sync — both streams are trimmed with the
     same keep-segments).
  2. Cleans up the remaining audio: high-pass filter (rumble/hum),
     compressor (evens out loud/quiet parts), loudnorm (EBU R128 —
     consistent, "loud and clear" podcast loudness).
  3. Encodes video with NVIDIA NVENC (h264_nvenc), per project
     convention of preferring the GPU for video processing.

Gaps are CAPPED, not flattened: a silence shorter than --gap is left entirely
alone (those are natural speech beats), and a longer one is shortened to
--max-gap rather than to a fixed fraction of a second. The old behaviour
collapsed every gap to 2x--pad, which stripped the rhythm out of the speech.

Leading and trailing dead air are trimmed separately (--head / --tail) rather
than through the gap logic, which otherwise leaves a fraction-of-a-second stub
of silence flashing at the start or end of the clip.

Usage:
  process_recording.py <input> [output] [options]

Options:
  --no-cut            keep every pause; master audio only (see below)
  --gap SECONDS       mid-speech silence long enough to shorten  [1.0]
  --noise DB          dBFS threshold below which audio counts as silence  [-30]
  --max-gap SECONDS   what a shortened gap becomes  [0.7]
  --head SECONDS      silence kept before the first word  [0.15]
  --tail SECONDS      silence kept after the last word  [0.35]
  --min-seg SECONDS   drop kept segments shorter than this (sliver guard)  [0.35]
  --dry-run           print the cut plan and exit without encoding

--no-cut skips the cutting stage ENTIRELY and runs only the mastering
chain (highpass, compressor, loudnorm) plus the NVENC encode. It exists for
hook footage in raw/initial/, where the pauses are the performance -- a
dramatic beat before the reveal is not dead air to reclaim. Trim for those
clips belongs in the beat's startFromSec/toSec (scripts/hook_lib.py), where
it is non-destructive and survives a replan, rather than burned into the
file.

--no-cut also switches loudnorm to TWO passes with linear=true, which the
cutting path does not need. Gating keeps silence out of the measurement, but
single-pass loudnorm is DYNAMIC: across a long intentional pause it ramps the
gain up during the silence and the speech returns hotter. Measured on an 8s
clip with one 4s pause: single-pass landed -13.4 LUFS against a -16 target,
two-pass linear landed -15.9. Since long deliberate pauses are the entire
reason this flag exists, the accurate path is the right default here.

Requires: ffmpeg, ffprobe (both on PATH).
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# How close to 0 / duration a silence must start / end to count as
# leading / trailing dead air rather than a mid-speech gap.
EDGE_EPS = 0.4

# Silences are always detected at this resolution, independent of --gap, so
# leading/trailing dead air gets trimmed even when it is shorter than the
# mid-speech gap threshold.
EDGE_GAP = 0.25


# The mastering chain, with no cutting in it. Both paths below build on
# this so the two can never drift apart. Split at loudnorm because the
# two-pass path has to measure the signal AFTER highpass+compressor.
PRE_LOUDNORM = (
    "highpass=f=80,"
    "acompressor=threshold=-18dB:ratio=3:attack=5:release=50"
)
LOUDNORM_TARGET = "I=-16:TP=-1.5:LRA=11"
MASTER_CHAIN = f"{PRE_LOUDNORM},loudnorm={LOUDNORM_TARGET}"


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


def detect_silences(path, noise_db, duration):
    out = run([
        "ffmpeg", "-i", str(path),
        "-af", f"silencedetect=noise={noise_db}dB:d={EDGE_GAP}",
        "-f", "null", "-",
    ])
    log = out.stderr
    starts = [float(m) for m in re.findall(r"silence_start:\s*([-\d.]+)", log)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([-\d.]+)", log)]
    # A trailing silence_start with no matching silence_end means the silence
    # runs to EOF — close it at the duration so --tail can trim it, instead of
    # dropping it and leaving the dead air in.
    return [(s, ends[i] if i < len(ends) else duration) for i, s in enumerate(starts)]


def keep_segments(duration, silences, gap, max_gap, head, tail, min_seg):
    """Segments of the source to keep, in order.

    A mid-speech silence shorter than `gap` is left completely alone — those are
    natural speech beats. A longer one is shortened to `max_gap`, removing half
    from each side so the pause stays centred between the two phrases.

    Leading/trailing silence is trimmed to head/tail regardless of length, since
    dead air at a clip boundary is never a beat.

    Segments shorter than min_seg are dropped so no sliver of a frame survives.
    """
    segments = []
    cursor = 0.0

    for start, end in silences:
        leading = start <= EDGE_EPS
        trailing = end >= duration - EDGE_EPS

        if leading and trailing:
            continue  # entire file is silent; caller errors out on empty result

        if leading:
            # Start just before the first word instead of at t=0.
            cursor = max(0.0, end - head)
            continue

        if trailing:
            stop = min(duration, start + tail)
            if stop > cursor:
                segments.append((cursor, stop))
            cursor = duration
            continue

        length = end - start
        if length < gap:
            continue  # natural speech beat, leave it alone
        pad = min(length, max_gap) / 2.0
        cut_start = start + pad
        cut_end = end - pad
        if cut_end <= cut_start:
            continue  # nothing left to remove
        if cut_start > cursor:
            segments.append((cursor, cut_start))
        cursor = max(cursor, cut_end)

    if cursor < duration:
        segments.append((cursor, duration))

    return [(s, e) for s, e in segments if e - s >= min_seg]


def build_select_expr(segments):
    return "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in segments)


def measure_loudnorm(path):
    """First pass of a two-pass loudnorm: measure, don't apply.

    Returns the measured_* parameter string, or None if the measurement
    could not be parsed (caller falls back to single-pass).

    WHY two passes for --no-cut and not for the cutting path: single-pass
    loudnorm runs in DYNAMIC mode, adjusting gain as it goes. Across a long
    intentional pause it ramps the gain up during the silence, so the speech
    after the pause comes back hotter -- measured 1.9 LU hot on an 8s clip
    with one 4s pause. Gating keeps silence out of the MEASUREMENT, but it
    does not stop dynamic-mode pumping. Hook footage is exactly the material
    where that bites, because the pauses are deliberate and long. Two passes
    with linear=true apply ONE constant gain instead, which is both accurate
    and leaves the performance's dynamics alone.
    """
    out = run([
        "ffmpeg", "-i", str(path),
        "-af", f"{PRE_LOUDNORM},loudnorm={LOUDNORM_TARGET}:print_format=json",
        "-f", "null", "-",
    ])
    try:
        blob = out.stderr[out.stderr.rindex("{"):]
        blob = blob[:blob.index("}") + 1]
        m = json.loads(blob)
        return (
            f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
            f"offset={m['target_offset']}:linear=true"
        )
    except (ValueError, KeyError):
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output", nargs="?")
    ap.add_argument("--no-cut", action="store_true", help="keep every pause; run mastering + encode only")
    ap.add_argument("--gap", type=float, default=1.0, help="mid-speech silence (s) long enough to shorten; shorter ones are left alone")
    ap.add_argument("--noise", type=float, default=-30.0, help="silence threshold in dB")
    ap.add_argument("--max-gap", type=float, default=0.7, help="what a shortened gap becomes (s)")
    ap.add_argument("--head", type=float, default=0.15, help="silence kept before the first word (s)")
    ap.add_argument("--tail", type=float, default=0.35, help="silence kept after the last word (s)")
    ap.add_argument("--min-seg", type=float, default=0.35, help="drop kept segments shorter than this (s)")
    ap.add_argument("--dry-run", action="store_true", help="print the cut plan and exit without encoding")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.is_file():
        sys.exit(f"Error: '{src}' not found.")

    if args.output:
        dst = Path(args.output)
    else:
        repo_root = Path(__file__).resolve().parent.parent
        dst = repo_root / "processed" / src.name

    duration = ffprobe_duration(src)
    video = has_video_stream(src)

    if args.no_cut:
        # No detection, no keep-segments, no select filters. Mastering only.
        print(f"Duration: {duration:.1f}s -> {duration:.1f}s "
              f"(--no-cut: every pause kept, mastering + encode only)")
        if args.dry_run:
            print("  no cut plan — --no-cut leaves the timeline untouched")
            return
        segments = None
    else:
        silences = detect_silences(src, args.noise, duration)
        segments = keep_segments(duration, silences, args.gap, args.max_gap,
                                 args.head, args.tail, args.min_seg)

        if not segments:
            sys.exit("Error: silence detection removed the entire recording — check --noise/--gap.")

        kept = sum(e - s for s, e in segments)
        print(f"Duration: {duration:.1f}s -> {kept:.1f}s "
              f"(gaps >= {args.gap}s shortened to {args.max_gap}s, {len(segments)} segment(s) kept)")

        if args.dry_run:
            for i, (s, e) in enumerate(segments):
                gap_before = f"  gap {s - segments[i - 1][1]:.2f}s before" if i else ""
                print(f"  keep {s:7.3f} -> {e:7.3f}  ({e - s:5.2f}s){gap_before}")
            return

    dst.parent.mkdir(parents=True, exist_ok=True)

    if segments is None:
        # Mastering-only path: no filter_complex at all, so nothing can
        # re-time the streams. Video is still re-encoded on the GPU so the
        # output is uniform with every other clip in processed/.
        measured = measure_loudnorm(src)
        if measured:
            chain = f"{PRE_LOUDNORM},loudnorm={LOUDNORM_TARGET}:{measured}"
            print("  two-pass loudnorm (linear): pauses cannot pump the gain")
        else:
            chain = MASTER_CHAIN
            print("  warn: loudnorm measurement failed, falling back to single-pass",
                  file=sys.stderr)
        cmd = ["ffmpeg", "-y", "-i", str(src), "-af", chain]
        if video:
            cmd += ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19", "-b:v", "0"]
        cmd += ["-c:a", "aac", "-b:a", "192k", str(dst)]
    else:
        expr = build_select_expr(segments)
        audio_chain = f"aselect='{expr}',asetpts=N/SR/TB,{MASTER_CHAIN}"

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
