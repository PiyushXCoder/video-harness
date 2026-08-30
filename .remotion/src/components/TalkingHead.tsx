import React from 'react';
import {
  AbsoluteFill, interpolate, OffthreadVideo, staticFile, useCurrentFrame,
} from 'remotion';
import type {PunchData} from '../timeline';
import {vignette} from '../design';

/**
 * The presenter's own picture, with the two things a locked-off webcam shot
 * needs to stop feeling like a locked-off webcam shot.
 *
 * PUNCHES. A slow, continuous scale across a window -- not a snap. The take is
 * captured at exactly the delivery frame, so unlike a crop out of an oversized
 * screencast this IS a true upscale; the manifest refuses anything past 1.25
 * and the movement is slow enough that the softening never resolves as
 * softening. Movement is linear rather than sprung here on purpose: a spring
 * settles, and a settle reads as the camera arriving somewhere, which is a
 * different (and more distracting) gesture than a drift that never stops.
 *
 * originY defaults to 0.4 rather than 0.5 because a head sits above centre in
 * this framing; scaling about the true centre pushes the face upward out of
 * frame.
 *
 * VIGNETTE. Darkens the edges so the eye is pulled to the speaker. This is the
 * "darkness focus" that a flat, evenly-lit room does not supply on its own,
 * and it does a second job: it deepens the corners the flank captions sit in,
 * so type over a bright wall gets separation for free.
 *
 * Neither treatment is ever applied to a cutaway. A screencast is 1:1 and
 * stays that way.
 */
export const TalkingHead: React.FC<{
  src: string;
  punches: PunchData[];
  vignetteStrength: number;
}> = ({src, punches, vignetteStrength}) => {
  const frame = useCurrentFrame();

  const active = punches.find(
    (p) => frame >= p.fromFrame && frame < p.fromFrame + p.durationInFrames,
  );

  let scale = 1;
  let originY = 0.4;
  if (active) {
    originY = active.originY;
    scale = interpolate(
      frame,
      [active.fromFrame, active.fromFrame + active.durationInFrames - 1],
      [active.from, active.to],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
    );
  }

  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <AbsoluteFill
        style={{
          transform: `scale(${scale})`,
          transformOrigin: `50% ${originY * 100}%`,
        }}
      >
        <OffthreadVideo src={staticFile(src)} />
      </AbsoluteFill>
      {vignetteStrength > 0 ? (
        <AbsoluteFill
          style={{background: vignette(vignetteStrength), pointerEvents: 'none'}}
        />
      ) : null}
    </AbsoluteFill>
  );
};
