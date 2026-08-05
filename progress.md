# Progress

## 2026-08-05
- Repo scaffolded: scripts, manim, memes, raw, audio, processed, remotion, screencasts, plans dirs.
- Added CLAUDE.md, progress.md.
- Added SPEC.md (machine spec: i7-12700H, RTX 3050 4GB VRAM, 15GB RAM); linked from CLAUDE.md.
- CLAUDE.md: always prefer NVIDIA GPU for video processing (nvenc/cuda) over Intel iGPU/CPU.
- Added `scripts/trim_to_short_video.sh` — trim video1 to first N min, concat video2, NVENC/CUDA accelerated.
- Added `scripts/process_recording.py` — raw/ -> processed/ pipeline: cuts silent gaps >=1s (video+audio sync), cleans audio (highpass, compressor, loudnorm) for podcast-style loud/clear sound, h264_nvenc encode. Tested against synthetic clip.
- Scaffolded `.manim/` project (manim.cfg: 2048x1280 @ 30fps, matches recorder aspect ratio) + `.manim/scenes/`.
- Added `manim-clip` skill (`.claude/skills/manim-clip/`) — write scene -> render -> publish to `manim/<clip>.mp4` workflow.
- Scaffolded `.remotion/` project (React+TS, deps installed, 2048x1280 @ 30fps default composition size).
- Added `remotion-clip` skill (`.claude/skills/remotion-clip/`) — write composition -> register in Root.tsx -> render -> publish to `remotion/<clip>.mp4` workflow. Verified end-to-end with a throwaway smoke-test composition.
- Noted screencasts/ is captured manually, no tooling needed.
- Added `scripts/find_audio.py` — search+download royalty-free music (Jamendo) / SFX (Freesound) via official APIs into `audio/`. Needs `JAMENDO_CLIENT_ID`/`FREESOUND_API_KEY` in gitignored `.env`.
- Added `find-audio` skill (`.claude/skills/find-audio/`) — picks the right source/query from a mood/genre/duration requirement, searches, picks best match, downloads. Guides first-time API key setup.
