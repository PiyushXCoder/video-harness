---
name: find-audio
description: Find, import and level a single music track or sound effect into audio/, free-licence only. Use when the user asks for a track, background music, a sound effect, or SFX for a specific moment.
---

# Find & import audio

`scripts/find_audio.py`. Output goes to `audio/` (gitignored). For planning a whole video's music and SFX, use `audio-pass` instead — this skill sources **one** asset.

## The hard rule

**Nothing that costs money.** No subscriptions, no per-track purchases — not Epidemic Sound, Artlist, Musicbed, PremiumBeat, Soundstripe, or Uppbeat's paid tier. If the answer to "can I use this in a monetised video" is "buy a licence", it's out.

The script enforces this with an **allowlist**: only **CC0 / public domain** and plain **CC-BY** pass. Rejected — NonCommercial (a monetised video *is* commercial use), NoDerivatives (trimming/fading/ducking is a derivative), ShareAlike (can oblige licensing the finished video alike), Sampling+, and anything unrecognised or empty. Do not weaken this, and do not reach for `--allow-nc/--allow-nd/--allow-sa` to make a thin search return more hits; those are for non-monetised work only and cannot whitelist an unknown licence.

## 1. import — no API key, preferred

```bash
python3 scripts/find_audio.py import ~/Downloads/track.mp3 --role music \
    --name bed --title "Track Name" --artist "Artist" \
    --license "YouTube Audio Library" --source-name "YouTube Audio Library"
```

Point the user at the **YouTube Audio Library** first (studio.youtube.com → Audio Library): free, no key, cleared for YouTube specifically so it will not draw a Content ID claim, and most of it needs no attribution. **Pixabay Audio** and **Incompetech** (CC-BY) are the other good free sources.

## 2. search / download — Freesound / Jamendo

```bash
export FREESOUND_API_KEY=...        # or put it in .env at the repo root
python3 scripts/find_audio.py search --type sfx --query "success chime"
python3 scripts/find_audio.py download --type sfx --id <id> --name confirm
```

- **Freesound** (`--type sfx`) — free key at https://freesound.org/apiv2/apply/. Good for effects.
- **Jamendo** (`--type music`) — needs care. Its catalogue is mostly NonCommercial and it sells commercial licences separately (Jamendo Licensing / Pro). The filter only passes genuinely CC-BY tracks, which the CC grant makes free commercially, but the docs are ambiguous about monetised use of the CC catalogue. Prefer the Audio Library or Pixabay where there's no ambiguity.

Keys are read from the environment **or** `.env`, environment winning. `.env` is gitignored, so it does not travel between git worktrees — exporting is more reliable in this repo.

Pass `--duration MIN-MAX` when length matters (a bed must outlast the video). `search` prints JSON including `license` and a plain-English `license_note`; read it and pick deliberately rather than taking the first hit. Offer the user 2–3 candidates when the choice is taste.

## Levels

Both paths normalise on the way in, so the Remotion mix starts somewhere sane:

- `--role music` → **-20 LUFS** integrated. The narration is mastered to -16 LUFS by `process_recording.py` (measured -16.2), so a bed at -20 sits ~4 LU under it.
- `--role sfx` → **-6 dBFS** peak, leading/trailing silence trimmed, so effects land at a consistent level.

Say explicitly that this is a starting point, not a mix: the bed still wants ducking 6–9 dB under speech, driven from the `.srt` cue ranges in the composition.

## Attribution

Every import and download appends to `audio/CREDITS.md` — file, role, source, title, artist, licence, page. CC-BY **requires** crediting in the video description; CC0 doesn't. Tell the user that file exists and is what the description gets built from.

Freesound/Jamendo audio can still attract a YouTube Content ID claim even when correctly licensed; `CREDITS.md` is the evidence for disputing one. The Audio Library sidesteps it.

## Notes

- SFX come from Freesound's `preview-hq-mp3` (no OAuth needed). The lossless original needs Freesound OAuth2, not implemented.
- Jamendo tracks without `audiodownload_allowed` are skipped — a streaming URL is not a licence to reuse the audio.
- A source quieter than the silence-trim threshold would otherwise be consumed entirely; the script detects that and falls back to untrimmed with a warning.
- `audio/*` is gitignored — downloads stay local.
