#!/usr/bin/env python3
"""
find_audio.py

Search and download royalty-free audio into audio/, via two official,
CC-licensed APIs:
  - Jamendo   (music)   https://developer.jamendo.com/v3.0
  - Freesound (sfx)     https://freesound.org/docs/api/

Two-step flow — search first, inspect candidates, then download the one
that actually fits:

  find_audio.py search --type music --query "upbeat corporate" --duration 60-180
  find_audio.py download --type music --id <id> [--name my-intro-music]

  find_audio.py search --type sfx --query "keyboard click"
  find_audio.py download --type sfx --id <id> [--name click]

Requires API keys in a .env file at the repo root (never commit this file):
  JAMENDO_CLIENT_ID=...
  FREESOUND_API_KEY=...

  Jamendo:   https://devportal.jamendo.com/  -> create an app -> "Client ID" (instant, free)
  Freesound: https://freesound.org/apiv2/apply/  -> register an app -> API key (instant, free)

Note: Freesound downloads use the "preview-hq-mp3" URL (available with just
an API key, no OAuth) — good enough quality for most use. The original
lossless file requires Freesound OAuth2, not implemented here.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = REPO_ROOT / "audio"
ENV_FILE = REPO_ROOT / ".env"

JAMENDO_URL = "https://api.jamendo.com/v3.0/tracks/"
FREESOUND_URL = "https://freesound.org/apiv2/search/text/"


def load_env():
    env = {}
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "audio"


def require_key(env, key, setup_url):
    value = env.get(key)
    if not value:
        sys.exit(
            f"Error: {key} not set in {ENV_FILE}.\n"
            f"Sign up (free) at {setup_url}, then add:\n  {key}=<your key>\nto {ENV_FILE}"
        )
    return value


def search_music(env, query, duration, limit):
    client_id = require_key(env, "JAMENDO_CLIENT_ID", "https://devportal.jamendo.com/")
    params = {
        "client_id": client_id,
        "format": "json",
        "limit": limit,
        "search": query,
        "include": "musicinfo licenses",
        "audioformat": "mp32",
    }
    if duration:
        lo, hi = duration
        params["durationbetween"] = f"{lo}_{hi}"
    resp = requests.get(JAMENDO_URL, params=params, timeout=30)
    resp.raise_for_status()
    results = []
    for t in resp.json().get("results", []):
        download_url = t["audiodownload"] if t.get("audiodownload_allowed") else t["audio"]
        results.append({
            "id": t["id"],
            "name": t["name"],
            "artist": t["artist_name"],
            "duration_s": t["duration"],
            "license": t.get("license_ccurl", ""),
            "url": download_url,
        })
    return results


def search_sfx(env, query, duration, limit):
    token = require_key(env, "FREESOUND_API_KEY", "https://freesound.org/apiv2/apply/")
    params = {
        "query": query,
        "token": token,
        "page_size": limit,
        "fields": "id,name,username,duration,license,previews",
    }
    if duration:
        lo, hi = duration
        params["filter"] = f"duration:[{lo} TO {hi}]"
    resp = requests.get(FREESOUND_URL, params=params, timeout=30)
    resp.raise_for_status()
    results = []
    for s in resp.json().get("results", []):
        results.append({
            "id": s["id"],
            "name": s["name"],
            "artist": s["username"],
            "duration_s": s["duration"],
            "license": s.get("license", ""),
            "url": s["previews"]["preview-hq-mp3"],
        })
    return results


def cmd_search(args, env):
    duration = None
    if args.duration:
        lo, hi = args.duration.split("-")
        duration = (int(lo), int(hi))

    if args.type == "music":
        results = search_music(env, args.query, duration, args.limit)
    else:
        results = search_sfx(env, args.query, duration, args.limit)

    if not results:
        print("No results.", file=sys.stderr)
        return
    print(json.dumps(results, indent=2))


def cmd_download(args, env):
    # Freesound/Jamendo download URLs aren't stable ids on their own, so we
    # relocate the chosen result by re-running the same search and matching
    # on id, rather than requiring the caller to pass the raw URL around.
    if not args.query:
        sys.exit("Error: download needs --query (the same one used for search) to relocate the item's URL.")

    duration = None
    if args.duration:
        lo, hi = args.duration.split("-")
        duration = (int(lo), int(hi))

    if args.type == "music":
        results = search_music(env, args.query, duration, max(args.limit, 20))
    else:
        results = search_sfx(env, args.query, duration, max(args.limit, 20))

    match = next((r for r in results if str(r["id"]) == str(args.id)), None)
    if not match:
        sys.exit(f"Error: id {args.id} not found in a re-search for '{args.query}'. Re-run search first.")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    basename = args.name or slugify(match["name"])
    dest = AUDIO_DIR / f"{basename}.mp3"

    print(f"Downloading '{match['name']}' by {match['artist']} ({match['duration_s']}s, {match['license']}) -> {dest}")
    resp = requests.get(match["url"], timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"Done. Saved to '{dest}'")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("search", help="search for candidates, prints JSON")
    sp.add_argument("--type", choices=["music", "sfx"], required=True)
    sp.add_argument("--query", required=True)
    sp.add_argument("--duration", default=None, help="seconds range MIN-MAX, e.g. 60-180")
    sp.add_argument("--limit", type=int, default=10)

    dp = sub.add_parser("download", help="download a specific result by id into audio/")
    dp.add_argument("--type", choices=["music", "sfx"], required=True)
    dp.add_argument("--id", required=True)
    dp.add_argument("--query", default=None, help="same query used for search, to relocate the id")
    dp.add_argument("--duration", default=None, help="seconds range MIN-MAX, e.g. 60-180")
    dp.add_argument("--limit", type=int, default=10)
    dp.add_argument("--name", default=None, help="output basename (without extension)")

    args = ap.parse_args()
    env = load_env()

    if args.command == "search":
        cmd_search(args, env)
    else:
        cmd_download(args, env)


if __name__ == "__main__":
    main()
