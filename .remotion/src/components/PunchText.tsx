import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT_DISPLAY, WEIGHT, SHADOW, resolveColor, glow} from '../design';

interface Props {
  words: string[];
  color?: string;
  size?: number;
  durationInFrames: number;
}

/**
 * A short punch line of text, word-popped in the LOWER THIRD.
 *
 * This is the layer that used to be `kineticText` and got deleted wholesale
 * after it kept landing on the speaker's face. Deleting it was an
 * over-correction -- the problem was never that punch text exists, it was
 * two specific defects, both fixed here and enforced elsewhere:
 *
 *  - it rendered dead-centre, i.e. exactly on the face in a talking-head
 *    shot. Now it sits in the lower third, over the chest/background.
 *  - it fired at its cue's START rather than when its words were actually
 *    spoken. Now every instance is checked by check_not_early() in
 *    build_timeline_manifest.py, which fails the build on a lead > 0.35s.
 *
 * It is also never combined with subtitle captions on the same segment (the
 * manifest builder rejects that), so the two text layers can't stack.
 */
export const PunchText: React.FC<Props> = ({
  words, color = 'text', size = 56, durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const hex = resolveColor(color);

  const out = interpolate(
    frame,
    [durationInFrames - 8, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <div style={{
      position: 'absolute', bottom: 150, left: 0, right: 0,
      display: 'flex', flexWrap: 'wrap', justifyContent: 'center',
      gap: '4px 14px', maxWidth: 1400, margin: '0 auto', padding: '0 60px',
      opacity: out,
    }}>
      {words.map((word, i) => {
        const wordFrame = i * 3;
        const progress = spring({
          frame: frame - wordFrame,
          fps,
          config: {damping: 13, stiffness: 220, mass: 0.5},
        });
        const opacity = interpolate(frame - wordFrame, [0, 3], [0, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });

        return (
          <span key={i} style={{
            fontFamily: FONT_DISPLAY, fontSize: size, fontWeight: WEIGHT.bold,
            color: hex, opacity,
            transform: `scale(${interpolate(progress, [0, 1], [0.75, 1])})`,
            display: 'inline-block',
            textShadow: `${glow(hex)}, ${SHADOW.text}`,
          }}>
            {word}
          </span>
        );
      })}
    </div>
  );
};
