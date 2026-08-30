import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {CalloutData} from '../timeline';
import {FONT_DISPLAY, MOTION, RADIUS, resolveColor, ROLE, SHADOW, SPACE, TYPE, glow} from '../design';

/**
 * An accent rectangle plus a short label, anchored to part of the frame.
 *
 * The one graphic that says "look here" without changing what is on screen.
 * Reach for it when the subject is already visible and the narration is
 * naming one part of it. That is what DESIGN.md means by the accent being
 * functional -- the rectangle means "this is the thing", never "this is
 * decorated".
 *
 * The label sits OUTSIDE the rect, never over it, because the rect exists to
 * let you look at what is inside it.
 */
export const Callout: React.FC<{callout: CalloutData}> = ({callout}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {x, y, w, h, label, labelSide, durationInFrames} = callout;
  const color = resolveColor(callout.color);

  const draw = spring({frame, fps, config: {damping: 200}, durationInFrames: 12});
  const opacity = interpolate(
    frame,
    [0, MOTION.entrance, durationInFrames - MOTION.exit, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const pct = (v: number) => `${v * 100}%`;
  const labelStyle: React.CSSProperties = {
    position: 'absolute',
    left: pct(x),
    fontFamily: FONT_DISPLAY,
    fontSize: TYPE.tag.size,
    fontWeight: TYPE.tag.weight,
    letterSpacing: TYPE.tag.tracking,
    textTransform: TYPE.tag.transform,
    color,
    // Section 10.3: text over footage always carries the black shadow. The
    // accent glow is layered over it, never instead of it.
    textShadow: `${SHADOW.text}, ${glow(color, 24)}`,
    whiteSpace: 'nowrap',
  };

  return (
    <AbsoluteFill style={{opacity}}>
      <div
        style={{
          position: 'absolute',
          left: pct(x),
          top: pct(y),
          width: pct(w),
          height: pct(h),
          borderRadius: RADIUS.sm,
          // The border draws on rather than popping: scaleX from the left so
          // the motion means "this region", not "a box appeared".
          transform: `scaleX(${draw})`,
          transformOrigin: 'left center',
          boxShadow: `inset 0 0 0 3px ${color}, ${SHADOW.card}`,
        }}
      />
      {label ? (
        <div
          style={{
            ...labelStyle,
            ...(labelSide === 'above'
              ? {top: `calc(${pct(y)} - ${SPACE.xl}px)`}
              : {top: `calc(${pct(y + h)} + ${SPACE.md}px)`}),
            opacity: draw,
          }}
        >
          {label}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
