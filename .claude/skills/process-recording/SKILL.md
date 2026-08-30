---
name: process-recording
description: Turn raw screen/camera recordings into edited clips with subtitles — transcribes the raw take, cuts only the silences the transcript says are dead air, cleans audio, encodes on the GPU, and remaps the subtitles onto the cut. Use when the user asks to process a recording, process raw, clean up a recording, or generate subtitles/captions/transcripts for clips.
---

# Process raw recordings + subtitles

Two-stage pipeline, both stages GPU-accelerated:

1. `scripts/generate_subtitles.sh` — transcribe the **raw** takes via whisper.cpp large-v3-turbo on CUDA.
2. `scripts/process_recording.py --pauses-from` — `raw/` → `processed/`: shortens silent gaps *the transcript says are dead air*, cleans audio (highpass → compressor → loudnorm EBU R128), encodes with `h264_nvenc`, and writes the remapped `.srt` beside the output.

**Transcribe first, then cut.** This is the reverse of the old order, and the reason is that duration alone cannot tell a deliberate pause from a stall — the words either side can. Stage 2 then projects the raw cues through its own cut map, so `processed/*.srt` matches the cut exactly and whisper runs **once**. Do not transcribe `processed/` separately; that is how a sidecar ends up silently describing the uncut source.

## Workflow

1. **Find the inputs.** `ls raw/` — the user may name specific files or mean "everything not yet processed". Skip any input that already has a `processed/<same-name>` unless they asked to redo it.

2. **Transcribe the raw takes.** Skips anything that already has a non-empty `.srt`; `--force` redoes it.
   ```bash
   ./scripts/generate_subtitles.sh raw/*.mkv
   ```

3. **Dry-run before encoding** — with `--pauses-from` this also prints the per-gap verdict and the reason, which is the cheapest way to check the heuristic agrees with your ear:
   ```bash
   python3 scripts/process_recording.py "raw/<file>.mkv" \
     --pauses-from "raw/<file>.srt" --dry-run
   ```
   Read the `KEEP`/`cut` lines with their surrounding transcript text. A pause you know is deliberate showing up as `cut` is a signal to look at the wording, not to reach for `--gap`.

4. **Process.** One file at a time — NVENC on a 4 GiB RTX 3050 has limited concurrent sessions, and parallel encodes buy nothing here since each runs at ~3x realtime:
   ```bash
   for f in raw/*.mkv; do
     python3 scripts/process_recording.py "$f" --pauses-from "${f%.*}.srt"
   done
   ```
   Output defaults to `processed/<same-basename>`, with the remapped `.srt` beside it. Report per-file OK/FAIL rather than dumping ffmpeg logs.

5. **Verify, don't assume.** Compare durations and check the cut quality:
   ```bash
   ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "processed/<file>.mkv"
   ```
   Read a generated `.srt` and check the transcript actually reads as sentences — a garbled one usually means the wrong `--noise` floor let dead air through, not a whisper problem.

6. **Report**: per-clip raw → processed duration, total silence removed, cue counts. Mention that planning comes next (`main-plan`) and that final assembly happens in Remotion (`main-build`, then `combine-all`), and that the `.srt` cue times are what the assembly uses to cut on speech boundaries and duck the music bed.

## Tuning stage 1

Defaults: `--gap 1.0 --max-gap 0.7 --noise -30 --head 0.15 --tail 0.35 --min-seg 0.35`.

| symptom | knob |
|---|---|
| a deliberate pause got flattened | use `--pauses-from` — that is what it is for |
| pacing feels rushed, no breathing room | raise `--max-gap` (0.8–1.0) |
| natural beats getting cut | `--pauses-from` first; only then raise `--gap` (1.2–1.5) |
| too much dead air left in | lower `--gap` (0.8) |
| tiny fragments flashing mid-clip | raise `--min-seg` |
| dead air at clip start/end | raise `--head` / `--tail` |
| speech being cut as if silent | lower `--noise` (-35, -40) |
| loud room noise not detected as silence | raise `--noise` (-25) |

Key semantics, easy to get wrong:
- With `--pauses-from`, a silence overlapping a **kept** gap is left alone however long it is. Without it, duration is the only test and a 2.5 s dramatic beat is indistinguishable from 2.5 s of hesitation.
- `--pauses-from` and `--no-cut` are **mutually exclusive** — `--no-cut` keeps every pause unconditionally, so there is nothing left for the transcript to decide.
- A silence **shorter than `--gap` is left completely untouched** — those are natural speech beats.
- A longer one is shortened to **exactly `--max-gap`** (half removed from each side, so the pause stays centred). `--max-gap` is the resulting pause, not a padding amount.
- Leading/trailing dead air is trimmed via `--head`/`--tail` regardless of length, detected independently at `EDGE_GAP = 0.25`. Don't try to control clip boundaries with `--gap`.

## Tuning stage 2

Defaults: large-v3-turbo, `LANG_CODE=en`, `MAX_LEN=42` chars per caption line, and a subject-agnostic `PROMPT` that steers punctuation and capitalisation only.

- **Caption lines too long/short**: `MAX_LEN=32 ./scripts/generate_subtitles.sh --force`. Captions are not burned in — the `.srt` is uploaded to YouTube — so this only affects on-screen callouts you derive from it.
- **Wrong domain jargon**: write `plans/vocabulary.txt`, one term per line, and re-run with `--force`. This is what makes accented technical speech resolve correctly, and it is **per-video** — the template ships no domain terms, so a fresh episode starts with none and says so on stderr. Keep the list to words that actually get misheard: whisper keeps ~224 tokens of prompt and drops the rest **silently**, so padding it weakens the terms that matter. The script warns when the list gets long.
  ```bash
  printf 'niri\nWayland\ncompositor\n' > plans/vocabulary.txt
  ./scripts/generate_subtitles.sh --force raw/*.mkv
  ```
  `PROMPT="..."` still overrides the whole prompt if you want to hand-write it.
- **Accuracy still poor**: swap the model rather than fighting parameters — `WHISPER_MODEL=~/.local/share/whisper.cpp/models/ggml-large-v3.bin` (slower, more accurate than turbo on heavy accents). Download models from `https://huggingface.co/ggerganov/whisper.cpp` into `~/.local/share/whisper.cpp/models/`.

## Gotchas

- **Never touch `raw/`** — it's the only copy of the source. All outputs go to `processed/`. Every parameter choice is redoable because of this; say so when the user is unsure about settings.
- **Re-processing invalidates subtitles** — unless you used `--pauses-from`, which rewrites the sidecar from the cut map every run. If you cut without it, or split a file with `ffmpeg -ss/-to`, regenerate the `.srt` with `--force` in the same pass. A stale `.srt` looks fine and drifts out of sync.
- **whisper-cli needs ggml backend packages**: `ggml-cpu` + `ggml-cuda` alongside `ggml`. The base `ggml` package ships no compute backend and `whisper-cli` aborts in `ggml_backend_dev_backend_reg` before reading the model. If that happens the fix is `sudo pacman -S ggml-cpu ggml-cuda` — not a different model or file format.
- **whisper.cpp reads only wav/mp3/ogg/flac**, so `generate_subtitles.sh` extracts 16 kHz mono WAV to a temp dir first. That's why it needs ffmpeg too.
- `processed/*` is gitignored — media and `.srt` files stay local.
