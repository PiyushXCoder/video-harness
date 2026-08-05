# YouTube Template

Repo for producing YouTube videos: scripts + asset directories, one project per video.

## Directory layout

- `scripts/` — automation scripts (rendering, encoding, uploads, etc.)
- `manim/` — rendered Manim clips (output). Actual Manim project source lives in `.manim/`.
- `remotion/` — rendered Remotion clips (output). Actual Remotion project source lives in `.remotion/`.
- `raw/` — raw screen/camera recordings, unedited
- `processed/` — video processed/edited from `raw/`
- `screencasts/` — screen recordings
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
