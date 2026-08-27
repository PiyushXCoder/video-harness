---
name: remotion-clip
description: Create a Remotion animation/video clip for this video project — writing the composition, rendering it, and publishing the output to remotion/. Use when the user asks to create/make/add a remotion clip, composition, or animated video.
---

# Remotion clip creation

Remotion project source lives in `.remotion/` (React + TypeScript, deps already installed via `npm install` in that dir); rendered, ready-to-use clips are published to `remotion/` at the repo root — see `CLAUDE.md` for that convention.

## Workflow

1. **Name the clip.** Pick a kebab-case `<clip_name>` (ask the user if not obvious from context) and derive a `PascalCase` component name from it (e.g. `title-card` → `TitleCard`).

2. **Write the composition.** Create `.remotion/src/compositions/<ComponentName>.tsx`:
   ```tsx
   import React from 'react';
   import {AbsoluteFill, useCurrentFrame} from 'remotion';

   export const <ComponentName>: React.FC = () => {
     const frame = useCurrentFrame();
     return <AbsoluteFill>...</AbsoluteFill>;
   };
   ```
   Build the animation with Remotion's frame-based primitives (`useCurrentFrame`, `interpolate`, `spring`, `Sequence`, etc.) per what the user described.

3. **Register it** in `.remotion/src/Root.tsx` — add an import and a `<Composition>` entry:
   ```tsx
   <Composition
     id="<clip_name>"
     component={<ComponentName>}
     durationInFrames={<N>}
     fps={30}
     width={2048}
     height={1280}
   />
   ```
   Default to 2048x1280 @ 30fps (8:5 — matches this project's screen-recording aspect ratio) unless the user wants a one-off different size for that clip. `durationInFrames` = seconds × fps.

4. **Render** from `.remotion/`:
   ```bash
   cd .remotion && npx remotion render src/index.ts <clip_name> out/<clip_name>.mp4
   ```

5. **Publish.** Copy `.remotion/out/<clip_name>.mp4` to `remotion/<clip_name>.mp4` at the repo root — that's the deliverable other steps (concat, editing) consume.

6. **Report** the final path and duration (`ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 remotion/<clip_name>.mp4`) back to the user.

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
- **Highlighting must match** `DESIGN.md` section 10.9, encoded in `.remotion/src/design.ts`
  (keywords mauve, strings green, comments overlay2, constants peach, operators
  keyword green, string blue, number orange, comment faint gray). Add a highlighter to `.remotion/`
  if the clip needs one rather than assuming one is installed.
- **Ligatures are safe here.** The old Manim path banned Fira Code on code blocks
  because its `//` ligature desynced Manim's per-character glyph mapping and
  crashed `Code()` with `IndexError` in `_gen_chars`. Remotion renders text in
  Chromium with no such mapping, so `FONT` from `palette.ts` is fine and `->` /
  `==` render as intended. This is one of the reasons code clips moved.

## Notes

- Remotion renders via headless Chromium — compositing itself can use GPU (Chromium's own rasterizer), but the final encode is Remotion's bundled x264 (CPU), not NVENC. This project's "prefer NVIDIA GPU" rule (see `CLAUDE.md`) doesn't cleanly apply to Remotion's render step; if you need a GPU re-encode afterward, run the published clip back through `scripts/process_recording.py`-style ffmpeg NVENC settings.
- `.remotion/node_modules/` and `.remotion/out/` are gitignored. `.remotion/src/**`, `package.json`, and `remotion.config.ts` are the tracked source.
- If `.remotion/node_modules` is missing (fresh clone), run `npm install` inside `.remotion/` first.
