import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {HookTextData} from '../hook';
import {FONT_DISPLAY, WEIGHT, TYPE, SHADOW, ZONE, scrim, resolveColor} from '../design';

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
  // Flanking: beside the speaker. justifyContent is the VERTICAL axis here
  // (the fill is a column), so these centre vertically and pin horizontally.
  left: {alignItems: 'flex-start', justifyContent: 'center', paddingLeft: ZONE.flankPadX},
  right: {alignItems: 'flex-end', justifyContent: 'center', paddingRight: ZONE.flankPadX},
};

const IS_FLANK = (a: HookTextData['anchor']) => a === 'left' || a === 'right';

export const HookText: React.FC<{
  words: string[];
  color?: string;
  size?: number | null;
  anchor?: HookTextData['anchor'];
  scrim?: boolean;
  durationInFrames: number;
}> = ({words, color = 'text', size, anchor = 'center', scrim: withScrim = false, durationInFrames}) => {
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

  // DESIGN.md 10.3 offers a scrim OR a heavy shadow. A title on our own dark
  // background needs neither beyond the shadow; a year card sitting over a
  // wall of readable terminal text needs both, because a shadow alone only
  // separates text from a SMOOTH background.
  const band =
    anchor === 'top' ? ('top' as const)
    : anchor === 'left' ? ('left' as const)
    : anchor === 'right' ? ('right' as const)
    : anchor === 'center' ? null
    : ('bottom' as const);
  const flank = IS_FLANK(anchor);

  return (
    <AbsoluteFill style={{...ANCHORS[anchor], opacity: out}}>
      {withScrim && band && (
        <AbsoluteFill
          style={
            flank
              ? {
                  left: band === 'left' ? 0 : undefined,
                  right: band === 'right' ? 0 : undefined,
                  width: ZONE.scrimFlankWidth,
                  backgroundImage: scrim(band),
                }
              : {
                  top: band === 'top' ? 0 : undefined,
                  bottom: band === 'bottom' ? 0 : undefined,
                  height:
                    band === 'top' ? ZONE.scrimTopHeight : ZONE.scrimBottomHeight,
                  backgroundImage: scrim(band),
                }
          }
        />
      )}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0 0.35em',
          justifyContent: flank
            ? anchor === 'left'
              ? 'flex-start'
              : 'flex-end'
            : 'center',
          maxWidth: flank ? ZONE.flankMaxWidth : 1600,
          padding: flank ? 0 : '0 48px',
          fontFamily: FONT_DISPLAY,
          fontSize,
          fontWeight: WEIGHT.bold,
          lineHeight: 1.2,
          color: hex,
          textAlign: flank ? (anchor === 'left' ? 'left' : 'right') : 'center',
          // DESIGN.md §10.3, which plans/hook.md lists as NOT suspendable:
          // every piece of on-screen text carries a scrim or a heavy shadow,
          // always. This was a single-layer `0 4px 24px #000` -- it renders
          // fine on black and disappears over a bright CRT, which is exactly
          // where the hook's year cards sit.
          textShadow: flank ? SHADOW.textHeavy : SHADOW.text,
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
