---
name: manim-clip
description: Create a Manim animation clip for this video project — writing the scene, rendering it, and publishing the output to manim/. Use when the user asks to create/make/add a manim clip, animation, or scene.
---

# Manim clip creation

Manim Community v0.19.1. Scene source lives in `.manim/` (the actual project); rendered, ready-to-use clips are published to `manim/` at the repo root — see `CLAUDE.md` for that convention.

## Workflow

1. **Name the clip.** Pick a kebab-case `<clip_name>` (ask the user if not obvious from context) and derive a `PascalCase` Scene class name from it (e.g. `binary-search` → `BinarySearch`).

2. **Write the scene.** Create/edit `.manim/scenes/<clip_name>.py`:
   ```python
   from manim import *


   class <ClassName>(Scene):
       def construct(self):
           ...
   ```
   One `.py` file per clip. Implement `construct()` to match what the user described.

3. **Render** from `.manim/`:
   ```bash
   cd .manim && manim render scenes/<clip_name>.py <ClassName> -o <clip_name>
   ```
   Resolution (2048x1280, 8:5 — matches this project's screen-recording aspect ratio) and frame rate (30fps) come from `.manim/manim.cfg`; don't repeat them on the command line. Only pass `-r WIDTH,HEIGHT` / `--fps N` if the user explicitly wants a one-off different size for that clip.

4. **Publish.** Manim writes to `.manim/media/videos/<clip_name>/<quality_folder>/<clip_name>.mp4`. Copy that file to `manim/<clip_name>.mp4` at the repo root — that's the deliverable other steps (concat, editing) consume.

5. **Report** the final path and duration (`ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 manim/<clip_name>.mp4`) back to the user.

## Notes

- Manim's renderer (Cairo, the default) is CPU-bound — this project's "prefer NVIDIA GPU" rule (see `CLAUDE.md`) applies to the ffmpeg-based scripts (`trim_to_short_video.sh`, `process_recording.py`), not to Manim rendering itself.
- `.manim/media/` is gitignored (regenerable render cache). `.manim/scenes/*.py` and `.manim/manim.cfg` are the tracked source.
- If a scene needs iterating, re-run the same render command — Manim caches unchanged animations by default and only re-renders what changed.
