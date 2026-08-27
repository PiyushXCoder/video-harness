---
name: main-build
description: Build the main body of the video from plans/main.md — generate the clips, run the meme and audio passes, write the timeline manifest, and export the FinalVideo composition on the GPU. Use when the user asks to build the body, build the main video, generate the clips, or assemble everything in Remotion.
---

# Build the main body

The implementation half of `main-plan`. That skill decides what the video *is*;
this one realises it and **invents nothing** — every creative choice comes from
`plans/main.md`, every mechanical one (durations, frame numbers, encode flags) is
derived here. **Remotion is the editor; there is no manual NLE step.**

## Read before assembling anything

**`DESIGN.md`** — the design authority. Section 10 is the video adaptation and
overrides section 3's web-scaled sizes; section 8 does not apply. Everything it
specifies is encoded in **`.remotion/src/design.ts`** and
**`.manim/scenes/design.py`**; those two are the only files allowed to name a
raw value, and `python3 scripts/check_design.py` fails the build otherwise.

**`docs/remotion-video-guidelines.md`** — the composition standard.

The editorial plan you write in step 5 is a design consumer too: **stamp, punch
and emoji colours are ROLE NAMES** (`accent`, `warning`, `info`, `text_muted`),
never hex codes. `resolveColor()` accepts a hex, so a hardcoded one renders
perfectly and then silently fails to change when `DESIGN.md` does — the failure
is invisible until someone re-themes and half the video stays put.

**Do not pass a `size`.** Omit it and the component uses its design token. The
manifest builder deliberately injects no default: stamp size lived in three
places at once (the token, the Python default, the component default) until that
was fixed, and a size in the plan re-creates exactly that fork.

This builds the body only. `hook-build` builds the opening, and `combine-all`
joins them.

## Workflow

1. **Read `plans/main.md` and stop if it is not usable.** Required sections:
   `## Theme`, `## Spine`, `## Visual language`, `## Visuals`, `## Leave clean`,
   `## The promise`, `## Runtime`, `## Open questions`. If the file is absent or
   a section is missing, say so and run `main-plan` — do not substitute your own
   idea of a good video. An unresolved `## Open questions` item is a question for
   the user, not a decision for you.

2. **Generate the visuals the plan asked for, with the engine the plan named.**

   - **`manim-clip`** — only where the subject IS mathematics (a function, an
     equation, a geometric argument). Design by constraint, audit geometry with
     `-s` before rendering video, then look at a frame.
   - **`remotion-clip`** — everything else, *including plots, charts and
     diagrams*: architecture diagrams, measured-data charts, timelines, title
     cards, kinetic type, code clips.

   Code on screen is real source with elisions marked `// ...`, never invented.

   For a diagram revealed across several narration beats, keep node positions
   fixed and animate only each stage's delta, so cuts between clips don't make
   boxes jump. **Don't hold one short clip across a long window** — a 1.7 s clip
   stretched to 25 s looks dead and blocks every overlay for those 25 s; split
   the scene into two clips sharing a base class instead.

   **Render at 2048×1280**, the project's native 8:5, so clips fill the frame and
   nothing is scaled. `.manim/manim.cfg` already does this; leave it alone.

3. **Memes** — `meme-pass` for the sweep, `find-memes` for individual assets.

   The video should feel dense, but: **a gif is used at most ONCE in the whole
   video** (`check_no_repeated_gifs()` fails the build on a repeat), budget
   roughly one per 15–20 s, match the beat's *emotion* not its topic, and
   **render each candidate into a real frame and LOOK at it** — a GIPHY title is
   not evidence. Two titled plainly `robot GIF` and `Happy Robot GIF` were both
   Bender from Futurama; others that sounded generic carried a network watermark,
   burned-in captions, or an identifiable actor. Drop studio IP and identifiable
   private people, and report the call rather than shipping it silently. Writes
   `memes/PLACEMENT.md`.

4. **Audio** — `audio-pass` for the plan, `find-audio` for individual assets.

   One bed plus SFX on moments in the generated clips. **Free licences only** —
   the allowlist passes CC0 and plain CC-BY and nothing else. Prefer the YouTube
   Audio Library: no key, no Content ID risk. Writes `audio/PLACEMENT.md`.

5. **Write the editorial plan as code.** `scripts/build_timeline_manifest.py` is
   gitignored — it is this episode's content. It imports the tracked engine
   `scripts/timeline_lib.py`, which probes every asset's real duration and
   dimensions with `ffprobe`. **Never hand-type a duration or a frame number.**

   ```bash
   cd .remotion && pnpm install     # node_modules is gitignored and does not
                                    # travel between git worktrees
   cd .. && python3 scripts/build_timeline_manifest.py
   ```

   Re-run it after **every** change; it writes `.remotion/src/timeline-data.json`.

6. **Let the build gates adjudicate, not your eye.** The manifest build fails or
   reports on: text appearing before it is spoken (`check_not_early`, which
   interpolates each word's real onset — a whisper cue's start is *not* when its
   third word lands), a gif used twice (`check_no_repeated_gifs`), a cutaway
   starting at/after its segment's end so it could never render, and any stretch
   outside a cutaway with nothing on screen (`report_coverage`). Treat its output
   as the source of truth over your reading of the timing.

7. **Smoke-render before any long render.** `tsc --noEmit` does *not* catch
   everything esbuild rejects — a malformed JSX comment typechecked clean and
   failed the bundle. Never pipe `tsc` through `head` and trust the exit status;
   a pipe reports the *last* command's status.

   ```bash
   cd .remotion
   npx remotion still FinalVideo out/probe.png --frame=90
   npx remotion render FinalVideo out/body.mp4 --frames=0-300   # 10s slice
   ```

   Run Remotion **from `.remotion/`** — `npx --prefix .remotion` silently no-ops
   (it cannot find the entry point and still exits 0).

8. **Export on the GPU.**

   ```bash
   cd .remotion
   npx remotion render FinalVideo out/body.mp4 \
       --hardware-acceleration=required --concurrency=6
   ```

   `required` makes a silent fall back to CPU encoding fail loudly. NVENC covers
   h264/h265 only, and **never pass `--crf` alongside it** — Remotion drops to
   software encoding when a CRF is set with hardware acceleration.

9. **Verify, and look at it.** Run the design lint first — it is instant, and a
   stray hex renders perfectly so the eye will not catch it:

   ```bash
   python3 scripts/check_design.py
   ```

   ```bash
   ffprobe -v error -select_streams v:0 \
     -show_entries stream=codec_name,width,height,r_frame_rate \
     -of csv=p=0 .remotion/out/body.mp4        # want h264,2048,1280,30/1
   ffmpeg -hide_banner -nostats -i .remotion/out/body.mp4 \
     -af ebur128=peak=true -f null - 2>&1 | grep -A2 'Integrated\|Peak'
   ```

   Confirm the duration matches the manifest, extract frames at transitions and
   **look at them**, and check peaks stay under 0 dBFS.

10. **Report** the runtime, what's in it, anything the plan asked for that you
    could not deliver, and the contents of `memes/CREDITS.md` +
    `audio/CREDITS.md` for the description box.

## Where this goes wrong

- **Building before planning.** The expensive mistake. Clips generated against a
  spine that later changes are wasted work — that is why this is a separate skill
  from `main-plan`.
- **Hardcoded durations.** They drift from the assets and produce freezes or
  truncation the studio preview doesn't reveal.
- **Unclamped `interpolate`.** Elements drift off frame in exactly the frames
  nobody previews.
- **Scaling or cropping a source.** Everything is 2048×1280 already; a rescale
  softens monospace text, and a 16:9 crop would clip Manim content that
  `audit_layout()` cannot see, because the clipping happens in the composition.
- **Stale `.srt` after a re-encode.** Looks fine, drifts out of sync, and
  `check_not_early` then validates against the wrong timeline.
- **A layer scheduled inside a cutaway window renders as nothing** —
  `CutawaySafeSequence` is doing its job. Check for that before debugging the
  layer itself; three overlays were once silently invisible this way.
- **A meme or cue on everything** because the tooling made it cheap. Restraint is
  the difference between professional and busy.
- **A hex or a `size` in the editorial plan.** It renders correctly today and
  quietly stops tracking `DESIGN.md` forever. Use role names, omit sizes, and let
  `check_design.py` and the design tokens do their job.
