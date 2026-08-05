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

## Notes

- Remotion renders via headless Chromium — compositing itself can use GPU (Chromium's own rasterizer), but the final encode is Remotion's bundled x264 (CPU), not NVENC. This project's "prefer NVIDIA GPU" rule (see `CLAUDE.md`) doesn't cleanly apply to Remotion's render step; if you need a GPU re-encode afterward, run the published clip back through `scripts/process_recording.py`-style ffmpeg NVENC settings.
- `.remotion/node_modules/` and `.remotion/out/` are gitignored. `.remotion/src/**`, `package.json`, and `remotion.config.ts` are the tracked source.
- If `.remotion/node_modules` is missing (fresh clone), run `npm install` inside `.remotion/` first.
