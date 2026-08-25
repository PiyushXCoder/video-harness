"""Catppuccin Mocha palette + shared scene furniture for this project's clips.

Palette values are the official ones from catppuccin/palette (palette.json),
cross-checked against https://catppuccin.com/palette/. Mocha is the DARK
flavour — `base` is the background, `text` is the foreground.

Semantic roles follow the Catppuccin style guide:
  base            page background          mantle/crust  secondary panes
  text            body copy + headlines    subtext0/1    sub-headlines
  overlay1        de-emphasised content    surface0-2    hierarchy / borders
  blue            links, interactive       green         success
  yellow          warnings                 red           errors
  mauve           keywords                 peach         constants
"""

import numpy as np

from manim import *

MOCHA = {
    "rosewater": "#f5e0dc",
    "flamingo": "#f2cdcd",
    "pink": "#f5c2e7",
    "mauve": "#cba6f7",
    "red": "#f38ba8",
    "maroon": "#eba0ac",
    "peach": "#fab387",
    "yellow": "#f9e2af",
    "green": "#a6e3a1",
    "teal": "#94e2d5",
    "sky": "#89dceb",
    "sapphire": "#74c7ec",
    "blue": "#89b4fa",
    "lavender": "#b4befe",
    "text": "#cdd6f4",
    "subtext1": "#bac2de",
    "subtext0": "#a6adc8",
    "overlay2": "#9399b2",
    "overlay1": "#7f849c",
    "overlay0": "#6c7086",
    "surface2": "#585b70",
    "surface1": "#45475a",
    "surface0": "#313244",
    "base": "#1e1e2e",
    "mantle": "#181825",
    "crust": "#11111b",
}

FONT = "Fira Code"


def _pick_code_font():
    """Font for CODE blocks -- must not have programming ligatures.

    Fira Code turns `//` into a single ligature glyph, so glyph count stops
    matching character count and Manim's Code() dies in _gen_chars with
    "IndexError: list index out of range" on any snippet containing a comment.
    (Text() is unaffected -- that is why `->` and `==` render as ligatures in the
    diagram clips, which is desirable there.) `disable_ligatures=True` does not
    help: Code breaks before it is applied.

    Fira Mono is Fira Code's ligature-free sibling and the closest match to the
    project's typeface. Install it with `sudo pacman -S ttf-fira-mono`; until
    then fall back to another mono face so code clips still render.
    """
    import shutil
    import subprocess

    candidates = ["Fira Mono", "DejaVu Sans Mono", "Liberation Mono", "Noto Sans Mono"]
    if not shutil.which("fc-match"):
        return candidates[1]
    for family in candidates:
        try:
            got = subprocess.run(["fc-match", family, "family"],
                                 capture_output=True, text=True, timeout=5).stdout
        except Exception:
            continue
        # fc-match always returns something; only trust it if it echoed the
        # family we asked for, otherwise fontconfig silently substituted.
        if family.lower() in got.lower():
            return family
    return candidates[1]


CODE_FONT = _pick_code_font()

# --- Spacing scale (guideline S9: consistent spacing, not ad-hoc buff values).
# Use these names everywhere instead of literals; a new value needs a reason.
# Prefixed to avoid shadowing Manim's own exports -- a bare NORMAL collides with
# Manim's font-weight constant and silently turns weight=NORMAL into weight=0.42.
GAP_XS = 0.12   # inside a component, between a shape and its own label
GAP_SM = 0.22   # label to its parent object
GAP_MD = 0.42   # peers within a tight cluster
GAP_LG = 0.75   # between sibling components in a row -- leaves room for an arrow
GAP_XL = 1.35   # between rows -- leaves room for edge labels between them

# Preferred edge-label offsets, derived from arrow ORIENTATION rather than tuned
# per edge. Consistency is what makes a diagram look deliberate (S9), so every
# horizontal edge puts its label at the same height; the solver only deviates
# from these when a specific label would actually collide (S13).
LBL_ABOVE = 0.72
LBL_BELOW = 0.88
LBL_SIDE = 0.95

# Frame is 2048x1280 (8:5), so frame_height 8 -> frame_width 12.8.
# Keep content inside x +/-6.1, y +/-3.7.
X_LIM, Y_LIM = 6.1, 3.7


class Region:
    """A named rectangle of the frame (guideline S3: semantic regions).

    Objects belong to a region; the region decides where they sit. Bounds are in
    Manim units, measured from frame centre.
    """

    def __init__(self, name, x0, x1, y0, y1):
        self.name, self.x0, self.x1, self.y0, self.y1 = name, x0, x1, y0, y1

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0

    @property
    def center(self):
        return np.array([(self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2, 0.0])

    def fit(self, mob, margin=GAP_SM):
        """Scale down only if needed, then centre in the region (S17)."""
        if mob.width > self.width - margin:
            mob.scale((self.width - margin) / mob.width)
        if mob.height > self.height - margin:
            mob.scale((self.height - margin) / mob.height)
        mob.move_to(self.center)
        return mob


# Safe area, and the two regions every scene here uses.
SAFE = Region("safe", -X_LIM, X_LIM, -Y_LIM, Y_LIM)
TITLE_REGION = Region("title", -X_LIM, X_LIM, 2.95, Y_LIM + 0.3)
CONTENT_REGION = Region("content", -X_LIM, X_LIM, -Y_LIM, 2.80)


def row(*mobs, gap=GAP_LG):
    """Siblings side by side (S5: group first, position later)."""
    return VGroup(*mobs).arrange(RIGHT, buff=gap)


def stack(*mobs, gap=GAP_XL):
    """Siblings top to bottom."""
    return VGroup(*mobs).arrange(DOWN, buff=gap)


def attach_label(parent, txt, side=DOWN, gap=GAP_SM, size=19, color=None):
    """Make a label a CHILD of its object so it can never drift (S11)."""
    lbl = Text(txt, font=FONT, font_size=size, color=color or MOCHA["subtext0"])
    lbl.next_to(parent, side, buff=gap)
    return VGroup(parent, lbl)


def _segment_hits(p0, p1, mob, margin=0.06, samples=48):
    """Does the segment p0->p1 pass through mob's bounding box?"""
    left, right = mob.get_left()[0] - margin, mob.get_right()[0] + margin
    bottom, top = mob.get_bottom()[1] - margin, mob.get_top()[1] + margin
    for i in range(samples + 1):
        t = i / samples
        x = p0[0] + (p1[0] - p0[0]) * t
        y = p0[1] + (p1[1] - p0[1]) * t
        if left <= x <= right and bottom <= y <= top:
            return True
    return False


def _endpoints(arrow):
    """Endpoints of a connection, working for dashed arrows too."""
    start = getattr(arrow, "layout_start", None)
    end = getattr(arrow, "layout_end", None)
    if start is None or end is None:
        start, end = arrow.get_start(), arrow.get_end()
    return np.array(start), np.array(end)


def endpoints(arrow):
    """Public alias -- endpoints of a connection, dashed arrows included."""
    return _endpoints(arrow)


def place_label_clear(label, arrow, obstacles=(), segments=(), gap=GAP_SM):
    """Put an edge label near its arrow in the least-conflicting free spot.

    Replaces hand-tuned per-edge offsets (S10/S11). The constraint is "readable,
    overlapping nothing, and not sitting on a line" (S13), so solve for it rather
    than guessing a magic vector per edge.

    obstacles: mobjects the label must not overlap (boxes, labels placed already)
    segments:  (start, end) pairs of every arrow -- a label must not sit on a line
    """
    start, end = _endpoints(arrow)
    mid = (start + end) / 2
    direction = end - start
    norm = np.linalg.norm(direction)
    unit = direction / norm if norm > 1e-6 else RIGHT
    perp = np.array([-unit[1], unit[0], 0.0])

    horizontal = abs(direction[0]) >= abs(direction[1])

    # Consistent first choices for this orientation, then a widening search.
    if horizontal:
        candidates = [mid + UP * LBL_ABOVE, mid + DOWN * LBL_BELOW]
    else:
        candidates = [mid + LEFT * LBL_SIDE, mid + RIGHT * LBL_SIDE]
    for k in (1, 2, 3, 4):
        for sign in (1, -1):
            candidates.append(mid + perp * (gap + 0.26 * k) * sign)
    for k in (1, 2, 3):
        for sign in (1, -1):
            candidates.append(mid + np.array([0.0, (gap + 0.26 * k) * sign, 0.0]))
            candidates.append(mid + np.array([(gap + 0.40 * k) * sign, 0.0, 0.0]))

    best, best_score = None, None
    for pos in candidates:
        label.move_to(pos)
        clamp_to_frame(label)
        score = sum(1 for o in obstacles if _overlaps(label, o))
        score += sum(1 for (a, b) in segments if _segment_hits(a, b, label))
        if score == 0:
            return label
        if best_score is None or score < best_score:
            best, best_score = label.get_center().copy(), score

    # Nothing was fully clear -- take the least-conflicting spot and let the
    # audit report it rather than silently shipping the first guess.
    label.move_to(best)
    return clamp_to_frame(label)


def _overlaps(a, b, tol=0.02):
    ox = min(a.get_right()[0], b.get_right()[0]) - max(a.get_left()[0], b.get_left()[0])
    oy = min(a.get_top()[1], b.get_top()[1]) - max(a.get_bottom()[1], b.get_bottom()[1])
    return ox > tol and oy > tol


def connect(a, b, color=None, both=False, dashed=False, follow=False):
    """Arrow between two objects, endpoints derived from the objects (S12).

    follow=True keeps the arrow glued to its endpoints via always_redraw, for
    scenes where objects move. These scenes are statically laid out, so the
    default is off -- always_redraw rebuilds the mobject every frame, which
    interferes with Create/GrowArrow on it.
    """
    if follow:
        return always_redraw(lambda: link(a, b, color, dashed=dashed, both=both))
    return link(a, b, color, dashed=dashed, both=both)


def dim(mob, tier="context"):
    """Push an object into the background so the new one dominates (S16).

    context = established and still relevant; ghost = introduced earlier, kept
    only for spatial memory (S19) rather than for reading.
    """
    opacity, stroke = (0.35, 0.9) if tier == "context" else (0.14, 0.35)
    for part in mob.family_members_with_points():
        part.set_stroke(opacity=stroke * (part.get_stroke_opacity() or 1))
        if part.get_fill_opacity():
            part.set_fill(opacity=part.get_fill_opacity() * opacity)
        else:
            part.set_opacity(part.get_fill_opacity() or 0.45)
    return mob


# --- Motion law: NO fades, ever. Entrances pop (scale from nothing with an
# ease-out-back overshoot), exits wind up and shrink away. Speed table:
# pops 0.25s, Create/GrowArrow arrows 0.2s, Write <=0.4s, waits 0.1-0.2s.

def pop_rate(t, s=1.70158):
    """easeOutBack -- overshoots past the target, then settles. The 'pop'."""
    t -= 1.0
    return 1.0 + t * t * ((s + 1.0) * t + s)


def drop_rate(t, s=1.70158):
    """easeInBack -- the mirror image: winds up slightly, then vanishes."""
    return t * t * ((s + 1.0) * t - s)


def pop_in(mob, run_time=0.25, from_edge=None, lag_ratio=None):
    """The project's ONLY entrance. GrowFromCenter/Edge + overshoot.

    from_edge=DOWN reads as the object sliding up into place while it pops
    (good for rows and captions under a stable anchor). When lag_ratio is set
    and the mobject has submobjects, each sub is animated individually via
    LaggedStart so it grows from ITS OWN centre with proper stagger.
    """
    from manim import LaggedStart

    if lag_ratio is not None and hasattr(mob, 'submobjects') and len(mob.submobjects) > 1:
        anims = []
        for sub in mob.submobjects:
            anims.append(GrowFromCenter(sub, rate_func=pop_rate))
        return LaggedStart(*anims, lag_ratio=lag_ratio, run_time=run_time)

    if from_edge is not None:
        return GrowFromEdge(mob, from_edge, run_time=run_time, rate_func=pop_rate)
    return GrowFromCenter(mob, run_time=run_time, rate_func=pop_rate)


def pop_out(mob, run_time=0.2, lag_ratio=None):
    """The only exit besides a hard cut: wind up, then shrink to nothing."""
    kwargs = {"run_time": run_time, "rate_func": drop_rate}
    if lag_ratio is not None:
        kwargs["lag_ratio"] = lag_ratio
    return ShrinkToCenter(mob, **kwargs)


class MochaScene(Scene):
    """Scene with the Mocha background and Fira Code defaults applied."""

    def setup(self):
        super().setup()
        self.camera.background_color = MOCHA["base"]

    def label(self, txt, size=26, color=None, weight=NORMAL):
        return Text(txt, font=FONT, font_size=size,
                    color=color or MOCHA["text"], weight=weight)

    def title(self, txt, size=34):
        t = self.label(txt, size=size, weight=BOLD)
        t.to_edge(UP, buff=0.45)
        return t

    def caption(self, txt, size=20):
        return self.label(txt, size=size, color=MOCHA["subtext0"])


def component(name, accent, sub=None, width=2.9, height=1.0, font_size=24):
    """A labelled box: accent-tinted fill, accent border, Latte `text` label."""
    box = RoundedRectangle(
        corner_radius=0.14, width=width, height=height,
        stroke_color=accent, stroke_width=2.5,
        fill_color=accent, fill_opacity=0.12,
    )
    lines = VGroup(Text(name, font=FONT, font_size=font_size, color=MOCHA["text"]))
    if sub:
        lines.add(Text(sub, font=FONT, font_size=font_size - 7, color=MOCHA["subtext0"]))
        lines.arrange(DOWN, buff=0.11)
    # Never let a label touch its border: Fira Code is monospace, so a long name
    # outgrows a fixed-width box quickly. Scale down to fit rather than clipping.
    margin = 0.26
    if lines.width > width - margin:
        lines.scale((width - margin) / lines.width)
    if lines.height > height - 0.18:
        lines.scale((height - 0.18) / lines.height)
    lines.move_to(box)
    return VGroup(box, lines)


def link(a, b, color=None, dashed=False, both=False, buff=0.10, width=3.0):
    """Arrow between two mobjects, Latte-toned."""
    cls = DashedVMobject if dashed else None
    arrow = (DoubleArrow if both else Arrow)(
        a.get_boundary_point(normalize(b.get_center() - a.get_center())),
        b.get_boundary_point(normalize(a.get_center() - b.get_center())),
        buff=buff, stroke_width=width,
        color=color or MOCHA["overlay1"],
        max_tip_length_to_length_ratio=0.12,
        tip_length=0.2,
    )
    # Record the endpoints on the mobject. A DashedVMobject holds its dashes as
    # submobjects and has no points of its own, so get_start()/get_end() throw on
    # it -- label placement and the audit read these attributes instead.
    start, end = arrow.get_start(), arrow.get_end()
    result = cls(arrow, num_dashes=18) if cls else arrow
    result.layout_start, result.layout_end = start, end
    return result


def clamp_to_frame(mob, pad=0.25):
    """Shift a mobject back inside the frame if it overhangs an edge.

    Cheap insurance: Fira Code is monospace, so a text width is easy to
    underestimate by a character or two and silently clip at the frame edge.
    """
    left, right = mob.get_left()[0], mob.get_right()[0]
    if left < -X_LIM + pad:
        mob.shift(RIGHT * (-X_LIM + pad - left))
    elif right > X_LIM - pad:
        mob.shift(LEFT * (right - X_LIM + pad))
    top, bottom = mob.get_top()[1], mob.get_bottom()[1]
    if bottom < -Y_LIM + pad:
        mob.shift(UP * (-Y_LIM + pad - bottom))
    elif top > Y_LIM + 0.25:
        mob.shift(DOWN * (top - Y_LIM - 0.25))
    return mob


def edge_label(txt, mob, size=17, color=None, shift=UP * 0.22):
    t = Text(txt, font=FONT, font_size=size, color=color or MOCHA["overlay2"])
    t.move_to(mob.get_center() + shift)
    return t


class LayoutError(AssertionError):
    """Raised when a scene's geometry is wrong, so the render fails loudly."""


def _box(m):
    return m.get_left()[0], m.get_right()[0], m.get_bottom()[1], m.get_top()[1]


def audit_layout(named, max_overlap=0.03, allow=(), connections=(),
                 min_ink=0.06, max_ink=0.62):
    """Fail the render if anything overflows the frame or collides.

    Manim will happily render text off the edge of the frame or two labels on
    top of each other -- it looks fine to the renderer and wrong to a viewer.
    Every layout bug in these scenes was of exactly that kind, so assert it
    instead of eyeballing frames.

    named:  {name: mobject} -- the things whose geometry matters. Pass boxes,
            labels and titles; leave arrows out, since an arrow is SUPPOSED to
            touch the boxes it connects.
    allow:  iterable of (nameA, nameB) pairs permitted to overlap.
    """
    allow = {frozenset(pair) for pair in allow}
    problems = []

    for name, m in named.items():
        left, right, bottom, top = _box(m)
        if left < -X_LIM - 0.05:
            problems.append(f"{name}: past left edge (x={left:.2f}, limit {-X_LIM:.2f})")
        if right > X_LIM + 0.05:
            problems.append(f"{name}: past right edge (x={right:.2f}, limit {X_LIM:.2f})")
        if bottom < -Y_LIM - 0.30:
            problems.append(f"{name}: past bottom edge (y={bottom:.2f})")
        if top > Y_LIM + 0.35:
            problems.append(f"{name}: past top edge (y={top:.2f})")

    items = list(named.items())
    for i, (na, ma) in enumerate(items):
        for nb, mb in items[i + 1:]:
            if frozenset((na, nb)) in allow:
                continue
            l1, r1, b1, t1 = _box(ma)
            l2, r2, b2, t2 = _box(mb)
            ox = min(r1, r2) - max(l1, l2)
            oy = min(t1, t2) - max(b1, b2)
            if ox > max_overlap and oy > max_overlap:
                problems.append(f"{na} overlaps {nb} by {ox:.2f} x {oy:.2f}")

    # Guideline S22 "Connections": an arrow may touch what it connects and
    # nothing else. connections = [(name, arrow, (endA, endB)), ...]
    for cname, arrow, ends in connections:
        start, end = _endpoints(arrow)
        for oname, mob in named.items():
            if oname in ends:
                continue
            if _segment_hits(start, end, mob):
                problems.append(f"{cname}: arrow passes through {oname} (not an endpoint)")

    # Guideline S22 "Composition": flag a frame that is nearly empty or packed
    # solid. Measured as the share of the safe area covered by content boxes.
    if named:
        area = sum(max(m.width, 0) * max(m.height, 0) for m in named.values())
        ink = area / (SAFE.width * SAFE.height)
        if ink < min_ink:
            problems.append(f"composition: only {ink:.0%} of the frame has content "
                            f"(under {min_ink:.0%}) -- looks empty")
        if ink > max_ink:
            problems.append(f"composition: {ink:.0%} of the frame is content "
                            f"(over {max_ink:.0%}) -- too dense, split the scene")

    if problems:
        raise LayoutError("layout audit failed:\n  - " + "\n  - ".join(problems))
    return True


# --- Syntax highlighting -----------------------------------------------------
# Catppuccin publishes code-editor roles in its style guide: keywords mauve,
# strings green, comments overlay2, constants peach, operators sky. Pygments has
# no Catppuccin style, so register one rather than settle for an approximate
# light theme -- Code() then matches the rest of the clip exactly.

def _register_pygments_style(name="catppuccin-mocha"):
    import sys
    import types

    import pygments.styles as pstyles
    from pygments.token import (Comment, Error, Keyword, Name, Number, Operator,
                                Punctuation, String, Token)
    from pygments.style import Style

    class CatppuccinMochaStyle(Style):
        background_color = MOCHA["mantle"]
        styles = {
            Token: MOCHA["text"],
            # Colour only, no italic/bold: Manim's Code char-generation miscounts
            # glyphs when a pygments style applies a font style, and dies with
            # "IndexError: list index out of range" in _gen_chars.
            Comment: MOCHA["overlay2"],
            Keyword: MOCHA["mauve"],
            Keyword.Type: MOCHA["yellow"],
            Name: MOCHA["text"],
            Name.Function: MOCHA["blue"],
            Name.Class: MOCHA["yellow"],
            Name.Namespace: MOCHA["yellow"],
            Name.Builtin: MOCHA["red"],
            Name.Builtin.Pseudo: MOCHA["red"],
            Name.Attribute: MOCHA["blue"],
            Name.Decorator: MOCHA["peach"],
            String: MOCHA["green"],
            String.Escape: MOCHA["pink"],
            Number: MOCHA["peach"],
            Operator: MOCHA["sky"],
            Punctuation: MOCHA["overlay2"],
            Error: MOCHA["red"],
        }

    module_name = "catppuccin_mocha_pygments"
    module = types.ModuleType(module_name)
    module.CatppuccinMochaStyle = CatppuccinMochaStyle
    sys.modules[module_name] = module
    pstyles._STYLE_NAME_TO_MODULE_MAP[name] = (module_name, "CatppuccinMochaStyle")
    if hasattr(pstyles, "STYLE_MAP"):
        pstyles.STYLE_MAP[name] = module_name
    return name


CODE_STYLE = _register_pygments_style()


def code_block(source, language="rust", size=17, width=None, line_numbers=False):
    """A syntax-highlighted snippet in the project's palette and font.

    Real source pasted from the project reads as authority; invented code reads
    as decoration. Keep snippets short -- a clip is not a code review.
    """
    block = Code(
        code_string=source.strip("\n"),
        language=language,
        formatter_style=CODE_STYLE,
        add_line_numbers=line_numbers,
        background="rectangle",
        background_config={
            "stroke_color": MOCHA["surface1"],
            "stroke_width": 2.0,
            "fill_color": MOCHA["mantle"],
            "fill_opacity": 1.0,
            "corner_radius": 0.12,
        },
        paragraph_config={"font": CODE_FONT, "font_size": size, "line_spacing": 0.55},
    )
    if width is not None and block.width > width:
        block.scale(width / block.width)
    return block
