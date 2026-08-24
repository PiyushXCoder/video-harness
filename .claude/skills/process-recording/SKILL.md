---
name: process-recording
description: Turn raw screen/camera recordings into edited clips with subtitles — cuts silent gaps, cleans audio, encodes on the GPU, then transcribes to sidecar .srt. Use when the user asks to process a recording, process raw, clean up a recording, or generate subtitles/captions/transcripts for clips.
---

# Process raw recordings + subtitles

Two-stage pipeline, both stages GPU-accelerated:

1. `scripts/process_recording.py` — `raw/` → `processed/`: shortens silent gaps, cleans audio (highpass → compressor → loudnorm EBU R128), encodes with `h264_nvenc`.
2. `scripts/generate_subtitles.sh` — `processed/*.mkv` → sidecar `processed/*.srt` via whisper.cpp large-v3-turbo on CUDA.

**Order matters.** Always process first, then transcribe. Stage 1 changes the timeline, so subtitles generated before it are wrong. Never transcribe from `raw/`.

## Workflow

1. **Find the inputs.** `ls raw/` — the user may name specific files or mean "everything not yet processed". Skip any input that already has a `processed/<same-name>` unless they asked to redo it.

2. **Dry-run before encoding** when tuning is plausible (new recording session, user complained about pacing, or you changed a parameter):
   ```bash
   python3 scripts/process_recording.py "raw/<file>.mkv" --dry-run
   ```
   Prints the cut plan — kept segments and the pause left before each — without encoding. Cheap; use it to sanity-check rather than encoding and re-encoding.

3. **Process.** One file at a time — NVENC on a 4 GiB RTX 3050 has limited concurrent sessions, and parallel encodes buy nothing here since each runs at ~3x realtime:
   ```bash
   for f in raw/*.mkv; do python3 scripts/process_recording.py "$f"; done
   ```
   Output defaults to `processed/<same-basename>`. Report per-file OK/FAIL rather than dumping ffmpeg logs.

4. **Generate subtitles** for everything that lacks an `.srt`:
   ```bash
   ./scripts/generate_subtitles.sh
   ```
   Defaults to all of `processed/*.mkv|mp4`, skips clips that already have a non-empty `.srt`. Add `--force` to redo. Pass explicit paths to limit it: `./scripts/generate_subtitles.sh "processed/<file>.mkv"`.

5. **Verify, don't assume.** Compare durations and check the cut quality:
   ```bash
   ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "processed/<file>.mkv"
   ```
   Read a generated `.srt` and check the transcript actually reads as sentences — a garbled one usually means the wrong `--noise` floor let dead air through, not a whisper problem.

6. **Report**: per-clip raw → processed duration, total silence removed, cue counts. Mention that final assembly happens in Remotion (see the `final-video` skill), and that the `.srt` cue times are what the assembly uses to cut on speech boundaries and duck the music bed.

## Tuning stage 1

Defaults: `--gap 1.0 --max-gap 0.7 --noise -30 --head 0.15 --tail 0.35 --min-seg 0.35`.

| symptom | knob |
|---|---|
| pacing feels rushed, no breathing room | raise `--max-gap` (0.8–1.0) |
| natural beats getting cut | raise `--gap` (1.2–1.5) |
| too much dead air left in | lower `--gap` (0.8) |
| tiny fragments flashing mid-clip | raise `--min-seg` |
| dead air at clip start/end | raise `--head` / `--tail` |
| speech being cut as if silent | lower `--noise` (-35, -40) |
| loud room noise not detected as silence | raise `--noise` (-25) |

Key semantics, easy to get wrong:
- A silence **shorter than `--gap` is left completely untouched** — those are natural speech beats.
- A longer one is shortened to **exactly `--max-gap`** (half removed from each side, so the pause stays centred). `--max-gap` is the resulting pause, not a padding amount.
- Leading/trailing dead air is trimmed via `--head`/`--tail` regardless of length, detected independently at `EDGE_GAP = 0.25`. Don't try to control clip boundaries with `--gap`.

## Tuning stage 2

Defaults: large-v3-turbo, `LANG_CODE=en`, `MAX_LEN=42` chars per caption line, and a `PROMPT` biasing BitTorrent vocabulary.

- **Caption lines too long/short**: `MAX_LEN=32 ./scripts/generate_subtitles.sh --force`. Captions are not burned in — the `.srt` is uploaded to YouTube — so this only affects on-screen callouts you derive from it.
- **Wrong domain jargon** (new video topic — the default prompt is BitTorrent-specific): override it, since this is what makes accented technical speech resolve correctly.
  ```bash
  PROMPT="Screencast about <topic>. Vocabulary: <term>, <term>, ..." ./scripts/generate_subtitles.sh --force
  ```
- **Accuracy still poor**: swap the model rather than fighting parameters — `WHISPER_MODEL=~/.local/share/whisper.cpp/models/ggml-large-v3.bin` (slower, more accurate than turbo on heavy accents). Download models from `https://huggingface.co/ggerganov/whisper.cpp` into `~/.local/share/whisper.cpp/models/`.

## Gotchas

- **Never touch `raw/`** — it's the only copy of the source. All outputs go to `processed/`. Every parameter choice is redoable because of this; say so when the user is unsure about settings.
- **Re-processing invalidates subtitles.** If you re-encode a clip that already has an `.srt`, regenerate it with `--force` in the same pass. Leaving a stale `.srt` behind is a silent failure — it looks fine and drifts out of sync.
- **whisper-cli needs ggml backend packages**: `ggml-cpu` + `ggml-cuda` alongside `ggml`. The base `ggml` package ships no compute backend and `whisper-cli` aborts in `ggml_backend_dev_backend_reg` before reading the model. If that happens the fix is `sudo pacman -S ggml-cpu ggml-cuda` — not a different model or file format.
- **whisper.cpp reads only wav/mp3/ogg/flac**, so `generate_subtitles.sh` extracts 16 kHz mono WAV to a temp dir first. That's why it needs ffmpeg too.
- `processed/*` is gitignored — media and `.srt` files stay local.
