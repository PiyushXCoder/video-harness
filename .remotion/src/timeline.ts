import manifestJson from './timeline-data.json';

export type CutawayData = {
  src: string;
  fromFrame: number;
  durationInFrames: number;
  srcDurationInFrames: number;
  hold: boolean;
  holdOnly: boolean;
  muted: boolean;
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
  file: string;
  durationInFrames: number;
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
};

// Built by scripts/build_timeline_manifest.py -- edit the editorial plan
// there, not here. Re-run the script after any change to durations, cue
// timing, or which asset goes where.
export const manifest = manifestJson as TimelineManifest;
