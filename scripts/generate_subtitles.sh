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
#   PROMPT         initial prompt biasing domain vocabulary
#
# Requires: whisper-cli (whisper-cpp), ggml-cpu + ggml-cuda backends, ffmpeg.

set -uo pipefail

MODEL="${WHISPER_MODEL:-$HOME/.local/share/whisper.cpp/models/ggml-large-v3-turbo.bin}"
LANG_CODE="${LANG_CODE:-en}"
MAX_LEN="${MAX_LEN:-42}"
PROMPT="${PROMPT:-Screencast about building a BitTorrent client from scratch. Vocabulary: BitTorrent, torrent, tracker, DHT, magnet link, peer, seeder, leecher, handshake, bencode, info hash, piece, block, bitfield, TCP, UDP, socket, async, buffer, payload.}"

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
