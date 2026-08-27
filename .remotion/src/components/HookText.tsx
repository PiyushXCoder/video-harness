import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {HookTextData} from '../hook';
import {ROLE, FONT_DISPLAY, WEIGHT, TYPE, resolveColor} from '../design';

const WORD_STAGGER = 3; // frames between words -- same cadence as PunchText
const FADE_IN = 8;
const FADE_OUT = 10;

/**
 * The hook's text layer.
 *
 * Unlike the body -- where text is locked to three layers in three fixed
 * zones and `center` is forbidden because that is where the speaker's face
 * sits -- the hook chooses its own anchor. A hook may be pure motion
 * graphics with no speaker at all, in which case the centre is the ONLY
 * sensible place for a title. Which anchors are legal is therefore decided
 * in plans/hook.md, not here.
 *
 * Rendered as the child of a <Sequence> the caller positioned, so
 * useCurrentFrame() is LOCAL and starts at 0.
 */
const ANCHORS: Record<HookTextData['anchor'], React.CSSProperties> = {
  top: {alignItems: 'center', justifyContent: 'flex-start', paddingTop: '12%'},
  center: {alignItems: 'center', justifyContent: 'center'},
  'lower-third': {alignItems: 'center', justifyContent: 'flex-end', paddingBottom: 150},
  bottom: {alignItems: 'center', justifyContent: 'flex-end', paddingBottom: 96},
};

export const HookText: React.FC<{
  words: string[];
  color?: string;
  size?: number | null;
  anchor?: HookTextData['anchor'];
  durationInFrames: number;
}> = ({words, color = 'text', size, anchor = 'center', durationInFrames}) => {
  const frame = useCurrentFrame();
  const fontSize = size ?? TYPE.hookTitle.size;
  // The manifest carries a DESIGN.md ROLE name ('accent'), not a hex
  // value -- same contract as Stamp/PunchText. Fall through to the literal
  // so a raw hex still works.
  const hex = resolveColor(color);

  // Every interpolate is clamped -- an unclamped one drifts the element off
  // frame in exactly the frames nobody previews (CLAUDE.md).
  const out = interpolate(
    frame,
    [durationInFrames - FADE_OUT, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill style={{...ANCHORS[anchor], opacity: out}}>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0 0.35em',
          justifyContent: 'center',
          maxWidth: 1600,
          padding: '0 48px',
          fontFamily: FONT_DISPLAY,
          fontSize,
          fontWeight: WEIGHT.bold,
          lineHeight: 1.2,
          color: hex,
          textAlign: 'center',
          textShadow: `0 4px 24px ${ROLE.scrim}`,
        }}
      >
        {words.map((word, i) => {
          const appear = i * WORD_STAGGER;
          const opacity = interpolate(frame, [appear, appear + FADE_IN], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          });
          const lift = interpolate(frame, [appear, appear + FADE_IN], [14, 0], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          });
          return (
            <span
              key={`${word}-${i}`}
              style={{opacity, transform: `translateY(${lift}px)`, display: 'inline-block'}}
            >
              {word}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
