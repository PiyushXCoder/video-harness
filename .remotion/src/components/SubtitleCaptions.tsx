import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {CueData} from '../timeline';
import {ROLE, FONT_DISPLAY, SIZE, WEIGHT, SHADOW, ZONE, scrim} from '../design';

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
export const SubtitleCaptions: React.FC<{
  cues: CueData[];
  /**
   * 'flank-left' moves the words off the subtitle band and into the empty
   * wall beside the speaker. The take frames the presenter centre-right with
   * a plain wall on the left, so that column is dead space the picture is
   * already giving away -- and it keeps DESIGN.md 10.5 by construction, since
   * text beside a face can never land on it. A bottom band under a talking
   * head reads as a subtitle track; the same words in the negative space read
   * as part of the design.
   */
  position?: 'bottom' | 'flank';
}> = ({cues, position = 'bottom'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const idx = cues.findIndex(
    (c) => frame >= c.fromFrame && frame < c.fromFrame + c.durationInFrames,
  );
  if (idx < 0) return null;
  const active = cues[idx];

  const local = frame - active.fromFrame;
  const perWord = active.durationInFrames / active.words.length;

  const flank = position === 'flank';
  // ALTERNATE SIDES. Always-left made the frame lopsided and turned the words
  // into furniture; switching per cue keeps the eye moving and uses both pockets
  // of dead space the framing actually gives us. Driven by the cue INDEX, not
  // by time, so a line never changes side halfway through itself.
  const right = flank && idx % 2 === 1;

  return (
    <>
      <div style={{
        position: 'absolute',
        ...(flank
          // A shadow alone does not separate type from a bright, SMOOTH wall,
          // which is exactly what is behind the flank column -- hence a side
          // scrim as well (DESIGN.md 10.3, same finding as the hook).
          ? right
            ? {top: 0, bottom: 0, right: 0, width: ZONE.scrimFlankWidth,
               background: scrim('right')}
            : {top: 0, bottom: 0, left: 0, width: ZONE.scrimFlankWidth,
               background: scrim('left')}
          : {bottom: 0, left: 0, right: 0, height: ZONE.scrimBottomHeight,
             background: scrim('bottom')}),
      }} />
      {/* maxWidth 1240 of 2048, not 1600: a full-width caption line reached
          into the bottom corners and collided with the corner meme insets
          (caught with "you know how" running under the reaction gif). Wrapping
          to a second line is the right trade for a subtitle. */}
      <div style={{
        position: 'absolute',
        display: 'flex', flexWrap: 'wrap',
        gap: '4px 14px',
        ...(flank
          ? {
              top: '50%', transform: 'translateY(-50%)',
              maxWidth: ZONE.flankMaxWidth,
              ...(right
                ? {right: ZONE.flankPadX, justifyContent: 'flex-end',
                   textAlign: 'right' as const}
                : {left: ZONE.flankPadX, justifyContent: 'flex-start'}),
            }
          : {bottom: ZONE.captionBottom, left: 0, right: 0,
             justifyContent: 'center', maxWidth: ZONE.captionMaxWidth,
             margin: '0 auto', padding: `0 ${ZONE.captionPadX}px`}),
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
              fontFamily: FONT_DISPLAY,
              fontSize: flank ? SIZE.xl : SIZE.xxl,
              fontWeight: WEIGHT.bold,
              color: ROLE.text, opacity,
              textShadow: flank ? SHADOW.textHeavy : SHADOW.text,
              // Settles to scale 1 and stays -- the pop is the entrance, not
              // a loop, so the line reads as stable text once it has landed.
              transform: `scale(${interpolate(progress, [0, 1], [0.7, 1])})`,
              display: 'inline-block',
            }}>
              {word}
            </span>
          );
        })}
      </div>
    </>
  );
};
