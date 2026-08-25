import React from 'react';
import {spring, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {MOCHA, FONT} from '../palette';

interface Props {
  text: string;
  color?: string;
  size?: number;
}

// A talking-head shot keeps the face roughly centered top-to-bottom -- a
// dead-center stamp lands directly on it. Banner zone near the top instead,
// clear of the face in every raw recording (same webcam framing throughout),
// with a scrim band behind it so it reads over any wall/background colour.
const BANNER_TOP = '15%';

export const Stamp: React.FC<Props> = ({
  text,
  color = 'text',
  size = 140,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const hex = (MOCHA as any)[color] || color;

  const progress = spring({
    frame,
    fps,
    config: {damping: 12, stiffness: 300, mass: 0.5},
  });
  const scale = interpolate(progress, [0, 1], [0.1, 1]);
  const rotate = interpolate(progress, [0, 1], [-8, 0]);
  const shake = progress < 0.5 ? (1 - progress * 2) * 6 : 0;

  const exitOpacity = interpolate(frame, [25, 35], [1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return (
    <>
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '32%',
        background: `linear-gradient(180deg, ${MOCHA.crust}cc 0%, ${MOCHA.crust}00 100%)`,
        opacity: exitOpacity,
      }} />
      <div style={{
        position: 'absolute', top: BANNER_TOP, left: '50%',
        transform: `translate(-50%, -50%) scale(${scale}) rotate(${rotate + shake}deg)`,
        fontFamily: FONT, fontSize: size, fontWeight: 700,
        color: hex, opacity: exitOpacity,
        textShadow: `0 0 80px ${hex}aa, 0 0 40px ${hex}66, 0 8px 40px rgba(0,0,0,0.9), 0 4px 16px rgba(0,0,0,0.7)`,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        whiteSpace: 'nowrap',
      }}>
        {text}
      </div>
    </>
  );
};
