# video-harness

A production harness for making YouTube videos: raw footage in, a finished
2048×1280 video plus its subtitle track out. The work is done by **13 Claude Code
skills** that own one stage each.

This repo is a **template**. Only what is generic to *any* video is tracked; one
episode's footage, clips and editorial plans live on disk and are gitignored. A
fresh checkout is a working harness with no content in it.

Delivery is **2048×1280 (8:5) at 30 fps** — the screen recorder's native ratio,
deliberately not 16:9, so screencasts and code are never rescaled.

**See it in action:** [this video](https://youtu.be/4oK_dbCLlCE) was made with the
harness end to end — planned, cut, animated, scored and subtitled by the skills
below. It is the video the harness was built on, so most of the rules here exist
because something in it went wrong first.

---

## The pipeline

```
raw/ ─┬─► main-plan ──► main-build ──┐
      │   (body)         (body)      │
      │                              ├─► combine-all ──► final.mp4 + final.srt
      └─► hook-plan ──► hook-build ──┘         │
          (first 30s)   (first 30s)            └─► extract-reels ──► reels/
```

**The body is planned first.** The hook advertises what the body contains, so you
cannot promise before you have decided. If a hook gets written first anyway, the
body must pay it off.

---

## Two patterns explain the whole layout

**1. Plan / build split.** Planning is a conversation the user leads; building is
mechanical execution. They fail differently, so they are separate skills. A plan
skill writes a markdown file; the matching build skill implements that file and
**invents nothing** — it refuses to run on a missing or incomplete plan.

| plan | writes | build | reads it and produces |
|---|---|---|---|
| `main-plan` | `plans/main.md` | `main-build` | `.remotion/out/body.mp4` |
| `hook-plan` | `plans/hook.md` | `hook-build` | `.remotion/out/hook.mp4` |

**2. Single / pass pairing.** A `find-*` skill sources **one** asset when you
already know the moment. A `*-pass` skill sweeps the whole video to *find* the
moments, then calls the single skill for each.

| finds the moments | sources one asset |
|---|---|
| `meme-pass` | `find-memes` |
| `audio-pass` | `find-audio` |

---

## Skills

| skill | stage | what it does |
|---|---|---|
| [`process-recording`](.claude/skills/process-recording/) | footage | `raw/` → `processed/`: transcribes, cuts only the silences the transcript says are dead air, masters audio, GPU encode, remaps subtitles onto the cut |
| [`main-plan`](.claude/skills/main-plan/) | plan | Works out spine, theme and visual language **with the user** → `plans/main.md` |
| [`main-build`](.claude/skills/main-build/) | build | Generates clips, runs the meme and audio passes, writes the timeline manifest, exports `FinalVideo` on the GPU |
| [`hook-plan`](.claude/skills/hook-plan/) | plan | Sharpens the user's idea for the opening 30 s into beats → `plans/hook.md` |
| [`hook-build`](.claude/skills/hook-build/) | build | Masters the take without flattening its pauses, writes the hook manifest, renders the `Hook` composition |
| [`combine-all`](.claude/skills/combine-all/) | deliver | Joins hook + body into `final.mp4` and builds `final.srt` with the body offset by the hook's real duration |
| [`manim-clip`](.claude/skills/manim-clip/) | visuals | **Mathematical animation only.** Designs layout by constraint, audits geometry, publishes to `manim/` |
| [`remotion-clip`](.claude/skills/remotion-clip/) | visuals | **Everything else** — diagrams, charts, title cards, kinetic type, code → `remotion/` |
| [`meme-pass`](.claude/skills/meme-pass/) | assets | Sweeps transcripts for beats wanting a reaction shot → `memes/PLACEMENT.md` |
| [`find-memes`](.claude/skills/find-memes/) | assets | Gets one reaction GIF or sticker into `memes/`, edit-ready |
| [`audio-pass`](.claude/skills/audio-pass/) | assets | Plans the music bed and SFX cues → `audio/PLACEMENT.md` |
| [`find-audio`](.claude/skills/find-audio/) | assets | Gets one track or effect into `audio/`, free licences only |
| [`extract-reels`](.claude/skills/extract-reels/) | repurpose | Cuts ≥5 vertical 9:16 reels from the finished video, with an animated end card |

### Footage

**`process-recording`** transcribes the raw take *first*, then cuts — because
duration alone cannot tell a deliberate pause from a stall, but the words either
side can. A completed sentence before a silence reads as rhetorical (keep);
trailing off mid-clause, or backing up to repeat yourself, reads as hesitation
(cut). Ambiguous gaps are **kept**: a pause wrongly kept costs a beat of dead
air, a pause wrongly cut destroys a delivery.

It then projects the raw cues through its own cut map, so `processed/*.srt`
matches the edit exactly and Whisper runs once.

### Planning

Both plan skills are **Socratic, not generative**. They interrogate the user's
idea — what is the promise, what open loop does it leave, does the payoff
actually exist — and refuse to invent a video on the user's behalf. Both show a
draft before writing anything, because reordering a plan costs a sentence and
reordering finished clips costs hours.

`hook-plan` additionally records which design rules the hook **suspends**, by
section number. Some are suspendable (text at frame centre, when there is no
speaker to sit behind it); others are not (legibility, minimum shot length, the
palette).

### Building

`main-build` and `hook-build` derive every mechanical value — durations, frame
numbers, encode flags — and hand-type none of it. The editorial plan is written
as Python that imports a tracked engine, which probes every asset's real length
with `ffprobe`.

### Delivery

`combine-all` joins with the concat **filter**, not the demuxer with `-c copy`.
AAC frames are 1024 samples, so a part that is a whole number of *video* frames
is not a whole number of *audio* frames; stream-copying two parts leaves the
audio ~21 ms longer than the video at the seam. It also checks both parts were
rendered against the **current** design before encoding — a stale part means the
join contains two design systems, and nothing errors.

---

## The design system

**[`DESIGN.md`](DESIGN.md) is the design authority, and it is read, not parsed.**

A design system is judgement — *the accent is functional, never decorative*; *the
content supplies the colour so the frame stays achromatic*; *shadows are heavy
because thin ones are invisible on dark* — and none of that survives a token
extractor. Every skill that touches a pixel reads it first.

It lands in exactly two hand-authored files:

| file | owns |
|---|---|
| `.remotion/src/design.ts` | palette, semantic roles, type scale, spacing, elevation, spatial zones, motion counts |
| `.manim/scenes/design.py` | the same roles for Manim, spacing in scene units, layout regions, the code theme |

Swap `DESIGN.md`, update those two, re-render. Nothing else may name a colour or
a size — `scripts/check_design.py` fails the build on a raw hex or a bare font
size anywhere else, including the per-video editorial plans.

---

## What the build enforces

Editorial rules are **build-time failures**, not conventions to remember. Each of
these caught a real defect that reviewing by eye had missed.

| check | triggers on | effect |
|---|---|---|
| `check_not_early()` | on-screen text appears before its words are spoken | **fails** |
| `check_no_repeated_gifs()` | a gif is used more than once in the video | **fails** |
| `check_min_shot()` | a beat under 45 frames — below that a shot reads as a glitch | **fails** |
| `check_beat_window()` | a trim window inverted, or starting past the end of its source | **fails** |
| `check_duration_target()` | the hook past its ceiling | **fails** |
| `audit_layout()` | a Manim mobject overflows the frame, or two collide | **fails** |
| `check_design.py` | a colour or size named outside the two design modules | **fails** |
| `report_coverage()` | a stretch outside a cutaway with nothing on screen | reports to stderr |
| `check_duration_target()` | the hook off its target band but inside the ceiling | warns |

`report_coverage()` reports rather than failing on purpose — a bare stretch is
sometimes the right call, and a hard failure would make "leave this beat clean" a
fight with the tooling.

None of these replaces looking at a rendered frame. They catch overflow and
drift; they cannot tell you a composition is lopsided, that a diagonal reads
badly, or that a label is technically clear but ambiguous.

---

## Layout

```
scripts/          engines and tooling (tracked)
docs/             standards: manim layout, remotion composition
.claude/skills/   the 13 skills
.remotion/src/    composition source + design.ts
.manim/scenes/    design.py (the one tracked scene file)
DESIGN.md         the design authority
CLAUDE.md         project conventions, loaded every session

raw/ processed/ screencasts/ audio/ memes/ manim/ remotion/ reels/
                  one episode's media — gitignored
video_clips/      short clips the user drops in by hand for a plan to
                  draw on — gitignored like the rest
plans/            plans/main.md, plans/hook.md — per-video, gitignored
```

**Requires:** ffmpeg with NVENC, whisper.cpp (`ggml-cpu` + `ggml-cuda`), Manim
Community, Node with pnpm. GPU-first throughout: encode, decode and export run on
NVIDIA, never the iGPU. See `SPEC.md` for the machine this is tuned for — 4 GiB
VRAM is the binding constraint on render concurrency.

---

## Licence

MIT — see [LICENSE](LICENSE). Copyright © 2026 Piyush Raj
<piyushxcoder@gmail.com>.

Note that the licence covers **this harness**, not the media a video is made
from. Sourced music and memes carry their own terms, recorded in
`audio/CREDITS.md` and `memes/CREDITS.md`.
