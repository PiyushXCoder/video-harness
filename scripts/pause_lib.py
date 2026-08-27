#!/usr/bin/env python3
"""
pause_lib.py -- decide which silences are PERFORMANCE and which are dead air.

TEMPLATE code. Used by scripts/process_recording.py via --pauses-from.

WHY THIS EXISTS

The cutter's original test for "is this pause intentional?" was duration alone:
a gap under --gap was called a natural speech beat and left alone, anything
longer was capped to --max-gap. That flattens a deliberate 2.5s pause before a
reveal to 0.7s, and it cannot tell that pause apart from 2.5s of the speaker
deciding what to say next. Both are just "long" to an amplitude threshold.

The .srt knows the difference, because it carries the WORDS either side.

WHY THE SRT IS ALSO A BETTER MEASUREMENT

generate_subtitles.sh runs whisper.cpp with -sow -sns (split on word, split on
no speech), so cue boundaries land on real speech starts and stops. A gap
measured as cue[N].end -> cue[N+1].start is therefore robust to room tone,
breath and keyboard noise -- the things that make a -30dB threshold fire in the
wrong places. Note that -ml 42 also splits cues purely for LENGTH, so most
consecutive cues are contiguous speech with a ~0 gap; only gaps at or above
min_gap are considered here, which filters those out.

BIAS

When the signals disagree or say nothing, the verdict is KEEP. A pause wrongly
kept costs a beat of dead air, which is cheap and visible. A pause wrongly cut
destroys a delivery and cannot be recovered without re-encoding from raw.
"""

import re

# A completed thought before a silence reads as rhetorical, not hesitant.
TERMINAL = (".", "?", "!", "…", ":", "--", "—")

# Ending on a function or filler word means the sentence was still going and
# the speaker stalled. These are the reliable hesitation tells.
HESITATION_TAIL = re.compile(
    r"\b(um|uh|erm?|ah|so|and|but|or|like|the|a|an|to|of|for|that|this|"
    r"is|was|it|i|we|you|they|in|on|at|with|because|if|when)\s*[,]?\s*$",
    re.I,
)

# A reversal or reveal after the silence means the silence was its setup.
REVERSAL_HEAD = re.compile(
    r"^\s*(but|actually|however|though|except|turns?\s+out|here'?s|wait|"
    r"now|except|the\s+problem|the\s+thing|and\s+that'?s)\b",
    re.I,
)

WORD_RE = re.compile(r"[a-z0-9']+")


def _words(text):
    return WORD_RE.findall(text.lower())


def gaps_from_cues(cues, min_gap):
    """Silences between consecutive cues that are long enough to matter."""
    gaps = []
    for i in range(len(cues) - 1):
        start, end = cues[i].end, cues[i + 1].start
        if end - start < min_gap:
            continue
        gaps.append({
            "index": i,
            "start": start,
            "end": end,
            "duration": end - start,
            "before": cues[i].text.strip(),
            "after": cues[i + 1].text.strip(),
        })
    return gaps


def _is_restart(before, after):
    """The speaker backed up and said the same words again -- a flub."""
    tail = _words(before)[-4:]
    head = _words(after)[:4]
    if len(tail) < 2 or len(head) < 2:
        return False
    # Two or more of the same words reappearing immediately after the gap.
    return len(set(tail) & set(head)) >= 2


def classify_gap(gap):
    """('keep'|'cut', reason). Order matters: a flub outranks everything.

    Only 'cut' is ever acted on -- an unsure gap is returned as 'keep' with
    reason 'unsure', so the caller can report it without losing the pause.
    """
    before, after = gap["before"], gap["after"]

    if _is_restart(before, after):
        return "cut", "restart: the words before repeat after the gap"

    if before.endswith(TERMINAL):
        return "keep", f"completed thought before the pause ({before[-1]!r})"

    if REVERSAL_HEAD.match(after):
        return "keep", "the line after the pause is a reversal/reveal"

    m = HESITATION_TAIL.search(before)
    if m:
        return "cut", f"trails off mid-clause on {m.group(1).lower()!r}"

    return "keep", "unsure"


def pause_plan(srt_path, min_gap):
    """[{start, end, duration, verdict, reason, before, after}] for every gap.

    `read_srt` is imported lazily so this module can be used from a script that
    already has srt_lib on its path without a hard import order.
    """
    from srt_lib import read_srt

    plan = []
    for gap in gaps_from_cues(read_srt(srt_path), min_gap):
        verdict, reason = classify_gap(gap)
        gap["verdict"] = verdict
        gap["reason"] = reason
        plan.append(gap)
    return plan


def protected_windows(plan, pad=0.25):
    """(start, end) source-time spans a silence must NOT be shortened inside.

    Padded on both sides because the two measurements disagree slightly: the
    .srt gap is speech-to-speech, while silencedetect fires on amplitude and
    will typically start a little later and end a little earlier.
    """
    return [
        (max(0.0, g["start"] - pad), g["end"] + pad)
        for g in plan if g["verdict"] == "keep"
    ]


def is_protected(start, end, windows):
    """Does this detected silence overlap a pause we decided to keep?"""
    return any(start < w_end and end > w_start for w_start, w_end in windows)


# ── Remapping cue times through a cut ───────────────────────────────────


def remap_time(t, segments, forward=True):
    """Map a source time onto the cut timeline, or None if it was removed.

    `segments` is the ordered list of (start, end) kept spans. A time inside a
    removed hole is nudged to the next kept segment's start (forward=True, for
    a cue's start) or the previous one's end (forward=False, for a cue's end).
    """
    offset = 0.0
    for s, e in segments:
        if t < s:
            return offset if forward else None
        if t <= e:
            return offset + (t - s)
        offset += e - s
    return None if forward else offset


def remap_cues(cues, segments):
    """Cues rewritten onto the cut timeline, dropping any that were cut away.

    This is why --pauses-from can hand back a correct .srt without a second
    whisper pass: the cut map is known exactly, so the raw transcript can be
    projected through it. It also removes a whole bug class -- a `processed/`
    clip whose sidecar .srt silently still describes the uncut raw.
    """
    from srt_lib import Cue

    out = []
    for c in cues:
        start = remap_time(c.start, segments, forward=True)
        end = remap_time(c.end, segments, forward=False)
        if start is None or end is None or end - start <= 0.01:
            continue
        out.append(Cue(start, end, c.text))
    return out
