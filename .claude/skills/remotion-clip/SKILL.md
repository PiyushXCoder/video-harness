---
name: remotion-clip
description: Create a Remotion animation/video clip for this video project — writing the composition, rendering it, and publishing the output to remotion/. Use when the user asks to create/make/add a remotion clip, composition, or animated video.
---

# Remotion clip creation

Remotion project source lives in `.remotion/` (React + TypeScript); rendered, ready-to-use clips are published to `remotion/` at the repo root — see `CLAUDE.md` for that convention.

**This is the default clip engine.** Manim is for mathematical animation only, so everything else lands here: architecture diagrams, charts of measured data, timelines, title cards, kinetic type and code.

## Before you write anything

**Read `DESIGN.md`.** It is the design authority for the whole video, and it is **read, not parsed** — the load-bearing parts are judgements no token can carry:

- the accent is **functional, never decorative** — it marks state, not mood, and never fills a background;
- the content supplies the colour, so the frame around it stays achromatic;
- shadows are **heavy** because thin ones are invisible on dark, and over unpredictable footage they do a second job — separating text from whatever is behind it;
- the weight hierarchy is a **700/400 binary**, not a ladder of sizes.

**Section 10 is the video adaptation and overrides section 3's web-scaled sizes** (web's 10–24 px becomes 28–140 px, because this is read at distance). **Section 8 does not apply at all** — one fixed 2048×1280 frame, no breakpoints, no hover, no inputs. Section 10.4 gives the spatial zones, 10.5 the centre rule, 10.6 the motion frame counts, 10.9 the code theme.

Everything it specifies is already encoded in **`.remotion/src/design.ts`**. Import tokens — **never write a hex, a font size or a shadow string yourself.** `python3 scripts/check_design.py` fails the build if you do, and it is not decoration: the composition had accumulated fifteen ad-hoc font sizes and five bespoke shadow recipes across eleven components before this existed.

## Workflow

1. **Name the clip.** Pick a kebab-case `<clip_name>` (ask the user if not obvious from context) and derive a `PascalCase` component name from it (e.g. `title-card` → `TitleCard`).

2. **Write the composition.** Create `.remotion/src/compositions/<ComponentName>.tsx`:
   ```tsx
   import React from 'react';
   import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
   import {ROLE, FONT_DISPLAY, TYPE, SPACE, ZONE, MOTION, SHADOW} from '../design';

   export const <ComponentName>: React.FC<{durationInFrames: number}> = ({durationInFrames}) => {
     const frame = useCurrentFrame();
     // Clamp BOTH ends of every interpolate — an unclamped one drifts the
     // element off frame in exactly the frames nobody previews.
     const opacity = interpolate(frame, [0, MOTION.fadeIn], [0, 1], {
       extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
     });
     return (
       <AbsoluteFill style={{backgroundColor: ROLE.bg, opacity}}>
         <div style={{
           fontFamily: FONT_DISPLAY,
           fontSize: TYPE.hookTitle.size,
           fontWeight: TYPE.hookTitle.weight,
           color: ROLE.text,
           textShadow: SHADOW.text,
         }}>...</div>
       </AbsoluteFill>
     );
   };
   ```
   Build the animation with Remotion's frame-based primitives (`useCurrentFrame`, `interpolate`, `spring`, `Sequence`). Read `fps` from `useVideoConfig()` — never hardcode 30.

   Two `DESIGN.md` rules that decide layout, not just colour:

   - **Nothing at frame centre while a speaker is on screen** (10.5) — that is their face. A clip with no speaker in it may use the centre; say so when you do.
   - **Every piece of text carries a scrim or a heavy shadow** (10.3). Over arbitrary footage contrast is never guaranteed, so `scrim()` or `SHADOW.text` is not optional. A coloured `glow()` may sit on top for emphasis but never replaces the black shadow underneath.

3. **Register it** in `.remotion/src/Root.tsx` — add both imports and a `<Composition>` entry:
   ```tsx
   import {<ComponentName>} from './compositions/<ComponentName>';
   import {VIDEO} from './design';
   // ...
   <Composition
     id="<clip_name>"
     component={<ComponentName>}
     durationInFrames={<N>}
     fps={VIDEO.fps}
     width={VIDEO.width}
     height={VIDEO.height}
   />
   ```
   `VIDEO` comes from `./design` (Root.tsx sits beside it) — 2048×1280 @ 30 fps (8:5, this project's native recording ratio), so a clip fills the frame and nothing is scaled. Only override for a deliberately different deliverable (a vertical reel). `durationInFrames` = seconds × fps.

4. **Render** from `.remotion/` — a still first, then video. A still is seconds and proves both that `staticFile()` paths resolve and that a real frame decodes:
   ```bash
   cd .remotion
   npx remotion still <clip_name> out/<clip_name>.png --frame=30
   npx remotion render <clip_name> out/<clip_name>.mp4 \
       --hardware-acceleration=required --concurrency=6
   ```
   Run Remotion **from `.remotion/`** — `npx --prefix .remotion` silently no-ops (it cannot find the entry point and still exits 0). Never pass `--crf` alongside hardware acceleration: Remotion drops to software encoding when both are set, and the log line is easy to miss.

5. **Check the design lint and look at a frame.** A stray hex renders perfectly and silently forks the design system, so the eye will not catch it:

   ```bash
   python3 scripts/check_design.py
   ```

6. **Publish.** Copy `.remotion/out/<clip_name>.mp4` to `remotion/<clip_name>.mp4` at the repo root — that's the deliverable other steps (concat, editing) consume.

7. **Report** the final path and duration (`ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 remotion/<clip_name>.mp4`) back to the user.

## Code clips

Code on screen is Remotion's job — Manim is for mathematical animation only
(`CLAUDE.md`). The rules that used to live in the deleted `code-clip` skill:

- **Every character must be real source** from the implementation repo (this
  series: `/home/piyush/Projects/dhaar-torrent`). Read the file, copy the lines,
  mark anything removed with `// ...`. Never retype from memory and never write
  plausible-looking code — pasted source reads as authority, and invented code a
  viewer can't find in the repo undermines the whole video. If the user asks for
  something the code doesn't do, say so instead of inventing it. Trimming is fine
  and usually necessary (dropping error branches, collapsing an argument list);
  changing semantics is not.
- **Cite the origin file on screen** (`src/piece_manager/mod.rs`) so a viewer can
  find it.
- **Under ~28 lines.** Past that the type shrinks below readability at 2048×1280.
- **Reading time is the point:** hold 2.5 s + 0.3 s per line. 27 lines of Rust
  wants ~12 s, not the 3 s a default duration gives.
- **Verify bracket balance before rendering** — a stray bracket once put broken
  code on screen here:
  ```bash
  python3 - <<'PY'
  import re, pathlib, sys
  body = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/dev/stdin").read_text()
  s = re.sub(r'//.*', '', re.sub(r'/\*.*?\*/', '', body, flags=re.S))
  for o, c in (("(", ")"), ("{", "}"), ("[", "]")):
      print(o + c, "ok" if s.count(o) == s.count(c) else f"UNBALANCED {s.count(o)}/{s.count(c)}")
  PY
  ```
  Then diff what you pasted against the original by eye.
- **Use `FONT_CODE`** from `../design` for the block itself, and **highlighting must match** `DESIGN.md` section 10.9, encoded as `SYNTAX` roles
  (keywords mauve, strings green, comments overlay2, constants peach, operators
  keyword green, string blue, number orange, comment faint gray). Add a highlighter to `.remotion/`
  if the clip needs one rather than assuming one is installed.
- **Ligatures are safe here.** The old Manim path banned Fira Code on code blocks
  because its `//` ligature desynced Manim's per-character glyph mapping and
  crashed `Code()` with `IndexError` in `_gen_chars`. Remotion renders text in
  Chromium with no such mapping, so `FONT` from `palette.ts` is fine and `->` /
  `==` render as intended. This is one of the reasons code clips moved.

## Notes

- Remotion renders via headless Chromium, so **compositing is CPU/RAM-bound** — each worker is a Chromium instance, which is why `remotion.config.ts` caps concurrency at 6 on this machine's 15 GiB. The **encode** does use the GPU: Remotion's bundled FFmpeg has NVENC on Linux x64 for h264/h265, and `Config.setHardwareAcceleration('if-possible')` is already set. Pass `--hardware-acceleration=required` on a real render so a silent fall back to software fails loudly instead of quietly costing minutes.
- `.remotion/node_modules/` and `.remotion/out/` are gitignored. `.remotion/src/**`, `package.json`, and `remotion.config.ts` are the tracked source.
- If `.remotion/node_modules` is missing (fresh clone, or a new git worktree — `node_modules` does not travel between them), run `pnpm install` inside `.remotion/`. The project is pnpm; a stale `package-lock.json` is also present but `pnpm-lock.yaml` is the real one.
