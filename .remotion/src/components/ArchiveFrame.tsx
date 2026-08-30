import React from 'react';
import {
  AbsoluteFill,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type {HookSourceData, HookMotionData, HookGradeData} from '../hook';
import {ARCHIVE, GRADE, ROLE, vignette} from '../design';

/**
 * One beat's base picture: third-party archival footage, framed honestly.
 *
 * WHY THIS EXISTS AT ALL
 *
 * `<OffthreadVideo>` on its own fills the 2048x1280 AbsoluteFill with no
 * objectFit, so a 312x240 or 992x620 source is STRETCHED to 8:5 and
 * distorted. That is not a styling nicety; it is a wrong picture.
 *
 * DESIGN.md §10.7 forbids scaling a source on the premise that "every asset
 * is already 2048x1280". That premise is false for archival footage, so this
 * component is the recorded exception (see ARCHIVE in design.ts): the source
 * sits INSET on the page background at its native aspect, one consistent
 * treatment for every era. A body screencast must never use it -- that really
 * is 2048x1280 and belongs edge to edge.
 *
 * Motion, grade and playbackRate live here too, because all three are
 * properties of "how this beat's footage is presented" and splitting them
 * across three wrappers made the transform order ambiguous.
 */

/** Ken Burns transform for the current frame. Both ends clamped, always. */
function useKenBurns(motion: HookMotionData, durationInFrames: number) {
  const frame = useCurrentFrame();
  const opts = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
  const span: [number, number] = [0, Math.max(durationInFrames - 1, 1)];

  if (motion.kind === 'none') return 'none';

  if (motion.kind === 'push-in' || motion.kind === 'pull-out') {
    const scale = interpolate(frame, span, [motion.from, motion.to], opts);
    return `scale(${scale})`;
  }

  // Drift: from/to are PERCENTAGES of the element's own width, so a drift
  // reads the same regardless of how large the inset box ended up.
  const sign = motion.kind === 'drift-left' ? -1 : 1;
  const pct = interpolate(frame, span, [motion.from, motion.to], opts);
  return `translateX(${sign * pct}%)`;
}

export const ArchiveFrame: React.FC<{
  source: HookSourceData;
  motion: HookMotionData;
  grade: HookGradeData;
  durationInFrames: number;
}> = ({source, motion, grade, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const transform = useKenBurns(motion, durationInFrames);

  const padX = Math.round(width * source.inset);
  const padY = Math.round(height * source.inset);

  return (
    <AbsoluteFill style={{backgroundColor: ROLE.bg}}>
      <AbsoluteFill
        style={{
          paddingLeft: padX,
          paddingRight: padX,
          paddingTop: padY,
          paddingBottom: padY,
        }}
      >
        {/* The card. overflow:hidden is what makes a push-in crop INSIDE the
            card instead of growing past its edges and defeating the inset. */}
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: '100%',
            overflow: 'hidden',
            borderRadius: ARCHIVE.radius,
            border: `${ARCHIVE.borderWidth}px solid ${ARCHIVE.borderColor}`,
            boxShadow: ARCHIVE.shadow,
            backgroundColor: ROLE.bg,
          }}
        >
          <div style={{width: '100%', height: '100%', transform}}>
            <OffthreadVideo
              src={staticFile(source.src)}
              startFrom={source.startFromFrame}
              playbackRate={source.playbackRate}
              muted={source.muted}
              // contain, NOT cover: nothing is cropped away. A 4:3 capture
              // shows its own bars inside the card, which is the point --
              // the card is the constant, the source keeps its shape.
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'contain',
                // Applied to the SOURCE, beneath the vignette/darken/grain
                // layers, so the grade affects the footage and not our own
                // overlays. 1.0/1.0 emits no filter at all.
                filter:
                  grade.contrast === 1 && grade.saturate === 1
                    ? undefined
                    : `contrast(${grade.contrast}) saturate(${grade.saturate})`,
              }}
            />
          </div>

          {grade.vignette > 0 && (
            <AbsoluteFill
              style={{backgroundImage: vignette(grade.vignette)}}
            />
          )}

          {grade.darken > 0 && (
            <AbsoluteFill
              style={{backgroundColor: GRADE.darkenColor, opacity: grade.darken}}
            />
          )}

          {grade.grain > 0 && (
            <AbsoluteFill
              style={{
                backgroundImage: GRADE.grainTexture,
                backgroundSize: `${GRADE.grainTile}px ${GRADE.grainTile}px`,
                // Offset by frame so the grain MOVES. A static grain reads as
                // a dirty lens; film grain is different every frame. The
                // prime-ish strides keep the tile from visibly repeating.
                backgroundPosition: `${(frame * 37) % GRADE.grainTile}px ${
                  (frame * 23) % GRADE.grainTile
                }px`,
                opacity: grade.grain,
                mixBlendMode: 'overlay',
              }}
            />
          )}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
