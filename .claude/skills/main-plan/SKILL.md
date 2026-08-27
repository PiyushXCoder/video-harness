---
name: main-plan
description: Plan the main body of the video — process the raw takes, transcribe them, then work out the spine, theme and visual language with the user and write plans/main.md. Use when the user asks to plan the video, plan the main body, work out the structure or spine, or hands over a batch of raw recordings to shape.
---

# Plan the main body

The body's counterpart to `hook-plan`, and the same contract: **the user's idea
leads, this skill sharpens it**, and `main-build` implements only what gets
written down. Output is `plans/main.md`.

The user may hand over a full manual plan, a rough sketch, or nothing but
footage. Whichever it is, they will refine it — so get a draft in front of them
early rather than polishing in private.

**This is the stage that decides whether the video is good.** Do not let it get
skipped on the way to generating clips.

## Inputs you'll be handed

| where | what | notes |
|---|---|---|
| `raw/` | raw recordings, `.mkv` | unedited, possibly with flubbed takes |
| `raw/initial/` | the hook take | belongs to `hook-plan`, not here |
| `screencasts/` | screen recordings, meaningfully named | captured manually |
| `video_clips/` | short clips the user dropped in | tracked in git, so small |
| `images/` or as given | stills | diagrams, screenshots, logos |
| `memes/` | assets the user already picked | may be empty |

Names are information. `handshake-failure.mkv` tells you where it belongs; ask
rather than guess when a name is opaque.

## Workflow

1. **Process the footage, then transcribe.** Delegate to `process-recording`;
   do not re-derive it here.

   ```bash
   for f in raw/*.mkv; do python3 scripts/process_recording.py "$f"; done
   ./scripts/generate_subtitles.sh
   ```

   The order is fixed: processing changes the timeline, so subtitles come after.
   `raw/initial/` is excluded automatically — both scripts glob `raw/*.mkv`, and
   the hook is never silence-cut anyway. If you re-encode anything later,
   regenerate its `.srt` with `--force` in the same pass; a stale `.srt` is a
   silent failure.

2. **Discard bad takes.** Read the transcripts for false starts and flubs — they
   trail off mid-sentence, or repeat a line a later clip does better. Move them
   to `raw/discarded/` with a README saying why and what superseded them. Never
   delete; a subdirectory drops out of the pipeline by itself.

3. **Read every transcript, all the way through.**

   ```bash
   for f in processed/*.srt; do echo "=== $(basename "$f" .srt)"; \
     sed -e '/^[0-9]\+$/d' -e '/-->/d' -e '/^$/d' "$f" | tr '\n' ' '; echo; done
   ```

4. **Ask for the user's own plan before proposing one.** If they have a structure
   in mind, that is the starting point and your job is to pressure-test it. If
   they don't, draft one — but present it as a draft.

5. **Work out the plan and show it to the user before anything gets built:**

   - **Spine** — the narrative order of clips. Recording order is not always it.
   - **Theme** — what the video argues, in one sentence. Everything serves it.
   - **Visual language** — Catppuccin Mocha + Fira Code is fixed (`CLAUDE.md`).
     Decide the recurring motifs: does the architecture diagram return as a
     through-line? Is there a consistent colour for the component under
     discussion?
   - **What needs a visual** — where the narration describes something spatial or
     procedural that words alone won't carry.
   - **What needs nothing** — talking-head stretches that should stay clean. An
     explainer does not need a graphic every 20 seconds.
   - **The promise the hook will have to make.** The body is planned first and
     the hook advertises it (`hook-plan` runs after this), so decide here what
     the video's most compelling claim actually is. If `plans/hook.md` already
     exists, read it and reconcile: a hook promising something the body never
     delivers is the one failure that costs subscribers rather than views, and
     the fix may be in either plan.
   - **Runtime estimate**, and where it's slack.

6. **Decide the engine for each visual as you plan it**, so `main-build` never has
   to guess:

   - **Manim — only when the subject IS mathematics**: animating a function,
     an equation being transformed, a geometric or algebraic argument. That is
     what Manim is uniquely good at.
   - **Remotion — everything else, including plots, charts and diagrams.** An
     architecture diagram, a bar chart of measured throughput, a timeline, a
     title card, kinetic type, a code snippet: all Remotion. A plot of *data* is
     Remotion; a plot of a *function being reasoned about* is Manim.

   Where source code appears, name the real file and symbol now — every
   character on screen must be real source (`CLAUDE.md`), so a beat that wants
   code the repo doesn't contain is a planning problem, not a build problem.

7. **Confirm the spine explicitly before writing the file.** Reordering a plan
   costs a sentence; reordering finished clips costs hours.

8. **Write `plans/main.md`.** `main-build` refuses to run without these sections,
   so write "none" rather than leaving one empty.

   | section | job |
   |---|---|
   | `## Theme` | one sentence: what the video argues |
   | `## Spine` | ordered clips: # \| clip \| what it covers \| runtime |
   | `## Visual language` | recurring motifs, colour roles, what returns |
   | `## Visuals` | beat \| engine (manim/remotion) \| what it shows \| real source ref |
   | `## Leave clean` | stretches that get no graphic, and why |
   | `## The promise` | the video's most compelling claim, and where the body delivers it — what `hook-plan` will advertise |
   | `## Runtime` | estimate, and where it's slack |
   | `## Open questions` | what planning could not settle |

9. **Report** the spine, the runtime estimate, the visual count split by engine,
   and which calls are taste the user should overrule.

## Judgement

Restraint is the whole skill. A technical explainer does not need a graphic every
20 seconds, and "what needs nothing" is a real section, not a formality — the
stretches where the viewer is concentrating on an explanation are the ones a
cutaway damages.

Where a beat has two defensible treatments, name both and let the user pick.
Where you think a beat is marginal, say so.

The failure mode is planning the video you can build most easily from the assets
on hand, rather than the one the transcripts are actually about. If the footage
doesn't support the spine, say that instead of quietly reshaping the argument
around it.

## Notes

- `plans/main.md` is gitignored (`plans/*`), like every per-video artifact.
  Anything learned here that applies to *every* video belongs in `CLAUDE.md`,
  `docs/`, or a skill — a lesson left only in the plan dies with the episode.
- **Ask where the source code lives** if the video explains software and you
  don't already know. For this series it is
  `/home/piyush/Projects/dhaar-torrent`, but confirm rather than assume, and
  check names and constants against the code rather than the narration — this
  project's narration omits `request_manager` entirely and misnames
  `PieceWriter`.
- The hook is planned separately by `hook-plan` and joined at the end by
  `combine-all`. This skill plans the body only.
