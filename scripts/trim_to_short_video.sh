#!/bin/bash
#
# trim_concat.sh
#
# Keeps only the first 3 minutes of VIDEO1, then concatenates VIDEO2 onto
# the end of that clip, producing OUTPUT.
#
# Usage:
#   ./trim_concat.sh <video1> <video2> <output>
#
# Example:
#   ./trim_concat.sh intro.mp4 main.mp4 final.mp4
#
# Notes:
#   - Uses ffmpeg's concat *filter* (not the concat demuxer), so it works
#     even if the two videos have different codecs/resolutions/frame rates.
#     Both inputs are scaled/padded to a common resolution and fps before
#     concatenation (the concat filter requires matching parameters).
#   - Uses NVIDIA GPU acceleration: CUDA for decoding the inputs and
#     h264_nvenc for encoding the output. Requires an NVIDIA GPU with
#     NVENC support and ffmpeg built with --enable-cuda / --enable-nvenc
#     (check with: ffmpeg -hide_banner -encoders | grep nvenc).
#   - "Trim to the first 3 minutes" means: keep only the first 3 minutes of
#     video1 (from 0:00 to 3:00), then append video2 after that.
#   - Adjust CLIP_DURATION below if you want a different length kept.
#   - By default the output resolution/fps is taken from VIDEO1. Override
#     with OUT_WIDTH / OUT_HEIGHT / OUT_FPS env vars if you want something
#     else (e.g. the larger of the two, or a standard size like 1920x1080).

set -euo pipefail

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <video1> <video2> <output>"
    exit 1
fi

VIDEO1="$1"
VIDEO2="$2"
OUTPUT="$3"

# Amount of video1 to keep, starting from 0:00 (HH:MM:SS)
CLIP_DURATION="00:03:00"

if [ ! -f "$VIDEO1" ]; then
    echo "Error: '$VIDEO1' not found." >&2
    exit 1
fi

if [ ! -f "$VIDEO2" ]; then
    echo "Error: '$VIDEO2' not found." >&2
    exit 1
fi

# Determine target resolution/fps (default: match video1), unless overridden.
if [ -z "${OUT_WIDTH:-}" ] || [ -z "${OUT_HEIGHT:-}" ]; then
    IFS=',' read -r OUT_WIDTH OUT_HEIGHT < <(ffprobe -v error -select_streams v:0 \
        -show_entries stream=width,height -of csv=p=0 "$VIDEO1")
fi
if [ -z "${OUT_FPS:-}" ]; then
    OUT_FPS=$(ffprobe -v error -select_streams v:0 \
        -show_entries stream=r_frame_rate -of csv=p=0 "$VIDEO1")
fi

echo "Target resolution: ${OUT_WIDTH}x${OUT_HEIGHT} @ ${OUT_FPS}fps"
echo "Keeping first $CLIP_DURATION of '$VIDEO1' and concatenating with '$VIDEO2' -> '$OUTPUT'"
echo "Using NVIDIA GPU: CUDA decode + h264_nvenc encode"

ffmpeg -y \
    -hwaccel cuda -t "$CLIP_DURATION" -i "$VIDEO1" \
    -hwaccel cuda -i "$VIDEO2" \
    -filter_complex "
        [0:v]scale=${OUT_WIDTH}:${OUT_HEIGHT}:force_original_aspect_ratio=decrease,
             pad=${OUT_WIDTH}:${OUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2,
             fps=${OUT_FPS},setpts=PTS-STARTPTS[v0];
        [0:a]asetpts=PTS-STARTPTS[a0];
        [1:v]scale=${OUT_WIDTH}:${OUT_HEIGHT}:force_original_aspect_ratio=decrease,
             pad=${OUT_WIDTH}:${OUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2,
             fps=${OUT_FPS},setpts=PTS-STARTPTS[v1];
        [1:a]asetpts=PTS-STARTPTS[a1];
        [v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]
    " \
    -map "[outv]" -map "[outa]" \
    -c:v h264_nvenc -preset p5 -cq 19 -b:v 0 \
    -c:a aac -b:a 192k \
    "$OUTPUT"

echo "Done. Output written to '$OUTPUT'"
