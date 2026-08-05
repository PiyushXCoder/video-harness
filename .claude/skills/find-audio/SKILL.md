---
name: find-audio
description: Find and download royalty-free background music or sound effects into audio/, based on a mood/genre/duration requirement. Use when the user asks to find, get, or download music, a track, a sound effect, or SFX for a video.
---

# Find & download royalty-free audio

Uses two official CC-licensed APIs via `scripts/find_audio.py`:
- **Jamendo** — music
- **Freesound** — sound effects

## First-time setup (API keys)

Check for `.env` at the repo root with `JAMENDO_CLIENT_ID` and/or `FREESOUND_API_KEY`. If missing (the script will error out naming exactly which key is missing and where to get it), walk the user through it:

- **Jamendo**: https://devportal.jamendo.com/ → create an app → copy the "Client ID" (instant, free).
- **Freesound**: https://freesound.org/apiv2/apply/ → register an app → copy the API key (instant, free).

Add to `.env` (repo root, gitignored — never commit this file):
```
JAMENDO_CLIENT_ID=...
FREESOUND_API_KEY=...
```

## Workflow

1. **Figure out the requirement** from the user's ask: type (music vs sfx), search terms (mood/genre/instrument for music; sound description for sfx), and a duration range if it matters (e.g. background music for a 90s clip needs ≥90s).

2. **Search:**
   ```bash
   python3 scripts/find_audio.py search --type music --query "upbeat corporate" --duration 60-180
   python3 scripts/find_audio.py search --type sfx --query "keyboard click"
   ```
   Prints a JSON array of candidates: `id`, `name`, `artist`, `duration_s`, `license`, `url`.

3. **Pick the best match** yourself from the JSON (closest to the requested mood/duration/name) — don't just take the first result blindly. Mention the top 2-3 candidates to the user if the choice is ambiguous.

4. **Download** the chosen one — pass the *same* `--query`/`--duration` used in search plus the chosen `--id` (the script re-searches to relocate it, so args must match):
   ```bash
   python3 scripts/find_audio.py download --type music --id 12345 --query "upbeat corporate" --duration 60-180 --name intro-music
   ```
   Saves to `audio/<name>.mp3` (or a slugified version of the track name if `--name` omitted).

5. **Report** what was downloaded, its license, and the destination path. Note the license terms if attribution is required (Jamendo/Freesound results vary by track — check the `license` field).

## Notes

- Freesound downloads use the `preview-hq-mp3` URL — good quality, no OAuth needed. The original lossless file requires Freesound OAuth2, not implemented here.
- `audio/*` is gitignored (per project convention) — downloaded files stay local, not committed.
