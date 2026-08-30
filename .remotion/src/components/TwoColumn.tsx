import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {TwoColumnData} from '../timeline';
import {FONT_DISPLAY, MOTION, resolveColor, ROLE, SHADOW, SPACE, TYPE, ZONE} from '../design';

/**
 * A this-versus-that build: two labelled columns, side by side.
 *
 * This is for a SPEAKER-FREE beat, which is why it may use the full frame
 * including the centre (DESIGN.md 10.5's stated exception). The plan records
 * that explicitly; if a speaker is ever on screen under this, the layout is
 * wrong, not the rule.
 *
 * The left column is the accent because it is the thing under discussion; the
 * right is muted because it is the absence or the alternative being described.
 * That is the accent doing a functional job, not a decorative one -- so put
 * the subject on the left, always, or the colour stops meaning anything.
 */
export const TwoColumn: React.FC<{twoColumn: TwoColumnData}> = ({twoColumn}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {left, right, leftTitle, rightTitle, durationInFrames} = twoColumn;
  const leftColor = resolveColor(twoColumn.leftColor);
  const rightColor = resolveColor(twoColumn.rightColor);

  const opacity = interpolate(
    frame,
    [0, MOTION.fadeIn, durationInFrames - MOTION.fadeOut, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const column = (
    title: string,
    items: string[],
    color: string,
    delayFrames: number,
  ) => (
    <div style={{flex: 1, display: 'flex', flexDirection: 'column', gap: SPACE.md}}>
      <div
        style={{
          fontFamily: FONT_DISPLAY,
          fontSize: TYPE.tag.size,
          fontWeight: TYPE.tag.weight,
          letterSpacing: TYPE.tag.tracking,
          textTransform: TYPE.tag.transform,
          color: ROLE.textMuted,
          textShadow: SHADOW.textSoft,
          borderBottom: `1px solid ${ROLE.border}`,
          paddingBottom: SPACE.sm,
        }}
      >
        {title}
      </div>
      {items.map((item, i) => {
        const enter = spring({
          frame: frame - delayFrames - i * MOTION.lineStagger,
          fps,
          config: {damping: 200},
          durationInFrames: 14,
        });
        return (
          <div
            key={item}
            style={{
              fontFamily: FONT_DISPLAY,
              fontSize: TYPE.cardBody.size,
              fontWeight: TYPE.hudLabel.weight,
              color,
              textShadow: SHADOW.textSoft,
              opacity: enter,
              transform: `translateY(${(1 - enter) * SPACE.md}px)`,
            }}
          >
            {item}
          </div>
        );
      })}
    </div>
  );

  return (
    <AbsoluteFill style={{backgroundColor: ROLE.bg, opacity}}>
      <div
        style={{
          position: 'absolute',
          inset: ZONE.safeInset,
          display: 'flex',
          gap: SPACE.xxl,
          alignItems: 'flex-start',
          justifyContent: 'center',
          paddingTop: ZONE.insetTop,
        }}
      >
        {column(leftTitle, left, leftColor, 0)}
        {/* The divider is the argument: two categories, one boundary. */}
        <div style={{width: 1, alignSelf: 'stretch', backgroundColor: ROLE.border}} />
        {column(rightTitle, right, rightColor, left.length * MOTION.lineStagger)}
      </div>
    </AbsoluteFill>
  );
};
