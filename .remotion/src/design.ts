/**
 * The Remotion half of DESIGN.md.
 *
 * HAND-AUTHORED, NOT GENERATED. DESIGN.md is prose because a design system is
 * judgement -- "the accent is functional, never decorative", "thin shadows are
 * invisible on dark" -- and none of that survives a token extractor. This file
 * is what an agent writes after READING DESIGN.md.
 *
 * Every colour and every size in the composition comes from here. No component
 * names a hex or a font size directly; scripts/check_design.py fails the build
 * if one does. Change DESIGN.md -> change this file (and .manim/scenes/design.py)
 * -> re-render. There is no third place to look.
 *
 * Section numbers below refer to DESIGN.md.
 */

// ── Palette (DESIGN.md section 2) ───────────────────────────────────────
// Raw values, named as the design system names them. Components should use
// ROLE, not this -- these exist so a role can be re-pointed in one line.
export const PALETTE = {
  // Near-black surfaces: depth through shade, not through colour.
  nearBlack: '#121212',
  darkSurface: '#181818',
  midDark: '#1f1f1f',
  darkCard: '#252525',
  midCard: '#272727',

  // The single brand accent. Functional only (section 7, section 10.7).
  green: '#1ed760',
  greenBorder: '#1db954',

  // Text
  white: '#ffffff',
  silver: '#b3b3b3',
  nearWhite: '#cbcbcb',
  light: '#fdfdfd',

  // Semantic
  negativeRed: '#f3727f',
  warningOrange: '#ffa42b',
  announcementBlue: '#539df5',

  // Structure
  borderGray: '#4d4d4d',
  lightBorder: '#7c7c7c',
  black: '#000000',
} as const;

/**
 * Semantic roles. THIS is what components use.
 *
 * A role says what a colour is FOR, so re-theming is re-pointing these and
 * nothing else. `accent` is deliberately the only non-achromatic role in
 * normal use -- the footage supplies the colour (section 10.7).
 */
export const ROLE = {
  bg: PALETTE.nearBlack,
  surface: PALETTE.darkSurface,
  surfaceAlt: PALETTE.midDark,
  elevated: PALETTE.darkCard,
  border: PALETTE.borderGray,
  borderMuted: PALETTE.lightBorder,

  text: PALETTE.white,
  textMuted: PALETTE.silver,
  textFaint: PALETTE.lightBorder,

  accent: PALETTE.green,
  accentBorder: PALETTE.greenBorder,

  success: PALETTE.green,
  warning: PALETTE.warningOrange,
  error: PALETTE.negativeRed,
  info: PALETTE.announcementBlue,

  // Scrims and shadows are pure black, not a tinted dark: over arbitrary
  // footage a tinted scrim shifts the footage's own colour.
  scrim: PALETTE.black,
} as const;

export type RoleName = keyof typeof ROLE;

/**
 * Resolve a manifest colour value to a hex.
 *
 * The editorial plan writes role names ('accent', 'warning'), so the plan stays
 * readable and re-themes with the design system. A raw hex still passes through,
 * for the rare one-off -- but check_design.py flags raw hexes in the manifest
 * builder too, so prefer a role.
 */
export function resolveColor(name: string | undefined): string {
  if (!name) return ROLE.text;
  if (name in ROLE) return ROLE[name as RoleName];
  if (name in PALETTE) return PALETTE[name as keyof typeof PALETTE];
  if (/^#[0-9a-fA-F]{3,8}$/.test(name)) return name;
  return ROLE.text;
}

// ── Type (DESIGN.md section 10.2, which overrides section 3's web sizes) ─
// Fira Code for display; CODE_FONT-equivalent mono for code. SpotifyMixUI /
// CircularSp are commercial Lineto faces and are not available here.
export const FONT_DISPLAY = 'Fira Code, Noto Sans, monospace';
export const FONT_CODE = 'Fira Mono, DejaVu Sans Mono, monospace';

/**
 * The type SCALE. Section 3's principle is a narrow, systematic range -- the
 * composition had accumulated fifteen ad-hoc sizes (14, 15, 16, 18, 20, 22, 24,
 * 28, 32, 52, 54, 56, 96, 120, 140), which is not a system. Consolidated onto
 * these eleven steps; 15 snapped to xs, 18 to sm, 22 to base, 54 to hero.
 */
export const SIZE = {
  xs: 14, sm: 16, base: 20, md: 24, lg: 28, xl: 32,
  xxl: 52, hero: 56, giant: 96, emoji: 120, stamp: 140,
} as const;

/** Section 3's weight binary: 700 or 400, with 600 used sparingly. */
export const WEIGHT = {regular: 400, semibold: 600, bold: 700} as const;

export type TypeSpec = {
  size: number;
  weight: number;
  tracking?: string;
  transform?: 'uppercase' | 'capitalize' | 'none';
  leading?: number;
};

/**
 * The 700/400 weight binary from section 3 survives; the sizes are ~3-4x their
 * web equivalents because this is read at distance (section 10.1). Nothing
 * below 14 ships.
 */
export const TYPE: Record<string, TypeSpec> = {
  hookTitle: {size: SIZE.giant, weight: WEIGHT.bold, leading: 1.2},
  stamp: {size: SIZE.stamp, weight: WEIGHT.bold, tracking: '0.05em', transform: 'uppercase'},
  punch: {size: SIZE.hero, weight: WEIGHT.bold},
  caption: {size: SIZE.xxl, weight: WEIGHT.bold},
  emoji: {size: SIZE.emoji, weight: WEIGHT.regular},
  terminal: {size: SIZE.lg, weight: WEIGHT.regular, tracking: '0.02em'},
  tag: {size: SIZE.base, weight: WEIGHT.bold, tracking: '0.1em', transform: 'uppercase'},
  statusValue: {size: SIZE.xs, weight: WEIGHT.semibold, tracking: '0.5px'},
  statusLabel: {size: SIZE.xs, weight: WEIGHT.regular},
  hudTitle: {size: SIZE.xl, weight: WEIGHT.bold},
  hudLabel: {size: SIZE.sm, weight: WEIGHT.bold, tracking: '0.125em', transform: 'uppercase'},
  hudBanner: {size: SIZE.md, weight: WEIGHT.bold, tracking: '0.08em'},
  hudNote: {size: SIZE.xs, weight: WEIGHT.regular},
  hudGlyph: {size: SIZE.lg, weight: WEIGHT.regular},
  cardTitle: {size: SIZE.hero, weight: WEIGHT.bold},
  cardBody: {size: SIZE.lg, weight: WEIGHT.regular},
};

// ── Space, radius (sections 5, 10.4) ───────────────────────────────────
// 8px base unit, as section 5.
export const SPACE = {
  xs: 4, sm: 8, md: 16, lg: 24, xl: 40, xxl: 64,
} as const;

// Pill-and-circle geometry (section 4) as still-frame vocabulary.
export const RADIUS = {
  sm: 4, md: 8, lg: 16, pill: 500, circle: '50%',
} as const;

// ── Elevation (sections 6, 10.3) ───────────────────────────────────────
/**
 * Heavy by design. On a near-black ground a subtle shadow does not exist, and
 * over unpredictable footage it has to do a second job -- separating text from
 * whatever is behind it.
 */
export const SHADOW = {
  card: '0 8px 8px rgba(0,0,0,0.3)',
  dialog: '0 8px 24px rgba(0,0,0,0.5)',
  inset: `inset 0 0 0 1px ${PALETTE.lightBorder}`,
  // Text over footage. Never omitted, never replaced by a coloured glow alone.
  text: '0 4px 20px rgba(0,0,0,0.95), 0 2px 8px rgba(0,0,0,0.8)',
  textHeavy: '0 8px 40px rgba(0,0,0,0.9), 0 4px 16px rgba(0,0,0,0.7)',
  // Softer, for text on a card of our own making rather than over footage --
  // an end card controls its own background, so it needs less separation.
  textSoft: '0 2px 12px rgba(0,0,0,0.6)',
} as const;

/** Accent glow for emphasis. Always layered OVER SHADOW.text, never instead. */
export function glow(hex: string, spread = 40, alpha = '66'): string {
  return `0 0 ${spread}px ${hex}${alpha}`;
}

/**
 * A scrim gradient from one edge, sized to the text band it protects.
 *
 * left/right exist for the hook's FLANKING text, which sits beside a speaker
 * rather than above or below them. A bright wall behind flanking type defeats
 * a shadow on its own, and §10.3 is not suspendable.
 */
export function scrim(
  edge: 'top' | 'bottom' | 'left' | 'right',
  opacityHex = 'bb',
): string {
  const deg =
    edge === 'bottom' ? '0deg'
    : edge === 'top' ? '180deg'
    : edge === 'left' ? '90deg'
    : '270deg';
  return `linear-gradient(${deg}, ${ROLE.scrim}${opacityHex} 0%, ${ROLE.scrim}00 100%)`;
}

// ── Zones (DESIGN.md section 10.4) ─────────────────────────────────────
/**
 * Where each layer lives. These are tuned values, not arbitrary: the caption
 * max-width is 1240 of 2048 rather than 1600 because a full-width line collided
 * with the corner inset, and the inset's own top of 232 clears the HUD band
 * (hudTop + hudBandHeight) while its bottom clears the status bar.
 *
 * CENTRE IS ABSENT ON PURPOSE. It is the speaker's face (section 10.5).
 */
export const ZONE = {
  safeInset: 48,

  captionBottom: 96,
  captionMaxWidth: 1240,
  captionPadX: 40,
  scrimBottomHeight: '28%',

  punchBottom: 150,
  punchMaxWidth: 1400,
  punchPadX: 60,

  stampTop: '15%',
  scrimTopHeight: '32%',

  emojiTop: '22%',
  emojiLeft: '80%',

  tagBottom: 80,
  tagLeft: 48,

  barHeight: 56,
  barPadX: 24,
  barGap: 20,

  // The HUD band and its timed marks. hudBandHeight is what insetTop below is
  // derived from -- the two are coupled, which is why they sit together.
  hudTop: 80,
  hudPadX: 80,
  hudBandHeight: 130,
  hudMeterHeight: 20,
  hudMarkTop: 260,
  hudMarkRight: 120,
  hudMarkBottom: 140,
  hudMarkLeft: 120,
  hudBannerTop: '78%',

  terminalTop: 80,
  terminalLeft: 80,
  scrimTerminalHeight: '42%',

  insetTop: 232, // 80 hud top + 130 band + 22 clear
  insetBottom: 104, // 48 clear + 56 status bar
  insetMargin: 48,

  hookTitlePadTop: '12%',

  // Flanking text (DESIGN.md 10.4): beside the speaker, never over them, so a
  // hook beat can carry large type without breaking 10.5. The only per-take
  // numbers in the zone table -- measure where the subject actually sits and
  // re-tune the column and the scrim together.
  flankPadX: 80,
  flankMaxWidth: 620,
  scrimFlankWidth: '46%',
} as const;

// ── Motion (DESIGN.md section 10.6) ────────────────────────────────────
/** Frame counts at 30 fps. Read fps from useVideoConfig(); never hardcode it. */
export const MOTION = {
  wordStagger: 3,
  lineStagger: 8,
  glyphStagger: 6,
  fadeIn: 8,
  fadeOut: 10,
  entrance: 6,
  exit: 6,
  // A LENGTH, not a pair of frame numbers: the component anchors the ramp to
  // the end of the window it is given (10.6).
  stampExit: 10,
  minShotFrames: 45,
  beatAfterPunch: 10,
  /**
   * Section 10.8: on-screen text must survive 2 s, not merely appear. A
   * layer's lifetime is a design value, so it lives here and not in whichever
   * composition happened to schedule it.
   */
  minTextFrames: 60,
} as const;

// ── Delivery ───────────────────────────────────────────────────────────
export const VIDEO = {width: 2048, height: 1280, fps: 30} as const;

// ── Archival framing & grade (DESIGN.md section 10.7) ──────────────────
/**
 * THE ARCHIVE CARD -- 10.7's carve-out for third-party archival footage.
 *
 * Such a source never was 2048x1280 and cannot be, so it is inset on the page
 * background at its NATIVE aspect: one treatment for every era, nothing
 * cropped, nothing stretched. A body screencast must never use this -- it is
 * 2048x1280 already and belongs edge to edge.
 */
export const ARCHIVE = {
  // Margin as a fraction of frame width/height. 0 renders edge to edge.
  inset: 0.07,
  radius: RADIUS.md,
  borderWidth: 1,
  borderColor: ROLE.border,
  shadow: SHADOW.dialog,
} as const;

/**
 * Per-beat grade for archival footage only (10.7). Graded per beat rather than
 * uniformly, because the grade carries the era -- the further back, the
 * heavier -- and modern footage takes none at all.
 *
 * `grain` is a 64x64 tiling noise texture rather than an SVG feTurbulence
 * filter -- turbulence at 2048x1280 is recomputed per frame and is far too
 * slow. The tile is offset by frame number so the grain MOVES; a static
 * grain reads as a dirty lens, not as film.
 */
export const GRADE = {
  vignetteColor: 'rgba(0,0,0,1)',
  // Radial stops: transparent to opaque black, sized by the beat's strength.
  vignetteInner: '38%',
  vignetteOuter: '100%',
  darkenColor: 'rgba(0,0,0,1)',
  grainTile: 64,
  grainTexture:
    'url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAAAAACPAi4CAAAQS0lEQVR42gFAEL/vALr9rZxuxSR8jRlYOMyjY1/GS7a+gILs0LnyYKdM3q8r0TDJVEMZ+KFpyZMIXZ7VOO1sOvqLYT5sDbhwYxXl2VUA/3Y/FNOFIikOnWQyuNwZbExh2J9xG7sWBUCCcdI0MLu/PoybG6eCk6LfXdRG3uTGMEKdjjZLzwaxCi4hJRuGaQAoxK2nk4jtr7zglGpuNbBLeydtpLYxNACsd19AAWUdPFI1DhPemfUJA7wDGS0ruli9YnOUutaFKYd9a52OIoRpANoVIIceS2PviDTpVWDiBOnTMwtNlfMZ5PlFyaZWOQUbAj8NmAvpzjhKbDD3BCEhaP8toAXJNEElIXb1lYVXY8cAA4zt8AVhbcMtSwCuPghx1pqeoCivIUDrumF6C3aRIKPaom3+V0SlAYQ3Q2BWlibMbKj5sCYzC8BtDnSxqJc3zgAsnsG0X0I5Pcz0iGGYnlD5YUZnrzvbkwxrNnaPS3h6p95OyYt7EMjp4zLcp4lbkr9pCefe3r+xDFPOD6jXU/DHANEMBp0ydBk8socIlwxvqQu1GcSD40/WrINkkXozCtPy/+R8wGNeR+f5EZ1BiIyO+JTdQffUrWLE1oaNocXYxekAjv/DiGRedPeoBUqt/Ffm7GjrLK+/nwumyq/LkZxKJojh6BV6MLKR5Y28OOHKctcdHYvJ59d7A/ttgDXbv5p10gBxzO4GnvBS4M7Fdi+wO6GYDVjfmhbW142DU5otCqqKz4CXYk0A+uFHO25p3fzkwkKfH+C43+w+K0nQXLZ91SlBACBkjKOi1zymNHD9OSqlLB6Qip/1EHOBNlE7Jc/PqVlYH5yifi2A0j6pkxT9w7zkqovkBa26cY7fbhXb4oCtLEYACFRuqQkwvg6xm6JzLsR4CprC/CUhjOrJabADPc6LUaFAoAOfFbTt6UMmZkLyz3RyDSWfo4KR4UPtZGhqYel9lAAtEJNQd+lXIZ7fNaTtZRS0+lAmmvBdpX1W17SDmv71C8FnDohreIdhpm99Pevw85UjWGOKv86L5QO8HcuwwkXaAC0Saa4rC0xa7rtb0DtRLr75A0hAa2vHYtLCtMpqZxmXuYB2VHhZPkYn3OdmWedHtBB2erQrForici783nEG+NAAqxNr+mOoMaT+BuI3SfJEngG3dzlvFxPXRXBmrodPxfU5iRlWFeSI7F/s6xGnktf474iZVXh9hm8mz8qmm74pywCNVNW8n9qWaEcW88wHgXO4CNidXYCTzaWtrJVE5SxLjwjiYYlchK+BVO/O4s8iLthhlox7VbEZb7sC53L31d/sAL8aMdeag6m/jVzRKkq74PNS2JPZ9RLtpqTnOvtdWtuPuCtSNrj7V8QMjckvyuCRKZeLfpustfZpn5v+Y9pZ6kIA7FyodNI444DMThSEdAgYvrAxJ2T85N2ot3SJVwOB8vez0sNeuRpdk/tprfPmWiwY/fpo4zwpQy8Ls4UlJ7llQgB1QMjdG3lB1biTqAqBl0KdjCgYz+bWxct4f/c+g0rozsX6esYO7yIP7bspelvC7I8O9fkpsno3h+QxeS0rbC1XAPsfhLU2P0/IgQVB72YTsj367GdZ/jTfj83nHlmV5EWygpINx+EqImONIvUzT8LwXlK+Is8E3jRH4rJmTG7TkoEAkNJOPnksSN08gwJ8HwWYhjPiwytczj6pt7HQDEvr2f3VK9OyiFsORQltE2YtKWPSWkD2CxNjBd240cLav/bUzACq5zUjhN58jTIGA8aSGEV5TbPe2Sy0VJc3csX/7s1airBZKDjdI7FR+Ebs447y+w8n0RCmHhs1s/GvSrqHboJNAGPay1QEO530C61wmdGfhFFnvjT8ZMoK8Jc9ltxmwJyOTDM0dINys8AU2fRGmE9lLxSH5VGlahhc/LyidgNJeOcAOZadl4o8Q91orn8PBb+CjUua3Mv23GXE1KdEJyE4s1TUwbgvyT0n9TzD+Kzr711AOOVyhOe80siOJG18wvuQdQDHmQ5JMRdgpUC6qCrLm0cuBEpng9LuqO87zJJUncdsRVfBvISUNzaWDaeTD27aeAnBMGnTh6UysqAtODV6Rn68ANjmbWv5k+u57DYuXYFs4mluTu7e/8g6fuOjImtU2ayX8sSIw+5AA87TNrX+OqdZJdgnKujleFwy2167YjQt2VEA2jwh4AlEAtewRFnCZoNp1e2ulgRgOZFizTXNYrrJAT6D73BuwptUA4jsipOID6ZZ/Ye+kXIjI4vrVvy9jTlaogB1l5IKd1h7G+jiJl6Qb1kJBPs4n3KXpn5nMKlNwXavAQNuWGSmzWiORWWXrmAsyb3TPl4EW48dK1JNQXTEYIG/AOsgoxuVbXQZkCGqcLQlz/YysykYeUXViNhrYPgizc68KFxY449E0P7TBRs2WYwq6ViAFqTOERGof11iZVL8xx0AWGbXrewBBInNUHP4YTTddwytaI08Msh2GyOKRdJGOSrPtumENyuO7mRxqkOEcoD2xT3s2382CeIjto2e1pFZ6wDXc5EYkk00e4pUA/i3xelVJqb+kR2DlXmXuigdweXoAhaJv1855xF4JocJ16XoGxrcJ7eoaIZyIMT+UX3fne9wAF4wEVgUeAQdfeHufcVPa0jpeHUw3ND/3Q34OIS5zYcGoXyvH3KD5ogzwSOWRx6Zn5iIbOrGiw+zx/MpPBuKVpIADAMnydkqbVnEYEUeF3Nwn9iR1EYYEJG1BQqjgZzNYuiTmDaS/EkUglRIS7lFd/UO2Ka0vBn1C4yeY3yJMqpb8wBhydtNnc4USTJpdV+KmsQK2+ezZG3pZU6UB5IHvU1bz+fFeGIvjY3rP8RFlLdWEwfugIeRSoOAwFFIBAh6XteQACClgfz8TpO+d045oZ+K1yp8QVog+x/YI8U7KzgyKYc+nuqnASk6cFRFS06aXTen0YUTxh/fevbY8YH5oYXlJo0AfOZGO+v8Y3JHe0sisWX/9U6BS2jJ3WOMc/QDfuK4glL4K+6sh2Gxav59tzliyc/tpxGMeowN/jYb7WlHN/UObACE7tYb7Vp+RwccPKdh8QO0NO8w/PYEykP1si6TdlitXha/DcTxTQTua51FyAnGnW/UMnaCnnYKQbSvME4/4jPcAEYpTZ4WF3PEWTlCVK2lHhxnJlaSbqcUDi5HmrySuYXHZyb2y+0EHlxlEDjgalW6FWesEs5jUftWwkTZW2YA0eYAclN2eJOYJQd3knFGwcjW3Wm0Y3DTMMRKmDoeCZH+4cbtnNFfhZcSdLMh1pwde1tDHDsKIyZGi3B1I3dum4/qXACOSaUQK/v7+x+fvCqsCTVk71683aQtdEnJ2onzc1T/vTXwY/VdxhEoBbtCt0DIvAZE14jRCBIeJrKnG6SCIXK1AIyoLE2VrgXOiMF4JTqiY9Bz3jGcdj1wbWfwB5p4vYnYLHUQ2LUlFvWiEGLwdcUO+Oyg5AgT+5C+LENGykyjhKUAeDMKAiBeGtOIdk1fkGnNU7ADSIL3gPzqdV1KUHk+YDvI8HoS08Bjes6295VVIBZWM+dUQAuW33K3WCFASbMQ3wD2kJ8otlT0K/qix4LIJrk8n1MNILpz4f0QmCJnGKA04C7c6GyZpCzZhnYULP5nu1Bu2CLpckuLPCrJcqghI3H2AOxez9t2oKpHepAjOVD086sQHHFw1ens172cMCSnulm9uIH87wNEr7eAyxI/ybNaqOpmVGkcdiXXD8x9MZibAYQAHiwKm2OD9OJxxLFQor5VlqYNX3xFsGOFz3vZBO4zBtI8ze3ZnlXE41XNOEyezqF4f0rGZivj1E6Nh0Y3ZmGeDwD77r/pyfRJcyftuh5Rm0ICtyUzX0VVGDrbtlZNnvL0TV5jfBirONSR2NvUHj8CMJe5vwAzLziJd+zwgGhw5lSCAMcuVXdI+qClp8udXeCND14lFcCjPHJu4ybeR91c9mLMXTTcInmWKdqMu0zMwskbXC6Vsq11gCoNo/Ao1Vl+71kASPw0HZoN9Z+xcsAUGEDdqz1Ge/oc6R2TV9/O4d1C3K77s9sG3GVQB5svikYBi+qquRiwBrIc4LMm1DXMDLD32gDXnKlnI/WtQ0t6rJncfx9NwxstoEXcTOhHS0fQ32bVZH9rr1fbVkWAhTi4UMmG32PSeenSzwiUpxXNZ1P1hMA+APy5UZsEUNlfw+XA0K4FJcYc8C5h6wa2DzX5wdSR0MiVwHfgwRrTBCFcSax0mVmx27VpG1AVGJ8b3WvhXg9oKHsAhJh2qZmGCP4hd/Ci1/FTYnlN0ZJrQxbglkRJ+gPqodQQ3K255oxe2SvL2HmWpQKnuSo7RHki658f/WaD3EHzxAC4uWKUnYmB2UtQivYtEWidMaiul9QjBHPDjGsfZFExfNPpZw/uWUjWxBlBB33hPJpV0NGr8jWdd8hgH4uSTxjBALETxbVhIpnZUTjsa131Oy3bub1oJge0kxSbJgxHOoPe7bk92iOOGm9GmLXLrByHaEvGO3AWE0m4PB60AWVeU8QA76fZwONai/PhjXvQbMWTUquplydmXKbB6swJjk01GrvrtbHM//8jIAJznAjjY6xsA/9Z+FHhABF1BvdQUMWKJQCmXEl1MGFqHb0b4JafLTE8fDU9VJ7yDV1fdlDY1N8CaFazdJxPiRq5eoqoU+rjXNjz5wNTXMq8s25A90GFx+prAIwjsjoz66Lb+wiRA7VGoix0dMK7eguo2+fJ6/wP0G78txa+aUvnlkIkgVvPsjDUHV8p8bmMEM7P3UuS1Bejf9sAQR7YzgzRfrW/qaQP/Wn240KaUa5szpVC+TKLLF4l4uzeDqrXAkjzpApNqFESP8VJcGjv/C4JLVafpb15IlbwLwBBeksL+ij21++Sz97cI9xCkZDraAg/JYYn+1AdBnIdey5pGf1iX9YZWkPrudMjRjH4vQfEMFTj7L2kY1R5JiTpAG7PlJl6mPgHAplckM3vToWzH7v8S6tjkaUnAOB4rnBxdqZnCSacwp6iFxg4oVDO2I5WVySD0AVpmbgwBwhD1JsAupBGAjYVDgTyejwlEXq11yBJpuk5wxQ8+QNrry+fIVHBneJ4G6a3qcMfICLqOu/RIkJQTYdRdeVTE5Zg9/jrIAA0O2mc+wCILK3AWb/Z4NzxaJIyw5y8IuzyQG5t55Z2UaBiINHw4VaDARN3YM1aKG7pqId7sVASyy5TXJ1rXSJJAKF3l+qNijtuTcAsx8LmVmCegaO2rOWTra6c3DmHba0m6buOujFWyCGwGrbkf2X7qVHhx5PbAANK4XUvoH+wQMYA8MuLHEyJ+fJpoa1JD7wMt77YkGbGkOjYNMWdirYxB73+5aOfWA+oQ0h5T7WF4yAolrsQgBkjFOGjJOlgUZuV1AAe3Z0aTYPJ0G7ELsPOUvSSlAvFIdluaqRUMLv/ntMEFtj7nt0cYvsdE0eHMnSwXwOY42Ocj3WpJE77qCPqShSaAKEkN39rj5uRhI5/EJ2kPUjYMbMNJGzohg87Tf0g7vMWY6umN96dUtw0BS8/jyQrOynzgsKYk5XqapbE3AQSkwWrXwdT8+NRfAAAAABJRU5ErkJggg==")',
} as const;

/** A radial vignette at a given strength (0-1). Layered over the source. */
export function vignette(strength: number): string {
  return `radial-gradient(ellipse at center, transparent ${GRADE.vignetteInner}, rgba(0,0,0,${strength}) ${GRADE.vignetteOuter})`;
}
