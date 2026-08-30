import React from 'react';
import {AbsoluteFill, interpolate, Loop, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import type {OverlayData} from '../timeline';
import {ROLE, SHADOW, ZONE} from '../design';

const ENTRANCE_FRAMES = 6;
const EXIT_FRAMES = 6;

// Top corners clear the HUD band -- its kicker, title, meter and readout
// (DESIGN.md 10.4, ZONE.hudTop + ZONE.hudBandHeight); at top: 48 the insets
// landed right on the meter. Bottom corners clear the status bar. Both come
// from ZONE so the coupling is visible: move the HUD band and this follows.
const TOP_INSET = ZONE.insetTop;
const BOTTOM_INSET = ZONE.insetBottom;
const CORNER_STYLE: Record<OverlayData['corner'], React.CSSProperties> = {
  tl: {top: TOP_INSET, left: 48},
  tr: {top: TOP_INSET, right: 48},
  bl: {bottom: BOTTOM_INSET, left: 48},
  br: {bottom: BOTTOM_INSET, right: 48},
};

/**
 * A meme/sticker overlay, rendered as the child of a <Sequence> the caller
 * has already positioned at overlay.fromFrame -- useCurrentFrame() here is
 * local to the overlay's own window.
 *
 * Transparent stickers (ProRes 4444 .mov) render full-frame with alpha;
 * opaque memes render as a bordered corner inset, sized to the SOURCE's real
 * aspect ratio (srcWidth/srcHeight from the manifest) rather than a guessed
 * ratio -- memes here range from square to 480x232, and objectFit:'cover'
 * against the wrong ratio would crop the joke.
 *
 * Reaction GIFs are usually well under the display window (0.4-2s vs a 4-5s
 * hold) -- <Loop> repeats the source for the window's duration rather than
 * freezing on a random mid-gesture frame (a diagram cutaway should NOT loop
 * -- see Cutaway.tsx). <Loop> defaults to the same absolute-fill layout as
 * <Sequence>: without layout="none" here, its content is laid out relative
 * to a parent height that a width-only div never establishes, and silently
 * collapses to a 0-height box (visible only as a hairline border) -- this
 * bit the very first render of this overlay. Always pair layout="none" on
 * Loop with an explicit, correctly-ratioed size on whatever contains it.
 */
export const MemeOverlay: React.FC<{overlay: OverlayData}> = ({overlay}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(
    frame,
    [0, ENTRANCE_FRAMES, overlay.durationInFrames - EXIT_FRAMES, overlay.durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const scale = interpolate(frame, [0, ENTRANCE_FRAMES], [0.85, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const video = (
    <Loop durationInFrames={overlay.srcDurationInFrames} layout="none">
      <OffthreadVideo
        src={staticFile(overlay.src)}
        muted
        transparent={overlay.transparent}
        style={{width: '100%', height: '100%', objectFit: overlay.transparent ? 'cover' : 'contain'}}
      />
    </Loop>
  );

  if (overlay.transparent) {
    return <AbsoluteFill style={{opacity}}>{video}</AbsoluteFill>;
  }

  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          ...CORNER_STYLE[overlay.corner],
          width: `${overlay.widthPct * 100}%`,
          aspectRatio: `${overlay.srcWidth} / ${overlay.srcHeight}`,
          opacity,
          transform: `scale(${scale})`,
          borderRadius: 14,
          overflow: 'hidden',
          border: `2px solid ${ROLE.border}`,
          boxShadow: SHADOW.card,
          backgroundColor: ROLE.surface,
        }}
      >
        {video}
      </div>
    </AbsoluteFill>
  );
};
