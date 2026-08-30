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
# Delivery frame (DESIGN.md 10, docs/remotion-video-guidelines.md 1). Needed
# here because a focus crop is expressed relative to the frame it must fill.
VIDEO_WIDTH = 2048
VIDEO_HEIGHT = 1280

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


FOCUS_MAX_ZOOM = 1.5  # see DESIGN.md 10.7 and the note on build_focus()


def build_focus(seg_id, src, focus):
    """A moving 2048x1280 crop window over a larger source.

    zoom is expressed RELATIVE TO FIT: 1.0 shows the whole source in the
    frame, and FOCUS_MAX_ZOOM shows a 1:1 pixel window of a source that is
    exactly 1.5x the delivery frame. That is not an arbitrary ceiling -- this
    project's screencasts are 3072x1920 against a 2048x1280 delivery, so at
    1.5 no resampling happens at all and DESIGN.md 10.7's "never scale a
    source" is honoured rather than suspended. Past it, glyphs soften and the
    rule bites, so the build refuses.
    """
    src_w, src_h = probe_dimensions(src)
    fit = VIDEO_WIDTH / src_w
    native_zoom = 1.0 / fit  # zoom at which one source pixel is one out pixel
    out = {
        "srcWidth": src_w,
        "srcHeight": src_h,
        "zoomFrom": float(focus.get("zoomFrom", 1.0)),
        "zoomTo": float(focus.get("zoomTo", focus.get("zoomFrom", 1.0))),
        "cxFrom": float(focus.get("cxFrom", 0.5)),
        "cyFrom": float(focus.get("cyFrom", 0.5)),
        "cxTo": float(focus.get("cxTo", focus.get("cxFrom", 0.5))),
        "cyTo": float(focus.get("cyTo", focus.get("cyFrom", 0.5))),
    }
    for key in ("zoomFrom", "zoomTo"):
        if out[key] < 1.0:
            sys.exit(
                f"Error: {seg_id}: {src} {key}={out[key]} is below 1.0, which "
                f"would letterbox the source inside the frame."
            )
        if out[key] > FOCUS_MAX_ZOOM + 1e-6:
            sys.exit(
                f"Error: {seg_id}: {src} {key}={out[key]} exceeds the "
                f"{FOCUS_MAX_ZOOM} ceiling -- past this the source is upscaled "
                f"and monospace glyphs soften (DESIGN.md 10.7)."
            )
        if out[key] > native_zoom + 1e-6:
            print(
                f"warn: {seg_id}: {src} is {src_w}x{src_h}, so {key}="
                f"{out[key]} upscales it (1:1 is {native_zoom:.2f}). Soft.",
                file=sys.stderr,
            )
    return out


def build_segment(seg):
    # A segment with no `file` is a picture-only montage -- the showcase has no
    # narration at all, so there is no take to probe and no .srt to read. Its
    # length comes from the plan and its picture comes entirely from cutaways.
    if seg.get("file"):
        dur = probe_duration(seg["file"])
        cues = parse_srt(seg["file"])
    else:
        if not seg.get("durationSec"):
            sys.exit(f"Error: {seg['id']}: a segment with no file needs durationSec")
        dur = float(seg["durationSec"])
        cues = []
    timeline = word_timeline(cues)
    out = {
        "id": seg["id"],
        "file": seg.get("file"),
        "durationInFrames": frames(dur),
        "cutaways": [],
        "overlays": [],
        "stamps": [],
        "punchTexts": [],
        "bootTerminal": None,
        "emoji": [],
        "sfx": [],
        # Attention layers. spotlights and callouts direct the eye INSIDE a
        # cutaway without moving the crop; buildLists and twoColumns are
        # speaker-free full-frame builds.
        "spotlights": [],
        "callouts": [],
        "buildLists": [],
        "twoColumns": [],
        # Talking-head only. `punches` slowly scale the base picture so a long
        # take is never a locked-off static shot; `vignette` darkens the edges
        # so the eye is pulled to the speaker. Neither ever touches a cutaway:
        # a screencast is 1:1 and stays that way.
        "punches": [],
        "vignette": float(seg.get("vignette", 0.0)),
        # Where word-pop captions sit. 'flank-left' puts them in the empty wall
        # beside the speaker instead of a subtitle band under them.
        "captionPos": seg.get("captionPos", "bottom"),
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
        # A still has no duration; it simply holds for its window.
        is_image = c["src"].lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        src_dur = window if is_image else probe_duration(c["src"])
        src_w, src_h = probe_dimensions(c["src"])
        # AUTO-CONTAIN. <OffthreadVideo> in an AbsoluteFill has no objectFit,
        # so a 1920x1080 or 960x540 source is STRETCHED to 8:5 -- a wrong
        # picture, not a styling nicety. Anything that is not exactly the
        # delivery frame is therefore centred on the page background at its
        # native aspect, the same treatment the hook gives archival footage.
        # Deciding this from the probed dimensions rather than from a flag in
        # the plan means it cannot be forgotten for one clip out of twenty.
        contain = c.get("contain")
        if contain is None:
            # Compare ASPECT, not exact pixels. A 3072x1920 screencast is the
            # same 8:5 as the delivery frame and simply larger, so it fills
            # edge to edge; insetting it into a card would be wrong and was
            # the first version of this rule. Only a source whose SHAPE
            # differs -- a 16:9 recording, a 4:3 archive clip, a screenshot --
            # gets the centred treatment, because that is the case where
            # filling the frame would stretch or crop real content.
            delivery_aspect = VIDEO_WIDTH / VIDEO_HEIGHT
            contain = abs((src_w / src_h) - delivery_aspect) > 0.01
        entry = {
            "src": c["src"],
            "fromFrame": frames(c["fromSec"]),
            "durationInFrames": frames(window),
            "srcDurationInFrames": frames(src_dur),
            "isImage": is_image,
            "contain": bool(contain),
            "srcWidth": src_w,
            "srcHeight": src_h,
            # How the shot ARRIVES. Scale is one effect among several and was
            # being used for all of them; these are the alternatives, so a cut
            # can be given the entrance its content deserves instead of
            # everything pushing in.
            "enter": c.get("enter", "fade"),
            # Era grade, archive footage only. A modern screenshot given grain
            # and a vignette would be dressed up as something it is not.
            "grade": {
                "vignette": float(c.get("vignette", 0.0)),
                "grain": float(c.get("grain", 0.0)),
                "contrast": float(c.get("contrast", 1.0)),
                "saturate": float(c.get("saturate", 1.0)),
            },
            # Slow drift for archival stills and clips, as the hook does it.
            # Deliberately separate from `focus`: this moves the CARD's content
            # a percent or two, it does not crop a modern screencast.
            "drift": c.get("drift", "none"),
            "hold": bool(c.get("hold", False)),
            "holdOnly": bool(c.get("holdOnly", False)),
            "muted": True,
            "focus": build_focus(seg["id"], c["src"], c["focus"]) if c.get("focus") else None,
        }
        if not is_image and not entry["hold"] and window > src_dur + 0.5:
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
            # None -> the component uses TYPE.stamp.size from design.ts.
            # Injecting a default here would override DESIGN.md silently.
            "size": s.get("size"),
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
            # A plan may write the line as a plain string; the component wants
            # words. check_not_early() already accepts either, so normalising
            # here keeps the two from disagreeing -- passing a string straight
            # through rendered fine for 300 frames and then died with
            # "words.map is not a function" deep in the timeline.
            "words": pt["words"] if isinstance(pt["words"], list) else pt["words"].split(),
            "color": pt.get("color", "text"),
            "size": pt.get("size"),  # None -> TYPE.punch.size
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
    # Rects are fractions of the DELIVERY FRAME, not of the source: a
    # spotlight sits on top of whatever is showing, which may be a focus crop
    # that has already moved. Expressing it in frame space means the plan says
    # "this part of the picture", which is what the editor actually means.
    for sp in seg.get("spotlights", []):
        window = sp["toSec"] - sp["fromSec"]
        if window <= 0:
            sys.exit(f"Error: {seg['id']}: spotlight window <= 0 ({sp})")
        out["spotlights"].append({
            "fromFrame": frames(sp["fromSec"]),
            "durationInFrames": frames(window),
            "x": float(sp["x"]), "y": float(sp["y"]),
            "w": float(sp["w"]), "h": float(sp["h"]),
            "dim": float(sp.get("dim", 0.72)),
        })
    for co in seg.get("callouts", []):
        window = co["toSec"] - co["fromSec"]
        if window <= 0:
            sys.exit(f"Error: {seg['id']}: callout window <= 0 ({co})")
        if co.get("label"):
            check_not_early(seg["id"], "callout", co["label"], co["fromSec"], timeline)
        out["callouts"].append({
            "fromFrame": frames(co["fromSec"]),
            "durationInFrames": frames(window),
            "x": float(co["x"]), "y": float(co["y"]),
            "w": float(co["w"]), "h": float(co["h"]),
            "label": co.get("label", ""),
            "color": co.get("color", "accent"),
            "labelSide": co.get("labelSide", "below"),
        })
    for bl in seg.get("buildLists", []):
        window = bl["toSec"] - bl["fromSec"]
        if window <= 0:
            sys.exit(f"Error: {seg['id']}: buildList window <= 0 ({bl})")
        out["buildLists"].append({
            "fromFrame": frames(bl["fromSec"]),
            "durationInFrames": frames(window),
            "items": bl["items"],
            "title": bl.get("title", ""),
            "color": bl.get("color", "text"),
            "strike": bool(bl.get("strike", False)),
        })
    for tc in seg.get("twoColumns", []):
        window = tc["toSec"] - tc["fromSec"]
        if window <= 0:
            sys.exit(f"Error: {seg['id']}: twoColumn window <= 0 ({tc})")
        out["twoColumns"].append({
            "fromFrame": frames(tc["fromSec"]),
            "durationInFrames": frames(window),
            "leftTitle": tc["leftTitle"],
            "rightTitle": tc["rightTitle"],
            "left": tc["left"],
            "right": tc["right"],
            "leftColor": tc.get("leftColor", "accent"),
            "rightColor": tc.get("rightColor", "textMuted"),
        })
    for pu in seg.get("punches", []):
        window = pu["toSec"] - pu["fromSec"]
        if window <= 0:
            sys.exit(f"Error: {seg['id']}: punch window <= 0 ({pu})")
        to_scale = float(pu.get("to", 1.15))
        # The talking head is captured at exactly the delivery frame, so a
        # punch here is a TRUE upscale, unlike a crop out of an oversized
        # screencast. A camera image of a face has no monospace glyphs to
        # protect, but the softening is real, so the ceiling is tight.
        if to_scale > 1.25 or float(pu.get("from", 1.0)) > 1.25:
            sys.exit(
                f"Error: {seg['id']}: punch scale {to_scale} exceeds 1.25. The "
                f"take is already 2048x1280, so this is a true upscale."
            )
        out["punches"].append({
            "fromFrame": frames(pu["fromSec"]),
            "durationInFrames": frames(window),
            "from": float(pu.get("from", 1.0)),
            "to": to_scale,
            "originY": float(pu.get("originY", 0.4)),
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
        for layer in ("callouts", "buildLists", "twoColumns"):
            for item in seg[layer]:
                mark(covered, item["fromFrame"], item["durationInFrames"])
        # A spotlight is NOT coverage: it dims part of the picture rather than
        # adding anything to read, so a stretch carrying only a spotlight is
        # still bare.

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


def build_manifest(segments, end_card, progress_unit=None, beds=()):
    """Build + validate + write the manifest. Call this from your plan file.

    `beds` are music cues on the VIDEO's absolute timeline, not inside any
    segment. That distinction is load-bearing: a bed placed in a segment is
    clipped by that segment's <Series.Sequence>, so a 40s track under a 28s
    beat is silently truncated -- the same trap CLAUDE.md records for a hook
    beat's own sfx. Each bed carries its own duck level so a montage can run
    the music loud and a tour can sit it under speech.
    """
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
        "beds": [
            {
                "file": b["file"],
                "fromFrame": frames(b["atSec"]),
                "durationInFrames": frames(b["toSec"] - b["atSec"]),
                "startFromFrame": frames(b.get("startFromSec", 0.0)),
                "gain": float(b.get("gain", 0.0)),
                "fadeInFrames": frames(b.get("fadeInSec", 0.0)),
                "fadeOutFrames": frames(b.get("fadeOutSec", 0.0)),
            }
            for b in beds
        ],
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
