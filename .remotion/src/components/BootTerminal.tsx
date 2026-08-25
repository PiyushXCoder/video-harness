import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {MOCHA, FONT} from '../palette';

interface Props {
  lines: string[];
  durationInFrames: number;
}

const LINE_STAGGER = 8; // frames between lines -- reads as a boot sequence

/**
 * The opening "system boot" terminal list -- component names typing
 * themselves out, top-left, green on a dark scrim.
 *
 * This was part of the old ColdOpen and got removed with it. Only the
 * hardcoded HEADLINE in that component was actually broken (it duplicated a
 * caption and appeared ~14s before the line was spoken); the terminal
 * sequence itself was fine, so it comes back on its own here.
 *
 * Top-left is deliberate: subtitle captions live in the bottom band, so the
 * two never overlap.
 */
export const BootTerminal: React.FC<Props> = ({lines, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const out = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <>
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '42%',
        background: `linear-gradient(180deg, ${MOCHA.crust}aa 0%, ${MOCHA.crust}00 100%)`,
        opacity: out,
      }} />
      <div style={{
        position: 'absolute', top: 80, left: 80,
        display: 'flex', flexDirection: 'column', gap: 6,
        opacity: out,
      }}>
        {lines.map((line, i) => {
          const delay = i * LINE_STAGGER;
          if (frame < delay) return null;

          const progress = spring({
            frame: frame - delay,
            fps,
            config: {damping: 15, stiffness: 200, mass: 0.5},
          });
          const opacity = interpolate(frame - delay, [0, 4], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          });

          return (
            <div key={i} style={{
              fontFamily: FONT, fontSize: 28, color: MOCHA.green,
              opacity,
              transform: `translateX(${interpolate(progress, [0, 1], [-20, 0])}px)`,
              textShadow: `0 0 20px ${MOCHA.green}66, 0 2px 8px rgba(0,0,0,0.85)`,
              letterSpacing: '0.02em',
            }}>
              <span style={{color: MOCHA.mauve}}>{'>'}</span>{' '}{line}
            </div>
          );
        })}
      </div>
    </>
  );
};
