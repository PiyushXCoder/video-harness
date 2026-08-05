# YouTube Template

Repo for producing YouTube videos: scripts + asset directories, one project per video.

## Directory layout

- `scripts/` — automation scripts (rendering, encoding, uploads, etc.)
- `manim/` — rendered Manim clips (output). Actual Manim project source lives in `.manim/`.
- `remotion/` — rendered Remotion clips (output). Actual Remotion project source lives in `.remotion/`.
- `raw/` — raw screen/camera recordings, unedited
- `processed/` — video processed/edited from `raw/`
- `screencasts/` — screen recordings, taken manually by user (no automated capture tooling)
- `audio/` — audio tracks (voiceover, music, SFX)
- `memes/` — meme assets
- `plans/` — planning docs for videos/features
- `progress.md` — running log of progress

## Machine spec

See `SPEC.md` for CPU/GPU/RAM/disk. Key constraint: 4 GiB VRAM (RTX 3050 Laptop) — keep render concurrency low, check nvenc/CUDA tools bind to NVIDIA not Intel iGPU.

Always prefer NVIDIA GPU for video processing (encode/decode/render), not Intel iGPU or CPU-only. E.g. ffmpeg use `-hwaccel cuda` / `h264_nvenc`/`hevc_nvenc`; force `prime-run` where needed.

## Conventions

- `.manim/` and `.remotion/` hold actual project source (configs, scenes, components); `manim/` and `remotion/` hold their rendered output only.
- Keep raw recordings in `raw/` untouched; edits go to `processed/`.

## Scripts

- `scripts/trim_to_short_video.sh <video1> <video2> <output>` — keep first N min of video1, concat video2 after it. NVENC/CUDA-accelerated (GPU decode+encode). Handles mismatched resolution/fps via scale+pad filter.
- `scripts/process_recording.py <input> [output]` — raw/ → processed/ pipeline. Cuts silent gaps >=1s (video+audio stay in sync), then cleans audio (highpass, compressor, loudnorm EBU R128) for loud/clear podcast-style sound. Video encoded with h264_nvenc (GPU).

## Skills

- `manim-clip` (`.claude/skills/manim-clip/`) — writes a Manim scene to `.manim/scenes/<clip_name>.py`, renders it (2048x1280 @ 30fps, set in `.manim/manim.cfg`), publishes the result to `manim/<clip_name>.mp4`. Manim's render is CPU-bound (Cairo) — the GPU-first rule above applies to the ffmpeg scripts, not to Manim itself.
- `remotion-clip` (`.claude/skills/remotion-clip/`) — writes a Remotion composition to `.remotion/src/compositions/<Name>.tsx`, registers it in `.remotion/src/Root.tsx`, renders it (2048x1280 @ 30fps default), publishes the result to `remotion/<clip_name>.mp4`. Render encode is CPU x264 (Remotion's bundled ffmpeg), not NVENC.
