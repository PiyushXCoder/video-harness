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
import os
import re
import subprocess
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = REPO_ROOT / "audio"
ENV_FILE = REPO_ROOT / ".env"

JAMENDO_URL = "https://api.jamendo.com/v3.0/tracks/"
FREESOUND_URL = "https://freesound.org/apiv2/search/text/"


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


# ALLOWLIST, not a blocklist. The rule is "no licence that costs money and no
# licence with an obligation we cannot meet", so anything not positively
# recognised as free-for-commercial is rejected. A blocklist silently passes
# every licence string it has not been taught about.
#
# Passes:
#   CC0 / public domain  -- no obligations at all
#   CC-BY                -- free commercially, attribution required (CREDITS.md)
#
# Rejected, and why:
#   CC-BY-NC / NC        -- NonCommercial. A monetised video is commercial use.
#   CC-BY-ND / ND        -- NoDerivatives. Trimming, fading and ducking a track
#                           to fit a video is exactly that.
#   CC-BY-SA / SA        -- ShareAlike. Can oblige licensing the FINISHED VIDEO
#                           under the same terms. Costs nothing, but it is not
#                           an obligation to accept by accident.
#   Sampling+            -- retired by Creative Commons, ambiguous scope.
#   anything unknown     -- including an empty licence field.
RESTRICTIVE = (
    ("-nc", "noncommercial", "non-commercial"),
    ("-nd", "noderiv"),
    ("-sa", "sharealike", "share-alike"),
)
RESTRICTION_NAMES = ("NonCommercial", "NoDerivatives", "ShareAlike")
RESTRICTION_ABBR = {"NonCommercial": "NC", "NoDerivatives": "ND", "ShareAlike": "SA"}


def _restrictions(licence):
    text = (licence or "").lower()
    return [name for terms, name in zip(RESTRICTIVE, RESTRICTION_NAMES)
            if any(t in text for t in terms)]


def is_public_domain(licence):
    text = (licence or "").lower()
    return any(t in text for t in ("publicdomain", "/zero/", "creative commons 0", "cc0"))


def is_attribution(licence):
    text = (licence or "").lower()
    return "/by/" in text or text.strip() in ("attribution", "cc-by", "by")


def licence_ok(licence, allow_nc=False, allow_nd=False, allow_sa=False):
    """True only for licences that are free for commercial use with no payment."""
    text = (licence or "").lower()
    if not text.strip():
        return False
    if "sampling" in text:
        return False
    found = _restrictions(licence)
    overrides = {"NonCommercial": allow_nc, "NoDerivatives": allow_nd, "ShareAlike": allow_sa}
    if any(not overrides[name] for name in found):
        return False
    if found:
        # Only reachable via an explicit --allow-* override.
        return True
    return is_public_domain(licence) or is_attribution(licence)


def licence_label(licence):
    found = _restrictions(licence)
    if "sampling" in (licence or "").lower():
        return "Sampling+ (retired licence - rejected)"
    if found:
        return "CC-BY-" + "-".join(RESTRICTION_ABBR[n] for n in found) + \
               f" ({', '.join(found)} - rejected)"
    if is_public_domain(licence):
        return "CC0 / public domain (no obligations)"
    if is_attribution(licence):
        return "CC-BY (free commercially, attribution REQUIRED)"
    return f"unrecognised licence, rejected: {licence or '<empty>'}"


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "audio"


def require_key(env, key, setup_url):
    value = env.get(key)
    if not value:
        sys.exit(
            f"Error: {key} is not set.\n"
            f"Sign up (free) at {setup_url}, then either export it:\n"
            f"  export {key}=<your key>\n"
            f"or add it to {ENV_FILE}:\n  {key}=<your key>"
        )
    return value


def search_music(env, query, duration, limit, allow_nc=False, allow_nd=False, allow_sa=False):
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
    params["limit"] = max(limit * 3, limit)  # over-fetch, licence filter drops some
    resp = requests.get(JAMENDO_URL, params=params, timeout=30)
    resp.raise_for_status()
    results = []
    for t in resp.json().get("results", []):
        licence = t.get("license_ccurl", "")
        if not licence_ok(licence, allow_nc, allow_nd, allow_sa):
            continue
        if not t.get("audiodownload_allowed"):
            continue  # not offered for download; the stream URL is not a licence
        download_url = t["audiodownload"]
        results.append({
            "id": t["id"],
            "name": t["name"],
            "artist": t["artist_name"],
            "duration_s": t["duration"],
            "license": licence,
            "license_note": licence_label(licence),
            "url": download_url,
        })
        if len(results) >= limit:
            break
    return results


def search_sfx(env, query, duration, limit, allow_nc=False, allow_nd=False, allow_sa=False):
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
    params["page_size"] = max(limit * 3, limit)
    resp = requests.get(FREESOUND_URL, params=params, timeout=30)
    resp.raise_for_status()
    results = []
    for snd in resp.json().get("results", []):
        licence = snd.get("license", "")
        if not licence_ok(licence, allow_nc, allow_nd, allow_sa):
            continue
        results.append({
            "id": snd["id"],
            "name": snd["name"],
            "artist": snd["username"],
            "duration_s": snd["duration"],
            "license": licence,
            "license_note": licence_label(licence),
            "url": snd["previews"]["preview-hq-mp3"],
        })
        if len(results) >= limit:
            break
    return results


def cmd_search(args, env):
    duration = None
    if args.duration:
        lo, hi = args.duration.split("-")
        duration = (int(lo), int(hi))

    if args.type == "music":
        results = search_music(env, args.query, duration, args.limit, args.allow_nc, args.allow_nd, args.allow_sa)
    else:
        results = search_sfx(env, args.query, duration, args.limit, args.allow_nc, args.allow_nd, args.allow_sa)

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


def run_ff(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


SFX_PEAK_DBFS = -6.0
TRIM = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.02,"
        "areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.02,"
        "areverse")


def duration_of(path):
    """Duration in seconds, 0.0 when ffprobe cannot tell (e.g. an empty file)."""
    out = run_ff(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                  "-of", "default=nw=1:nk=1", str(path)]).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def measure_peak(path):
    """Peak level in dBFS, via volumedetect."""
    res = run_ff(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
                  "-af", "volumedetect", "-f", "null", "-"])
    for line in res.stderr.splitlines():
        if "max_volume:" in line:
            try:
                return float(line.split("max_volume:")[1].strip().split()[0])
            except (IndexError, ValueError):
                return None
    return None


def normalise(src, dst, role):
    """Bring an audio file to a predictable level for the Kdenlive mix.

    music: loudnorm to -20 LUFS integrated. process_recording.py masters the
           narration to -16 LUFS (measured: -16.2), so a bed at -20 sits about
           4 LU under the voice and still leaves room to duck further.
    sfx:   peak-normalised to SFX_PEAK_DBFS with leading/trailing silence
           trimmed, so effects land at a consistent level. This is a real
           two-pass measure-then-apply: a limiter alone caps peaks without
           raising them, which left files ~6 dB quieter than intended.
    """
    if role == "music":
        res = run_ff(["ffmpeg", "-y", "-v", "error", "-i", str(src),
                      "-af", "loudnorm=I=-20:TP=-2:LRA=11",
                      "-ar", "48000", "-c:a", "pcm_s16le", str(dst)])
        return res.returncode == 0, res.stderr

    tmp = dst.with_suffix(".trim.wav")
    res = run_ff(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", TRIM,
                  "-ar", "48000", "-c:a", "pcm_s16le", str(tmp)])
    if res.returncode != 0:
        tmp.unlink(missing_ok=True)
        return False, res.stderr

    # A source quieter than the trim threshold gets eaten entirely. Fall back to
    # the untrimmed audio rather than emitting an empty file.
    if duration_of(tmp) < 0.02:
        tmp.unlink(missing_ok=True)
        tmp = dst.with_suffix(".trim.wav")
        res = run_ff(["ffmpeg", "-y", "-v", "error", "-i", str(src),
                      "-ar", "48000", "-c:a", "pcm_s16le", str(tmp)])
        if res.returncode != 0:
            tmp.unlink(missing_ok=True)
            return False, res.stderr
        print("Note: source was quieter than the silence threshold, so nothing was "
              "trimmed.", file=sys.stderr)

    peak = measure_peak(tmp)
    gain = 0.0 if peak is None else SFX_PEAK_DBFS - peak
    # No limiter here: alimiter auto-levels back to 0 dBFS by default, which
    # silently undoes the gain we just computed. The measured gain lands on the
    # target exactly, so a limiter would only be able to hurt.
    res = run_ff(["ffmpeg", "-y", "-v", "error", "-i", str(tmp),
                  "-af", f"volume={gain:.2f}dB",
                  "-ar", "48000", "-c:a", "pcm_s16le", str(dst)])
    tmp.unlink(missing_ok=True)
    return res.returncode == 0, res.stderr


def record_credit(name, role, source, title, artist, licence, page):
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    credits = AUDIO_DIR / "CREDITS.md"
    if not credits.is_file():
        credits.write_text(
            "# Audio credits\n\n"
            "CC-BY requires attribution in the video description. CC0 does not, but\n"
            "crediting is still polite. NonCommercial and NoDerivatives licences are\n"
            "filtered out by find_audio.py -- a monetised video is a commercial use.\n\n"
            "Note: Freesound/Jamendo audio can still attract a YouTube Content ID claim\n"
            "even when correctly licensed. Keep this file as your evidence.\n\n"
            "| file | role | source | title | artist | licence | page |\n"
            "|---|---|---|---|---|---|---|\n"
        )
    clean = lambda x: str(x or "").replace("|", "/").replace("\n", " ")
    credits.write_text(credits.read_text() + (
        f"| `{name}` | {role} | {source} | {clean(title)} | {clean(artist)} | "
        f"{clean(licence)} | {clean(page)} |\n"
    ))
    return credits


def cmd_import(args, env):
    """No API involved: normalise an audio file the user already has.

    The safest source for a monetised YouTube video is the YouTube Audio Library
    (studio.youtube.com -> Audio Library): cleared for YouTube specifically, so it
    will not trigger a Content ID claim, and most of it needs no attribution.
    """
    src = Path(args.source).expanduser()
    if not src.is_file():
        sys.exit(f"Error: '{src}' not found.")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    name = slugify(args.name or src.stem)
    dst = AUDIO_DIR / f"{name}.wav"
    ok, err = normalise(src, dst, args.role)
    if not ok:
        sys.exit(f"Normalisation failed:\n{err[:400]}")
    dur = duration_of(dst)
    target = "-20 LUFS (bed, sits under -16 LUFS narration)" if args.role == "music" \
        else "peak -6 dBFS, silence trimmed"
    print(f"Imported: {dst}  ({dur:.1f}s, {target})")
    credits = record_credit(dst.name, args.role, args.source_name or "manual",
                            args.title or name, args.artist, args.license, str(src))
    print(f"Credit recorded: {credits}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    ip = sub.add_parser("import", help="normalise an audio file you already have (no API key)")
    ip.add_argument("source", help="path to a local audio file")
    ip.add_argument("--role", choices=["music", "sfx"], required=True)
    ip.add_argument("--name", default=None, help="output basename (without extension)")
    ip.add_argument("--title", default=None)
    ip.add_argument("--artist", default=None)
    ip.add_argument("--license", default="see source", help="licence text for CREDITS.md")
    ip.add_argument("--source-name", default=None, help="e.g. 'YouTube Audio Library'")

    sp = sub.add_parser("search", help="search for candidates, prints JSON")
    sp.add_argument("--type", choices=["music", "sfx"], required=True)
    sp.add_argument("--query", required=True)
    sp.add_argument("--duration", default=None, help="seconds range MIN-MAX, e.g. 60-180")
    sp.add_argument("--limit", type=int, default=10)
    sp.add_argument("--allow-nc", action="store_true",
                    help="include NonCommercial licences (NOT safe for a monetised video)")
    sp.add_argument("--allow-nd", action="store_true",
                    help="include NoDerivatives licences (trimming/ducking may breach these)")
    sp.add_argument("--allow-sa", action="store_true",
                    help="include ShareAlike (may oblige licensing the finished video alike)")

    dp = sub.add_parser("download", help="download a specific result by id into audio/")
    dp.add_argument("--type", choices=["music", "sfx"], required=True)
    dp.add_argument("--id", required=True)
    dp.add_argument("--query", default=None, help="same query used for search, to relocate the id")
    dp.add_argument("--duration", default=None, help="seconds range MIN-MAX, e.g. 60-180")
    dp.add_argument("--limit", type=int, default=10)
    dp.add_argument("--allow-nc", action="store_true",
                    help="include NonCommercial licences (NOT safe for a monetised video)")
    dp.add_argument("--allow-nd", action="store_true",
                    help="include NoDerivatives licences (trimming/ducking may breach these)")
    dp.add_argument("--allow-sa", action="store_true",
                    help="include ShareAlike (may oblige licensing the finished video alike)")
    dp.add_argument("--name", default=None, help="output basename (without extension)")

    args = ap.parse_args()
    env = load_env()

    {"search": cmd_search, "download": cmd_download, "import": cmd_import}[args.command](args, env)


if __name__ == "__main__":
    main()
