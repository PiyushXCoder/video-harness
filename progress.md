# Progress

## 2026-08-05
- Repo scaffolded: scripts, manim, memes, raw, audio, processed, remotion, screencasts, plans dirs.
- Added CLAUDE.md, progress.md.
- Added SPEC.md (machine spec: i7-12700H, RTX 3050 4GB VRAM, 15GB RAM); linked from CLAUDE.md.
- CLAUDE.md: always prefer NVIDIA GPU for video processing (nvenc/cuda) over Intel iGPU/CPU.
- Added `scripts/trim_to_short_video.sh` — trim video1 to first N min, concat video2, NVENC/CUDA accelerated.
- Added `scripts/process_recording.py` — raw/ -> processed/ pipeline: cuts silent gaps >=1s (video+audio sync), cleans audio (highpass, compressor, loudnorm) for podcast-style loud/clear sound, h264_nvenc encode. Tested against synthetic clip.
