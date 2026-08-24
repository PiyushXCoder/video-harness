---
name: audio-pass
description: Plan and source the music bed and sound effects for a whole video — sweeping the transcripts and generated clips for moments that want a cue, then sourcing and normalising each. Use when the user asks to add music or sound effects, do an audio pass, or asks what the video needs soundwise.
---

# Audio pass over a whole video

The layer above `find-audio`. That skill sources **one** track when you know what you want; this one decides what's needed. Output is `audio/PLACEMENT.md` plus the normalised assets.

## Workflow

1. **Measure the narration first.** Everything else is specified relative to it:
   ```bash
   ffmpeg -hide_banner -nostats -i "processed/<clip>.mkv" -af ebur128 -f null - 2>&1 | grep -A2 'Integrated loudness'
   ```
   `process_recording.py` targets -16 LUFS, so expect about that. A music bed goes ~4 LU under it.

2. **Decide music from the video's length and shape, not by taste.** For a technical explainer, **one bed** for the whole runtime usually beats three cues — it must sit under code explanations without competing, so: no vocals, no strong melody, nothing rhythmically insistent. Check the bed is at least as long as the finished video or has a clean loop point:
   ```bash
   for f in processed/*.mkv; do ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$f"; done | paste -sd+ | bc
   ```
   Add a second cue only where the video has a genuine emotional peak (here: the demo actually working). Resist one-cue-per-section.

3. **Find the SFX moments from the CLIPS, not just the transcripts.** Most cues land on generated animation, not on speech. Sweep:
   - `manim/*.mp4` — every reveal, state change, success and failure in an animation is a candidate
   - `memes/PLACEMENT.md` — each cutaway wants an entry pop
   - `processed/*.srt` — hooks, punchlines and transitions in the narration

4. **Watch the repeat count.** A cue used once can be noticeable; a cue used six times must be nearly subliminal, and must be non-tonal — six repeats of a pitched sound become an unintended melody. Note the repeat count per cue in the plan, and say which one or two cues are allowed to be prominent. Repeated, too-loud effects are the single thing that makes a video feel cheap.

5. **Source it.** Prefer the **YouTube Audio Library** (studio.youtube.com → Audio Library): no API key, cleared for YouTube so no Content ID claim, mostly no attribution. Then `find_audio.py import` to normalise. Otherwise Jamendo (music) / Freesound (sfx) via `find-audio`.

6. **Normalise on the way in** — `import --role music|sfx` does it:
   - music → **-20 LUFS** integrated
   - sfx → **-6 dBFS** peak, leading/trailing silence trimmed

   This is so the Remotion mix starts from a sane place, not so it's finished. Tell the user the bed still needs ducking 6–9 dB under speech, driven from the `.srt` cue ranges.

7. **Write `audio/PLACEMENT.md`**: a music table and an SFX table, each row naming the moment, the requirement, and search terms. Keep it actionable when nothing is sourced yet — it doubles as the shopping list.

8. **Report** what's sourced, what's outstanding, and any licence constraint.

## Licensing — free only

**Nothing that costs money.** No subscriptions, no per-track purchases: not Epidemic
Sound, Artlist, Musicbed, PremiumBeat, Soundstripe, or Uppbeat's paid tier. If a
source's answer to "can I use this in a monetised video" is "buy a licence", it is out.

`find_audio.py` enforces this with an ALLOWLIST — only CC0 / public domain and plain
CC-BY pass; anything unrecognised is rejected rather than assumed fine. Do not weaken
that to a blocklist, and do not reach for `--allow-*` to make a search return more
results: those flags are for non-monetised work.

Jamendo needs care — its catalogue is mostly NonCommercial and it sells commercial
licences separately (Jamendo Licensing / Pro). The filter only passes genuinely CC-BY
tracks, which the CC grant makes free commercially, but prefer the YouTube Audio
Library or Pixabay where there is no ambiguity at all.

## Attribution

`find_audio.py` filters out **NonCommercial** and **NoDerivatives** results by default and this should not be overridden casually: a monetised video is a commercial use, and trimming/fading/ducking a track is exactly the adaptation ND forbids. `--allow-nc`/`--allow-nd` exist for non-monetised work only.

CC-BY requires attribution in the description; CC0 doesn't. Both land in `audio/CREDITS.md`.

Freesound/Jamendo audio can still attract a YouTube Content ID claim even when correctly licensed — `CREDITS.md` is the evidence for disputing one. The Audio Library sidesteps this, which is why it's the first recommendation.

## Judgement

Silence is a legitimate choice. A technical explainer does not need a cue on every transition, and an over-scored video is worse than an unscored one. If a stretch doesn't want music, say so rather than filling it.
