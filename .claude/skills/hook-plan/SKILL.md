---
name: hook-plan
description: Plan the video's opening 30 seconds — transcribe the hook take, sharpen the user's own idea for it into beats, and write plans/hook.md. Use when the user asks to plan the hook, the intro, the cold open, the first 30 seconds, or asks how the video should start.
---

# Plan the hook — the first 30 seconds

The layer above nothing: this is where a video is won or lost, and it is the one
stage where **the user's idea leads and yours follows**. `hook-build` implements
whatever this writes; it invents nothing. Output is `plans/hook.md`.

Do not use this skill to design a hook from scratch on the user's behalf. If they
have not said what they want the opening to do, ask — a hook assembled from your
taste rather than theirs is the failure mode here.

## Workflow

1. **Transcribe the hook take, from `raw/initial/`.**

   ```bash
   ./scripts/generate_subtitles.sh raw/initial/*.mkv
   ```

   The script takes explicit paths and writes `<basename>.srt` beside the input,
   so this needs no flags.

   This is the one place the project transcribes `raw/` rather than `processed/`,
   and it is deliberate. That rule exists because `process_recording.py` cuts
   silent gaps, so `raw/` timestamps stop matching the edit. **Hook footage is
   never silence-cut** (`--no-cut`), so its raw timestamps stay valid as planning
   coordinates. If there is no take yet — a motion-graphics hook — skip this step
   entirely rather than inventing narration.

2. **Ask for the user's own thoughts before reading anything else.** What do they
   want the opening to do? Which line, moment or image do they already have in
   mind? A hook plan that does not contain the user's own idea is the wrong
   output, however well-crafted.

3. **Inventory what actually exists**, because the hook composes from many dirs
   and not from one recording's length:

   ```bash
   for d in raw/initial video_clips screencasts memes audio manim; do
     for f in "$d"/*; do [ -f "$f" ] || continue
       printf '%-44s %6.2fs\n' "$f" \
         "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null || echo 0)"
     done
   done
   ```

   Check `manim/` only for existing **mathematical** animations. Per `CLAUDE.md`,
   anything else the hook wants — a chart, a title card, kinetic type — is
   Remotion work authored inside the composition, not a Manim clip and not a
   pre-rendered file.

4. **Interrogate the idea. This is the actual work of the skill.** Push on:

   - **What is the promise?** In one sentence, what does the viewer now expect?
   - **What is the open loop?** A hook creates a question it does not answer. If
     it resolves inside the 30 seconds, there is no reason to keep watching.
   - **Does the payoff exist?** Check the promise against `processed/*.srt`. A
     hook promising something the video never delivers is the one failure that
     costs subscribers rather than views.
   - **Why still watching at 0:08?** The drop-off is not at 0:30, it is early.
     Name what happens in the second beat, not just the first.
   - **What makes this skippable?** A slow build, a logo, a "hey guys", a claim
     the viewer has heard before.
   - **Is the first frame legible?** Most impressions are a thumbnail plus a
     muted autoplay. Something must read with no sound.

   Where the user's instinct and yours differ, say so once, plainly, and defer.

5. **Draft the beats and show them to the user before writing anything.** A table
   is enough. Iterate here — reordering a plan costs a sentence, reordering
   finished clips costs hours. Two hard numbers to respect while drafting:
   no beat under **45 frames (1.5 s)** and the whole hook under **45 s**; both
   are build failures in `scripts/hook_lib.py`, not suggestions.

6. **Decide explicitly which body rules the hook suspends**, and record why. The
   body reserves frame centre for the speaker's face, allows only three text
   layers in fixed zones, and never draws over a cutaway. A hook with no speaker
   has no reason to obey the first. A hook that is a montage may want type over
   footage. These are legitimate choices when they are *choices* — write them
   into `## Rule breaks` so `hook-build` can set `rulesSuspended` and the
   decision is visible in the data rather than implicit in the output.

7. **Write `plans/hook.md`** with every section below. `hook-build` refuses to
   run if one is missing, so do not leave a placeholder heading empty — say
   "none" instead.

   | section | job |
   |---|---|
   | `## Intent` | one sentence: what the viewer should feel or want to know by 0:30 |
   | `## Hook type` | dedicated take / cold-open montage / motion graphics / mix |
   | `## Duration target` | seconds, and the acceptable band |
   | `## Rule breaks` | each suspended body rule, with its reason |
   | `## Assets` | role \| path \| notes — footage only |
   | `## Beats` | # \| duration \| source (+ in/out) \| on screen \| audio \| note |
   | `## Raw handling` | which pauses are load-bearing, which takes to drop, where it splits |
   | `## Open questions` | what planning could not settle |

   `## Raw handling` carries *editorial intent*, not ffmpeg commands: "keep the
   2 s beat before the reveal", "drop the first false start", "split after 'let
   me show you'". `hook-build` derives the mechanics from it.

8. **Report** the beat count, total against target, which beats have no asset
   yet, and — plainly — which calls are taste the user should overrule.

## Judgement

A hook is taste, and on the opening 30 seconds the user's taste beats yours by
default: they know the channel, the audience and what they have already promised
elsewhere. Where a beat has two defensible treatments, name both and let them
choose rather than silently picking.

The failure mode is a hook that is *impressive* rather than *interesting* — a
title sequence, a music sting, a montage that shows off the edit. All of it reads
as filler to someone deciding whether to stay. Beats that ask a question earn
their place; beats that merely look good do not.

Silence and stillness are legitimate. A held pause before a line is a stronger
hook than a cut every eight frames, and `--no-cut` exists precisely so that
choice survives to the timeline.

## Notes

- The plan file is gitignored (`plans/*`), like every other per-video artifact.
  Anything learned here that applies to *every* video belongs in `CLAUDE.md`, in
  `docs/`, or in this skill — not left in `plans/hook.md` to die with the episode.
- The hook is a separate Remotion composition (`Hook`), not part of `FinalVideo`.
  `combine-all` joins it to the body at the end. Keeping it separate is what lets
  it break the body's rules without those freedoms leaking into the body.
- **The body is planned first**, by `main-plan`. Read `plans/main.md` and check
  the promise against it — the hook advertises what the body contains, and a
  promise the video never keeps is the one failure that costs subscribers rather
  than views. If `plans/main.md` does not exist yet, say so: planning the hook
  first means committing to a payoff the body has not been shaped around.
