#!/usr/bin/env python3
"""
timeline_lib.py -- the reusable engine behind scripts/build_timeline_manifest.py.

This file is TEMPLATE code: it knows nothing about any particular video. The
per-video editorial plan (which clip, gif, punch line and emoji goes where)
lives in build_timeline_manifest.py, which imports this.

What lives here:

  parse_srt / word_timeline / phrase_onset
      Read a segment's sidecar .srt and work out when each WORD is spoken.
      Whisper cues are multi-word chunks (-ml 42), so a cue's start time is
      NOT when its third word lands -- interpolating within the cue is what
      catches text keyed to a cue start.

  check_not_early
      Hard rule: nothing on screen may precede the words it refers to.
      Hand-timing drifts every time the edit changes, so this is enforced.

  check_no_repeated_gifs
      Hard rule: a gif is used at most once in a video. Reuse reads as a
      stock-footage budget rather than a joke.

  report_coverage
      Finds stretches with nothing on screen (no text, gif, emoji, stamp,
      boss frame) outside a full-frame cutaway. Density is measured, not
      assumed.

  build_segment / build_manifest
      Turn the plan into .remotion/src/timeline-data.json, probing every
      asset's real duration and dimensions with ffprobe rather than trusting
      a hand-typed number.
"""


import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / ".remotion" / "src" / "timeline-data.json"
FPS = 30

# How early an on-screen text cue may lead the word it refers to. A tiny lead
# reads as anticipation; more than this and the text spoils a line before it
# is spoken, which is the one thing on-screen text must never do.
LEAD_TOLERANCE_SEC = 0.35


def parse_srt(rel_video):
    """Real cue times for a segment, from its sidecar .srt.

    The .srt is the authority for anything timed to speech -- see CLAUDE.md.
    Cues are whisper's own multi-word chunks (-ml 42), NOT single words.
    """
    srt = (REPO_ROOT / rel_video).with_suffix(".srt")
    if not srt.is_file():
        sys.exit(f"Error: no .srt beside {rel_video} -- run scripts/generate_subtitles.sh")
    cues = []
    for block in re.split(r"\n\s*\n", srt.read_text().strip()):
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        m = re.match(
            r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", lines[1])
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, m.groups())
        cues.append({
            "start": h1 * 3600 + m1 * 60 + s1 + ms1 / 1000,
            "end": h2 * 3600 + m2 * 60 + s2 + ms2 / 1000,
            "text": " ".join(lines[2:]).strip(),
        })
    return cues


def word_timeline(cues):
    """(onset_sec, word) for every spoken word.

    A cue only carries a start and an end for the whole chunk, so a word's
    onset is interpolated across its cue. Approximate, but it is measured
    from the real transcript rather than guessed, and it is what catches a
    caption keyed to a cue's START when its actual word lands seconds later.
    """
    out = []
    for cue in cues:
        words = cue["text"].split()
        if not words:
            continue
        span = cue["end"] - cue["start"]
        for i, w in enumerate(words):
            out.append((cue["start"] + (i / len(words)) * span, w))
    return out


def _norm(word):
    return re.sub(r"[^a-z0-9]", "", word.lower())


def phrase_onset(timeline, words):
    """When `words` starts being spoken, or None if it is not in the transcript.

    Tolerates up to two intervening words per step, so a caption that
    condenses ("50 people yelling at you" over "there are 20, 50 people
    yelling at you") still matches.
    """
    target = [_norm(w) for w in words if _norm(w)]
    if not target:
        return None
    for i in range(len(timeline)):
        cursor, ok = i, True
        for t in target:
            hit = False
            for j in range(cursor, min(cursor + 3, len(timeline))):
                if _norm(timeline[j][1]) == t:
                    cursor, hit = j + 1, True
                    break
            if not hit:
                ok = False
                break
        if ok:
            return timeline[i][0]
    return None

# SEGMENTS below names emoji by intent ("rocket"), not by literal glyph --
# resolved here so a typo fails loudly at build time instead of putting a
# literal word on screen (EmojiBurst just renders whatever string it gets).
EMOJI_MAP = {
    "rocket": "\U0001F680",
    "lightning": "⚡",
    "check_mark": "✅",
    "magnet": "\U0001F9F2",
    "cross_mark": "❌",
    "floppy_disk": "\U0001F4BE",
    "repeat": "\U0001F501",
    "turtle": "\U0001F422",
    "party_popper": "\U0001F389",
}


def probe_duration(rel_path):
    p = REPO_ROOT / rel_path
    if not p.is_file():
        sys.exit(f"Error: asset not found: {rel_path}")
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(p)],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        return float(out)
    except ValueError:
        sys.exit(f"Error: ffprobe could not read duration of {rel_path}")


def probe_dimensions(rel_path):
    p = REPO_ROOT / rel_path
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(p)],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        w, h = out.split("x")
        return int(w), int(h)
    except ValueError:
        sys.exit(f"Error: ffprobe could not read dimensions of {rel_path}")


def frames(seconds):
    return round(seconds * FPS)


# --- Editorial plan --------------------------------------------------------
# cutaways replace the picture full-frame while the narration segment's own
# audio keeps playing underneath (muted=True on the cutaway's own audio).
# overlays are a bordered corner inset (memes) or a full-frame transparent
# sticker, on top of whatever is currently showing.
# stamps are short CONCEPT LABELS (NO./YES./TRACKER/EVENT LOOP) slammed into
# the top banner. They are the only text layer that is not a quote of the
# narration -- there used to be a `kineticText` layer that popped the
# narrator's own words a second time, mid-frame, which both landed on the
# speaker's face and said the same thing the audio already did. Speech
# belongs in captions (see `captions` below), concepts in stamps, and nothing
# says the same words twice.
# captions=True runs word-pop subtitles from the segment's own .srt: each word
# appears at its real onset and HOLDS until its cue ends.
# emoji are burst pops at specific moments.
# sfx are sound-effect cue points (file + timing).
# statusBar tracks protocol-state text per segment.
# nameTags are terminal lower-thirds on first component mention.
#
# fromSec/toSec are in the SEGMENT's own timeline (i.e. as read off its .srt).


END_CARD_SECONDS = 6.0  # longer end card for seed CTA + next-up


def check_not_early(seg_id, kind, text, from_sec, timeline):
    """Fail the build if on-screen text precedes the words it refers to.

    The hard rule: never show a thing before it is spoken. Hand-timing drifts
    every time the edit changes, so this is checked here rather than trusted.
    Text that is not a quote of the narration (a stamp like "NO." or a
    component name) has nothing to match and is skipped.
    """
    words = text if isinstance(text, list) else text.split()
    onset = phrase_onset(timeline, words)
    if onset is None:
        return
    if from_sec < onset - LEAD_TOLERANCE_SEC:
        sys.exit(
            f"Error: {seg_id}: {kind} {' '.join(words)!r} shows at "
            f"{from_sec:.2f}s but is not spoken until {onset:.2f}s "
            f"({onset - from_sec:.2f}s early). Move it to >= "
            f"{onset - LEAD_TOLERANCE_SEC:.2f}s."
        )


def build_segment(seg):
    dur = probe_duration(seg["file"])
    cues = parse_srt(seg["file"])
    timeline = word_timeline(cues)
    out = {
        "id": seg["id"],
        "file": seg["file"],
        "durationInFrames": frames(dur),
        "cutaways": [],
        "overlays": [],
        "stamps": [],
        "punchTexts": [],
        "bootTerminal": None,
        "emoji": [],
        "sfx": [],
        "statusBar": seg.get("statusBar", ""),
        "nameTags": [],
        "bossFrame": None,
        # Word-pop caption cues, only for segments that opt in. Each cue
        # carries its own real start/end so the renderer can hold a line for
        # exactly as long as it is being spoken.
        "cues": [
            {
                "fromFrame": frames(c["start"]),
                "durationInFrames": max(frames(c["end"] - c["start"]), 1),
                "words": c["text"].split(),
            }
            for c in cues
        ] if seg.get("captions") else [],
    }
    for c in seg.get("cutaways", []):
        window = c["toSec"] - c["fromSec"]
        if window <= 0:
            sys.exit(f"Error: {seg['id']}: cutaway window <= 0 ({c})")
        # A cutaway starting at/after the segment's end never renders at all.
        # Three screencasts were silently dead this way -- which is exactly why
        # the footage looked unused.
        if c["fromSec"] >= dur:
            sys.exit(
                f"Error: {seg['id']}: cutaway {c['src']} starts at "
                f"{c['fromSec']}s but the segment is only {dur:.1f}s long, so "
                f"it would never appear."
            )
        if c["toSec"] > dur + 0.05:
            print(f"warn: {seg['id']}: cutaway {c['src']} runs to {c['toSec']}s "
                  f"past the segment end {dur:.1f}s -- the tail is discarded",
                  file=sys.stderr)
        src_dur = probe_duration(c["src"])
        entry = {
            "src": c["src"],
            "fromFrame": frames(c["fromSec"]),
            "durationInFrames": frames(window),
            "srcDurationInFrames": frames(src_dur),
            "hold": bool(c.get("hold", False)),
            "holdOnly": bool(c.get("holdOnly", False)),
            "muted": True,
        }
        if not entry["hold"] and window > src_dur + 0.5:
            print(f"warn: {seg['id']}: {c['src']} window {window:.1f}s exceeds "
                  f"source {src_dur:.1f}s with hold=False -- will freeze on last frame "
                  f"by default OffthreadVideo behaviour once it ends", file=sys.stderr)
        out["cutaways"].append(entry)
    for o in seg.get("overlays", []):
        window = o["toSec"] - o["fromSec"]
        if window <= 0:
            sys.exit(f"Error: {seg['id']}: overlay window <= 0 ({o})")
        src_dur = probe_duration(o["src"])
        src_w, src_h = probe_dimensions(o["src"])
        out["overlays"].append({
            "src": o["src"],
            "fromFrame": frames(o["fromSec"]),
            "durationInFrames": frames(window),
            "srcDurationInFrames": max(frames(src_dur), 1),
            "srcWidth": src_w,
            "srcHeight": src_h,
            "corner": o.get("corner", "br"),
            "widthPct": o.get("widthPct", 0.30),
            "transparent": bool(o.get("transparent", False)),
        })
    for s in seg.get("stamps", []):
        check_not_early(seg["id"], "stamp", s["text"], s["fromSec"], timeline)
        out["stamps"].append({
            "text": s["text"],
            "fromFrame": frames(s["fromSec"]),
            "color": s.get("color", "text"),
            "size": s.get("size", 140),
        })
    if seg.get("kineticText"):
        sys.exit(
            f"Error: {seg['id']}: kineticText was renamed punchText (and moved "
            f"out of the frame centre, off the speaker's face)."
        )
    if seg.get("punchText"):
        sys.exit(f"Error: {seg['id']}: punchText is now a list -- use punchTexts=[...]")
    for pt in seg.get("punchTexts", []):
        # Where a segment also has captions (the hook), CaptionsGate suppresses
        # the caption for exactly the punch's window, so the emphasised line
        # takes over its moment instead of printing the sentence twice at once.
        check_not_early(seg["id"], "punchText", pt["words"], pt["fromSec"], timeline)
        out["punchTexts"].append({
            "fromFrame": frames(pt["fromSec"]),
            "durationInFrames": frames(pt.get("holdSec", 2.2)),
            "words": pt["words"],
            "color": pt.get("color", "text"),
            "size": pt.get("size", 56),
        })
    bt = seg.get("bootTerminal")
    if bt:
        out["bootTerminal"] = {
            "fromFrame": frames(bt["fromSec"]),
            "durationInFrames": frames(bt["toSec"] - bt["fromSec"]),
            "lines": bt["lines"],
        }
    for e in seg.get("emoji", []):
        if e["emoji"] not in EMOJI_MAP:
            sys.exit(f"Error: {seg['id']}: unknown emoji name {e['emoji']!r} -- add it to EMOJI_MAP")
        out["emoji"].append({
            "emoji": EMOJI_MAP[e["emoji"]],
            "fromFrame": frames(e["fromSec"]),
            "color": e.get("color", "text"),
        })
    for sfx in seg.get("sfx", []):
        out["sfx"].append({
            "file": sfx["file"],
            "fromFrame": frames(sfx["fromSec"]),
            "gain": sfx.get("gain", 0),
        })
    for nt in seg.get("nameTags", []):
        out["nameTags"].append({
            "name": nt["name"],
            "fromFrame": frames(nt["fromSec"]),
            "durationInFrames": frames(nt["durationSec"]),
        })
    bf = seg.get("bossFrame")
    if bf:
        # Sub-element times are LOCAL to the boss frame's own window, since
        # BossFrame reads useCurrentFrame() inside its <Sequence>. None means
        # "never show this element" rather than "show from the start".
        def local(key):
            if bf.get(key) is None:
                return None
            return frames(bf[key] - bf["fromSec"])

        out["bossFrame"] = {
            "fromFrame": frames(bf["fromSec"]),
            "durationInFrames": frames(bf["toSec"] - bf["fromSec"]),
            "label": bf["label"],
            "hpBar": bool(bf.get("hpBar", False)),
            "fastPeersFrame": local("fastPeersSec"),
            "slowPeerFrame": local("slowPeerSec"),
            "powerUpFrame": local("powerUpSec"),
        }
    return out


MAX_BARE_SEC = 1.5  # a stretch longer than this with nothing on screen reads as dead air


def report_coverage(built):
    """Find stretches with NO text/gif/emoji on screen.

    The rule: outside a Manim diagram (which is already wall-to-wall content
    of its own), no part of the video should be bare. This walks every frame
    and reports the gaps, so density is measured rather than assumed.
    """
    gaps = []
    for seg in built:
        dur = seg["durationInFrames"]
        covered = [False] * dur
        # ANY full-frame cutaway is content in its own right -- a diagram to
        # read or real terminal output -- so those stretches are exempt from
        # needing decoration on top (and nothing may be drawn there anyway).
        cutaway = [False] * dur

        def mark(target, start, length):
            for f in range(max(start, 0), min(start + length, dur)):
                target[f] = True

        for c in seg["cutaways"]:
            mark(cutaway, c["fromFrame"], c["durationInFrames"])
        for cue in seg["cues"]:
            mark(covered, cue["fromFrame"], cue["durationInFrames"])
        for o in seg["overlays"]:
            mark(covered, o["fromFrame"], o["durationInFrames"])
        for s in seg["stamps"]:
            mark(covered, s["fromFrame"], 30)
        for e in seg["emoji"]:
            mark(covered, e["fromFrame"], 30)
        for nt in seg["nameTags"]:
            mark(covered, nt["fromFrame"], nt["durationInFrames"])
        for pt in seg["punchTexts"]:
            mark(covered, pt["fromFrame"], pt["durationInFrames"])
        if seg["bootTerminal"]:
            mark(covered, seg["bootTerminal"]["fromFrame"], seg["bootTerminal"]["durationInFrames"])
        if seg["bossFrame"]:
            mark(covered, seg["bossFrame"]["fromFrame"], seg["bossFrame"]["durationInFrames"])

        run = 0
        for f in range(dur + 1):
            bare = f < dur and not covered[f] and not cutaway[f]
            if bare:
                run += 1
            else:
                if run / FPS > MAX_BARE_SEC:
                    gaps.append((seg["id"], (f - run) / FPS, run / FPS))
                run = 0
    return gaps


def check_no_repeated_gifs(built):
    """Every gif appears at most once in the whole video.

    A reaction gif reused three times stops reading as a joke and starts
    reading as a stock-footage budget, so this is a hard rule rather than a
    guideline. Transparent stickers are included -- there is no reason to
    repeat one of those either.
    """
    seen = {}
    for seg in built:
        for o in seg["overlays"]:
            seen.setdefault(o["src"], []).append(seg["id"])
    repeats = {src: segs for src, segs in seen.items() if len(segs) > 1}
    if repeats:
        for src, segs in sorted(repeats.items()):
            print(f"Error: {src} used {len(segs)}x ({', '.join(segs)})", file=sys.stderr)
        sys.exit("Error: a gif may only be used once -- source a new one.")


def build_manifest(segments, end_card, progress_unit=None):
    """Build + validate + write the manifest. Call this from your plan file."""
    built = [build_segment(s) for s in segments]
    check_no_repeated_gifs(built)
    total_frames = sum(s["durationInFrames"] for s in built)
    # No title-card block: segment 0's real audio+picture play from frame 0,
    # and its on-screen text comes from its own .srt cues (captions=True).
    total_frames += frames(END_CARD_SECONDS)

    manifest = {
        "fps": FPS,
        "width": 2048,
        "height": 1280,
        "endCardFrames": frames(END_CARD_SECONDS),
        "endCard": end_card,
        "progressUnit": progress_unit,
        "totalDurationInFrames": total_frames,
        "segments": built,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")

    mins = total_frames / FPS / 60
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}")
    print(f"{len(built)} segments, total {total_frames} frames "
          f"({total_frames / FPS:.1f}s = {mins:.2f} min) @ {FPS}fps")

    gaps = report_coverage(built)
    if gaps:
        print(f"\nBARE STRETCHES (> {MAX_BARE_SEC}s with no text/gif/emoji, "
              f"outside Manim):", file=sys.stderr)
        for seg_id, at, length in gaps:
            print(f"  {seg_id:16s} {at:6.1f}s  for {length:4.1f}s", file=sys.stderr)
        print(f"  {len(gaps)} gap(s), {sum(g[2] for g in gaps):.1f}s total",
              file=sys.stderr)
    else:
        print("Coverage: no bare stretches outside cutaways.")
