#!/usr/bin/env python3
"""
find_memes.py

Search and download GIFs / transparent stickers into memes/, via the official
Tenor API (Google):
  https://developers.google.com/tenor/guides/quickstart

Two-step flow — search first, inspect candidates, then download the one that
actually fits:

  find_memes.py search --type gif --query "this is fine"
  find_memes.py download --type gif --id <id> [--name this-is-fine]

  find_memes.py search --type sticker --query "confused"
  find_memes.py download --type sticker --id <id> [--name confused]

Downloads land in memes/ as BOTH the original file and an edit-ready render:
  gif     -> memes/<name>.gif  +  memes/<name>.mp4   (h264_nvenc, GPU)
  sticker -> memes/<name>.gif  +  memes/<name>.mov   (ProRes 4444, alpha kept)

Kdenlive handles GIFs badly — variable inter-frame delays drift and palette
transparency gives hard edges — so import the .mp4/.mov, not the .gif.

Every download appends a row to memes/CREDITS.md. Tenor's terms require
attribution, and a lot of the catalogue is copyrighted film/TV, so keep that
file around when writing the video description.

Requires an API key in a .env file at the repo root (never commit this file):
  TENOR_API_KEY=...

  Tenor: https://developers.google.com/tenor/guides/quickstart
         -> enable the Tenor API in a Google Cloud project -> create an API key
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
MEMES_DIR = REPO_ROOT / "memes"
ENV_FILE = REPO_ROOT / ".env"
CREDITS = MEMES_DIR / "CREDITS.md"

GIPHY_GIF_SEARCH = "https://api.giphy.com/v1/gifs/search"
GIPHY_STICKER_SEARCH = "https://api.giphy.com/v1/stickers/search"
GIPHY_GIF_BY_ID = "https://api.giphy.com/v1/gifs/{gif_id}"

# GIPHY content rating cap. "pg-13" keeps ordinary internet humour and drops
# the explicit tier; raise it only if the user asks.
RATING = "pg-13"

GIPHY_SETUP = "https://developers.giphy.com/dashboard/"


def load_env():
    """Keys from .env at the repo root, with the real environment taking priority.

    An exported GIPHY_API_KEY should just work without a .env file -- following
    the usual dotenv convention that an already-set environment variable wins.
    """
    env = {}
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    for key in ("GIPHY_API_KEY", "JAMENDO_CLIENT_ID", "FREESOUND_API_KEY", "TENOR_API_KEY"):
        if os.environ.get(key):
            env[key] = os.environ[key]
    return env


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "meme"


def require_key(env, key, setup_url):
    value = env.get(key)
    if not value:
        sys.exit(
            f"Error: {key} is not set.\n"
            f"Get one (free) at {setup_url}, then either export it:\n"
            f"  export {key}=<your key>\n"
            f"or add it to {ENV_FILE}:\n  {key}=<your key>"
        )
    return value


def _pick_rendition(images, want_transparent):
    """Best rendition for our purposes: a real GIF, big enough to scale up.

    GIPHY returns many renditions. `original` is full size; the fixed_* ones are
    smaller re-encodes. For stickers the GIF itself carries the transparency, so
    the same keys apply -- there is no separate transparent rendition.
    """
    order = ["original", "downsized_medium", "fixed_height", "fixed_width", "downsized"]
    for key in order:
        entry = images.get(key) or {}
        url = entry.get("url")
        if url and ".gif" in url:
            return key, entry
    return None, None


def _normalise(item, want_transparent):
    key, media = _pick_rendition(item.get("images", {}), want_transparent)
    if not media:
        return None
    return {
        "id": item.get("id"),
        "title": (item.get("alt_text") or item.get("title") or "").strip(),
        "rendition": key,
        "rating": item.get("rating"),
        "size_kb": round(int(media.get("size") or 0) / 1024),
        "dims": f"{media.get('width', '?')}x{media.get('height', '?')}",
        "url": media["url"],
        "page": item.get("url"),
    }


def search(env, kind, query, limit):
    key = require_key(env, "GIPHY_API_KEY", GIPHY_SETUP)
    url = GIPHY_STICKER_SEARCH if kind == "sticker" else GIPHY_GIF_SEARCH
    r = requests.get(url, params={
        "api_key": key, "q": query, "limit": limit, "rating": RATING, "lang": "en",
    }, timeout=30)
    if r.status_code == 429:
        sys.exit("GIPHY rate limit hit (beta keys allow 100 calls/hour). Wait, or use "
                 "`convert` with a GIF you found in a browser -- no key needed.")
    if r.status_code != 200:
        sys.exit(f"GIPHY search failed ({r.status_code}): {r.text[:300]}")
    out = []
    for item in r.json().get("data", []):
        norm = _normalise(item, kind == "sticker")
        if norm:
            out.append(norm)
    return out


def fetch_by_id(env, kind, gif_id):
    key = require_key(env, "GIPHY_API_KEY", GIPHY_SETUP)
    r = requests.get(GIPHY_GIF_BY_ID.format(gif_id=gif_id),
                     params={"api_key": key}, timeout=30)
    if r.status_code != 200:
        sys.exit(f"GIPHY lookup failed ({r.status_code}): {r.text[:300]}")
    item = r.json().get("data")
    if not item:
        sys.exit(f"Error: no GIPHY result with id {gif_id}")
    rendition, media = _pick_rendition(item.get("images", {}), kind == "sticker")
    if not media:
        sys.exit(f"Error: result {gif_id} has no usable GIF rendition")
    return item, rendition, media


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def has_alpha(path, frames=6):
    """Does this GIF actually carry transparency?

    Decoded rather than assumed: a "sticker" can be opaque and a plain GIF can
    have a transparent border. ffmpeg composites GIF frames, so a frame that
    only uses the transparent palette index for inter-frame optimisation comes
    out opaque here -- which is what we want.
    """
    res = subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(path),
        "-frames:v", str(frames), "-f", "rawvideo", "-pix_fmt", "rgba", "-",
    ], capture_output=True)
    data = res.stdout
    if not data:
        return False
    # Every 4th byte is alpha; anything below opaque means real transparency.
    return any(b < 250 for b in data[3::4])


def to_mp4(src, dst):
    """Opaque GIF -> H.264. NVENC per the project's GPU-first rule.

    yuv420p needs even dimensions, hence the pad; GIFs are often odd-sized.
    """
    res = run([
        "ffmpeg", "-y", "-v", "error", "-i", str(src),
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30",
        "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "20", "-pix_fmt", "yuv420p",
        "-an", str(dst),
    ])
    return res.returncode == 0, res.stderr


def to_prores_alpha(src, dst):
    """Transparent GIF -> ProRes 4444 with a real alpha channel.

    CPU-only on purpose: NVENC cannot encode an alpha channel, so the project's
    GPU-first rule does not apply here. ProRes 4444 is the format Kdenlive/MLT
    handles most reliably for alpha.
    """
    res = run([
        "ffmpeg", "-y", "-v", "error", "-i", str(src),
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30",
        "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
        "-alpha_bits", "16", "-vendor", "apl0", "-an", str(dst),
    ])
    return res.returncode == 0, res.stderr


def record_credit(name, kind, source, description, ref, page):
    MEMES_DIR.mkdir(parents=True, exist_ok=True)
    if not CREDITS.is_file():
        CREDITS.write_text(
            "# Meme / sticker credits\n\n"
            "Attribution for everything in `memes/`. GIPHY's terms require attribution\n"
            "(\"Powered by GIPHY\"), and much of the catalogue -- wherever it came from --\n"
            "is copyrighted film/TV/sport. Check before publishing and credit what you\n"
            "use in the video description.\n\n"
            "| file | kind | source | description | ref | page |\n"
            "|---|---|---|---|---|---|\n"
        )
    clean = (description or "").replace("|", "/").replace("\n", " ")
    CREDITS.write_text(CREDITS.read_text() + (
        f"| `{name}` | {kind} | {source} | {clean} | `{ref}` | {page or '-'} |\n"
    ))


def publish(gif_path, name, kind, source, description, ref, page, force_alpha=None):
    """Convert a local GIF to an edit-ready render and record its provenance."""
    transparent = has_alpha(gif_path) if force_alpha is None else force_alpha
    if transparent:
        out = MEMES_DIR / f"{name}.mov"
        ok, err = to_prores_alpha(gif_path, out)
        note = "ProRes 4444, alpha preserved (CPU -- NVENC cannot encode alpha)"
    else:
        out = MEMES_DIR / f"{name}.mp4"
        ok, err = to_mp4(gif_path, out)
        note = "H.264 via NVENC (GPU)"

    print(f"Transparency:    {'yes' if transparent else 'no'} (detected from the file)")
    if not ok:
        print(f"Warning: conversion failed, original GIF kept.\n{err[:400]}", file=sys.stderr)
    else:
        print(f"Edit-ready:      {out}  ({out.stat().st_size // 1024} KB, {note})")

    record_credit(out.name if ok else gif_path.name, kind, source, description, ref, page)
    print(f"Credit recorded: {CREDITS}")
    if transparent and ok:
        print("Import the .mov in Kdenlive -- it carries the alpha channel.")
    return out if ok else gif_path


def cmd_search(args, env):
    results = search(env, args.type, args.query, args.limit)
    if not results:
        sys.exit("No results — try different search terms.")
    print(json.dumps(results, indent=2))


def cmd_download(args, env):
    item, rendition, media = fetch_by_id(env, args.type, args.id)
    desc = (item.get("alt_text") or item.get("title") or "").strip()
    name = slugify(args.name or desc or f"meme-{args.id}")
    MEMES_DIR.mkdir(parents=True, exist_ok=True)

    gif_path = MEMES_DIR / f"{name}.gif"
    r = requests.get(media["url"], timeout=120)
    if r.status_code != 200:
        sys.exit(f"Download failed ({r.status_code}) for {media['url']}")
    gif_path.write_bytes(r.content)
    print(f"Saved original:  {gif_path}  ({len(r.content) // 1024} KB, {rendition})")

    publish(gif_path, name, args.type, "giphy", desc, args.id, item.get("url"))


def cmd_convert(args, env):
    """No API involved: take a GIF the user already found and make it editable."""
    MEMES_DIR.mkdir(parents=True, exist_ok=True)
    source = args.source
    is_url = source.startswith(("http://", "https://"))

    if is_url:
        name = slugify(args.name or Path(source.split("?")[0]).stem or "meme")
        gif_path = MEMES_DIR / f"{name}.gif"
        r = requests.get(source, timeout=120,
                         headers={"User-Agent": "Mozilla/5.0 (find_memes.py)"})
        if r.status_code != 200:
            sys.exit(f"Download failed ({r.status_code}) for {source}")
        gif_path.write_bytes(r.content)
        print(f"Saved original:  {gif_path}  ({len(r.content) // 1024} KB)")
        ref, page = "-", source
    else:
        src = Path(source).expanduser()
        if not src.is_file():
            sys.exit(f"Error: '{src}' not found.")
        name = slugify(args.name or src.stem)
        gif_path = MEMES_DIR / f"{name}{src.suffix or '.gif'}"
        if src.resolve() != gif_path.resolve():
            gif_path.write_bytes(src.read_bytes())
        print(f"Saved original:  {gif_path}  ({gif_path.stat().st_size // 1024} KB)")
        ref, page = "-", str(src)

    force = True if args.alpha else (False if args.no_alpha else None)
    publish(gif_path, name, args.type, "manual", args.description or name, ref, page,
            force_alpha=force)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    cp = sub.add_parser("convert", help="convert a GIF you already have (no API key)")
    cp.add_argument("source", help="path to a local .gif, or a direct URL to one")
    cp.add_argument("--name", default=None, help="output basename (without extension)")
    cp.add_argument("--type", choices=["gif", "sticker"], default="gif",
                    help="only labels the credit row; transparency is detected")
    cp.add_argument("--description", default=None, help="what it is, for CREDITS.md")
    cp.add_argument("--alpha", action="store_true", help="force the alpha (ProRes) path")
    cp.add_argument("--no-alpha", action="store_true", help="force the opaque (mp4) path")

    sp = sub.add_parser("search", help="search GIPHY for candidates, prints JSON")
    sp.add_argument("--type", choices=["gif", "sticker"], required=True)
    sp.add_argument("--query", required=True)
    sp.add_argument("--limit", type=int, default=12)

    dp = sub.add_parser("download", help="download one GIPHY result by id into memes/")
    dp.add_argument("--type", choices=["gif", "sticker"], required=True)
    dp.add_argument("--id", required=True)
    dp.add_argument("--name", default=None, help="output basename (without extension)")

    args = ap.parse_args()
    env = load_env()
    {"search": cmd_search, "download": cmd_download, "convert": cmd_convert}[args.cmd](args, env)


if __name__ == "__main__":
    main()
