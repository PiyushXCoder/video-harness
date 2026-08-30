import React from 'react';
import {spring, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {ROLE, FONT_DISPLAY, WEIGHT, TYPE, SHADOW, MOTION, resolveColor, glow} from '../design';

interface Props {
  text: string;
  color?: string;
  size?: number | null;
  /**
   * The stamp's whole window. The exit is anchored to the END of it rather
   * than to a fixed frame, so a stamp can never be cut off mid-fade by a
   * sequence shorter than its own animation -- which is exactly what used to
   * happen with a 30-frame window against a 35-frame exit ramp.
   */
  durationInFrames: number;
}

// A talking-head shot keeps the face roughly centered top-to-bottom -- a
// dead-center stamp lands directly on it. Banner zone near the top instead,
// clear of the face in every raw recording (same webcam framing throughout),
// with a scrim band behind it so it reads over any wall/background colour.
const BANNER_TOP = '15%';

export const Stamp: React.FC<Props> = ({
  text,
  color = 'text',
  size,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  // null/undefined -> the design token, so DESIGN.md owns the size.
  const fontSize = size ?? TYPE.stamp.size;
  const {fps} = useVideoConfig();
  const hex = resolveColor(color);

  const progress = spring({
    frame,
    fps,
    config: {damping: 12, stiffness: 300, mass: 0.5},
  });
  const scale = interpolate(progress, [0, 1], [0.1, 1]);
  const rotate = interpolate(progress, [0, 1], [-8, 0]);
  const shake = progress < 0.5 ? (1 - progress * 2) * 6 : 0;

  const exitOpacity = interpolate(
    frame,
    [durationInFrames - MOTION.stampExit, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <>
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '32%',
        background: `linear-gradient(180deg, ${ROLE.scrim}cc 0%, ${ROLE.scrim}00 100%)`,
        opacity: exitOpacity,
      }} />
      <div style={{
        position: 'absolute', top: BANNER_TOP, left: '50%',
        transform: `translate(-50%, -50%) scale(${scale}) rotate(${rotate + shake}deg)`,
        fontFamily: FONT_DISPLAY, fontSize, fontWeight: WEIGHT.bold,
        color: hex, opacity: exitOpacity,
        textShadow: `${glow(hex, 80, 'aa')}, ${glow(hex)}, ${SHADOW.textHeavy}`,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        whiteSpace: 'nowrap',
      }}>
        {text}
      </div>
    </>
  );
};
