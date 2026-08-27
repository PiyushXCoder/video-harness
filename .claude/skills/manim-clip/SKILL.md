---
name: manim-clip
description: Create a Manim animation clip for this video project — designing the layout by constraint, auditing its geometry, rendering, and publishing to manim/. Use when the user asks to create/make/add a manim clip, animation, diagram, or scene.
---

# Manim clip creation

Manim Community v0.19.1. Scene source lives in `.manim/scenes/`; rendered clips are published to `manim/` at the repo root (see `CLAUDE.md`). Resolution 2048x1280 @ 30fps and the Mocha background come from `.manim/manim.cfg` — never repeat them on the command line.

**Read `docs/manim-layout-guidelines.md` before designing a non-trivial scene.** It is 30 rules on layout engineering; the ones that bite hardest here are S2/S28 (express position as relationships, not coordinates), S9 (one spacing scale), S16 (dim context so the new thing dominates), and S22 (validate before shipping).

## Workflow

1. **Name the clip.** Kebab-case `<clip_name>`, `PascalCase` Scene class (`binary-search` → `BinarySearch`). Ask if it isn't obvious from context.

2. **Check the facts.** If the clip explains this project's torrent client, verify component names, topology and constants against `/home/piyush/Projects/dhaar-torrent` — its `README.md` "Architecture" section and `src/` tree. The narration is NOT reliable for this: it never mentions `request_manager` and calls `PieceWriter` a "disk writer". A diagram that contradicts the code is worse than no diagram.

3. **Design the layout as constraints, not coordinates.** Decide what appears, and how things relate; let the helpers decide where. A scene with a table of `move_to([x, y, 0])` literals will cost you three render-and-nudge cycles — that is exactly the failure the guideline exists to prevent.

   ```python
   from manim import *
   from catppuccin import (MOCHA, MochaScene, audit_layout, component, connect,
                           dim, endpoints, place_label_clear, row, stack,
                           CONTENT_REGION, GAP_LG, GAP_XL)


   class <ClassName>(MochaScene):
       def construct(self):
           title = self.title("what this beat says")
           boxes = {k: component(...) for k in SPEC}
           top = row(boxes["a"], boxes["b"], gap=GAP_LG)
           bottom = row(boxes["c"], boxes["d"], gap=GAP_LG)
           CONTENT_REGION.fit(VGroup(top, bottom).arrange(DOWN, buff=GAP_XL))
           ...
           audit_layout({"title": title, **boxes}, connections=conns)
   ```

   Engine API in `.manim/scenes/catppuccin.py`:

   | helper | use |
   |---|---|
   | `MOCHA[...]` | every colour. Never `BLUE`/`RED` — Manim's defaults clash with Mocha |
   | `GAP_XS/SM/MD/LG/XL` | every gap. A new literal needs a reason (S9) |
   | `row()` / `stack()` | siblings side by side / top to bottom (S5) |
   | `Region`, `CONTENT_REGION.fit()` | assign objects to a region; scale-to-fit only if needed (S3/S17) |
   | `component(name, accent, sub=)` | labelled box; the label auto-fits so it cannot overflow |
   | `connect(a, b, follow=)` | arrow derived from its endpoints (S12) |
   | `place_label_clear(lbl, arrow, obstacles=, segments=)` | solves an edge label's position instead of you tuning an offset (S10/S13) |
   | `attach_label(parent, txt)` | make a label a child so it cannot drift (S11) |
   | `dim(mob, "context"/"ghost")` | push established objects back so the new one dominates (S16) |
   | `clamp_to_frame(mob)` | last-resort nudge for text whose width you underestimated |

4. **Audit the geometry — before rendering any video.** Manim renders text off the frame edge, or two labels on top of each other, without complaining. It looks right to the renderer and wrong to a viewer; every layout bug in this project was that kind. `audit_layout()` at the end of `construct()` turns those into a hard failure. Pass the boxes, labels and titles whose geometry matters, plus `connections=[(name, arrow, (endA, endB))]` so an arrow crossing an unrelated object is caught too. Leave arrows out of the first dict — an arrow is meant to touch what it connects.

   ```bash
   cd .manim && manim render -s scenes/<clip_name>.py <ClassName>
   ```
   `-s` runs `construct()` fully but writes only a PNG — seconds, not a full encode. Iterate here until it passes:
   ```
   LayoutError: layout audit failed:
     - lanes: past right edge (x=6.17, limit 6.10)
     - arrow[a->b]: arrow passes through label[c->d] (not an endpoint)
   ```

5. **Then look at a frame.** The audit catches overflow, collisions and crossings. It cannot tell you a composition is lopsided, that a diagonal reads badly, or that a label is technically clear but ambiguous. Those were all real defects here, and only looking caught them.
   ```bash
   ffmpeg -y -v error -sseof -1.5 -i <rendered>.mp4 -frames:v 1 /tmp/frame.png
   ```

6. **Render video**, several scenes in one invocation when a clip has staged variants:
   ```bash
   cd .manim && manim render scenes/<clip_name>.py Scene1 Scene2 -o <clip_name>
   ```

7. **Publish** from `.manim/media/videos/<file>/1280p30/<Scene>.mp4` to `manim/<clip_name>.mp4`.

8. **Report** path and duration (`ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1`).

## Staged clips

For a diagram revealed across several narration beats, build the FULL layout once and have each stage reveal a subset. Positions then stay fixed across stages with nothing hardcoded — satisfying both S2 (no coordinates) and S7/S19 (established objects never move, so cuts between clips don't make boxes jump). Put that full layout in a single `build_graph()`-style helper the stage classes share. In the episode this was worked out on, adding a whole new component to the diagram later needed no repositioning at all.

Give each stage its own narrative-beat method rather than one long `construct()` (S25), and dim prior stages' components to `context`, ghosting anything the story has moved past (S16/S14).

## Split a clip rather than freezing it

Size the clip to the narration beat it explains. If the narration covers a
diagram's *problem* and its *fix* tens of seconds apart, that is **two clips**,
not one clip frozen across the gap.

A single clip held over a long window is bad twice over: it looks dead, and
because nothing may be drawn on top of a cutaway, it blocks every gif, emoji,
stamp and punch line for the whole hold. One 1.7 s clip was being stretched to
25 s, and a 6.3 s one to 47 s.

When splitting, put the shared geometry in a base class so the two clips place
their objects identically — the diagram must not jump on the cut (S7/S19). Have
part 2 open in part 1's **end** state rather than rebuilding from scratch, so the
cut reads as the same diagram continuing. Concretely: a private `_Diagram` base holding the geometry, with
`ThingProblem` / `ThingSolution` subclasses playing the two halves.

## Audit every mobject you create

`audit_layout()` only checks what you hand it. A caption placed under a box near
the frame edge overflowed and shipped reading `sh set drops the repeats` — the
note was never passed to the audit. Pass **everything** visible, and run
`clamp_to_frame()` on anything positioned relative to another object.

## Notes

- Manim's Cairo renderer is CPU-bound — the project's "prefer NVIDIA GPU" rule applies to the ffmpeg scripts, not to Manim.
- `.manim/media/` is gitignored (regenerable). `.manim/manim.cfg` and the shared engine `.manim/scenes/catppuccin.py` are template code; the per-episode scene files are this video's content, so don't fold them into a template commit.
- Re-running a render reuses Manim's cache for unchanged animations.
- Naming a spacing/style constant after a Manim export shadows it. A constant called `NORMAL` silently turned `weight=NORMAL` into `weight=0.42`; hence the `GAP_` prefix.
- `DashedVMobject` keeps its dashes as submobjects and has no points itself, so `get_start()`/`get_end()` throw on a dashed arrow. `link()` records `layout_start`/`layout_end`; read them via `endpoints(arrow)`.
- For a clip that shows source code, use the `code-clip` skill instead.
