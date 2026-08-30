# Design System Inspired by Spotify

> **This file is the design authority for the whole video.** Both render engines
> derive from it; neither owns a palette of its own.
>
> - **Read this before writing any Remotion composition or Manim scene.** Same gate
>   as `docs/manim-layout-guidelines.md`.
> - It is **not parsed**. A design system is judgement, not a token table — the
>   load-bearing parts here are rules like "the accent is functional, never
>   decorative" and "thin shadows are invisible on dark", which no schema captures.
>   An agent reads this and writes code that obeys it.
> - It lands in exactly **two** places, and nowhere else:
>   `.remotion/src/design.ts` and `.manim/scenes/design.py`. Components and scenes
>   import from those. Replace this document, update those two files, re-render.
> - `scripts/check_design.py` fails the build if a component hardcodes a colour or
>   a font size instead of importing a token.
> - **Font substitution:** SpotifyMixUI / CircularSp are commercial Lineto faces,
>   not installed and not licensable here. This project uses **Fira Code** for
>   display and an auto-detected ligature-free mono (`CODE_FONT`) for code. Every
>   weight, size and tracking rule below still applies.
> - Sections 1–7 apply as written. **Section 8 (Responsive) does not apply** —
>   delivery is a single fixed 2048×1280 frame with no interaction. Section 10
>   below is the video adaptation and **overrides sizes in section 3**, which are
>   web-scaled.

## 1. Visual Theme & Atmosphere

Spotify's web interface is a dark, immersive music player that wraps listeners in a near-black cocoon (`#121212`, `#181818`, `#1f1f1f`) where album art and content become the primary source of color. The design philosophy is "content-first darkness" — the UI recedes into shadow so that music, podcasts, and playlists can glow. Every surface is a shade of charcoal, creating a theater-like environment where the only true color comes from the iconic Spotify Green (`#1ed760`) and the album artwork itself.

The typography uses SpotifyMixUI and SpotifyMixUITitle — proprietary fonts from the CircularSp family (Circular by Lineto, customized for Spotify) with an extensive fallback stack that includes Arabic, Hebrew, Cyrillic, Greek, Devanagari, and CJK fonts, reflecting Spotify's global reach. The type system is compact and functional: 700 (bold) for emphasis and navigation, 600 (semibold) for secondary emphasis, and 400 (regular) for body. Buttons use uppercase with positive letter-spacing (1.4px–2px) for a systematic, label-like quality.

What distinguishes Spotify is its pill-and-circle geometry. Primary buttons use 500px–9999px radius (full pill), circular play buttons use 50% radius, and search inputs are 500px pills. Combined with heavy shadows (`rgba(0,0,0,0.5) 0px 8px 24px`) on elevated elements and a unique inset border-shadow combo (`rgb(18,18,18) 0px 1px 0px, rgb(124,124,124) 0px 0px 0px 1px inset`), the result is an interface that feels like a premium audio device — tactile, rounded, and built for touch.

**Key Characteristics:**
- Near-black immersive dark theme (`#121212`–`#1f1f1f`) — UI disappears behind content
- Spotify Green (`#1ed760`) as singular brand accent — never decorative, always functional
- SpotifyMixUI/CircularSp font family with global script support
- Pill buttons (500px–9999px) and circular controls (50%) — rounded, touch-optimized
- Uppercase button labels with wide letter-spacing (1.4px–2px)
- Heavy shadows on elevated elements (`rgba(0,0,0,0.5) 0px 8px 24px`)
- Semantic colors: negative red (`#f3727f`), warning orange (`#ffa42b`), announcement blue (`#539df5`)
- Album art as the primary color source — the UI is achromatic by design

## 2. Color Palette & Roles

### Primary Brand
- **Spotify Green** (`#1ed760`): Primary brand accent — play buttons, active states, CTAs
- **Near Black** (`#121212`): Deepest background surface
- **Dark Surface** (`#181818`): Cards, containers, elevated surfaces
- **Mid Dark** (`#1f1f1f`): Button backgrounds, interactive surfaces

### Text
- **White** (`#ffffff`): `--text-base`, primary text
- **Silver** (`#b3b3b3`): Secondary text, muted labels, inactive nav
- **Near White** (`#cbcbcb`): Slightly brighter secondary text
- **Light** (`#fdfdfd`): Near-pure white for maximum emphasis

### Semantic
- **Negative Red** (`#f3727f`): `--text-negative`, error states
- **Warning Orange** (`#ffa42b`): `--text-warning`, warning states
- **Announcement Blue** (`#539df5`): `--text-announcement`, info states

### Surface & Border
- **Dark Card** (`#252525`): Elevated card surface
- **Mid Card** (`#272727`): Alternate card surface
- **Border Gray** (`#4d4d4d`): Button borders on dark
- **Light Border** (`#7c7c7c`): Outlined button borders, muted links
- **Separator** (`#b3b3b3`): Divider lines
- **Light Surface** (`#eeeeee`): Light-mode buttons (rare)
- **Spotify Green Border** (`#1db954`): Green accent border variant

### Shadows
- **Heavy** (`rgba(0,0,0,0.5) 0px 8px 24px`): Dialogs, menus, elevated panels
- **Medium** (`rgba(0,0,0,0.3) 0px 8px 8px`): Cards, dropdowns
- **Inset Border** (`rgb(18,18,18) 0px 1px 0px, rgb(124,124,124) 0px 0px 0px 1px inset`): Input border-shadow combo

## 3. Typography Rules

### Font Families
- **Title**: `SpotifyMixUITitle`, fallbacks: `CircularSp-Arab, CircularSp-Hebr, CircularSp-Cyrl, CircularSp-Grek, CircularSp-Deva, Helvetica Neue, helvetica, arial, Hiragino Sans, Hiragino Kaku Gothic ProN, Meiryo, MS Gothic`
- **UI / Body**: `SpotifyMixUI`, same fallback stack

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|------|--------|-------------|----------------|-------|
| Section Title | SpotifyMixUITitle | 24px (1.50rem) | 700 | normal | normal | Bold title weight |
| Feature Heading | SpotifyMixUI | 18px (1.13rem) | 600 | 1.30 (tight) | normal | Semibold section heads |
| Body Bold | SpotifyMixUI | 16px (1.00rem) | 700 | normal | normal | Emphasized text |
| Body | SpotifyMixUI | 16px (1.00rem) | 400 | normal | normal | Standard body |
| Button Uppercase | SpotifyMixUI | 14px (0.88rem) | 600–700 | 1.00 (tight) | 1.4px–2px | `text-transform: uppercase` |
| Button | SpotifyMixUI | 14px (0.88rem) | 700 | normal | 0.14px | Standard button |
| Nav Link Bold | SpotifyMixUI | 14px (0.88rem) | 700 | normal | normal | Navigation |
| Nav Link | SpotifyMixUI | 14px (0.88rem) | 400 | normal | normal | Inactive nav |
| Caption Bold | SpotifyMixUI | 14px (0.88rem) | 700 | 1.50–1.54 | normal | Bold metadata |
| Caption | SpotifyMixUI | 14px (0.88rem) | 400 | normal | normal | Metadata |
| Small Bold | SpotifyMixUI | 12px (0.75rem) | 700 | 1.50 | normal | Tags, counts |
| Small | SpotifyMixUI | 12px (0.75rem) | 400 | normal | normal | Fine print |
| Badge | SpotifyMixUI | 10.5px (0.66rem) | 600 | 1.33 | normal | `text-transform: capitalize` |
| Micro | SpotifyMixUI | 10px (0.63rem) | 400 | normal | normal | Smallest text |

### Principles
- **Bold/regular binary**: Most text is either 700 (bold) or 400 (regular), with 600 used sparingly. This creates a clear visual hierarchy through weight contrast rather than size variation.
- **Uppercase buttons as system**: Button labels use uppercase + wide letter-spacing (1.4px–2px), creating a systematic "label" voice distinct from content text.
- **Compact sizing**: The range is 10px–24px — narrower than most systems. Spotify's type is compact and functional, designed for scanning playlists, not reading articles.
- **Global script support**: The extensive fallback stack (Arabic, Hebrew, Cyrillic, Greek, Devanagari, CJK) reflects Spotify's 180+ market reach.

## 4. Component Stylings

### Buttons

**Dark Pill**
- Background: `#1f1f1f`
- Text: `#ffffff` or `#b3b3b3`
- Padding: 8px 16px
- Radius: 9999px (full pill)
- Use: Navigation pills, secondary actions

**Dark Large Pill**
- Background: `#181818`
- Text: `#ffffff`
- Padding: 0px 43px
- Radius: 500px
- Use: Primary app navigation buttons

**Light Pill**
- Background: `#eeeeee`
- Text: `#181818`
- Radius: 500px
- Use: Light-mode CTAs (cookie consent, marketing)

**Outlined Pill**
- Background: transparent
- Text: `#ffffff`
- Border: `1px solid #7c7c7c`
- Padding: 4px 16px 4px 36px (asymmetric for icon)
- Radius: 9999px
- Use: Follow buttons, secondary actions

**Circular Play**
- Background: `#1f1f1f`
- Text: `#ffffff`
- Padding: 12px
- Radius: 50% (circle)
- Use: Play/pause controls

### Cards & Containers
- Background: `#181818` or `#1f1f1f`
- Radius: 6px–8px
- No visible borders on most cards
- Hover: slight background lightening
- Shadow: `rgba(0,0,0,0.3) 0px 8px 8px` on elevated

### Inputs
- Search input: `#1f1f1f` background, `#ffffff` text
- Radius: 500px (pill)
- Padding: 12px 96px 12px 48px (icon-aware)
- Focus: border becomes `#000000`, outline `1px solid`

### Navigation
- Dark sidebar with SpotifyMixUI 14px weight 700 for active, 400 for inactive
- `#b3b3b3` muted color for inactive items, `#ffffff` for active
- Circular icon buttons (50% radius)
- Spotify logo top-left in green

## 5. Layout Principles

### Spacing System
- Base unit: 8px
- Scale: 1px, 2px, 3px, 4px, 5px, 6px, 8px, 10px, 12px, 14px, 15px, 16px, 20px

### Grid & Container
- Sidebar (fixed) + main content area
- Grid-based album/playlist cards
- Full-width now-playing bar at bottom
- Responsive content area fills remaining space

### Whitespace Philosophy
- **Dark compression**: Spotify packs content densely — playlist grids, track lists, and navigation are all tightly spaced. The dark background provides visual rest between elements without needing large gaps.
- **Content density over breathing room**: This is an app, not a marketing site. Every pixel serves the listening experience.

### Border Radius Scale
- Minimal (2px): Badges, explicit tags
- Subtle (4px): Inputs, small elements
- Standard (6px): Album art containers, cards
- Comfortable (8px): Sections, dialogs
- Medium (10px–20px): Panels, overlay elements
- Large (100px): Large pill buttons
- Pill (500px): Primary buttons, search input
- Full Pill (9999px): Navigation pills, search
- Circle (50%): Play buttons, avatars, icons

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Base (Level 0) | `#121212` background | Deepest layer, page background |
| Surface (Level 1) | `#181818` or `#1f1f1f` | Cards, sidebar, containers |
| Elevated (Level 2) | `rgba(0,0,0,0.3) 0px 8px 8px` | Dropdown menus, hover cards |
| Dialog (Level 3) | `rgba(0,0,0,0.5) 0px 8px 24px` | Modals, overlays, menus |
| Inset (Border) | `rgb(18,18,18) 0px 1px 0px, rgb(124,124,124) 0px 0px 0px 1px inset` | Input borders |

**Shadow Philosophy**: Spotify uses notably heavy shadows for a dark-themed app. The 0.5 opacity shadow at 24px blur creates a dramatic "floating in darkness" effect for dialogs and menus, while the 0.3 opacity at 8px blur provides a more subtle card lift. The unique inset border-shadow combination on inputs creates a recessed, tactile quality.

## 7. Do's and Don'ts

### Do
- Use near-black backgrounds (`#121212`–`#1f1f1f`) — depth through shade variation
- Apply Spotify Green (`#1ed760`) only for play controls, active states, and primary CTAs
- Use pill shape (500px–9999px) for all buttons — circular (50%) for play controls
- Apply uppercase + wide letter-spacing (1.4px–2px) on button labels
- Keep typography compact (10px–24px range) — this is an app, not a magazine
- Use heavy shadows (`0.3–0.5 opacity`) for elevated elements on dark backgrounds
- Let album art provide color — the UI itself is achromatic

### Don't
- Don't use Spotify Green decoratively or on backgrounds — it's functional only
- Don't use light backgrounds for primary surfaces — the dark immersion is core
- Don't skip the pill/circle geometry on buttons — square buttons break the identity
- Don't use thin/subtle shadows — on dark backgrounds, shadows need to be heavy to be visible
- Don't add additional brand colors — green + achromatic grays is the complete palette
- Don't use relaxed line-heights — Spotify's typography is compact and dense
- Don't expose raw gray borders — use shadow-based or inset borders instead

## 8. Responsive Behavior

> **NOT APPLICABLE TO VIDEO.** Delivery is one fixed 2048×1280 frame. There are
> no breakpoints, no hover states, no inputs, no sidebar and no clickable cards.
> Kept for reference if this system is ever used for a web property.

### Breakpoints
| Name | Width | Key Changes |
|------|-------|-------------|
| Mobile Small | <425px | Compact mobile layout |
| Mobile | 425–576px | Standard mobile |
| Tablet | 576–768px | 2-column grid |
| Tablet Large | 768–896px | Expanded layout |
| Desktop Small | 896–1024px | Sidebar visible |
| Desktop | 1024–1280px | Full desktop layout |
| Large Desktop | >1280px | Expanded grid |

### Collapsing Strategy
- Sidebar: full → collapsed → hidden
- Album grid: 5 columns → 3 → 2 → 1
- Now-playing bar: maintained at all sizes
- Search: pill input maintained, width adjusts
- Navigation: sidebar → bottom bar on mobile

## 9. Agent Prompt Guide

### Quick Color Reference
- Background: Near Black (`#121212`)
- Surface: Dark Card (`#181818`)
- Text: White (`#ffffff`)
- Secondary text: Silver (`#b3b3b3`)
- Accent: Spotify Green (`#1ed760`)
- Border: `#4d4d4d`
- Error: Negative Red (`#f3727f`)

### Example Component Prompts
- "Create a dark card: #181818 background, 8px radius. Title at 16px SpotifyMixUI weight 700, white text. Subtitle at 14px weight 400, #b3b3b3. Shadow rgba(0,0,0,0.3) 0px 8px 8px on hover."
- "Design a pill button: #1f1f1f background, white text, 9999px radius, 8px 16px padding. 14px SpotifyMixUI weight 700, uppercase, letter-spacing 1.4px."
- "Build a circular play button: Spotify Green (#1ed760) background, #000000 icon, 50% radius, 12px padding."
- "Create search input: #1f1f1f background, white text, 500px radius, 12px 48px padding. Inset border: rgb(124,124,124) 0px 0px 0px 1px inset."
- "Design navigation sidebar: #121212 background. Active items: 14px weight 700, white. Inactive: 14px weight 400, #b3b3b3."

### Iteration Guide
1. Start with #121212 — everything lives in near-black darkness
2. Spotify Green for functional highlights only (play, active, CTA)
3. Pill everything — 500px for large, 9999px for small, 50% for circular
4. Uppercase + wide tracking on buttons — the systematic label voice
5. Heavy shadows (0.3–0.5 opacity) for elevation — light shadows are invisible on dark
6. Album art provides all the color — the UI stays achromatic

---

## 10. Video Adaptation — 2048×1280 delivery

Sections 1–7 carry the identity. This section makes it work in a moving 8:5 frame
watched from across a room, which is not what a web UI is designed for. **Where
this section and section 3 disagree on a number, this one wins.**

### 10.1 What changes from web, and why

| web assumption | video reality |
|---|---|
| 10–24 px type, read at arm's length | **28–140 px**, read at distance on a phone or TV. A 14 px caption is illegible. |
| Backgrounds are yours to control | Text sits over **arbitrary footage** — a face, a terminal, a diagram. Contrast is never guaranteed. |
| Hover reveals meaning | Nothing is interactive. Everything must read in the ~2 s it is on screen. |
| Layout reflows | One fixed frame. Nothing reflows, nothing collapses. |
| Centre of the viewport is prime space | **Centre is the speaker's face.** It is the worst place for text, not the best. |

The *ratios* and *principles* from section 3 transfer intact — the 700/400 weight
binary, the compact range, uppercase wide-tracked labels. The absolute pixel sizes
do not; multiply by roughly 3–4×.

### 10.2 Type scale (video)

Fira Code throughout for display; `CODE_FONT` for code blocks.

| role | size | weight | tracking | transform | use |
|---|---|---|---|---|---|
| Hook title | 96 | 700 | normal | — | the opening's own type; may sit at centre (10.5) |
| Stamp | 140 | 700 | 0.05em | uppercase | top-banner concept label |
| Punch | 56 | 700 | normal | — | lower-third emphasised line |
| Caption | 52 | 700 | normal | — | bottom-band spoken words |
| Emoji | 120 | — | — | — | burst glyph |
| Terminal | 28 | 400 | 0.02em | — | boot/terminal list, mono |
| Tag | 20 | 700 | 0.1em | uppercase | lower-third name tag |
| Status value | 15 | 600 | 0.5px | — | status bar reading |
| Status label | 14 | 400 | normal | — | status bar caption, HUD meter readout |
| HUD title | 32 | 700 | normal | — | what the HUD band names |
| HUD label | 16 | 700 | 0.125em | uppercase | the HUD's kicker above the title |
| HUD banner | 24 | 700 | 0.08em | — | a HUD flash mark's one line |
| HUD note | 14 | 400 | normal | — | a HUD note mark's label |
| HUD glyph | 28 | — | — | — | a HUD mark's glyph |
| Card title | 56 | 700 | normal | — | column / list heading on a graphics beat |
| Card body | 28 | 400 | normal | — | column / list line |

Nothing below **14 px** ever ships: at 2048 wide that is under 1% of frame height
and vanishes on a phone.

### 10.3 Legibility over footage — the rule web does not need

Every piece of on-screen text carries **one** of these, always:

- a **scrim** — a gradient from `scrim` at the frame edge to transparent, sized to
  the text band: 28% height bottom (captions), 32% top (stamps), 42% top (terminal),
  46% width from either side (flanking text, 10.4); or
- a **heavy text shadow** — `0 4px 20px rgba(0,0,0,0.95), 0 2px 8px rgba(0,0,0,0.8)`.

This is section 6's shadow philosophy doing a second job: on dark *and* over
unpredictable footage, shadows must be heavy to exist at all. An accent-coloured
glow (`0 0 40px <accent>66`) may be added for emphasis but never replaces the
black shadow underneath — coloured glow over bright footage reads as blur.

### 10.4 Spatial zones

The frame is divided so layers cannot collide. Values in px from the named edge.

| zone | position | occupant |
|---|---|---|
| Top banner | 15% from top | stamps |
| Top-left | 80, 80 | terminal list |
| HUD band | 80 from top and both sides, ~130 tall | HUD kicker, title, meter |
| HUD marks | 260 from top-right / 140 from bottom-left / 78% banner | the HUD's timed annotations |
| Upper-right | 22% top, 80% left | emoji burst |
| **Centre** | — | **the speaker. Reserved. See 10.5** |
| Flank left / right | 80 from side, max-width 620 | text beside a speaker (hook only) |
| Lower third | 150 from bottom | punch lines |
| Bottom band | 96 from bottom, max-width 1240 | captions |
| Bottom-left | 80, 48 | name tag |
| Bottom bar | 56 tall, full width | status bar |
| Corner inset | top 232 / bottom 104, 48 from side | meme overlay |
| Safe inset | 48 | nothing closer to any edge |

Caption max-width is **1240 of 2048, not 1600** — a full-width line collided with
the corner inset.

**The HUD band and the top banner are mutually exclusive.** They are the only
two layers that both claim the top of the frame — a 140px stamp sits at 15%
(~192px) while the HUD band runs y=80..210 — and rendered together the meter
draws straight through the stamp's letters. Neither is moved, because both want
the same thing: the top of the frame, uncontested. A beat that seems to need
both is really two beats. `check_hud_stamp_collision()` fails the build.

The **corner inset** is derived, not chosen: its top of 232 clears the HUD band
and its bottom of 104 clears the status bar. That is the one place two zones are
coupled, so moving the HUD band moves this number with it. Both live as tokens
side by side for exactly that reason.

The **flank** zones are the only per-take numbers in this table. 620px each side
clears a subject occupying the middle quarter of the frame; measure where yours
actually sits and re-tune both the column width and the scrim, rather than
assuming. They exist only so the hook can obey 10.5 — see there.

### 10.5 The centre rule

**Nothing is placed at frame centre while a speaker is on screen.** A kinetic-text
layer that popped the narrator's own words dead-centre was deleted for landing on
their face in every shot.

Horizontally centred is not the same as *at frame centre*. The HUD's banner mark
is centred left-to-right but sits at 78% height, well down in the lower band, and
is fine — it was moved there after an earlier version landed on the narrator's
face. The rule is about the **middle of the frame**, where a face is, not about
the horizontal axis.

The one exception is a beat with **no speaker** — a title card, a chart, a pure
motion-graphics hook. There the centre is the only sensible place for a title, and
`plans/hook.md` records the suspension explicitly.

When a speaker *is* on screen and the beat still needs large type, the answer is
to **flank** them (10.4), not to shrink the type or fade it back. Words in a
column beside a face read at full size and never cross it; words at 40% opacity
over a face are simply unreadable text on top of a person.

### 10.6 Motion

Frame counts at 30 fps. Read `fps` from `useVideoConfig()`; never hardcode 30.

| event | frames |
|---|---|
| Word stagger (captions, punch) | 3 |
| Line stagger (terminal, build list) | 8 |
| Glyph pop stagger (HUD marks) | 6 |
| Fade in | 8 |
| Fade out | 10 |
| Overlay entrance / exit | 6 |
| Stamp exit ramp | 10 |
| Minimum text lifetime | **60** (2 s — see 10.8) |
| Minimum shot | **45** (1.5 s) |
| Beat after a punchline | 10 |

Every `interpolate` is **clamped** at both ends. An unclamped one drifts the
element off frame in exactly the frames nobody previews.

**An exit ramp is anchored to the END of the window the layer is given, never to
a fixed frame number.** A ramp written as "fade out over frames 25→35" is a
silent bet that every caller grants at least 35 frames; the stamp layer lost that
bet against a 30-frame sequence and was hard-cut halfway through its own fade, in
both compositions, for the life of a video. The ramp is a *length*; the component
derives its position from its `durationInFrames` prop. Two files disagreeing about
how long a layer lives is the bug, not the number.

Section 4's pill-and-circle geometry survives as the still-frame vocabulary
(insets, tags, bars); it is not animated as a button press, because nothing here
is pressed.

### 10.7 Colour in motion

- **The accent stays functional.** In a video that means it marks state — success,
  a component under discussion, a progress reading. It is never a decorative
  flourish and never a background fill.
- **The footage is the album art.** Section 1's "content-first darkness" maps
  exactly: screencasts, code and diagrams supply the colour; the UI around them
  stays achromatic so they can be read.
- **Never scale or tint one of *our* sources.** A screencast, a code clip or a
  talking-head take is authored at the delivery frame; rescaling it softens
  monospace glyphs and grading it changes what the viewer is being shown. This
  is the rule; the two paragraphs below are its only carve-outs, and both exist
  because the premise "every asset is already 2048×1280" is not always true.

**Capture oversized so a move costs nothing.** Record screencasts at **3072×1920**
— exactly 1.5× the delivery frame, same 8:5 ratio. A 2048×1280 crop out of that is
a 1:1 pixel window, so a focus pan or punch-in up to **1.5×** resamples nothing and
this rule is *honoured* rather than suspended. The build enforces the ceiling and
warns when a source is too small to sustain the move. A take captured at native
2048×1280 has no such headroom: punches there are true upscales, so cap them at
**1.2×**, ration them to emphasis lines, and get your rhythm from cutaways instead.

**Third-party archival footage is the exception, and it is framed, not stretched.**
A 320×240 VHS capture never was 2048×1280 and cannot be; filling the frame with it
distorts the picture, which is a *wrong image*, not a styling choice. So archival
footage sits **inset on the page background at its native aspect** — one treatment
for every era, nothing cropped away — and it is the one source that may be graded
(vignette, grain, contrast, saturation), per beat, because there the grade carries
the era rather than hiding a defect. The rule above protects our own screencasts'
sharpness; a VHS capture of a CRT has no sharpness to protect. A body screencast
must never use this path.

### 10.9 Code highlighting

Code is the one place this system needs more than one hue. Section 7 says green +
achromatic grays is the complete palette, and for UI that holds — but a snippet
highlighted in a single colour is unreadable, and reading real source is a large
part of what these videos do.

So the syntax theme is drawn **only from colours section 2 already declares** —
no new hues are invented:

| token | colour | why |
|---|---|---|
| keyword | Spotify Green `#1ed760` | the accent's functional job here is structure |
| string | Announcement Blue `#539df5` | already declared, reads as data |
| number / constant | Warning Orange `#ffa42b` | already declared |
| type / class | White `#ffffff` | max emphasis, achromatic |
| function | Near White `#cbcbcb` | one step below a type |
| operator / punctuation | Silver `#b3b3b3` | structural, recedes |
| comment | Light Border `#7c7c7c` | recedes furthest, still legible |
| error | Negative Red `#f3727f` | already declared |

Background is Dark Surface `#181818`, one step up from the page, so a code block
reads as an elevated surface (section 6, level 1).

**Colour only — never italic or bold.** Manim's `Code` miscounts glyphs when a
pygments style applies a font style and dies with `IndexError` in `_gen_chars`.

### 10.8 Reading time

Text must survive its own duration, not just appear.

- On-screen text: minimum **2 s**, and never before its words are spoken
  (`check_not_early()` fails the build).
- Code: **2.5 s + 0.3 s per line.** 27 lines of Rust wants ~12 s, not 3.

---

## 11. Where this lands in code

Two files, and nowhere else. Both are hand-authored translations of this
document — **not generated from it**.

| file | owns |
|---|---|
| `.remotion/src/design.ts` | colour roles, the 10.2 type scale, spacing, radii, elevation, the 10.4 zones, the 10.6 motion counts, the 10.7 archive card and grade |
| `.manim/scenes/design.py` | the same roles for Manim, the `GAP_*` spacing scale in scene units, layout regions, the code-highlighting theme |

Rules:

1. **A component or scene never names a colour or a size directly.** It imports a
   token. `scripts/check_design.py` fails the build on a raw hex or a bare font
   size — in the components, the scenes, **and the per-video editorial plans**
   (`scripts/build_timeline_manifest.py`, `scripts/build_hook_manifest.py`),
   which is where colours actually get chosen episode to episode. The plan writes
   ROLE NAMES (`accent`, `warning`), never hex codes, and omits sizes entirely so
   the component uses its token.
2. **Changing this document means editing those two files**, then re-rendering.
   That is the whole update path; there is no third place to look.
3. Manim works in **scene units**, not pixels: at 1280 px tall and a frame height
   of 8.0 units, `units = px / 160`. `design.py` does that conversion so the two
   engines stay dimensionally in step.
