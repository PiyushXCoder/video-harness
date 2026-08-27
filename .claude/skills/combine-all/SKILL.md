---
name: combine-all
description: Join the hook and the main body into the delivered video and build its master subtitle file. Use when the user asks to combine everything, concat hook and main, produce the final video, stitch the parts together, or asks for the finished deliverable and its subtitles.
---

# Combine hook + body into the deliverable

The last stage. `hook-build` produced the opening, `main-build` produced the
body; this joins them into `final.mp4` and builds the matching `final.srt`.

Two outputs, and both are the deliverable — a video whose subtitles are offset by
the length of the hook is worse than no subtitles at all, so they are built
together here rather than left to whoever remembers.

## Inputs

| what | where | from |
|---|---|---|
| hook video | `.remotion/out/hook.mp4` | `hook-build` |
| body video | `.remotion/out/body.mp4` | `main-build` |
| hook manifest | `.remotion/src/hook-data.json` | `build_hook_manifest.py` |
| body manifest | `.remotion/src/timeline-data.json` | `build_timeline_manifest.py` |

The end card lives at the end of the **body** (`EndCard2` in `FinalVideo`), so the
join is simply hook then body and nothing is appended after.

## DESIGN.md, and why it matters here specifically

`DESIGN.md` is what makes the hook and the body look like **one video**. This
skill is where a violation of it finally becomes visible, because it is the first
time the two parts sit next to each other.

The failure mode is not a wrong colour — it is a **stale part**. Change
`DESIGN.md`, rebuild the body, forget the hook, and the join contains two design
systems: different type sizes, a different background, an accent that shifts at
0:30. Nothing errors. It just looks amateur.

So step 2 checks freshness by timestamp before anything is encoded. Rebuilding a
part is minutes; shipping a seam where the design changes is the kind of thing a
viewer cannot name but does notice.

## Workflow

1. **Check both parts exist and match.** A mismatch in size or fps produces a
   join that plays but is subtly wrong, so verify rather than assume:

   ```bash
   for f in .remotion/out/hook.mp4 .remotion/out/body.mp4; do
     printf '%-32s ' "$f"
     ffprobe -v error -select_streams v:0 \
       -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt \
       -of csv=p=0 "$f"
   done
   ```

   Both must be `h264, 2048, 1280, 30/1, yuv420p`. If either differs, fix it at
   its source — do not paper over it with a scale filter in the join, which would
   soften every monospace glyph in the video.

2. **Check both parts were built against the CURRENT design.** A part rendered
   before the last `DESIGN.md` (or design-module) edit carries the old design:

   ```bash
   for part in .remotion/out/hook.mp4 .remotion/out/body.mp4; do
     for src in DESIGN.md .remotion/src/design.ts .manim/scenes/design.py; do
       [ "$src" -nt "$part" ] && \
         echo "STALE: $part predates $src — rebuild it before joining"
     done
   done
   ```

   Any hit means re-running `hook-build` or `main-build` for that part. Do not
   join a stale one and plan to fix it later: the fix is a full re-render and a
   fresh `final.srt`, so it is cheaper now.

   Also run `python3 scripts/check_design.py` — if it fails, at least one part
   was built from a forked design value and the seam may be inconsistent for a
   reason no timestamp reveals.

3. **Check the loudness of the two parts against each other.** A jump at the
   30-second mark is one of the most audible defects in a video, and the hook is
   mastered on a different path from the body (`--no-cut` uses two-pass linear
   loudnorm, the body uses single-pass).

   ```bash
   for f in .remotion/out/hook.mp4 .remotion/out/body.mp4; do
     printf '%-32s ' "$f"
     ffmpeg -hide_banner -nostats -i "$f" -af ebur128 -f null - 2>&1 \
       | grep -A1 'Integrated loudness' | tail -1
   done
   ```

   Within ~1 LU is fine. More than that, say so and offer to re-master the
   quieter part rather than shipping the step.

4. **Join with the concat FILTER, not the concat demuxer.**

   ```bash
   ffmpeg -y -hwaccel cuda \
     -i .remotion/out/hook.mp4 -i .remotion/out/body.mp4 \
     -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]" \
     -map "[v]" -map "[a]" \
     -c:v h264_nvenc -preset p5 -cq 19 -b:v 0 -pix_fmt yuv420p \
     -c:a aac -b:a 192k \
     final.mp4
   ```

   **Why not `-c copy` with the concat demuxer**, which would be lossless and
   instant: AAC frames are 1024 samples (~21.3 ms at 48 kHz), so a part whose
   video is a whole number of frames long is *not* a whole number of audio frames
   long. Stream-copying two such parts emits `Non-monotonic DTS` and leaves the
   audio longer than the video — measured on two 3.000 s parts, the join came out
   video 6.000 s / audio 6.021 s, i.e. a 21 ms desync at the seam that grows with
   every part joined. Re-encoding the audio while copying video does **not** fix
   it; the discontinuity is already in the demuxed stream. The concat filter
   resamples across the boundary and produces 6.000/6.000.

   The cost is a full video re-encode. On NVENC at `cq 19` that is fast and
   visually near-lossless, and this project re-encodes with those settings
   everywhere else.

5. **Build the master subtitles.** The offset comes from the hook manifest, never
   from a typed number:

   ```bash
   python3 scripts/build_master_subtitles.py
   ```

   It reads `hook-data.json` first — emitting each hook beat's cues shifted for
   that beat's own trim and clipped to its window — then offsets every body cue
   by the hook's real total duration. A beat with no source (a title card)
   contributes no cues but still advances the cursor, because it occupies real
   time in the delivered video. Pass `--no-hook` only when delivering the body
   alone.

   Output is `.remotion/out/final.srt`. **Do not burn it in** — upload it to
   YouTube, where it is searchable and translatable.

6. **Verify the join, and look at the seam.**

   ```bash
   # Duration must equal hook + body.
   for f in .remotion/out/hook.mp4 .remotion/out/body.mp4 final.mp4; do
     printf '%-32s %s\n' "$f" \
       "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")"
   done
   # Video and audio stream durations must agree with each other.
   ffprobe -v error -show_entries stream=codec_type,duration -of csv=p=0 final.mp4
   # Peaks under 0 dBFS.
   ffmpeg -hide_banner -nostats -i final.mp4 -af ebur128=peak=true -f null - 2>&1 \
     | grep -A2 'Integrated\|Peak'
   ```

   Then extract frames either side of the seam and **look at them**. Two things
   to judge: whether a hard cut between two unrelated shots reads badly, and
   whether the two frames look like the **same design** — same background, same
   type weight, an accent that has not shifted. A design discontinuity at 0:30
   is the tell that one part is stale:

   ```bash
   HOOK_SEC=$(ffprobe -v error -show_entries format=duration -of csv=p=0 .remotion/out/hook.mp4)
   ffmpeg -y -v error -ss "$(echo "$HOOK_SEC - 0.1" | bc)" -i final.mp4 -frames:v 1 /tmp/seam-before.png
   ffmpeg -y -v error -ss "$(echo "$HOOK_SEC + 0.1" | bc)" -i final.mp4 -frames:v 1 /tmp/seam-after.png
   ```

7. **Spot-check the subtitles against the picture.** Pick a cue from late in the
   file and confirm the words are actually spoken at that timestamp in
   `final.mp4`. This is the check that catches a wrong hook offset, and it is
   cheap:

   ```bash
   tail -8 .remotion/out/final.srt
   ```

8. **Report** the total runtime, the hook/body split, where `final.mp4` and
   `final.srt` are, the measured loudness and peak, and the contents of
   `memes/CREDITS.md` + `audio/CREDITS.md` for the description box.

## Gotchas

- **`final.mp4` at the repo root is gitignored** (`/final.*`), as is
  `.remotion/out/`. Both are episode output, not template.
- **Regenerate `final.srt` after any re-render of either part.** Its offsets
  encode the hook's exact duration; a re-cut hook silently invalidates every body
  cue. It is cheap to rebuild and expensive to notice.
- **A stale sidecar `.srt` shows up here, not earlier.** If the master's last cue
  ends well past the timeline the script warns — that means a clip was re-encoded
  without regenerating its `.srt`.
- **Don't scale or pad in the join.** If the parts don't match, the fix is
  upstream; every source in this project is already 2048×1280, and `DESIGN.md`
  forbids rescaling because it softens every monospace glyph.

## Notes

- The hook and body are separate Remotion compositions joined here, rather than
  one composition, so the hook can break the body's layering rules without those
  freedoms leaking into the 20 minutes that follow. The trade is this
  re-encode — worth knowing if a future change makes prepending the hook inside
  `FinalVideo` attractive instead.
- Delivery is 2048×1280 (8:5), deliberately not 16:9. YouTube pillarboxes it by
  about 5% of width each side; that is the accepted trade for pixel-perfect
  screencasts and code.
- For vertical cutdowns of the finished video, use `extract-reels`, which reads
  `.remotion/out/final.srt`.
