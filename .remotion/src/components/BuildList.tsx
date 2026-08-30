import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {BuildListData} from '../timeline';
import {FONT_DISPLAY, MOTION, resolveColor, ROLE, SHADOW, SPACE, TYPE, ZONE, scrim} from '../design';

/**
 * A list that assembles itself, one line at a time.
 *
 * For a beat whose point is the ACCUMULATION -- a cost that mounts, a list of
 * things you have to do -- so the lines must arrive one by one rather than
 * appear as a block. An 8-frame line stagger (MOTION.lineStagger) is slow
 * enough to read as a sequence and fast enough not to feel like a queue.
 *
 * It lives in the lower-third zone, not at centre, so it stays legal over a
 * beat with a speaker on screen -- DESIGN.md 10.5 reserves the middle of the
 * frame for their face.
 */
export const BuildList: React.FC<{buildList: BuildListData}> = ({buildList}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {items, title, strike, durationInFrames} = buildList;
  const color = resolveColor(buildList.color);

  const opacity = interpolate(
    frame,
    [0, MOTION.fadeIn, durationInFrames - MOTION.fadeOut, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill style={{opacity}}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: scrim('bottom'),
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: ZONE.tagLeft,
          bottom: ZONE.punchBottom,
          display: 'flex',
          flexDirection: 'column',
          gap: SPACE.sm,
        }}
      >
        {title ? (
          <div
            style={{
              fontFamily: FONT_DISPLAY,
              fontSize: TYPE.tag.size,
              fontWeight: TYPE.tag.weight,
              letterSpacing: TYPE.tag.tracking,
              textTransform: TYPE.tag.transform,
              color: ROLE.textMuted,
              textShadow: SHADOW.text,
              marginBottom: SPACE.xs,
            }}
          >
            {title}
          </div>
        ) : null}
        {items.map((item, i) => {
          const enter = spring({
            frame: frame - i * MOTION.lineStagger,
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
                textShadow: SHADOW.text,
                opacity: enter,
                transform: `translateX(${(1 - enter) * -SPACE.xl}px)`,
                textDecoration: strike ? 'line-through' : 'none',
                whiteSpace: 'nowrap',
              }}
            >
              {item}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
