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
  hudLabel: {size: SIZE.sm, weight: WEIGHT.bold},
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

/** A top or bottom scrim gradient, sized to the text band it protects. */
export function scrim(edge: 'top' | 'bottom', opacityHex = 'bb'): string {
  const deg = edge === 'bottom' ? '0deg' : '180deg';
  return `linear-gradient(${deg}, ${ROLE.scrim}${opacityHex} 0%, ${ROLE.scrim}00 100%)`;
}

// ── Zones (DESIGN.md section 10.4) ─────────────────────────────────────
/**
 * Where each layer lives. These are tuned values, not arbitrary: the caption
 * max-width is 1240 of 2048 rather than 1600 because a full-width line collided
 * with the corner inset, and the inset's own top of 232 clears the boss-frame
 * header while its bottom clears the status bar.
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

  terminalTop: 80,
  terminalLeft: 80,
  scrimTerminalHeight: '42%',

  insetTop: 232,
  insetBottom: 104, // 48 clear + 56 status bar
  insetMargin: 48,

  hookTitlePadTop: '12%',
} as const;

// ── Motion (DESIGN.md section 10.6) ────────────────────────────────────
/** Frame counts at 30 fps. Read fps from useVideoConfig(); never hardcode it. */
export const MOTION = {
  wordStagger: 3,
  lineStagger: 8,
  fadeIn: 8,
  fadeOut: 10,
  entrance: 6,
  exit: 6,
  stampExitFrom: 25,
  stampExitTo: 35,
  minShotFrames: 45,
  beatAfterPunch: 10,
} as const;

// ── Delivery ───────────────────────────────────────────────────────────
export const VIDEO = {width: 2048, height: 1280, fps: 30} as const;
