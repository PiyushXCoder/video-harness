#!/usr/bin/env bash
#
# generate_subtitles.sh — transcribe processed clips into sidecar .srt subtitles.
#
# For each input video, extracts 16 kHz mono WAV (whisper.cpp only reads
# wav/mp3/ogg/flac), runs whisper.cpp large-v3-turbo on the NVIDIA GPU
# (ggml-cuda backend), and writes <video-basename>.srt next to the video.
# Kdenlive auto-detects a sidecar .srt when the clip is imported.
#
# Usage:
#   scripts/generate_subtitles.sh [file ...]     # default: processed/*.mkv processed/*.mp4
#   scripts/generate_subtitles.sh --force ...    # re-transcribe even if .srt exists
#
# Env overrides:
#   WHISPER_MODEL  path to ggml model  (default ~/.local/share/whisper.cpp/models/ggml-large-v3-turbo.bin)
#   LANG_CODE      spoken language     (default en)
#   MAX_LEN        max caption chars   (default 42)
#   VOCAB_FILE     per-video term list (default plans/vocabulary.txt)
#   PROMPT         full initial prompt; overrides VOCAB_FILE entirely
#
# THE PROMPT IS PER-VIDEO, NOT PER-TEMPLATE. whisper's initial prompt is what
# makes accented technical speech resolve domain terms correctly -- but the
# terms belong to whatever this episode is about, so a subject baked in here
# actively mis-biases every other video. The template ships a neutral prompt
# that biases only FORMATTING (punctuation, capitalised proper nouns), and the
# episode supplies its own words in a gitignored file:
#
#   plans/vocabulary.txt   one term per line; blank lines and # comments ignored
#
# Requires: whisper-cli (whisper-cpp), ggml-cpu + ggml-cuda backends, ffmpeg.

set -uo pipefail

MODEL="${WHISPER_MODEL:-$HOME/.local/share/whisper.cpp/models/ggml-large-v3-turbo.bin}"
LANG_CODE="${LANG_CODE:-en}"
MAX_LEN="${MAX_LEN:-42}"
VOCAB_FILE="${VOCAB_FILE:-plans/vocabulary.txt}"

# Subject-agnostic: it steers punctuation and capitalisation, which every video
# wants, and names no domain at all.
BASE_PROMPT="Screencast narration, spoken clearly, with full punctuation and proper nouns capitalised."

if [ -z "${PROMPT:-}" ]; then
  PROMPT="$BASE_PROMPT"
  if [ -f "$VOCAB_FILE" ]; then
    # One term per line; strip comments and surrounding blanks, drop empties.
    terms=$(sed -e 's/#.*//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
              "$VOCAB_FILE" | grep -v '^$')
    if [ -n "$terms" ]; then
      count=$(printf '%s\n' "$terms" | grep -c .)
      # `paste -sd, -` then widen: -d takes a CYCLIC LIST of delimiters, so
      # `-d ', '` alternates comma and space and silently mangles the list.
      joined=$(printf '%s\n' "$terms" | paste -sd, - | sed 's/,/, /g')
      PROMPT="$BASE_PROMPT Vocabulary: $joined."
      echo "vocab: $count terms from $VOCAB_FILE"
    fi
  else
    echo "vocab: no $VOCAB_FILE -- transcribing with no domain vocabulary." >&2
    echo "       Domain terms and proper nouns will be guessed phonetically." >&2
  fi
fi

# whisper's initial prompt is capped at 224 tokens and the excess is dropped
# SILENTLY -- a long list would look applied while its tail did nothing. ~4
# chars per token is the usual rule of thumb, so warn well before the cliff.
if [ "${#PROMPT}" -gt 800 ]; then
  echo "warn: prompt is ${#PROMPT} chars; whisper keeps only ~224 tokens and" >&2
  echo "      drops the rest silently. Trim $VOCAB_FILE to the terms that" >&2
  echo "      actually get misheard." >&2
fi

FORCE=0
args=()
for a in "$@"; do
  case "$a" in
    --force) FORCE=1 ;;
    *) args+=("$a") ;;
  esac
done

if [ "${#args[@]}" -eq 0 ]; then
  shopt -s nullglob
  args=(processed/*.mkv processed/*.mp4)
  shopt -u nullglob
fi

if [ "${#args[@]}" -eq 0 ]; then
  echo "No input videos found in processed/." >&2
  exit 1
fi

command -v whisper-cli >/dev/null || { echo "whisper-cli not found (pacman -S whisper-cpp)" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "ffmpeg not found" >&2; exit 1; }
[ -f "$MODEL" ] || { echo "Model not found: $MODEL" >&2; exit 1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

ok=0; skip=0; fail=0
for video in "${args[@]}"; do
  [ -f "$video" ] || { echo "MISS $video"; fail=$((fail+1)); continue; }
  base="${video%.*}"
  srt="$base.srt"

  if [ -s "$srt" ] && [ "$FORCE" -eq 0 ]; then
    echo "SKIP $(basename "$srt") (exists; --force to redo)"
    skip=$((skip+1))
    continue
  fi

  wav="$TMP/audio.wav"
  if ! ffmpeg -y -v error -i "$video" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$wav"; then
    echo "FAIL $(basename "$video") (audio extract)"
    fail=$((fail+1))
    continue
  fi

  if whisper-cli -m "$MODEL" -l "$LANG_CODE" -t "$(nproc)" \
       -ml "$MAX_LEN" -sow -sns \
       --prompt "$PROMPT" --carry-initial-prompt \
       -osrt -of "$base" "$wav" >"$TMP/log" 2>&1 && [ -s "$srt" ]; then
    lines=$(grep -c '^[0-9]\+$' "$srt")
    echo "OK   $(basename "$srt") ($lines cues)"
    ok=$((ok+1))
  else
    echo "FAIL $(basename "$video") (whisper)"
    grep -viE 'search path' "$TMP/log" | tail -5 >&2
    fail=$((fail+1))
  fi
  rm -f "$wav"
done

echo "done: ok=$ok skip=$skip fail=$fail"
[ "$fail" -eq 0 ]
