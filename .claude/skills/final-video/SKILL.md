---
name: final-video
description: Produce a complete finished video end to end — process raw footage, transcribe, plan the theme, generate Manim and code clips, add memes and audio, and assemble everything in Remotion with a GPU export. Use when the user asks to make the video, build the final video, assemble everything, or hands over a batch of raw recordings and assets.
---

# Complete video production flow

The orchestrator. Each stage has its own skill with the detail; this one owns the
order, the hand-offs, and the assembly. **Remotion is the editor — there is no
manual NLE step.**

Read `docs/remotion-video-guidelines.md` before assembling anything.

## Inputs you'll be handed

| where | what | notes |
|---|---|---|
| `raw/` | raw recordings, `.mkv` | unedited, possibly with flubbed takes |
| `screencasts/` | screen recordings, meaningfully named | captured manually |
| `images/` or as given | stills, meaningfully named | diagrams, screenshots, logos |
| `memes/` | assets the user already picked | may be empty |

Names are information. A file called `handshake-failure.mkv` tells you where it
belongs; ask rather than guess when a name is opaque.

---

## Stage 1 — Process the footage

Use **`process-recording`**. Do not re-derive it here.

```bash
for f in raw/*.mkv; do python3 scripts/process_recording.py "$f"; done
./scripts/generate_subtitles.sh
```

Order is fixed: processing changes the timeline, so subtitles must come after. If
you re-encode anything later, regenerate its `.srt` with `--force` in the same
pass — a stale `.srt` is a silent failure.

**Discard bad takes.** Read the transcripts and find false starts and flubs —
they trail off mid-sentence, or repeat a line that a later clip does better. Move
them to `raw/discarded/` with a README, never delete. Both scripts glob
`raw/*.mkv` so a subdirectory drops out of the pipeline automatically.

## Stage 2 — Read everything, then plan the theme

**This is the stage that decides whether the video is good.** Do not skip to
generating clips.

```bash
for f in processed/*.srt; do echo "=== $(basename "$f" .srt)"; \
  sed -e '/^[0-9]\+$/d' -e '/-->/d' -e '/^$/d' "$f" | tr '\n' ' '; echo; done
```

From the transcripts, write a plan and **show it to the user before building**:

- **Spine** — the narrative order of clips. Recording order is not always it.
- **Theme** — what the video argues, in one sentence. Everything serves it.
- **Visual language** — Catppuccin Latte + Fira Code is fixed (`CLAUDE.md`).
  Decide the recurring motifs: does the architecture diagram return as a
  through-line? Is there a consistent colour for the component under discussion?
- **What needs a visual** — where the narration describes something spatial or
  procedural that words alone won't carry.
- **What needs nothing** — talking-head stretches that should stay clean. An
  explainer does not need a graphic every 20 seconds.
- **Runtime estimate** and where it's slack.

Ask the user to confirm the spine before generating anything. Reordering a plan
costs a sentence; reordering finished clips costs hours.

## Stage 3 — Generate visuals

**Ask where the source code lives** if the video explains software and you don't
already know. For this series it is `/home/piyush/Projects/dhaar-torrent`, but
confirm rather than assume — and check component names and constants against the
code, not the narration. The narration in this project omits `request_manager`
entirely and misnames `PieceWriter`.

- **`manim-clip`** — diagrams and animated explanations. Design by constraint,
  audit geometry with `-s` before rendering video, then look at a frame.
- **`code-clip`** — real source with elisions marked. Never invented code.

For a diagram revealed across several narration beats, keep node positions fixed
across the stages and animate only each stage's delta, so cuts between clips
don't make boxes jump.

**Render new clips at 2048×1280**, the project's native 8:5 — same as the
composition, so they fill the frame and nothing is scaled. This is what
`.manim/manim.cfg` already does; leave it alone.

## Stage 4 — Memes and stickers

Use **`meme-pass`** for the sweep, **`find-memes`** for individual assets.

Roughly one beat per 60–90 s of finished video, only where the narration already
carries the joke, and never over an explanation. Writes `memes/PLACEMENT.md`.

Flag obvious studio content (film/TV/sport) rather than shipping it silently.

## Stage 5 — Audio

Use **`audio-pass`** for the plan, **`find-audio`** for individual assets.

One bed plus SFX mapped to moments in the generated clips. **Free licences only**
— the allowlist passes CC0 and plain CC-BY and nothing else. Prefer the YouTube
Audio Library: no key, no Content ID risk. Writes `audio/PLACEMENT.md`.

## Stage 6 — Assemble in Remotion

Follow `docs/remotion-video-guidelines.md`. In short:

1. `cd .remotion && npm install && npm i @remotion/transitions @remotion/media-utils`
   — `node_modules` is gitignored and does **not** travel between git worktrees,
   so this is needed even though another worktree has it.
2. Build `src/timeline.ts` — a manifest of segments with durations read from the
   files (`ffprobe`/`getVideoMetadata`), never hand-typed.
3. Build `src/FinalVideo.tsx` with `<Series>` / `<TransitionSeries>`; register it
   in `src/Root.tsx` at **2048×1280 @ 30 fps** — the native source size.
4. Do not scale or crop any source: everything is already 2048×1280.
5. Overlays from `memes/PLACEMENT.md`, audio from `audio/PLACEMENT.md` with the
   bed ducked under speech using the `.srt` cue ranges.
6. Preview a slice before the full render: `--frames=0-300`.

**Export on the GPU:**

```bash
npx remotion render FinalVideo ../processed/final.mp4 \
    --hardware-acceleration=required --concurrency=6
```

`required` makes a silent fall back to CPU encoding fail loudly. NVENC covers
h264/h265 only.

## Stage 7 — Verify, then hand over

Run the checklist at the end of the guidelines. At minimum: `ffprobe` the output
for 2048×1280/30fps/h264, confirm the duration matches the manifest, extract
frames at transitions and **look at them**, and check audio peaks stay under
0 dBFS.

Report: runtime, what's in it, and the contents of `memes/CREDITS.md` +
`audio/CREDITS.md` for the description box.

---

## Order matters

```
raw ─► process ─► subtitles ─► READ + PLAN ─┬─► manim / code clips ─┐
                                            ├─► memes ──────────────┤
                                            └─► audio ──────────────┴─► Remotion ─► NVENC export
```

Subtitles after processing. Planning after reading, before building. Assembly
last, because every other stage feeds it durations.

## Where this goes wrong

- **Building before planning.** The expensive mistake. Clips generated against a
  spine that later changes are wasted work.
- **Hardcoded durations.** They drift from the assets and produce freezes or
  truncation that the studio preview doesn't reveal.
- **Unclamped `interpolate`.** Elements drift off frame in unpreviewed frames.
- **Scaling or cropping a source.** Everything is 2048×1280 already; a rescale
  softens monospace text and a 16:9 crop would clip Manim content that
  `audit_layout()` cannot see, because the clipping happens in the composition.
- **Stale `.srt` after a re-encode.** Looks fine, drifts out of sync.
- **A meme or cue on everything** because the tooling made it cheap. Restraint is
  the difference between professional and busy.
