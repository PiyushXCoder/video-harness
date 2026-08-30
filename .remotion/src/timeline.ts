import manifestJson from './timeline-data.json';

/**
 * A moving crop window over a source larger than the delivery frame.
 *
 * zoom is RELATIVE TO FIT: 1.0 fits the whole source in frame, 1.5 is a 1:1
 * pixel window of a 3072x1920 source against a 2048x1280 delivery. The build
 * refuses anything past 1.5, so a focus move never upscales and DESIGN.md
 * 10.7 holds. cx/cy are the source point (0-1) parked at frame centre.
 */
export type FocusData = {
  srcWidth: number;
  srcHeight: number;
  zoomFrom: number;
  zoomTo: number;
  cxFrom: number;
  cyFrom: number;
  cxTo: number;
  cyTo: number;
};

export type CutawayData = {
  src: string;
  fromFrame: number;
  durationInFrames: number;
  srcDurationInFrames: number;
  hold: boolean;
  holdOnly: boolean;
  muted: boolean;
  focus: FocusData | null;
  isImage: boolean;
  /** How the shot arrives. Scale is one option among several, not the default. */
  enter: 'none' | 'fade' | 'blur' | 'slide-up' | 'slide-left' | 'wipe';
  /** Era grade. Archive footage only -- 0/1 values emit no filter at all. */
  grade: {vignette: number; grain: number; contrast: number; saturate: number};
  /** Slow drift inside the card. Not a crop; distinct from `focus`. */
  drift: 'none' | 'left' | 'right' | 'in';
  // True whenever the source is not exactly the delivery frame. Decided from
  // the probed dimensions, not from a flag in the plan, so it cannot be
  // forgotten for one clip out of twenty.
  contain: boolean;
  srcWidth: number;
  srcHeight: number;
};

/** A slow scale on the talking head. Never applied to a cutaway. */
export type PunchData = {
  fromFrame: number;
  durationInFrames: number;
  from: number;
  to: number;
  originY: number;
};

/** Dims everything outside a rect. Directs the eye without moving the crop. */
export type SpotlightData = {
  fromFrame: number;
  durationInFrames: number;
  x: number;
  y: number;
  w: number;
  h: number;
  dim: number;
};

/** An accent rectangle plus a short label, anchored to part of the frame. */
export type CalloutData = {
  fromFrame: number;
  durationInFrames: number;
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  color: string;
  labelSide: 'above' | 'below';
};

export type BuildListData = {
  fromFrame: number;
  durationInFrames: number;
  items: string[];
  title: string;
  color: string;
  strike: boolean;
};

export type TwoColumnData = {
  fromFrame: number;
  durationInFrames: number;
  leftTitle: string;
  rightTitle: string;
  left: string[];
  right: string[];
  leftColor: string;
  rightColor: string;
};

/**
 * A music cue on the VIDEO's absolute timeline, deliberately not inside any
 * segment -- a bed placed in a segment is clipped by that segment's
 * <Series.Sequence>, so a 40s track under a 28s beat is silently truncated.
 */
export type BedData = {
  file: string;
  fromFrame: number;
  durationInFrames: number;
  startFromFrame: number;
  gain: number;
  fadeInFrames: number;
  fadeOutFrames: number;
};

export type OverlayData = {
  src: string;
  fromFrame: number;
  durationInFrames: number;
  srcDurationInFrames: number;
  srcWidth: number;
  srcHeight: number;
  corner: 'tl' | 'tr' | 'bl' | 'br';
  widthPct: number;
  transparent: boolean;
};

export type StampData = {
  text: string;
  fromFrame: number;
  color: string;
  // null/absent means "use the design token". The manifest builder does not
  // inject a default, so DESIGN.md stays the single source for the size.
  size?: number | null;
};

export type EmojiData = {
  emoji: string;
  fromFrame: number;
  color: string;
};

export type SfxData = {
  file: string;
  fromFrame: number;
  gain: number;
};

export type NameTagData = {
  name: string;
  fromFrame: number;
  durationInFrames: number;
};

export type BossFrameData = {
  fromFrame: number;
  durationInFrames: number;
  label: string;
  hpBar: boolean;
  // Frames are LOCAL to the boss frame's own window, each keyed to the cue
  // that actually speaks it. null means the element never shows.
  fastPeersFrame: number | null;
  slowPeerFrame: number | null;
  powerUpFrame: number | null;
  slowPeerLabel: string;
  powerUpLabel: string;
};

export type CueData = {
  fromFrame: number;
  durationInFrames: number;
  words: string[];
};

export type PunchTextData = {
  fromFrame: number;
  durationInFrames: number;
  words: string[];
  color: string;
  size?: number | null;
};

export type BootTerminalData = {
  fromFrame: number;
  durationInFrames: number;
  lines: string[];
};

export type SegmentData = {
  id: string;
  // null for a picture-only montage: the showcase has no narration take at
  // all, so its length comes from the plan and its picture from cutaways.
  file: string | null;
  durationInFrames: number;
  spotlights: SpotlightData[];
  callouts: CalloutData[];
  punches: PunchData[];
  vignette: number;
  captionPos: 'bottom' | 'flank';
  buildLists: BuildListData[];
  twoColumns: TwoColumnData[];
  cutaways: CutawayData[];
  overlays: OverlayData[];
  stamps: StampData[];
  emoji: EmojiData[];
  sfx: SfxData[];
  statusBar: string;
  nameTags: NameTagData[];
  bossFrame: BossFrameData | null;
  // Non-empty only for segments that opted into word-pop captions.
  cues: CueData[];
  // Lower-third punch lines. Several per segment; they are the main text
  // layer outside the hook (which uses captions instead).
  punchTexts: PunchTextData[];
  // Opening boot sequence, hook only.
  bootTerminal: BootTerminalData | null;
};

export type EndCardData = {
  progressLabel: string;
  headline: string;
  subline: string;
};

export type TimelineManifest = {
  fps: number;
  width: number;
  height: number;
  endCardFrames: number;
  // Per-video copy and counter -- the template hardcodes neither.
  endCard: EndCardData;
  progressUnit: {label: string; total: number} | null;
  totalDurationInFrames: number;
  segments: SegmentData[];
  beds: BedData[];
};

// Built by scripts/build_timeline_manifest.py -- edit the editorial plan
// there, not here. Re-run the script after any change to durations, cue
// timing, or which asset goes where.
export const manifest = manifestJson as TimelineManifest;
