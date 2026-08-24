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
- `docs/` — standards: `manim-layout-guidelines.md`, `remotion-video-guidelines.md`
- `progress.md` — running log of progress

## Machine spec

See `SPEC.md` for CPU/GPU/RAM/disk. Key constraint: 4 GiB VRAM (RTX 3050 Laptop) — keep render concurrency low, check nvenc/CUDA tools bind to NVIDIA not Intel iGPU.

ggml-based tools (whisper.cpp) need the backend packages `ggml-cpu` + `ggml-cuda` installed alongside `ggml` — the base `ggml` package ships no compute backend and aborts in `ggml_backend_dev_backend_reg`. Whisper models live in `~/.local/share/whisper.cpp/models/`.

Always prefer NVIDIA GPU for video processing (encode/decode/render), not Intel iGPU or CPU-only. E.g. ffmpeg use `-hwaccel cuda` / `h264_nvenc`/`hevc_nvenc`; force `prime-run` where needed.

## Conventions

- `.manim/` and `.remotion/` hold actual project source (configs, scenes, components); `manim/` and `remotion/` hold their rendered output only.
- Visual style for generated clips: **Catppuccin Latte** palette + **Fira Code**. `.manim/scenes/catppuccin.py` holds the 26 official Latte hex values (verified against `catppuccin/palette` `palette.json` and catppuccin.com/palette), a `LatteScene` base class, and `component()` / `link()` / `clamp_to_frame()` helpers. Import from it rather than hardcoding colors. Latte is a LIGHT theme — `background_color` in `.manim/manim.cfg` is `#eff1f5` (base), not black.
- **Source of truth for technical content: `/home/piyush/Projects/dhaar-torrent`** (the Rust/Tokio torrent client this series is about). Check component names, topology and constants against its `README.md` "Architecture" section and `src/` tree — the narration alone is not reliable (it never mentions `request_manager`, and calls `PieceWriter` a "disk writer").
- Code shown in clips must be REAL source pasted from that repo, with elisions marked `// ...`. Invented-but-plausible code undermines the video. `code_block()` in `catppuccin.py` renders it with a registered `catppuccin-latte` pygments style.
- Code blocks use `CODE_FONT` (auto-detected), NOT Fira Code: Fira Code's `//` ligature desyncs Manim's per-character glyph mapping and crashes `Code()` with `IndexError` in `_gen_chars`. Installing `ttf-fira-mono` upgrades code blocks to the matching ligature-free Fira face; until then they fall back to another mono. Display text keeps Fira Code, where the ligatures are desirable.
- Manim layout follows `docs/manim-layout-guidelines.md` (30 rules). The load-bearing ones: express position as RELATIONSHIPS not coordinates (S2/S28), use the `GAP_*` spacing scale rather than ad-hoc `buff=` values (S9), attach labels to their objects (S11), keep established objects still so the viewer's spatial map survives (S7/S19), dim context so the new component dominates (S16), and run the validation pass before shipping (S22).
- Generated clips must pass `audit_layout()` (in `.manim/scenes/catppuccin.py`) — it raises `LayoutError` if a mobject overflows the frame or two collide. Quick check: `cd .manim && manim render -s scenes/<file>.py <Scene>`. The audit does not replace looking at a rendered frame; it catches overflow/collision, not "an arrow crosses this paragraph".
- Semantic color roles follow the Catppuccin style guide: `text` for body, `subtext0` for captions, `blue` interactive, `green` success, `yellow` warning, `red` error, `mauve` keywords/coordination, `peach` constants/data, `teal`/`sapphire` external actors, `surface0-2`/`overlay0-2` for hierarchy.
- Keep raw recordings in `raw/` untouched; edits go to `processed/`.
- False starts / flubbed takes go to `raw/discarded/` rather than being deleted — both pipeline scripts glob `raw/*.mkv`, so a subdirectory is excluded automatically. `raw/discarded/README.md` records why each was dropped and what superseded it.
- **Audio must be free — no paid licences, subscriptions or per-track purchases.** `find_audio.py` enforces an allowlist: only CC0/public-domain and plain CC-BY pass; NC, ND, SA, Sampling+ and anything unrecognised are rejected. Prefer the YouTube Audio Library (free, no Content ID risk, mostly no attribution) or Pixabay over Jamendo, whose catalogue is mostly NC and which sells commercial licences separately.
- Audio levels are anchored on the narration: `process_recording.py` masters it to -16 LUFS (measured -16.2), music beds import at -20 LUFS, SFX at -6 dBFS peak. Still duck the bed 6-9 dB under speech in the Remotion composition — import levels are a starting point, not a mix.
- `memes/PLACEMENT.md` maps each meme to the transcript beat it belongs on; `memes/CREDITS.md` holds attribution. Both are written by tooling, both are gitignored with the rest of `memes/`.
- Use the `.mp4`/`.mov` from `memes/`, never the `.gif` — GIF per-frame delays drift against a fixed-fps timeline and palette transparency gives hard edges. In Remotion load them with `<OffthreadVideo>` (server-side FFmpeg, so ProRes works); transparent stickers need `transparent={true}`, which costs ~40% render time. `memes/CREDITS.md` tracks attribution.
- Subtitles live as sidecar `.srt` next to their clip in `processed/` (same basename). Do NOT burn them in — upload the `.srt` to YouTube, which is searchable and translatable. The cue times are also the authority for cutting on speech boundaries and for ducking the music bed.
- Transcribe from `processed/`, never `raw/`: `process_recording.py` cuts silent gaps, so `raw/` timestamps do not match the edited timeline.
- **Final assembly is done in Remotion, not manually.** `.remotion/` holds the composition that stitches `processed/`, `manim/`, `memes/` and `audio/` into the finished video; `docs/remotion-video-guidelines.md` is the standard and the `final-video` skill drives the whole flow. Kdenlive is no longer used.
- **Delivery is 2048x1280 (8:5), the recorder's native ratio** — deliberately not 16:9. Nothing is scaled, cropped or framed, so screencasts and code clips stay pixel-perfect (rescaling softens small monospace glyphs). YouTube pillarboxes 8:5 on a 16:9 player, ~5% of width each side; that is the accepted trade. Never scale a full-frame source in the composition, and keep `.manim/manim.cfg` at 2048x1280.
- Export on the GPU: Remotion's bundled FFmpeg has NVENC on Linux x64 for h264/h265 only. `Config.setHardwareAcceleration('if-possible')` is set in `.remotion/remotion.config.ts`; pass `--hardware-acceleration=required` on a real export so a silent fall back to CPU fails loudly.

## Scripts

- `scripts/trim_to_short_video.sh <video1> <video2> <output>` — keep first N min of video1, concat video2 after it. NVENC/CUDA-accelerated (GPU decode+encode). Handles mismatched resolution/fps via scale+pad filter.
- `scripts/process_recording.py <input> [output]` — raw/ → processed/ pipeline. Cuts silent gaps >=1s (video+audio stay in sync), then cleans audio (highpass, compressor, loudnorm EBU R128) for loud/clear podcast-style sound. Video encoded with h264_nvenc (GPU).
- `scripts/find_audio.py {import|search|download}` — audio into `audio/`. `import <file> --role music|sfx` needs no API key and normalises on the way in (music → -20 LUFS, sfx → -6 dBFS peak with silence trimmed); `search`/`download` use Jamendo (music) / Freesound (sfx). Keys via env var or gitignored `.env`. **NonCommercial and NoDerivatives licences are filtered out** — a monetised video is commercial use and ducking/trimming is a derivative. Attribution goes to `audio/CREDITS.md`.
- `scripts/find_memes.py {convert|search|download}` — reaction GIFs / transparent stickers into `memes/`. `convert <file-or-url>` needs no API key and is the primary path; `search`/`download` use GIPHY (free Beta key `GIPHY_API_KEY` in the gitignored `.env`, 100 calls/hour). Saves the original plus an edit-ready render — transparency is **detected from the file**, opaque → mp4 via NVENC, transparent → ProRes 4444 `.mov` with alpha (CPU-only; NVENC cannot encode alpha). Provenance goes to `memes/CREDITS.md`. **Tenor is unusable — Google stopped issuing new API keys in Jan 2026.**
- `scripts/generate_subtitles.sh [file ...]` — transcribes `processed/` clips into sidecar `.srt` (whisper.cpp large-v3-turbo on GPU via ggml-cuda). Defaults to all of `processed/*.mkv|mp4`, skips clips that already have an `.srt` unless `--force`. Overridable via `WHISPER_MODEL` / `LANG_CODE` / `MAX_LEN` / `PROMPT` env vars; the default `PROMPT` biases BitTorrent vocabulary so accented speech resolves domain terms correctly.

## Skills

- `final-video` (`.claude/skills/final-video/`) — the orchestrator for a whole video: process raw → subtitles → READ and plan the theme → Manim/code clips → memes → audio → assemble in Remotion → NVENC export. Owns the order and hand-offs; each stage's detail lives in its own skill. Follows `docs/remotion-video-guidelines.md`.
- `manim-clip` (`.claude/skills/manim-clip/`) — writes a Manim scene to `.manim/scenes/<clip_name>.py`, renders it (2048x1280 @ 30fps, set in `.manim/manim.cfg`), publishes the result to `manim/<clip_name>.mp4`. Manim's render is CPU-bound (Cairo) — the GPU-first rule above applies to the ffmpeg scripts, not to Manim itself.
- `remotion-clip` (`.claude/skills/remotion-clip/`) — writes a Remotion composition to `.remotion/src/compositions/<Name>.tsx`, registers it in `.remotion/src/Root.tsx`, renders it (2048x1280 @ 30fps default), publishes the result to `remotion/<clip_name>.mp4`. Render encode is CPU x264 (Remotion's bundled ffmpeg), not NVENC.
- `code-clip` (`.claude/skills/code-clip/`) — renders a syntax-highlighted snippet from the real implementation source into `manim/code-<name>.mp4`. Adds a class to `.manim/scenes/code_clips.py`. Hard rule: every character on screen is real source from `/home/piyush/Projects/dhaar-torrent` with elisions marked `// ...`; never retyped from memory, never invented.
- `audio-pass` (`.claude/skills/audio-pass/`) — the layer above `find-audio`: sweeps the clips and transcripts for moments wanting a cue, writes `audio/PLACEMENT.md`. Prefers the YouTube Audio Library (no key, no Content ID risk) over the APIs. Watches SFX repeat counts — a cue used 6 times must be near-subliminal.
- `meme-pass` (`.claude/skills/meme-pass/`) — the layer above `find-memes`: sweeps all of `processed/*.srt` for beats that want a reaction shot, sources one per beat, writes `memes/PLACEMENT.md`. Targets ~1 beat per 60-90s and never puts a meme on an explanation stretch.
- `find-memes` (`.claude/skills/find-memes/`) — prefers converting a GIF the user found themselves (no API), falls back to GIPHY search. Picks search terms from the *emotion* of a beat rather than its topic. Covers the GIF-on-a-timeline pitfalls, alpha handling, and the attribution/copyright caveat.
- `find-audio` (`.claude/skills/find-audio/`) — sources ONE track or effect into `audio/`. Prefers `import` from the YouTube Audio Library (no key, no Content ID risk) over the Freesound/Jamendo APIs. Carries the free-only allowlist rule and the -20 LUFS / -6 dBFS level targets.
- `process-recording` (`.claude/skills/process-recording/`) — drives the two-stage `raw/` → `processed/` pipeline: `process_recording.py` (silence cutting + audio cleanup + NVENC encode), then `generate_subtitles.sh` (sidecar `.srt`). Documents the tuning knobs for both stages and why the order can't be reversed.
