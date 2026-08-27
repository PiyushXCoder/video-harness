#!/usr/bin/env python3
"""
hook_lib.py -- the reusable engine behind scripts/build_hook_manifest.py.

This file is TEMPLATE code: it knows nothing about any particular video's
hook. The per-video editorial plan (which beat, clip, line and graphic goes
where) lives in build_hook_manifest.py, which imports this -- exactly the
split timeline_lib.py / build_timeline_manifest.py already uses for the body.

WHY A SEPARATE ENGINE AT ALL

The body's build_segment() cannot express a hook, for three reasons:

  * parse_srt() sys.exits when a segment has no .srt sidecar, and a
    motion-graphics hook has no narration to transcribe;
  * build_segment() requires seg["file"] and probes it -- every segment IS
    exactly one video file;
  * NarrationSegment.tsx renders <OffthreadVideo src={staticFile(...)}>
    unconditionally, so a beat with no footage renders as a broken source.

So the hook's unit is a BEAT, whose `source` is optional, and whose total
duration is COMPOSED from the beat list rather than derived from one
recording's length. A hook may draw on raw/initial/ takes, video_clips/,
screencasts/, memes/, audio/ and manim/ in the same 30 seconds.

Note on manim/: per CLAUDE.md, Manim is for MATHEMATICAL animation only.
Charts, title cards and kinetic type for the hook are authored as Remotion
components inside Hook.tsx, not pre-rendered to a file and pulled back in.

Everything shared with the body is imported from timeline_lib rather than
reimplemented: probe_duration, probe_dimensions, frames, parse_srt,
word_timeline, check_not_early, FPS.
"""

import json
import sys
from pathlib import Path

from timeline_lib import (  # noqa: F401  (re-exported for plan files)
    FPS,
    EMOJI_MAP,
    LEAD_TOLERANCE_SEC,
    REPO_ROOT,
    check_not_early,
    frames,
    parse_srt,
    phrase_onset,
    probe_dimensions,
    probe_duration,
    word_timeline,
)

OUT = REPO_ROOT / ".remotion" / "src" / "hook-data.json"
# Root.tsx imports BOTH manifests, so bundling anything -- even the Hook
# alone -- fails if the body's manifest is absent. See write_stub().
TIMELINE_OUT = REPO_ROOT / ".remotion" / "src" / "timeline-data.json"

# DESIGN.md ROLE["bg"] -- the background a pure-graphics beat sits on when the
# plan does not name one. Must match .manim/manim.cfg and
# .remotion/src/design.ts; change all three together.
DEFAULT_BACKGROUND = "#121212"

WIDTH, HEIGHT = 2048, 1280

# Pacing floor from docs/remotion-video-guidelines.md section 4: anything
# under ~15 frames reads as a glitch, and 45 frames (1.5 s) is the minimum
# shot the body already holds itself to. A hook cuts faster than the body but
# not below the point where a shot stops registering at all.
MIN_BEAT_FRAMES = 45

# A hook that runs long stops being a hook. Past the ceiling the build fails
# rather than warns, because "the first 30 seconds" is the entire premise.
DEFAULT_TARGET_SEC = 30.0
DURATION_CEILING_SEC = 45.0

VALID_ANCHORS = ("top", "center", "lower-third", "bottom")


def _fail(msg):
    sys.exit(f"Error: {msg}")


def _warn(msg):
    print(f"warn: {msg}", file=sys.stderr)


def _words(value):
    """Accept either a string or a pre-split list, like check_not_early does."""
    return value.split() if isinstance(value, str) else list(value)


# ── Validators ──────────────────────────────────────────────────────────
# The repo's philosophy is to encode editorial rules as BUILD-TIME FAILURES
# rather than conventions to remember. Every check here earns its place by
# catching something that eyeballing a preview does not.


def check_beat_window(beat_id, source_rel, start_sec, end_sec, src_dur):
    """A trim window must be non-empty and lie inside the real source.

    Mirrors build_segment()'s guard on a cutaway that starts at/after its
    segment's end -- that one renders as nothing at all, silently.
    """
    if end_sec <= start_sec:
        _fail(
            f"{beat_id}: window on {source_rel} is {end_sec - start_sec:.2f}s "
            f"({start_sec:.2f}s -> {end_sec:.2f}s) -- nothing would play."
        )
    if start_sec >= src_dur:
        _fail(
            f"{beat_id}: startFromSec {start_sec:.2f}s is at/past the end of "
            f"{source_rel} ({src_dur:.2f}s long), so the beat would render "
            f"nothing."
        )
    if end_sec > src_dur + 0.05:
        _warn(
            f"{beat_id}: toSec {end_sec:.2f}s runs past the end of "
            f"{source_rel} ({src_dur:.2f}s) -- the tail will freeze or go black."
        )


def check_min_shot(built):
    """No beat may be shorter than MIN_BEAT_FRAMES."""
    short = [
        (b["id"], b["durationInFrames"])
        for b in built
        if b["durationInFrames"] < MIN_BEAT_FRAMES
    ]
    if short:
        for beat_id, n in short:
            print(
                f"  {beat_id}: {n} frames ({n / FPS:.2f}s)", file=sys.stderr
            )
        _fail(
            f"beat(s) shorter than the {MIN_BEAT_FRAMES}-frame "
            f"({MIN_BEAT_FRAMES / FPS:.2f}s) minimum shot -- under ~15 frames a "
            f"shot reads as a glitch. Merge it into a neighbour or lengthen it."
        )


def check_duration_target(total_sec, target_sec, ceiling_sec=DURATION_CEILING_SEC):
    """Warn off-target, fail past the ceiling."""
    if total_sec > ceiling_sec:
        _fail(
            f"hook runs {total_sec:.1f}s, past the {ceiling_sec:.0f}s ceiling. "
            f"The first ~30 seconds is the whole premise -- cut beats rather "
            f"than raise this."
        )
    if target_sec and abs(total_sec - target_sec) > 5.0:
        _warn(
            f"hook runs {total_sec:.1f}s against a {target_sec:.0f}s target "
            f"(plans/hook.md). Off by {abs(total_sec - target_sec):.1f}s."
        )


def check_text_not_early(beat, source_rel, start_sec):
    """Text must not appear before the words it quotes are spoken.

    Only meaningful for a beat that HAS narration. check_not_early() already
    no-ops on text that is not a quote (a stamp, a title), so passing
    everything through it degrades cleanly.

    The srt must belong to the beat's OWN trimmed piece. This is the trap
    hook-build has to respect: once the raw take is split, the raw .srt's
    timestamps no longer describe the pieces.
    """
    srt_ref = beat.get("srt") or source_rel
    if not srt_ref:
        return
    if not (REPO_ROOT / srt_ref).with_suffix(".srt").is_file():
        return

    timeline = word_timeline(parse_srt(srt_ref))
    for t in beat.get("texts", []):
        # fromSec is in the beat's own timeline; the srt is in the SOURCE's,
        # so shift by the trim before comparing.
        check_not_early(
            beat["id"], "hook text", _words(t.get("words", t.get("text", ""))),
            t["fromSec"] + start_sec, timeline,
        )


# ── Beat builder ────────────────────────────────────────────────────────


def build_beat(beat):
    """Turn one plan dict into one manifest beat.

    Plan keys (all times in the BEAT's own timeline, seconds):

      id            required, stable slug -- appears in every error message
      source        optional repo-relative footage path; omit for a
                    pure-graphics beat (title card, chart, kinetic type)
      startFromSec  trim in-point inside source                    [0]
      toSec         trim out-point inside source        [source's real end]
      durationSec   REQUIRED when source is omitted
      captions      emit word-pop cues from source's sidecar .srt  [False]
      muted         drop this beat's own audio                     [False]
      background    css colour behind the beat      [DESIGN.md bg #121212]
      cutawaySafe   gate decoration off cutaways                    [True]
      rulesSuspended  body rules this beat drops, from plans/hook.md  [[]]
      texts / stamps / overlays / cutaways / emoji / sfx / bootTerminal
    """
    if "id" not in beat:
        _fail(f"a beat has no 'id': {beat!r}")
    beat_id = beat["id"]

    source_rel = beat.get("source")
    start_sec = float(beat.get("startFromSec", 0.0))

    if source_rel:
        src_dur = probe_duration(source_rel)
        end_sec = float(beat.get("toSec", src_dur))
        check_beat_window(beat_id, source_rel, start_sec, end_sec, src_dur)
        dur = end_sec - start_sec
        source = {
            "src": source_rel,
            "startFromFrame": frames(start_sec),
            "srcDurationInFrames": frames(src_dur),
            "muted": bool(beat.get("muted", False)),
        }
    else:
        if "durationSec" not in beat:
            _fail(
                f"{beat_id}: a beat with no 'source' must give 'durationSec' "
                f"-- there is no file to probe a length from."
            )
        dur = float(beat["durationSec"])
        if dur <= 0:
            _fail(f"{beat_id}: durationSec must be > 0, got {dur}.")
        end_sec = start_sec + dur
        source = None

    check_text_not_early(beat, source_rel, start_sec)

    cues = []
    if beat.get("captions"):
        if not source_rel:
            _fail(
                f"{beat_id}: captions=True but the beat has no 'source', so "
                f"there is no sidecar .srt to read."
            )
        srt_ref = beat.get("srt") or source_rel
        for c in parse_srt(srt_ref):
            # Shift into the beat's own timeline and drop cues outside the trim.
            c_from = c["start"] - start_sec
            c_to = c["end"] - start_sec
            if c_to <= 0 or c_from >= dur:
                continue
            cues.append({
                "fromFrame": frames(max(c_from, 0.0)),
                "durationInFrames": max(frames(min(c_to, dur) - max(c_from, 0.0)), 1),
                "words": c["text"].split(),
            })

    texts = []
    for t in beat.get("texts", []):
        anchor = t.get("anchor", "center")
        if anchor not in VALID_ANCHORS:
            _fail(
                f"{beat_id}: text anchor {anchor!r} is not one of "
                f"{VALID_ANCHORS}."
            )
        hold = float(t.get("holdSec", 2.2))
        texts.append({
            "fromFrame": frames(t["fromSec"]),
            "durationInFrames": max(frames(hold), 1),
            "words": _words(t.get("words", t.get("text", ""))),
            "color": t.get("color", "text"),
            "size": t.get("size", 72),
            "anchor": anchor,
        })

    cutaways = []
    for c in beat.get("cutaways", []):
        src_dur = probe_duration(c["src"])
        c_from = float(c["fromSec"])
        c_to = float(c.get("toSec", c_from + src_dur))
        if c_from >= dur:
            _fail(
                f"{beat_id}: cutaway {c['src']} starts at {c_from}s but the "
                f"beat is only {dur:.2f}s long, so it would never appear."
            )
        if c_to <= c_from:
            _fail(f"{beat_id}: cutaway {c['src']} has a non-positive window.")
        cutaways.append({
            "src": c["src"],
            "fromFrame": frames(c_from),
            "durationInFrames": frames(c_to - c_from),
            "srcDurationInFrames": frames(src_dur),
            "holdOnly": bool(c.get("holdOnly", False)),
        })

    overlays = []
    for o in beat.get("overlays", []):
        src_dur = probe_duration(o["src"])
        w, h = probe_dimensions(o["src"])
        o_from = float(o["fromSec"])
        o_to = float(o.get("toSec", o_from + src_dur))
        if o_to <= o_from:
            _fail(f"{beat_id}: overlay {o['src']} has a non-positive window.")
        overlays.append({
            "src": o["src"],
            "fromFrame": frames(o_from),
            "durationInFrames": frames(o_to - o_from),
            "srcDurationInFrames": frames(src_dur),
            "srcWidth": w,
            "srcHeight": h,
            "corner": o.get("corner", "br"),
            "widthPct": o.get("widthPct", 0.30),
            "transparent": bool(o.get("transparent", False)),
        })

    stamps = [
        {
            "text": s["text"],
            "fromFrame": frames(s["fromSec"]),
            "color": s.get("color", "text"),
            "size": s.get("size", 140),
        }
        for s in beat.get("stamps", [])
    ]

    emoji = []
    for e in beat.get("emoji", []):
        glyph = EMOJI_MAP.get(e["emoji"], e["emoji"])
        emoji.append({
            "emoji": glyph,
            "fromFrame": frames(e["fromSec"]),
            "color": e.get("color", "text"),
        })

    sfx = [
        {
            "file": s["file"],
            "fromFrame": frames(s["fromSec"]),
            "gain": s.get("gain", 0),
        }
        for s in beat.get("sfx", [])
    ]

    boot = beat.get("bootTerminal")
    boot_out = None
    if boot:
        boot_out = {
            "fromFrame": frames(boot["fromSec"]),
            "durationInFrames": frames(boot["toSec"] - boot["fromSec"]),
            "lines": boot["lines"],
        }

    return {
        "id": beat_id,
        "durationInFrames": frames(dur),
        "source": source,
        "background": beat.get("background", DEFAULT_BACKGROUND),
        "cutaways": cutaways,
        "overlays": overlays,
        "texts": texts,
        "stamps": stamps,
        "emoji": emoji,
        "sfx": sfx,
        "cues": cues,
        "bootTerminal": boot_out,
        "cutawaySafe": bool(beat.get("cutawaySafe", True)),
        "rulesSuspended": list(beat.get("rulesSuspended", [])),
    }


def build_hook(beats, music=None, target_sec=DEFAULT_TARGET_SEC):
    """The single entry point a build_hook_manifest.py plan calls.

    `music` is {"file": ..., "gainDb": ...} or None. `target_sec` should come
    from the plan's `## Duration target` section.
    """
    if not beats:
        _fail("the hook has no beats.")

    built = [build_beat(b) for b in beats]
    check_min_shot(built)

    total_frames = sum(b["durationInFrames"] for b in built)
    total_sec = total_frames / FPS
    check_duration_target(total_sec, target_sec)

    manifest = {
        "fps": FPS,
        "width": WIDTH,
        "height": HEIGHT,
        "totalDurationInFrames": total_frames,
        "music": music,
        "beats": built,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")

    print(
        f"Wrote {OUT.relative_to(REPO_ROOT)}: {len(built)} beat(s), "
        f"{total_frames} frames ({total_sec:.1f}s)"
    )
    for b in built:
        kind = b["source"]["src"] if b["source"] else "(graphics only)"
        suspended = (
            f"  [suspends: {', '.join(b['rulesSuspended'])}]"
            if b["rulesSuspended"] else ""
        )
        print(
            f"  {b['id']:24s} {b['durationInFrames']:5d}f "
            f"{b['durationInFrames'] / FPS:6.2f}s  {kind}{suspended}"
        )
    return manifest


# ── Stub, for working on the template with no episode content ───────────


STUB = {
    "fps": FPS,
    "width": WIDTH,
    "height": HEIGHT,
    "totalDurationInFrames": 180,
    "music": None,
    "beats": [
        {
            "id": "stub-title",
            "durationInFrames": 90,
            "source": None,
            "background": DEFAULT_BACKGROUND,
            "cutaways": [], "overlays": [], "stamps": [], "emoji": [],
            "sfx": [], "cues": [], "bootTerminal": None,
            "texts": [{
                "fromFrame": 0, "durationInFrames": 90,
                "words": ["STUB", "HOOK", "--", "run", "build_hook_manifest.py"],
                "color": "peach", "size": 72, "anchor": "center",
            }],
            "cutawaySafe": True,
            "rulesSuspended": ["centre-frame (no speaker in a stub)"],
        },
        {
            "id": "stub-second",
            "durationInFrames": 90,
            "source": None,
            "background": "#181825",
            "cutaways": [], "overlays": [], "stamps": [], "emoji": [],
            "sfx": [], "cues": [], "bootTerminal": None,
            "texts": [{
                "fromFrame": 0, "durationInFrames": 90,
                "words": ["second", "beat"],
                "color": "teal", "size": 56, "anchor": "lower-third",
            }],
            "cutawaySafe": True,
            "rulesSuspended": [],
        },
    ],
}


# Root.tsx registers FinalVideo alongside Hook and imports the body's
# manifest at module scope, so the Remotion bundler needs timeline-data.json
# to exist even when you only want to render the Hook. Both manifests are
# gitignored per-video content, so a fresh checkout has neither. This is the
# minimum shape that satisfies the import without pretending to be a video.
EMPTY_TIMELINE = {
    "fps": FPS,
    "width": WIDTH,
    "height": HEIGHT,
    "endCardFrames": 1,
    "endCard": {"progressLabel": "", "headline": "", "subline": ""},
    "progressUnit": None,
    "totalDurationInFrames": 1,
    "segments": [],
}


def write_stub():
    """Placeholder manifests so the template can be typechecked/previewed.

    hook-data.json is gitignored per-video content, so a fresh checkout has
    none and Root.tsx cannot resolve the import. Two graphics-only beats need
    no media at all, which is exactly the no-footage path worth smoke-testing.

    Also writes an EMPTY timeline-data.json when that is missing, because
    Root.tsx imports it too and the bundler resolves the whole module graph --
    without it, `remotion still Hook` fails on the body's manifest even though
    the Hook does not use it. Never overwrites a real one.
    """
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(STUB, indent=2) + "\n")
    print(f"Wrote stub {OUT.relative_to(REPO_ROOT)} (2 graphics-only beats, 6.0s)")

    if TIMELINE_OUT.is_file():
        print(f"Left existing {TIMELINE_OUT.relative_to(REPO_ROOT)} alone.")
    else:
        TIMELINE_OUT.write_text(json.dumps(EMPTY_TIMELINE, indent=2) + "\n")
        print(
            f"Wrote EMPTY {TIMELINE_OUT.relative_to(REPO_ROOT)} so the bundler "
            f"can resolve Root.tsx.\n"
            f"  NOTE: FinalVideo is now a 1-frame placeholder. Run "
            f"scripts/build_timeline_manifest.py before rendering the body."
        )


if __name__ == "__main__":
    if "--stub" in sys.argv:
        write_stub()
    else:
        sys.exit(
            "hook_lib.py is the engine, not the plan. Write the editorial plan "
            "in scripts/build_hook_manifest.py and run that.\n"
            "  python3 scripts/hook_lib.py --stub   # placeholder for template work"
        )
