---
name: code-clip
description: Create a syntax-highlighted code clip for this video project from the real implementation source, publishing to manim/. Use when the user asks to show code, add a code clip/snippet, or visualise a function, struct, or block of the torrent client.
---

# Code clips from real source

Renders a snippet as a Catppuccin Latte code block, 2048x1280 @ 30fps, published to `manim/`. Scenes live in `.manim/scenes/code_clips.py` — add a class there rather than starting a new file, so all code clips stay visually identical.

## The rule that matters

**Every character on screen must be real source from `/home/piyush/Projects/dhaar-torrent`.** Read the file, copy the lines, mark anything you removed with `// ...`. Never retype from memory and never write plausible-looking code: pasted source reads as authority, and invented code that a viewer later can't find in the repo undermines the whole video. If the user asks for something the code doesn't do, say so rather than inventing it.

Trimming is fine and usually necessary — dropping error branches, collapsing a long argument list to `/* ... */`. Changing semantics is not.

## Workflow

1. **Find the real code.** Locate the file and lines:
   ```bash
   cd /home/piyush/Projects/dhaar-torrent
   grep -rn "<symbol>" src/ crates/
   sed -n '<start>,<end>p' src/<path>.rs
   ```
   The module tree maps to the architecture: `torrent_parser/`, `crates/bencode/`, `peer_explorer/` (with `tracker/`), `peer_manager/`, `peer_connection/` (with `request_manager.rs`), `piece_manager/` (with `piece_writer.rs`), `wire_protocol/codec/`. `README.md` has an "Architecture" summary.

2. **Trim for screen.** Aim for **under ~28 lines** — beyond that the font shrinks past readability at 1280p. Keep the real identifiers, real constants and real comments; the project's own comments are often the best narration you'll get. Mark every elision.

3. **Add a scene** to `.manim/scenes/code_clips.py`:
   ```python
   MY_SNIPPET = """
   fn thing() -> bool {
       let digest: [u8; 20] = sha1::Sha1::digest(&data).into();
       digest == piece.hash
   }
   """


   class MySnippet(_CodeClip):
       TITLE = "what this code means"          # the idea, not the function name
       SOURCE = MY_SNIPPET
       ORIGIN = "src/piece_manager/mod.rs"     # always cite the file on screen
       CAPTION = "one line on why it matters"
   ```
   `_CodeClip` handles the block, the origin line, the caption, the audit, and a hold proportional to line count.

4. **Verify the snippet is valid.** A stray bracket puts broken code on screen — this has already happened once here. Check balance after stripping comments:
   ```bash
   python3 - <<'PY'
   import re, pathlib
   src = pathlib.Path(".manim/scenes/code_clips.py").read_text()
   body = re.search(r'MY_SNIPPET = """(.*?)"""', src, re.S).group(1)
   s = re.sub(r'//.*', '', re.sub(r'/\*.*?\*/', '', body))
   for o, c in (("(", ")"), ("{", "}"), ("[", "]")):
       print(o + c, "ok" if s.count(o) == s.count(c) else f"UNBALANCED {s.count(o)}/{s.count(c)}")
   PY
   ```
   Also re-read the original file and diff it by eye against what you pasted.

5. **Audit, then render and publish** (as in `manim-clip`):
   ```bash
   cd .manim && manim render -s scenes/code_clips.py MySnippet    # geometry check
   cd .manim && manim render scenes/code_clips.py MySnippet       # video
   cp .manim/media/videos/code_clips/1280p30/MySnippet.mp4 manim/code-<name>.mp4
   ```
   Publish as `code-<kebab-name>.mp4` so code clips sort together.

6. **Look at the frame.** Confirm it's readable and that highlighting picked up the language.

## Gotchas

- **Never set Fira Code on a code block.** Its `//` ligature collapses two characters into one glyph, so Manim's per-character mapping overruns and `Code()` dies with `IndexError: list index out of range` in `_gen_chars`. `disable_ligatures=True` does not help — `Code` breaks before applying it. `code_block()` uses `CODE_FONT`, auto-detected as a ligature-free mono. `sudo pacman -S ttf-fira-mono` installs the matching ligature-free Fira face and `_pick_code_font()` will pick it up automatically; otherwise it falls back to DejaVu Sans Mono. Display text elsewhere keeps Fira Code, where ligatures render `->` and `==` attractively.
- Highlighting uses a `catppuccin-latte` pygments style registered at import in `catppuccin.py` (keywords mauve, strings green, comments overlay2, constants peach, operators sky). Do not pass a stock style — it will not match the other clips.
- Avoid font styles in that pygments style. Italic/bold entries were the first suspect for the `_gen_chars` crash, and colour-only keeps it simple.
- Reading time is the whole point: 27 lines of Rust needs ~12s, not the ~3s a default `wait()` gives. `_CodeClip` scales the hold; don't override it downward.
- Language is `rust` by default. Pass `language=` to `code_block()` for anything else (`toml` for `Cargo.toml`, `bash` for CLI usage).
