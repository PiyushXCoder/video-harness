import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {CueData} from '../timeline';
import {ROLE, FONT_DISPLAY, SIZE, WEIGHT, SHADOW} from '../design';

/**
 * Word-pop captions driven by the segment's OWN .srt cues.
 *
 * Two rules this exists to enforce, both of which hand-timed text kept
 * breaking:
 *
 *  1. Nothing appears before it is spoken. A word pops in at its own onset
 *     inside its cue, never at the cue's start -- whisper's cues are
 *     multi-word chunks (-ml 42), so "the hash" can sit 2s into its cue.
 *  2. Once shown, a line HOLDS for the rest of its cue. Words accumulate and
 *     stay put until the cue ends, instead of each word flashing away.
 *
 * Rendered without its own <Sequence>, so useCurrentFrame() here is already
 * segment-local and lines up with the cue frames the manifest computed.
 */
export const SubtitleCaptions: React.FC<{cues: CueData[]}> = ({cues}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const active = cues.find(
    (c) => frame >= c.fromFrame && frame < c.fromFrame + c.durationInFrames,
  );
  if (!active) return null;

  const local = frame - active.fromFrame;
  const perWord = active.durationInFrames / active.words.length;

  return (
    <>
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0, height: '28%',
        background: `linear-gradient(0deg, ${ROLE.scrim}bb 0%, ${ROLE.scrim}00 100%)`,
      }} />
      {/* maxWidth 1240 of 2048, not 1600: a full-width caption line reached
          into the bottom corners and collided with the corner meme insets
          (caught with "you know how" running under the reaction gif). Wrapping
          to a second line is the right trade for a subtitle. */}
      <div style={{
        position: 'absolute', bottom: 96, left: 0, right: 0,
        display: 'flex', flexWrap: 'wrap', justifyContent: 'center',
        gap: '4px 14px', maxWidth: 1240, margin: '0 auto', padding: '0 40px',
      }}>
        {active.words.map((word, i) => {
          const wordFrame = i * perWord;
          // Not yet spoken -> not on screen at all.
          if (local < wordFrame) return null;

          const progress = spring({
            frame: local - wordFrame,
            fps,
            config: {damping: 14, stiffness: 240, mass: 0.5},
          });
          const opacity = interpolate(local - wordFrame, [0, 3], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          });

          return (
            <span key={i} style={{
              fontFamily: FONT_DISPLAY, fontSize: SIZE.xxl, fontWeight: WEIGHT.bold,
              color: ROLE.text, opacity,
              // Settles to scale 1 and stays -- the pop is the entrance, not
              // a loop, so the line reads as stable text once it has landed.
              transform: `scale(${interpolate(progress, [0, 1], [0.7, 1])})`,
              display: 'inline-block',
              textShadow: SHADOW.text,
            }}>
              {word}
            </span>
          );
        })}
      </div>
    </>
  );
};
