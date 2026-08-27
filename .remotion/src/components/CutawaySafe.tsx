import React from 'react';
import {Sequence, useCurrentFrame} from 'remotion';

/**
 * The minimum shape this module needs from a cutaway. Both `CutawayData`
 * (timeline.ts, the main video) and `HookCutawayData` (hook.ts) are
 * structurally assignable to it, so the two manifests stay decoupled from
 * each other -- neither has to import the other's types to reuse the gate.
 */
export type CutawayLike = {
  src: string;
  fromFrame: number;
  durationInFrames: number;
};

export function activeCutaway<T extends CutawayLike>(
  segmentFrame: number,
  cutaways: T[],
): T | undefined {
  return cutaways.find(
    (c) => segmentFrame >= c.fromFrame
      && segmentFrame < c.fromFrame + c.durationInFrames,
  );
}

/**
 * Wraps a decorative overlay so it NEVER renders while ANY full-frame
 * cutaway is on screen.
 *
 * A cutaway IS the content -- a diagram to read, or a screencast showing
 * real output -- and decoration drawn on top of it hides exactly what the
 * viewer is meant to look at. Both real bugs this caught:
 *   - an emoji burst sat dead-center over `digest == piece.hash` in
 *     code-verify-piece.mp4, cutting the word "hash";
 *   - the celebration meme's corner inset landed on the `sha256sum` digest
 *     line of the demo screencast, cutting the hash again.
 * Hence "any cutaway", not just manim/: the screencast case proves a
 * manim-only rule is too narrow. Enforced here rather than by per-cue
 * timing, because timing drifts every time the edit changes.
 *
 * Extracted from NarrationSegment.tsx so the hook composition can reuse it
 * without importing from another composition's segment renderer. NOTE for
 * the hook: cutaway-safety there is OPT-IN per beat, because whether the
 * hook obeys the body's layering rules is the plan's call, not the
 * template's -- see .claude/skills/hook-plan/SKILL.md.
 */
export const CutawaySafeSequence: React.FC<{
  from: number;
  durationInFrames: number;
  cutaways: CutawayLike[];
  layout?: 'none';
  children: React.ReactNode;
}> = ({from, durationInFrames, cutaways, layout, children}) => (
  <Sequence from={from} durationInFrames={durationInFrames} layout={layout}>
    <CutawayGate from={from} cutaways={cutaways}>{children}</CutawayGate>
  </Sequence>
);

/**
 * Reconstructs the PARENT timeline's frame as `from + localFrame`.
 *
 * This is load-bearing: useCurrentFrame() resets to 0 inside the
 * <Sequence> above, so comparing it directly against a cutaway's
 * fromFrame (which is in parent coordinates) would mis-gate every overlay
 * that does not start at frame 0.
 */
export const CutawayGate: React.FC<{
  from: number;
  cutaways: CutawayLike[];
  children: React.ReactNode;
}> = ({from, cutaways, children}) => {
  const localFrame = useCurrentFrame();
  if (activeCutaway(from + localFrame, cutaways)) return null;
  return <>{children}</>;
};
