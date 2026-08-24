---
name: meme-pass
description: Sweep a whole video's transcripts for beats that want a reaction GIF or sticker, source one per beat, and write a placement plan. Use when the user asks to add memes to the video, do a meme pass, find gags for the whole video, or asks where memes should go.
---

# Meme pass over a whole video

The layer above `find-memes`. That skill sources **one** asset when you already know the moment; this one finds the moments. Use `find-memes` for "get me a facepalm gif", this for "add memes to the video".

Output is `memes/PLACEMENT.md` — a beat-to-asset table the editor works from — plus the assets themselves.

## Workflow

1. **Read the transcripts, all of them.** `processed/*.srt`, in filename order (they're timestamped, so that's chronological):
   ```bash
   for f in processed/*.srt; do echo "=== $(basename "$f" .srt)"; \
     sed -e '/^[0-9]\+$/d' -e '/-->/d' -e '/^$/d' "$f" | tr '\n' ' '; echo; done
   ```

2. **Find the beats — don't invent them.** A beat earns a meme when the narration *already* contains the joke or the exasperation, and the visual just lands it. Look for:
   - a punchline or reversal ("you think you know how torrents work")
   - the speaker insulting something ("that guy is a very dumb guy")
   - self-deprecation ("weeks of work — actually, weekends of work")
   - overwhelm or absurd scale ("50 people yelling at you")
   - a rhetorical question ("who will manage the piece?")

   Expect roughly **one every 60–90 seconds of finished video**. A technical explainer that cuts to a reaction GIF every 15 seconds reads as desperate, and it buries the actual explanation. If a stretch has no beat, leave it alone — silence is not a problem to solve.

3. **Never put a meme on an explanation.** The architecture and code stretches are where the viewer is concentrating; a cutaway there costs comprehension. Memes belong on the seams: hooks, transitions, complaints, payoffs.

4. **Search the emotion, not the topic** (see `find-memes`). "this is fine", "mind blown", "visible confusion" — never "torrent" or "rust", which return literal stock footage.

5. **Source one per beat** via `find_memes.py`. Prefer `convert` with something the user found, or GIPHY search. For each candidate check:
   - **Provenance** — skip obvious studio content (film/TV/sport) or flag it explicitly. Titles like "GIF by The Tonight Show" or a recognisable character name are the tell. Brand-channel and generic GIFs are the safer picks.
   - **Size** — at least ~400px on the long side for a full-frame cutaway; under that, plan it as a corner inset. Tiny renditions look soft on a 2048-wide timeline.
   - **Transparent vs opaque** — a sticker (`.mov`, alpha) can sit over the screencast; an opaque GIF needs its own frame or a bordered inset.

6. **Write `memes/PLACEMENT.md`** — a table of `clip | beat (quoted from the transcript) | asset | how to use`. Quote the actual line so the editor can find the moment by searching the `.srt`. Note anything undersized or transparent.

7. **Report** the beat count, the assets, and — plainly — anything you skipped for copyright and why. Say which picks are taste calls the user should overrule.

## Judgement

Meme choice is taste, and the user's taste beats yours. Where a beat has two or three defensible options, name them with their descriptions and let the user choose rather than silently picking. Where a beat is genuinely marginal, say you think it's marginal.

The failure mode to avoid is a meme on every beat because the tooling made it easy. A pass that adds four good ones and leaves eight beats bare is better than twelve mediocre cutaways.

## Attribution

`memes/CREDITS.md` is appended automatically per download. GIPHY's terms require attribution, and much of the catalogue is copyrighted regardless of source. That file is what the video description gets built from — tell the user it exists.
