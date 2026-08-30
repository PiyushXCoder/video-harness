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
  // >1 speeds the source up. The BEAT's own duration is already
  // (toSec - startFromSec) / playbackRate, computed in hook_lib -- so this is
  // only the playback instruction, never a length to re-derive here.
  playbackRate: number;
  // Archive-card margin as a fraction of the frame. 0 renders edge to edge.
  // See DESIGN.md ARCHIVE in design.ts for why archival footage is inset.
  inset: number;
};

/**
 * Ken Burns for one beat. Not decoration: this hook's archival sources are
 * often completely static (three windows already open, nothing moving), so
 * the push-in is the only thing keeping the shot alive.
 */
export type HookMotionData = {
  kind: 'none' | 'push-in' | 'pull-out' | 'drift-left' | 'drift-right';
  from: number;
  to: number;
};

/** Era grade, 0-1 each. Graded per beat, not applied over the whole hook. */
export type HookGradeData = {
  darken: number;
  vignette: number;
  grain: number;
  // Multipliers; 1.0 is untouched.
  contrast: number;
  saturate: number;
};

/**
 * Hook-level audio, on the hook's OWN timeline.
 *
 * Not per-beat sfx: a beat's sfx live inside its <Series.Sequence>, which
 * CLIPS them to that beat's length -- so anything spanning a cut is silently
 * truncated. A pitched-down chant runs from beat 3 into beat 5; a 7.6s riser
 * sits under a 2.8s beat. `fromFrame` is absolute hook time, like `music`.
 *
 * `kind` is editorial only ('voice' for takes, 'bed' for drones and risers).
 * Both render identically; the label keeps the manifest readable.
 */
export type HookAudioData = {
  kind: 'voice' | 'bed';
  file: string;
  fromFrame: number;
  startFromFrame: number;
  durationInFrames: number;
  gainDb: number;
  // Anti-click only. The edit point itself must land in real silence.
  fadeInFrames: number;
  fadeOutFrames: number;
};

/**
 * The hook's sfx carry a real WINDOW, which the body's SfxData does not.
 * Hook.tsx used to hardcode 60 frames, silently truncating any effect over
 * 2s -- a riser, a drone, a swell. Extending rather than editing SfxData
 * keeps the body's manifest (which emits no duration) valid.
 */
export type HookSfxData = SfxData & {durationInFrames: number};

export type HookCutawayData = {
  src: string;
  fromFrame: number;
  durationInFrames: number;
  // Where to start inside the cutaway's own source.
  startFromFrame: number;
  srcDurationInFrames: number;
  holdOnly: boolean;
  // A hook cutaway is third-party footage, so it renders through
  // <ArchiveFrame> (inset, native aspect) rather than the body's <Cutaway>,
  // which has no objectFit and would stretch a 16:9 clip into 8:5.
  inset: number;
  grade: HookGradeData;
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
  size?: number | null;
  anchor: 'top' | 'center' | 'lower-third' | 'bottom' | 'left' | 'right';
  // DESIGN.md 10.3: text over footage carries a scrim OR a heavy shadow. The
  // shadow is unconditional; this adds the scrim where the background behind
  // the text is BUSY rather than merely bright.
  scrim: boolean;
};

export type HookBeatData = {
  id: string;
  durationInFrames: number;
  // Fade up from black over the beat's first N frames. 0 = hard cut in.
  fadeInFrames: number;
  // null for a pure-graphics beat -- a title card, a chart, kinetic type.
  // This is why a hook cannot be a SegmentData: NarrationSegment renders
  // <OffthreadVideo src={staticFile(segment.file)}> unconditionally.
  source: HookSourceData | null;
  motion: HookMotionData;
  grade: HookGradeData;
  background: string;
  cutaways: HookCutawayData[];
  overlays: OverlayData[];
  texts: HookTextData[];
  stamps: StampData[];
  emoji: EmojiData[];
  sfx: HookSfxData[];
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
  // Voice takes and cross-cut beds, laid across the whole hook independent
  // of where the beat boundaries fall.
  audio: HookAudioData[];
  beats: HookBeatData[];
};

// Built by scripts/build_hook_manifest.py (this episode's editorial plan,
// gitignored) on top of scripts/hook_lib.py (the tracked engine). Edit the
// plan, never this file's data. `python3 scripts/hook_lib.py --stub` writes
// a placeholder so the composition can be typechecked and previewed with no
// episode content present.
export const hookManifest = hookJson as HookManifest;
