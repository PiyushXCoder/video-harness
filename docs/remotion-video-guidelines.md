# Final video assembly & animation guidelines (Remotion)

How the finished video is built. Remotion is the editor — there is no manual NLE
step. Everything here is specific to this project: 30 fps, Catppuccin Latte,
Fira Code, narration mastered to −16 LUFS.

Read `docs/manim-layout-guidelines.md` too. Its rules on relationships-over-
coordinates, spacing scale, focus/context and validation apply to composition
code as much as to Manim scenes.

---

## 1. Delivery format

**Deliver 2048×1280 — 8:5 (1.60), the screen recorder's native ratio.** Every
source in this project is already that size, so nothing is scaled, cropped or
framed. This is a deliberate choice over the 16:9 convention:

- **No resampling.** Screencasts and code clips go in pixel-for-pixel. Any
  rescale softens small monospace glyphs, and this is a programming video where
  the viewer is reading `request_manager` and `MAX_PEERS = 50` off the screen.
- **No cropping risk.** A 16:9 crop of 8:5 removes 128 px, 64 top and bottom.
  Manim content runs out to `Y_LIM = 3.7` of a 4.0 half-height — 0.3 units of
  margin against a 0.4-unit crop — so it would clip real content, and
  `audit_layout()` could not catch it because the clipping happens downstream
  here in the composition, not in the scene.
- **No framing machinery.** No backdrop, border or shadow needed to make
  letterboxing look intentional.

The trade-off, stated plainly: on a 16:9 desktop player YouTube **pillarboxes**
8:5 content — bars of about 96 px each side at 1080 height, roughly 5% of width.
YouTube handles any ratio and there is no algorithmic penalty; on a phone held
portrait, 8:5 actually gets *more* screen height than 16:9. Thumbnails are 16:9
regardless of the video, so design those separately.

Consequences to keep in mind:

- Keep `.manim/manim.cfg` at `pixel_width = 2048`, `pixel_height = 1280`. New
  clips match the composition and fill the frame with no work.
- The composition is 2048×1280 @ 30 fps. 2.6 Mpx per frame is about 27% more than
  1080p, so renders are correspondingly slower — budget for it.
- Nothing in the timeline should scale a video source. If you find yourself
  writing a `transform: scale()` on a full-frame clip, something is wrong.

## 2. Timeline structure

One `<FinalVideo>` composition. Never hand-place a `<Sequence from={...}>` with a
literal frame number — a single timing change would then require editing every
subsequent number.

Drive the edit from a **manifest**: an ordered array of segments, each naming its
source, its duration, and how it enters. Compute offsets by reduction.

```tsx
// src/timeline.ts
export type Segment = {
  id: string;
  kind: 'narration' | 'manim' | 'code' | 'screencast' | 'image';
  src: string;
  durationInFrames: number;
  transition?: {type: 'fade' | 'slide' | 'none'; frames: number};
  overlays?: Overlay[];   // memes, callouts, lower thirds
};
```

Then render with `<Series>`, or with `<TransitionSeries>` from
`@remotion/transitions` when segments need transitions. Both derive offsets for
you; `<Series>` is the default choice.

**Get durations from the files, not by hand.** `getVideoMetadata()` from
`@remotion/media-utils` at build time, or precompute a JSON manifest with
`ffprobe`. A hardcoded duration that disagrees with its asset produces either a
freeze-frame or a truncated clip, and neither is obvious in the studio preview.

---

## 3. Pacing

- **Frames, always.** Read `fps` from `useVideoConfig()`; never hardcode 30.
- **Minimum shot 45 frames (1.5 s).** Anything under ~15 frames reads as a
  glitch, which is the same lesson the silence-cutting pass taught: sub-0.5 s
  fragments look like a mistake, not an edit.
- **Cut on speech boundaries.** The `.srt` cue times in `processed/` are the
  authority — parse them rather than eyeballing. Never cut mid-word.
- **Let a beat land.** Hold ~10 frames after a punchline before the next segment.
- **Code needs reading time.** 2.5 s + 0.3 s per line, the same rule
  `_CodeClip` uses. 27 lines of Rust wants ~12 s, not 3.

---

## 4. Transitions

**A cut is the default.** A transition is punctuation, and a video where every
segment dissolves reads as a slideshow.

| situation | transition |
|---|---|
| within a topic | **cut** |
| topic change | `fade`, 9 frames (0.3 s) |
| narration → animation | **cut**, or 6-frame fade |
| into the demo / payoff | `fade` up to 15 frames |
| everything else | cut |

- 8–12 frames for a fade. Beyond ~15 it feels sluggish at 30 fps.
- **Never transition mid-sentence.** Check against the `.srt`.
- Avoid slide/wipe/flip unless the motion means something (e.g. sliding to a
  "next" state). Directionless movement is noise.
- Do not stack a transition with an entrance animation on the same content.

---

## 5. Animation

```tsx
const frame = useCurrentFrame();
const {fps} = useVideoConfig();

// Physical movement: spring.
const y = spring({frame, fps, config: {damping: 200}});

// Opacity and simple ramps: interpolate — ALWAYS clamped.
const opacity = interpolate(frame, [0, 8], [0, 1], {
  extrapolateLeft: 'clamp',
  extrapolateRight: 'clamp',
});
```

- **Clamp every `interpolate`.** Unclamped extrapolation is the most common
  Remotion bug: values keep travelling past the range and elements drift off
  screen or fade to negative opacity, often only in frames nobody previewed.
- **Entrances 6–10 frames.** Longer feels slow; the viewer is waiting for content.
- **Stagger 2–3 frames** between related elements — enough to read as sequence,
  not enough to feel like a queue.
- `damping: 200` for UI-like motion (no visible bounce). Only let something
  overshoot if the bounce is the joke.
- **Animate `transform` and `opacity`.** Animating layout properties (`width`,
  `top`, `margin`) costs render time and can jitter between frames.
- Motion must mean something: an element enters *from* where it came from.
  Decorative movement is what makes an edit feel amateur.

---

## 6. Overlays: memes, stickers, callouts

- Assets are in `memes/`, mapped to beats in `memes/PLACEMENT.md`. Use
  `<OffthreadVideo>`, not `<Video>`: it extracts frames server-side with FFmpeg,
  so it handles ProRes and is frame-accurate.
- **Transparent stickers** (`.mov`, ProRes 4444, `yuva444p`) need
  `transparent={true}`. That extracts frames as PNG and costs roughly **40% more
  render time** — use it only on genuinely transparent assets.
- **Opaque memes** (`.mp4`) go in a bordered inset, not full-frame over the
  narration: rounded corners, 1 px `surface1` border, soft shadow, ~28–34% of
  frame width, in a corner that isn't covering anything.
- Entrance 6 frames (scale 0.85→1 + fade), exit 6 frames. Hold 1–2.5 s. A meme
  that outstays the joke kills the joke.
- Cap it at **one overlay at a time**. Two competing overlays means neither reads.

---

## 7. Subtitles

Do **not** burn full captions in. YouTube's own captions are searchable,
translatable and toggleable — upload the `.srt` from `processed/` instead.

Do use **selective on-screen text** for things the ear mishears: component names
(`request_manager`), constants (`MAX_PEERS = 50`), and the domain terms whisper
itself got wrong (`bencode`, `Tokio`). Fira Code, `text` colour on a `mantle`
pill, 8-frame fade, out before the next beat.

---

## 8. Audio

One narration track, one music bed, SFX on top.

- **Narration** is the reference at −16 LUFS. Do not touch its level.
- **Bed** imports at −20 LUFS and still needs **ducking 6–9 dB under speech**.
  Drive it from the `.srt` cue ranges rather than by ear:

  ```tsx
  <Audio src={bed} volume={(f) => (isSpeaking(f) ? 0.35 : 0.8)} />
  ```

  `volume` as a function is per-frame; ramp over ~10 frames at each boundary or
  the level change will click audibly.
- **SFX** import at −6 dBFS peak. A cue used six times must be near-subliminal
  and non-tonal — repeated pitched effects become an unintended melody.
- Never let bed + SFX + narration sum past 0 dBFS. Leave ~3 dB headroom.

---

## 9. Rendering & export

```bash
cd .remotion
npm install                       # node_modules is gitignored and does NOT
                                  # travel between git worktrees
npm i @remotion/transitions @remotion/media-utils

# preview
npx remotion studio

# final, on the GPU
npx remotion render FinalVideo ../processed/final.mp4 \
    --hardware-acceleration=required \
    --concurrency=6
```

- **`--hardware-acceleration=required` for the real export.** Remotion's bundled
  FFmpeg has **NVENC on Linux x64**, for **h264/h265 only** — any other codec
  silently falls back to software. `required` makes a fallback fail loudly
  instead of quietly costing you 20 minutes.
- `--concurrency` bounds **Chromium** workers, which are CPU/RAM-bound, not GPU.
  With 15 GiB RAM, 6 is a sane cap; higher swaps and gets slower.
- Render a **10-second slice first** (`--frames=0-300`). A 9-minute render is not
  the place to discover a clamping bug.
- Expect a full render to take **minutes, not seconds**. Budget for it.

---

## 10. Validation before shipping

Same spirit as `audit_layout()` — check, don't assume:

- [ ] Total duration matches the manifest sum (`ffprobe` the output).
- [ ] Video is **2048×1280**, 30 fps, h264, `yuv420p`.
- [ ] NVENC actually ran — the render log says so; `required` proves it.
- [ ] No segment shorter than 45 frames.
- [ ] Extract frames at every transition and **look at them**: `-sseof`, or
      `-ss` at known boundaries. No source has been inadvertently scaled.
- [ ] Peak audio below 0 dBFS; bed audibly ducks under speech.
- [ ] Every `interpolate` clamped (grep for `interpolate(` and check).
- [ ] `CREDITS.md` from `memes/` and `audio/` folded into the description.
