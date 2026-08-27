#!/usr/bin/env python3
"""
srt_lib.py -- one .srt reader, shared.

TEMPLATE code. Three places needed to parse subtitles (the pause heuristic,
the master-subtitle builder, the timeline engine) and a parser copied three
times drifts three ways. This is the single definition.

Deliberately tolerant: some tools omit the cue number, and whisper.cpp
occasionally emits a cue with an empty body, which every caller wants dropped
rather than carried as a blank subtitle.
"""

import re
from collections import namedtuple

# start/end in seconds from the file's own zero; text as written.
Cue = namedtuple("Cue", "start end text")

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


def read_srt(path):
    """Cues in file order. Skips malformed and empty-bodied blocks."""
    cues = []
    text = path.read_text()
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.splitlines()
        # The cue number is usually line 0 and the timestamp line 1, but
        # tolerate either -- some tools omit the number entirely.
        ts_line = next((l for l in lines if CUE_RE.search(l)), None)
        if not ts_line:
            continue
        m = CUE_RE.search(ts_line)
        body = "\n".join(lines[lines.index(ts_line) + 1:]).strip()
        if not body:
            continue
        cues.append(Cue(
            to_seconds(*m.group(1, 2, 3, 4)),
            to_seconds(*m.group(5, 6, 7, 8)),
            body,
        ))
    return cues


def write_srt(path, cues):
    """Write cues as a numbered .srt."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{to_timestamp(c.start)} --> {to_timestamp(c.end)}\n"
                    f"{c.text}\n\n")
