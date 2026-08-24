---
name: find-memes
description: Get reaction GIFs or transparent stickers into memes/, converted to an edit-ready format. Use when the user asks for a gif, meme, sticker, reaction shot, or a visual gag for a video.
---

# Find & convert GIFs / stickers

`scripts/find_memes.py`. Output goes to `memes/` (gitignored). Two ways in — **prefer `convert`**.

## 1. convert — no API key, works on anything

```bash
python3 scripts/find_memes.py convert ~/Downloads/this-is-fine.gif --name this-is-fine \
    --description "this is fine, dog in burning room"
python3 scripts/find_memes.py convert "https://media.giphy.com/media/<id>/giphy.gif" --name mind-blown
```

This is the primary path, for two reasons. Picking a meme is a matter of comedic taste, so the user will usually find the right one in a browser faster than any search returns it. And it cannot be taken away — Tenor's API stopped accepting new clients in Jan 2026, which is exactly why this tool no longer uses it.

Ask the user to drop a GIF in `~/Downloads` or paste a direct `.gif` URL, then convert it.

## 2. search / download — GIPHY API, needs a free key

Only worth setting up if the user wants search driven from here.

- Key: https://developers.giphy.com/dashboard/ → create an account → "Create an API Key" → **Beta** key is instant and free, **100 calls/hour**.
- Add to `.env` at the repo root (gitignored, never commit): `GIPHY_API_KEY=...`

```bash
python3 scripts/find_memes.py search --type sticker --query "confused"
python3 scripts/find_memes.py download --type sticker --id <id> --name confused-nod
```

`search` prints JSON: `id`, `title`, `rendition`, `rating`, `size_kb`, `dims`, `url`, `page`. Read the titles and pick deliberately — don't take the first hit. Prefer results at least ~300px on the short side; the small renditions look mushy scaled onto a 2048-wide timeline. When the choice is taste (it usually is), offer the user the top 2–3 with descriptions instead of deciding for them.

**Tenor is not an option.** Google stopped accepting new Tenor API clients in Jan 2026 and posted a service-discontinuation notice. The endpoint still answers *existing* keys, so a live endpoint is not evidence it's usable — don't reintroduce it.

## Picking the right search terms

Search the **emotion of the beat**, not its topic: "this is fine", "mind blown", "slow clap", "visible confusion". Searching "torrent" or "rust" returns literal stock footage, not jokes. If the user hasn't said which moment it's for, read `processed/*.srt` to find the beat first.

`--type sticker` for transparent (sits over the screencast with no box); `--type gif` for a full-frame cutaway or corner inset.

## What you get

Both paths produce the original plus an edit-ready render, and append a row to `memes/CREDITS.md`:

- **opaque → `.mp4`** via `h264_nvenc` (GPU, per the project's rule)
- **transparent → `.mov`**, ProRes 4444 `yuva444p` with a real alpha channel

**Transparency is detected from the file**, not from `--type` — a "sticker" can be opaque and a plain GIF can have a transparent border. `has_alpha()` decodes frames and checks the alpha channel. Override with `--alpha` / `--no-alpha` if it ever guesses wrong.

The alpha path is **CPU-only on purpose**: NVENC cannot encode an alpha channel at all, so the GPU-first rule doesn't apply. ProRes 4444 also works in Remotion: `<OffthreadVideo>` extracts frames server-side with FFmpeg, so it decodes ProRes, and `transparent={true}` preserves the alpha (at ~40% more render time). Expect ~700 KB for a 2s 200×150 sticker, so tens of MB at full size — the cost of reliable alpha, and `memes/` is local-only.

Odd-sized GIFs are padded to even dimensions (`trunc(iw/2)*2`), which yuv420p requires.

## Why not import the GIF directly

GIFs are bad timeline sources: per-frame delays are variable so timing drifts against a fixed 30fps composition, and GIF transparency is a single palette index, which gives hard aliased edges over footage. The script normalises to 30fps. **Always use the `.mp4`/`.mov`, never the `.gif`.**

## Licensing — before publishing

`memes/CREDITS.md` records file, kind, source, description, ref and page for everything. GIPHY's terms require attribution ("Powered by GIPHY"), and much of the catalogue — from any source — is copyrighted film/TV/sport. Using a recognisable clip as a reaction shot is ordinary practice for commentary video, but it's the user's call made knowingly: say so plainly when a chosen result is obviously studio content rather than quietly shipping it. The GIPHY rating cap is `pg-13`; raise it only if asked.
