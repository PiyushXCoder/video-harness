import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {MOCHA, FONT} from '../palette';

type NameTagProps = {
  name: string;
  durationInFrames: number;
};

export const NameTag: React.FC<NameTagProps> = ({name, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const entrance = spring({
    frame,
    fps,
    config: {damping: 14, stiffness: 180, mass: 0.6},
  });
  const exit = interpolate(
    frame,
    [durationInFrames - 8, durationInFrames],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const x = interpolate(entrance, [0, 1], [-200, 0]);
  const opacity = 1 - exit;
  const width = interpolate(entrance, [0, 1], [0, 1]);

  return (
    <AbsoluteFill>
      <div style={{
        position: 'absolute', bottom: 80, left: 48,
        overflow: 'hidden',
      }}>
        <div style={{
          fontFamily: FONT, fontSize: 20, color: MOCHA.green,
          backgroundColor: MOCHA.crust + 'dd',
          padding: '8px 20px',
          borderLeft: `3px solid ${MOCHA.green}`,
          borderRadius: '0 6px 6px 0',
          transform: `translateX(${x}px)`,
          opacity,
          whiteSpace: 'nowrap',
        }}>
          {name}
        </div>
      </div>
    </AbsoluteFill>
  );
};
