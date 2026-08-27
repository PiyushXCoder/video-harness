---
name: hook-build
description: Build the video's opening 30 seconds from plans/hook.md — cut the raw take without touching its pauses, write the hook manifest, render the Hook composition on the GPU. Use when the user asks to build the hook, implement the intro or cold open, or render the first 30 seconds.
---

# Build the hook

The implementation half of `hook-plan`. That skill decides what the opening 30
seconds *is*; this one realises it and **invents nothing**. Every creative choice
comes from `plans/hook.md`; every mechanical choice — split points, encode flags,
frame numbers — is derived here.

Read `plans/hook.md` first. Read `docs/remotion-video-guidelines.md` for anything
the hook does not explicitly suspend.

## Workflow

1. **Read `plans/hook.md` and stop if it is not usable.** Required sections:
   `## Intent`, `## Hook type`, `## Duration target`, `## Rule breaks`,
   `## Assets`, `## Beats`, `## Raw handling`, `## Open questions`. If the file is
   absent or a section is missing, say so and run `hook-plan` instead — do **not**
   fill the gap with your own idea of a good hook. An unresolved item under
   `## Open questions` is a question for the user, not a decision for you.

2. **Realise `## Raw handling`.** The plan says which pauses are load-bearing and
   where the take splits; turn that into operations.

   Split on the plan's boundaries, GPU-decoded and NVENC-encoded:

   ```bash
   ffmpeg -y -hwaccel cuda -i raw/initial/<take>.mkv \
     -ss <in> -to <out> -c:v h264_nvenc -preset p5 -cq 19 -b:v 0 \
     -c:a aac -b:a 192k processed/hook-01-<slug>.mkv
   ```

   Then master each piece **without cutting anything**:

   ```bash
   python3 scripts/process_recording.py processed/hook-01-<slug>.mkv --no-cut
   ```

   `--no-cut` skips silence detection entirely and runs only highpass +
   compressor + loudnorm + NVENC. Never run the default path on hook footage: it
   shortens every gap over 1 s, which is exactly the performance the plan asked
   to keep. `--no-cut` also switches loudnorm to two passes with `linear=true`,
   because single-pass loudnorm is dynamic and ramps the gain up across a long
   pause — measured 1.9 LU hot on an 8 s clip with one 4 s pause.

   Prefer trimming in the manifest over trimming on disk. A beat's
   `startFromSec`/`toSec` is non-destructive and survives a replan; a re-encode
   does not.

3. **Regenerate the `.srt` for every piece you produced.**

   ```bash
   ./scripts/generate_subtitles.sh processed/hook-*.mkv
   ```

   This is load-bearing, not housekeeping. `hook-plan` transcribed the *raw*
   take; the moment you split or trim it those timestamps describe nothing on
   disk. `check_text_not_early()` compares text timing against the srt, so a
   stale one silently validates against the wrong timeline.

4. **Write `scripts/build_hook_manifest.py`** — this episode's editorial plan,
   gitignored. It imports the tracked engine and never hand-types a duration or
   a frame number:

   ```python
   #!/usr/bin/env python3
   """This video's hook. Engine: scripts/hook_lib.py. Plan: plans/hook.md."""
   import sys, pathlib
   sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
   from hook_lib import build_hook

   BEATS = [
       # Footage beat: duration comes from the trim window, probed not typed.
       {"id": "cold-line", "source": "processed/hook-01-cold-line.mkv",
        "startFromSec": 0.4, "toSec": 4.9, "captions": True,
        "texts": [{"words": "we don't know where the data is",
                   "fromSec": 1.2, "holdSec": 2.4, "anchor": "lower-third"}]},
       # Graphics-only beat: no file, so durationSec is required.
       {"id": "title", "durationSec": 2.5, "background": "#11111b",
        "texts": [{"words": "BitTorrent, from scratch", "fromSec": 0.2,
                   "holdSec": 2.0, "anchor": "center", "color": "peach"}],
        "rulesSuspended": ["centre-frame — no speaker in this beat"]},
   ]

   build_hook(BEATS, music={"file": "audio/hook-sting.wav", "gainDb": -6},
              target_sec=30.0)
   ```

   Beat keys are documented in `build_beat()`'s docstring. The ones that matter:
   `source` is **optional** (omit it for a title card, chart or kinetic type, and
   give `durationSec` instead); `cutawaySafe` defaults to `True` and should only
   be set `False` where `## Rule breaks` says so; `rulesSuspended` copies the
   plan's reasons in so the choice is visible in the data.

   Then run it:

   ```bash
   python3 scripts/build_hook_manifest.py   # writes .remotion/src/hook-data.json
   ```

5. **Let the build gates adjudicate, not your eye.** `hook_lib.py` fails on: a
   beat under 45 frames (`check_min_shot`), a hook past 45 s
   (`check_duration_target`), a trim window that is inverted or starts past the
   end of its source (`check_beat_window`), a cutaway that starts after its beat
   ends, `captions=True` on a beat with no source, and text that appears before
   its own words are spoken (`check_text_not_early`). It warns on a `toSec` past
   the source's real end and on a total off the plan's target. Trust the messages
   over your reading of the timing.

6. **Render on the GPU and LOOK at it.**

   ```bash
   cd .remotion
   npx remotion still Hook out/hook-f45.png --frame=45      # cheap first check
   npx remotion render Hook out/hook.mp4 \
       --hardware-acceleration=required --concurrency=6
   ```

   `required` makes a silent fall back to software encoding fail loudly instead
   of quietly costing minutes. Never pass `--crf` alongside it — Remotion drops
   to CPU when a CRF is set with hardware acceleration.

   Then verify, and actually view the frames:

   ```bash
   ffprobe -v error -select_streams v:0 \
     -show_entries stream=codec_name,width,height,r_frame_rate \
     -of csv=p=0 .remotion/out/hook.mp4          # want h264,2048,1280,30/1
   ffmpeg -hide_banner -nostats -i .remotion/out/hook.mp4 \
     -af ebur128=peak=true -f null - 2>&1 | grep -A2 'Integrated\|Peak'
   ```

   Extract a frame at every beat boundary and look for text landing on a face,
   an overlay covering something being read, and a beat that renders black
   because its source window fell outside the file.

7. **Report** the beat list with real durations, the total against the plan's
   target, which rules ended up suspended, and anything the plan asked for that
   you could not deliver — say it plainly rather than substituting something.

## Gotchas

- **A layer scheduled inside a cutaway window renders as nothing** when the beat
  is `cutawaySafe` — that is the gate working. If an overlay is mysteriously
  absent, check whether a cutaway covers its frames before debugging the layer.
- **`Config.setPublicDir('..')`** means `staticFile()` resolves from the repo
  root, so manifest paths are repo-relative (`processed/…`, `memes/…`) with no
  file copying.
- **Use the `.mp4`/`.mov` from `memes/`, never the `.gif`.** GIF frame delays
  drift against a fixed-fps timeline.
- **`Root.tsx` imports both manifests**, so bundling the `Hook` alone still needs
  `.remotion/src/timeline-data.json` to exist. On a checkout with no body built
  yet, `python3 scripts/hook_lib.py --stub` writes a placeholder of both — it
  never overwrites a real one, and it warns that `FinalVideo` is then a
  one-frame stub.
- **`Stamp` fades out over frames 25→35**, so the hook gives it a 35-frame window
  where the body gives 30 and clips its own exit. Don't "fix" that back to 30.

## Notes

- The hook is the `Hook` composition, separate from `FinalVideo`. Prepending it
  to the body is deliberately **not** wired up yet.
- `check_no_repeated_gifs()` polices the body's manifest only. A gif used in both
  the hook and the body will not be caught automatically — check by hand until
  the two manifests are validated together.
- Anything learned here that applies to every video belongs in `CLAUDE.md`,
  `docs/` or this skill. `scripts/build_hook_manifest.py` is gitignored and dies
  with the episode.
