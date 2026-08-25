import React from 'react';
import {AbsoluteFill, Freeze, OffthreadVideo, Sequence, staticFile, useCurrentFrame} from 'remotion';
import type {CutawayData} from '../timeline';

/**
 * A full-frame visual replacement, rendered as the child of a <Sequence> that
 * the caller has already positioned at cutaway.fromFrame -- so
 * useCurrentFrame() here is LOCAL to the cutaway's own window, starting at 0.
 *
 * The narration segment's own audio keeps playing underneath (this component
 * is always muted); the cutaway supplies picture only.
 *
 * If the window is longer than the source clip, the source plays once and
 * then FREEZES on its last frame for the remainder -- standard practice for
 * a diagram that finishes before the narration explaining it does, rather
 * than looping or stretching it.
 *
 * holdOnly skips the intro playback entirely and freezes on the last frame
 * from local frame 0 -- used to bring a diagram BACK on screen at its
 * finished state without replaying its whole build-up animation.
 */
export const Cutaway: React.FC<{cutaway: CutawayData}> = ({cutaway}) => {
  const frame = useCurrentFrame();
  const src = staticFile(cutaway.src);
  const freezeAt = Math.max(cutaway.srcDurationInFrames - 1, 0);

  if (cutaway.holdOnly) {
    return (
      <AbsoluteFill>
        <Freeze frame={freezeAt}>
          <OffthreadVideo src={src} muted />
        </Freeze>
      </AbsoluteFill>
    );
  }

  const isPlayingSource = frame < cutaway.srcDurationInFrames;

  return (
    <AbsoluteFill>
      {isPlayingSource ? (
        <OffthreadVideo src={src} muted />
      ) : (
        <Freeze frame={freezeAt}>
          <OffthreadVideo src={src} muted />
        </Freeze>
      )}
    </AbsoluteFill>
  );
};
