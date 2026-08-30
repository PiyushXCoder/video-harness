import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {SpotlightData} from '../timeline';
import {MOTION, ROLE, RADIUS} from '../design';

/**
 * Dims everything outside a rect.
 *
 * This is the attention tool for a screencast we must NOT move: a focus crop
 * changes what is on screen, which is wrong when the viewer needs to keep
 * seeing the whole desktop while one part of it is being talked about. It
 * adds nothing to read, which is why report_coverage() deliberately does not
 * count a spotlight as coverage.
 *
 * Built from four edge panels rather than a box-shadow so the dim is a flat,
 * predictable value at every edge -- a huge spread shadow banded visibly on a
 * near-black ground.
 */
export const Spotlight: React.FC<{spotlight: SpotlightData}> = ({spotlight}) => {
  const frame = useCurrentFrame();
  const {x, y, w, h, dim, durationInFrames} = spotlight;

  const opacity = interpolate(
    frame,
    [0, MOTION.entrance, durationInFrames - MOTION.exit, durationInFrames],
    [0, dim, dim, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const panel: React.CSSProperties = {
    position: 'absolute',
    backgroundColor: ROLE.scrim,
    opacity,
  };
  const pct = (v: number) => `${v * 100}%`;

  return (
    <AbsoluteFill>
      <div style={{...panel, left: 0, top: 0, width: '100%', height: pct(y)}} />
      <div style={{...panel, left: 0, top: pct(y + h), width: '100%', bottom: 0}} />
      <div style={{...panel, left: 0, top: pct(y), width: pct(x), height: pct(h)}} />
      <div style={{...panel, left: pct(x + w), top: pct(y), right: 0, height: pct(h)}} />
      {/* A hairline on the lit rect so its edge reads as deliberate rather
          than as a gradient artefact. */}
      <div
        style={{
          position: 'absolute',
          left: pct(x),
          top: pct(y),
          width: pct(w),
          height: pct(h),
          borderRadius: RADIUS.sm,
          boxShadow: `inset 0 0 0 1px ${ROLE.borderMuted}`,
          opacity: opacity / dim,
        }}
      />
    </AbsoluteFill>
  );
};
