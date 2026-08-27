import hookJson from './hook-data.json';

// The leaf LAYER types are shared with the main timeline on purpose: they are
// the prop contracts of components the hook reuses (Stamp, EmojiBurst,
// MemeOverlay, SubtitleCaptions, BootTerminal), so duplicating them here
// would let the two drift apart from the components they describe.
//
// These are `import type` -- erased at compile time -- so this module does
// NOT pull in timeline-data.json at runtime. That matters: the hook must be
// renderable without the main video's manifest existing.
//
// What is NOT shared is the STRUCTURE. A hook is a list of beats, not a list
// of narration segments, because a beat may have no video file and no
// transcript at all (see HookBeatData.source).
import type {
  OverlayData,
  StampData,
  EmojiData,
  SfxData,
  CueData,
  BootTerminalData,
} from './timeline';

export type {OverlayData, StampData, EmojiData, SfxData, CueData, BootTerminalData};

/**
 * Footage for a beat. Trim is expressed here rather than burned into the
 * file on disk, so re-planning a beat's in/out costs a re-run of the
 * manifest builder instead of a re-encode -- and the pauses in the take
 * survive, which is the whole point of the hook (see --no-cut in
 * scripts/process_recording.py).
 */
export type HookSourceData = {
  src: string;
  // Frames to skip at the head of the source.
  startFromFrame: number;
  // The source file's REAL probed length, so the builder can prove the
  // requested window actually fits inside it.
  srcDurationInFrames: number;
  // A beat whose audio is carried by a music bed or another beat is muted.
  muted: boolean;
};

export type HookCutawayData = {
  src: string;
  fromFrame: number;
  durationInFrames: number;
  srcDurationInFrames: number;
  holdOnly: boolean;
};

/**
 * Free-form text for the hook. Deliberately NOT the body's three-layer
 * model (captions / punchTexts / stamps in fixed zones): whether the hook
 * has a speaker on screen at all is the plan's call, so the plan also
 * chooses where text may sit. `anchor: 'center'` is legal here and illegal
 * in the body, where the centre is the speaker's face.
 */
export type HookTextData = {
  fromFrame: number;
  durationInFrames: number;
  words: string[];
  color: string;
  size: number;
  anchor: 'top' | 'center' | 'lower-third' | 'bottom';
};

export type HookBeatData = {
  id: string;
  durationInFrames: number;
  // null for a pure-graphics beat -- a title card, a chart, kinetic type.
  // This is why a hook cannot be a SegmentData: NarrationSegment renders
  // <OffthreadVideo src={staticFile(segment.file)}> unconditionally.
  source: HookSourceData | null;
  background: string;
  cutaways: HookCutawayData[];
  overlays: OverlayData[];
  texts: HookTextData[];
  stamps: StampData[];
  emoji: EmojiData[];
  sfx: SfxData[];
  // Word-pop subtitles, only for a beat that has its own regenerated .srt.
  cues: CueData[];
  bootTerminal: BootTerminalData | null;
  // OPT-IN, unlike the body where it is unconditional. Whether decoration
  // may sit on a cutaway is an editorial choice the plan makes.
  cutawaySafe: boolean;
  // Which body rules this beat suspends, copied from plans/hook.md so the
  // choice is visible in the data rather than implicit in the output.
  rulesSuspended: string[];
};

export type HookManifest = {
  fps: number;
  width: number;
  height: number;
  totalDurationInFrames: number;
  // Bed for the hook only. The main video's bed is a separate concern.
  music: {file: string; gainDb: number} | null;
  beats: HookBeatData[];
};

// Built by scripts/build_hook_manifest.py (this episode's editorial plan,
// gitignored) on top of scripts/hook_lib.py (the tracked engine). Edit the
// plan, never this file's data. `python3 scripts/hook_lib.py --stub` writes
// a placeholder so the composition can be typechecked and previewed with no
// episode content present.
export const hookManifest = hookJson as HookManifest;
