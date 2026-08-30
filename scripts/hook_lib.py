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

# A ROLE NAME, not a hex: `background` is resolved through resolveColor() on
# the TS side exactly like a text colour, so the plan never names a hex and
# check_design.py has nothing to flag. 'bg' is DESIGN.md's page ground; a beat
# wanting true black asks for 'scrim', the role that IS pure black.
DEFAULT_BACKGROUND = "bg"

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

VALID_ANCHORS = ("top", "center", "lower-third", "bottom", "left", "right")

# Ken Burns kinds. A hook draws on archival footage that is often STATIC --
# three windows already open, nothing moving -- so motion over a still frame
# is not decoration here, it is the only thing keeping the shot alive.
VALID_MOTION = ("none", "push-in", "pull-out", "drift-left", "drift-right")

# DESIGN.md ARCHIVE.inset. A beat may override per-beat; 0 renders the source
# edge to edge, which is what a 2048x1280 screencast wants and what a
# third-party archival capture does not.
DEFAULT_INSET = 0.07


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
        rate = float(beat.get("playbackRate", 1.0))
        if rate <= 0:
            _fail(f"{beat_id}: playbackRate must be > 0, got {rate}.")
        # SCREEN time, not source time. A 6.5s window at 2.5x occupies 2.6s of
        # the hook -- get this wrong and every later beat is offset.
        dur = (end_sec - start_sec) / rate
        source = {
            "src": source_rel,
            "startFromFrame": frames(start_sec),
            "srcDurationInFrames": frames(src_dur),
            "muted": bool(beat.get("muted", False)),
            "playbackRate": rate,
            "inset": float(beat.get("inset", DEFAULT_INSET)),
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
            "size": t.get("size"),  # None -> TYPE.hookTitle.size
            "anchor": anchor,
            "scrim": bool(t.get("scrim", False)),
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
        c_start = float(c.get("startFromSec", 0.0))
        if c_start >= src_dur:
            _fail(
                f"{beat_id}: cutaway {c['src']} startFromSec {c_start:.2f}s is "
                f"at/past the source's {src_dur:.2f}s, so it would be blank."
            )
        cg = c.get("grade") or {}
        cutaways.append({
            "src": c["src"],
            "fromFrame": frames(c_from),
            "durationInFrames": frames(c_to - c_from),
            "startFromFrame": frames(c_start),
            "srcDurationInFrames": frames(src_dur),
            "holdOnly": bool(c.get("holdOnly", False)),
            # A hook cutaway is third-party footage like any other beat source,
            # so it gets the ARCHIVE CARD, not a stretched full-frame fill. The
            # body's <Cutaway> has no objectFit and would distort a 16:9 clip
            # into 8:5.
            "inset": float(c.get("inset", DEFAULT_INSET)),
            "grade": {
                "darken": float(cg.get("darken", 0.0)),
                "vignette": float(cg.get("vignette", 0.0)),
                "grain": float(cg.get("grain", 0.0)),
                "contrast": float(cg.get("contrast", 1.0)),
                "saturate": float(cg.get("saturate", 1.0)),
            },
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
            "size": s.get("size"),  # None -> TYPE.stamp.size
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

    # An sfx window used to be hardcoded to 60 frames in Hook.tsx, which
    # silently truncated anything over 2s -- a riser, a drone, a swell. The
    # window now comes from the file's real length unless the plan overrides.
    sfx = []
    for s in beat.get("sfx", []):
        s_dur = probe_duration(s["file"])
        s_to = float(s.get("toSec", s["fromSec"] + s_dur))
        if s_to <= s["fromSec"]:
            _fail(f"{beat_id}: sfx {s['file']} has a non-positive window.")
        if s["fromSec"] >= dur:
            _fail(
                f"{beat_id}: sfx {s['file']} starts at {s['fromSec']}s but the "
                f"beat is only {dur:.2f}s long, so it would never be heard."
            )
        sfx.append({
            "file": s["file"],
            "fromFrame": frames(s["fromSec"]),
            "durationInFrames": max(frames(s_to - s["fromSec"]), 1),
            "gain": s.get("gain", 0),
        })

    boot = beat.get("bootTerminal")
    boot_out = None
    if boot:
        boot_out = {
            "fromFrame": frames(boot["fromSec"]),
            "durationInFrames": frames(boot["toSec"] - boot["fromSec"]),
            "lines": boot["lines"],
        }

    m = beat.get("motion") or {}
    kind = m.get("kind", "none")
    if kind not in VALID_MOTION:
        _fail(f"{beat_id}: motion kind {kind!r} is not one of {VALID_MOTION}.")
    motion = {
        "kind": kind,
        "from": float(m.get("from", 1.0)),
        "to": float(m.get("to", 1.0)),
    }

    # Era grade, 0-1 each. plans/hook.md grades PER BEAT (heaviest 1984, heavy
    # 1995, absent 2026) rather than applying one look over the whole hook.
    g = beat.get("grade") or {}
    grade = {
        "darken": float(g.get("darken", 0.0)),
        "vignette": float(g.get("vignette", 0.0)),
        "grain": float(g.get("grain", 0.0)),
        # Multipliers, not 0-1 fractions: 1.0 is untouched. The biggest
        # "cinematic" lever on a flat, brightly-lit room is contrast up and
        # saturation slightly down -- the latter also pulls a camera shot
        # toward the achromatic frame DESIGN.md section 10.7 asks for.
        "contrast": float(g.get("contrast", 1.0)),
        "saturate": float(g.get("saturate", 1.0)),
    }
    for k in ("darken", "vignette", "grain"):
        if not 0.0 <= grade[k] <= 1.0:
            _fail(f"{beat_id}: grade.{k} must be within 0..1, got {grade[k]}.")
    for k in ("contrast", "saturate"):
        if not 0.2 <= grade[k] <= 2.5:
            _fail(f"{beat_id}: grade.{k} must be within 0.2..2.5, got {grade[k]}.")

    # Fade up from black, applied to the WHOLE beat. plans/hook.md sets this
    # to 0.4s on beat 1, deliberately not 1.2s: a black frame is the worst
    # thing to spend the first second of a muted autoplay on.
    fade_in = float(beat.get("fadeInSec", 0.0))
    if fade_in < 0:
        _fail(f"{beat_id}: fadeInSec must be >= 0, got {fade_in}.")
    if fade_in > dur:
        _fail(
            f"{beat_id}: fadeInSec {fade_in:.2f}s is longer than the beat "
            f"({dur:.2f}s) -- it would never finish fading in."
        )

    return {
        "id": beat_id,
        "durationInFrames": frames(dur),
        "fadeInFrames": frames(fade_in),
        "source": source,
        "motion": motion,
        "grade": grade,
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


def build_audio(items, total_sec, kind):
    """Hook-level audio, laid on the hook's OWN timeline.

    Why this is not per-beat sfx: a beat's sfx live inside its
    <Series.Sequence>, which CLIPS them to the beat's own length. Anything
    that spans a cut is therefore silently truncated -- a pitched-down chant
    running from beat 3 into beat 5, a 7.6s riser under a 2.8s beat. And a
    `music`-shaped single slot cannot hold several of them.

    So `atSec` is ABSOLUTE hook time, like `music` is, and a beat boundary is
    simply not an event this track knows about.

    `kind` is 'voice' or 'bed' -- editorially distinct, mechanically
    identical, and carried into the manifest so the data stays readable.

    Each entry: {file, atSec, startFromSec?, toSec?, gainDb?}.
    """
    out = []
    for v in items or []:
        f = v["file"]
        src_dur = probe_duration(f)
        a = float(v.get("startFromSec", 0.0))
        b = float(v.get("toSec", src_dur))
        at = float(v["atSec"])
        if b <= a:
            _fail(f"voice {f}: window {a:.2f}->{b:.2f}s is empty.")
        if a >= src_dur:
            _fail(
                f"{kind} {f}: startFromSec {a:.2f}s is at/past the end of the "
                f"file ({src_dur:.2f}s), so nothing would be heard."
            )
        if b > src_dur + 0.05:
            _warn(f"{kind} {f}: toSec {b:.2f}s runs past the file's {src_dur:.2f}s.")
        if at >= total_sec:
            _fail(
                f"{kind} {f}: atSec {at:.2f}s is at/past the hook's end "
                f"({total_sec:.2f}s), so it would never be heard."
            )
        if at + (b - a) > total_sec + 0.05:
            _warn(
                f"{kind} {f}: runs to {at + (b - a):.2f}s, past the hook's "
                f"{total_sec:.2f}s -- the tail is cut."
            )
        # Fades exist to kill the click at an arbitrary sample boundary, NOT
        # to rescue a bad edit. An in/out point must already land in real
        # silence -- verify with silencedetect on the source, because a
        # transcript will NOT reveal a clipped word (whisper discards the
        # fragment) and interpolating .srt cue times lands mid-syllable.
        fi = float(v.get("fadeInSec", 0.0))
        fo = float(v.get("fadeOutSec", 0.0))
        if fi < 0 or fo < 0:
            _fail(f"{kind} {f}: fades must be >= 0.")
        if fi + fo > (b - a):
            _fail(
                f"{kind} {f}: fades ({fi:.2f}s + {fo:.2f}s) exceed the "
                f"{b - a:.2f}s window."
            )
        out.append({
            "kind": kind,
            "file": f,
            "fromFrame": frames(at),
            "startFromFrame": frames(a),
            "durationInFrames": max(frames(b - a), 1),
            "gainDb": float(v.get("gainDb", 0.0)),
            "fadeInFrames": frames(fi),
            "fadeOutFrames": frames(fo),
        })
    return out


def build_hook(beats, music=None, target_sec=DEFAULT_TARGET_SEC,
               voice=None, beds=None):
    """The single entry point a build_hook_manifest.py plan calls.

    `music` is {"file": ..., "gainDb": ...} or None. `voice` and `beds` are
    lists of hook-level audio placements on absolute hook time (see
    build_audio) -- voice for takes, beds for drones and risers that span
    cuts. `target_sec` should come from the plan's `## Duration target`.
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
        "audio": (build_audio(voice, total_sec, "voice")
                  + build_audio(beds, total_sec, "bed")),
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
    "audio": [],
    "beats": [
        {
            "id": "stub-title",
            "durationInFrames": 90,
            "source": None,
            "background": DEFAULT_BACKGROUND,
            "cutaways": [], "overlays": [], "stamps": [], "emoji": [],
            "sfx": [], "cues": [], "bootTerminal": None,
            "fadeInFrames": 0,
            "motion": {"kind": "none", "from": 1.0, "to": 1.0},
            "grade": {"darken": 0.0, "vignette": 0.0, "grain": 0.0,
                      "contrast": 1.0, "saturate": 1.0},
            "texts": [{
                "fromFrame": 0, "durationInFrames": 90,
                "words": ["STUB", "HOOK", "--", "run", "build_hook_manifest.py"],
                "color": "accent", "size": None, "anchor": "center",
                "scrim": False,
            }],
            "cutawaySafe": True,
            "rulesSuspended": ["centre-frame (no speaker in a stub)"],
        },
        {
            "id": "stub-second",
            "durationInFrames": 90,
            "source": None,
            "background": "surfaceAlt",
            "cutaways": [], "overlays": [], "stamps": [], "emoji": [],
            "sfx": [], "cues": [], "bootTerminal": None,
            "fadeInFrames": 0,
            "motion": {"kind": "none", "from": 1.0, "to": 1.0},
            "grade": {"darken": 0.0, "vignette": 0.0, "grain": 0.0,
                      "contrast": 1.0, "saturate": 1.0},
            "texts": [{
                "fromFrame": 0, "durationInFrames": 90,
                "words": ["second", "beat"],
                "color": "info", "size": None, "anchor": "lower-third",
                "scrim": False,
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
