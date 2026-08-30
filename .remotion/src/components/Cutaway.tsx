import React from 'react';
import {
  AbsoluteFill, Freeze, Img, interpolate, OffthreadVideo, spring, staticFile,
  useCurrentFrame, useVideoConfig,
} from 'remotion';
import type {CutawayData, FocusData} from '../timeline';
import {ARCHIVE, GRADE, MOTION, ROLE, VIDEO, vignette} from '../design';

/**
 * The moving crop window.
 *
 * A focus move is the one place this project may "scale a source" without
 * breaking DESIGN.md 10.7. The rule's stated reason is that rescaling softens
 * monospace glyphs -- but the screencasts here are 3072x1920 against a
 * 2048x1280 delivery, so a 2048x1280 crop is a 1:1 PIXEL WINDOW and no
 * resampling happens at all. zoom is expressed relative to fit (1.0 = whole
 * source visible, 1.5 = native 1:1), and the manifest builder refuses
 * anything past 1.5, which is exactly where upscaling would begin.
 *
 * Movement is a spring, not a linear ramp: a focus push that arrives at a
 * constant speed reads as a camera being cranked. damping 200 gives UI-like
 * motion with no overshoot (guidelines section 5).
 */
const FocusCrop: React.FC<{focus: FocusData; children: React.ReactNode}> = ({
  focus, children,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = spring({frame, fps, config: {damping: 200}, durationInFrames: 45});

  const zoom = interpolate(t, [0, 1], [focus.zoomFrom, focus.zoomTo], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const cx = interpolate(t, [0, 1], [focus.cxFrom, focus.cxTo], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const cy = interpolate(t, [0, 1], [focus.cyFrom, focus.cyTo], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const scale = (VIDEO.width / focus.srcWidth) * zoom;
  const renderedW = focus.srcWidth * scale;
  const renderedH = focus.srcHeight * scale;

  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <div
        style={{
          position: 'absolute',
          width: renderedW,
          height: renderedH,
          left: VIDEO.width / 2 - cx * renderedW,
          top: VIDEO.height / 2 - cy * renderedH,
        }}
      >
        {children}
      </div>
    </AbsoluteFill>
  );
};

/**
 * ENTRANCES.
 *
 * Every shot used to arrive the same way -- by scaling. Scale is one gesture
 * among several and it was doing all the work, which is why the edit started
 * to feel like one effect on repeat. These are the alternatives, and each says
 * something different: a blur resolving reads as attention settling, a wipe
 * reads as a reveal, a slide reads as something being brought in. None of them
 * touches the source's pixels the way a zoom does.
 */
function useEntrance(kind: CutawayData['enter'], durationInFrames: number) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
  const t = spring({frame, fps, config: {damping: 200}, durationInFrames: 14});
  // Everything fades at the tail so a cut never snaps to black.
  const out = interpolate(
    frame,
    [durationInFrames - MOTION.fadeOut, durationInFrames],
    [1, 0],
    clamp,
  );

  if (kind === 'none') return {opacity: out};
  if (kind === 'fade') {
    const o = interpolate(frame, [0, MOTION.fadeIn], [0, 1], clamp);
    return {opacity: Math.min(o, out)};
  }
  if (kind === 'blur') {
    const b = interpolate(frame, [0, 12], [18, 0], clamp);
    const o = interpolate(frame, [0, MOTION.fadeIn], [0, 1], clamp);
    return {opacity: Math.min(o, out), filter: `blur(${b}px)`};
  }
  if (kind === 'slide-up') {
    return {opacity: out, transform: `translateY(${(1 - t) * 60}px)`};
  }
  if (kind === 'slide-left') {
    return {opacity: out, transform: `translateX(${(1 - t) * 80}px)`};
  }
  // wipe: a left-to-right reveal of the card, no pixels moved at all.
  const pct = interpolate(t, [0, 1], [100, 0], clamp);
  return {opacity: out, clipPath: `inset(0 ${pct}% 0 0)`};
}

/** Slow drift inside the card, as the hook does for archival footage. */
function useDrift(kind: CutawayData['drift'], durationInFrames: number) {
  const frame = useCurrentFrame();
  const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
  const span: [number, number] = [0, Math.max(durationInFrames - 1, 1)];
  if (kind === 'none') return undefined;
  if (kind === 'in') {
    return `scale(${interpolate(frame, span, [1, 1.06], clamp)})`;
  }
  const sign = kind === 'left' ? -1 : 1;
  return `translateX(${sign * interpolate(frame, span, [0, 2.5], clamp)}%)`;
}

/**
 * A full-frame visual replacement, rendered as the child of a <Sequence> that
 * the caller has already positioned at cutaway.fromFrame -- so
 * useCurrentFrame() here is LOCAL to the cutaway's own window, starting at 0.
 *
 * The narration segment's own audio keeps playing underneath (this component
 * is always muted); the cutaway supplies picture only.
 *
 * If the window is longer than the source clip, the source plays once and
 * then FREEZES on its last frame for the remainder -- standard practice for
 * a diagram that finishes before the narration explaining it does, rather
 * than looping or stretching it.
 *
 * holdOnly skips the intro playback entirely and freezes on the last frame
 * from local frame 0 -- used to bring a diagram BACK on screen at its
 * finished state without replaying its whole build-up animation.
 */
export const Cutaway: React.FC<{cutaway: CutawayData}> = ({cutaway}) => {
  const frame = useCurrentFrame();
  const src = staticFile(cutaway.src);
  const freezeAt = Math.max(cutaway.srcDurationInFrames - 1, 0);

  const entrance = useEntrance(cutaway.enter, cutaway.durationInFrames);
  const drift = useDrift(cutaway.drift, cutaway.durationInFrames);
  const gradeFilter =
    cutaway.grade.contrast === 1 && cutaway.grade.saturate === 1
      ? undefined
      : `contrast(${cutaway.grade.contrast}) saturate(${cutaway.grade.saturate})`;
  const fit: React.CSSProperties = {
    width: '100%', height: '100%', objectFit: 'contain', filter: gradeFilter,
  };

  // `fit` goes on EVERY variant, not just the image. Applying it only to
  // <Img> left videos at their natural pixel size in the corner of a card --
  // a 992x620 source filled 56% of a 1761px card and read as a layout fault.
  const picture = cutaway.isImage ? (
    <Img src={src} style={fit} />
  ) : cutaway.holdOnly ? (
    <Freeze frame={freezeAt}>
      <OffthreadVideo src={src} muted style={fit} />
    </Freeze>
  ) : frame < cutaway.srcDurationInFrames ? (
    <OffthreadVideo src={src} muted style={fit} />
  ) : (
    <Freeze frame={freezeAt}>
      <OffthreadVideo src={src} muted style={fit} />
    </Freeze>
  );

  /**
   * CENTRED CARD for anything that is not exactly the delivery frame.
   *
   * An <OffthreadVideo> in a bare AbsoluteFill has no objectFit, so a
   * 1920x1080 screen recording or a 960x540 gif is STRETCHED to 8:5 -- a
   * distorted picture, not a styling nicety. Rather than crop away real
   * content, the source sits inset on the page background at its native
   * aspect: the same honest treatment the hook gives archival footage, and
   * the reason DESIGN.md's ARCHIVE tokens exist.
   *
   * A true 2048x1280 screencast skips all of this and goes edge to edge.
   */
  if (cutaway.contain) {
    const padX = Math.round(VIDEO.width * ARCHIVE.inset);
    const padY = Math.round(VIDEO.height * ARCHIVE.inset);
    const g = cutaway.grade;
    return (
      <AbsoluteFill style={{backgroundColor: ROLE.bg}}>
        <AbsoluteFill
          style={{
            paddingLeft: padX, paddingRight: padX,
            paddingTop: padY, paddingBottom: padY,
            ...entrance,
          }}
        >
          <div
            style={{
              width: '100%', height: '100%',
              position: 'relative',
              overflow: 'hidden',
              borderRadius: ARCHIVE.radius,
              border: `${ARCHIVE.borderWidth}px solid ${ARCHIVE.borderColor}`,
              boxShadow: ARCHIVE.shadow,
              aspectRatio: `${cutaway.srcWidth} / ${cutaway.srcHeight}`,
              margin: 'auto',
              backgroundColor: ROLE.bg,
            }}
          >
            <div style={{width: '100%', height: '100%', transform: drift}}>
              {picture}
            </div>

            {/* Grade layers sit INSIDE the card and above the source, so they
                affect the footage and never our own frame. All are zero for a
                modern screenshot -- dressing one up with grain would make it
                claim to be archive footage it is not. */}
            {g.vignette > 0 && (
              <AbsoluteFill style={{backgroundImage: vignette(g.vignette)}} />
            )}
            {g.grain > 0 && (
              <AbsoluteFill
                style={{
                  backgroundImage: GRADE.grainTexture,
                  backgroundSize: `${GRADE.grainTile}px ${GRADE.grainTile}px`,
                  // Offset by frame so the grain MOVES; a static grain reads
                  // as a dirty lens rather than as film.
                  backgroundPosition: `${(frame * 37) % GRADE.grainTile}px ${
                    (frame * 23) % GRADE.grainTile
                  }px`,
                  opacity: g.grain,
                  mixBlendMode: 'overlay',
                }}
              />
            )}
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }

  // No focus declared -> the previous behaviour exactly: the source fills the
  // frame and nothing is transformed.
  if (!cutaway.focus) {
    return <AbsoluteFill style={entrance}>{picture}</AbsoluteFill>;
  }

  return <FocusCrop focus={cutaway.focus}>{picture}</FocusCrop>;
};
