import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {HudData, HudMarkData} from '../timeline';
import {
  FONT_DISPLAY, MOTION, RADIUS, resolveColor, ROLE, SHADOW, SPACE, TYPE, ZONE, glow,
} from '../design';

/**
 * A heads-up display: a header band, plus annotations that arrive on cue.
 *
 * WHAT IT IS FOR
 *
 * A stretch of narration that runs a *process* — something with a state, a
 * quantity that moves, and moments along the way worth marking. The band names
 * what is happening and the meter shows how far along it is; each mark is a
 * beat of the story appearing at the frame its line is spoken.
 *
 * This began as a single-purpose "boss frame" for one episode's game metaphor,
 * with a hardcoded FINAL BOSS kicker and three fixed slots named after that
 * video's subject matter. The shapes were always generic — an eyebrow, a
 * title, a meter, and timed marks — so the vocabulary is now the manifest's to
 * choose. Its old three slots are just three marks:
 *
 *   glyphs  a row of glyphs popping in one after another   (was: fast peers)
 *   note    one glyph and a short label, fading in         (was: slow peer)
 *   flash   a colour wash and a one-line banner            (was: power-up)
 *
 * EVERY VISIBLE STRING COMES FROM THE MANIFEST. The template ships no copy,
 * because it cannot know what your video is counting or calling things.
 *
 * TIMING. Each mark's `atFrame` is LOCAL to the HUD's own window and is keyed
 * in the plan to the cue that speaks it. That is not a detail: when these were
 * booleans with hardcoded fractions of the window, two marks appeared ~10s
 * before they were mentioned and a third fired 9s early. A mark is an
 * illustration of a spoken line and has no meaning away from it.
 *
 * PLACEMENT is from ZONE (DESIGN.md 10.4), and the band's extent is what the
 * meme overlay's top inset is derived from — so it is a real zone with a real
 * dependent, not a loose set of offsets.
 */

/** Where the meter sits within its own range, for the default colour ramp. */
function meterColor(value: number, stops: number[]): string {
  const lo = Math.min(...stops);
  const hi = Math.max(...stops);
  // A meter that never moves is not in trouble; treat it as healthy.
  if (hi === lo) return ROLE.accent;
  const t = (value - lo) / (hi - lo);
  // By FRACTION OF ITS OWN RANGE, not by absolute 50/20 — those assumed a
  // 0-100 scale that depletes, so a meter counting up, or one running 0-24868,
  // came out permanently red.
  return t > 0.5 ? ROLE.accent : t > 0.2 ? ROLE.warning : ROLE.error;
}

const Mark: React.FC<{mark: HudMarkData; frame: number; fps: number}> = ({mark, frame, fps}) => {
  const color = resolveColor(mark.color);
  const local = frame - mark.atFrame;

  if (mark.kind === 'glyphs') {
    return (
      <div style={{
        position: 'absolute', top: ZONE.hudMarkTop, right: ZONE.hudMarkRight,
        display: 'flex', gap: SPACE.md,
      }}>
        {mark.glyphs.map((g, i) => (
          <span
            key={i}
            style={{
              fontSize: TYPE.hudGlyph.size,
              transform: `scale(${spring({
                frame: local - i * MOTION.glyphStagger,
                fps,
                config: {damping: 10, stiffness: 250},
              })})`,
            }}
          >
            {g}
          </span>
        ))}
      </div>
    );
  }

  if (mark.kind === 'note') {
    return (
      <div style={{
        position: 'absolute', bottom: ZONE.hudMarkBottom, left: ZONE.hudMarkLeft,
        display: 'flex', alignItems: 'center', gap: SPACE.sm,
        opacity: interpolate(local, [0, MOTION.entrance], [0, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        }),
      }}>
        {mark.glyphs[0] && <span style={{fontSize: TYPE.hudGlyph.size}}>{mark.glyphs[0]}</span>}
        {mark.label && (
          <span style={{
            fontFamily: FONT_DISPLAY, fontSize: TYPE.hudNote.size,
            fontWeight: TYPE.hudNote.weight, color,
            textShadow: SHADOW.text,
          }}>
            {mark.label}
          </span>
        )}
      </div>
    );
  }

  // 'flash' -- the banner sits in the lower band, never at frame centre
  // (DESIGN.md 10.5): an earlier version was dead-centre and landed on the
  // narrator's face in every talking-head shot.
  return (
    <div style={{
      position: 'absolute', top: ZONE.hudBannerTop, left: '50%',
      transform: 'translate(-50%, -50%)',
      fontFamily: FONT_DISPLAY, fontSize: TYPE.hudBanner.size,
      fontWeight: TYPE.hudBanner.weight, letterSpacing: TYPE.hudBanner.tracking,
      color,
      opacity: interpolate(local, [0, MOTION.fadeOut], [0, 1], {
        extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      }),
      // SHADOW.text, not textSoft: this sits over footage (DESIGN.md 10.3).
      textShadow: `${glow(color, 30)}, ${SHADOW.text}`,
      whiteSpace: 'nowrap',
    }}>
      {mark.label}
    </div>
  );
};

export const Hud: React.FC<{hud: HudData}> = ({hud}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {kicker, label, meter, marks, durationInFrames} = hud;

  const entrance = spring({frame, fps, config: {damping: 14, stiffness: 160}});

  // The meter walks its stops evenly across the window, so [100, 60, 20, 0]
  // depletes and [0, 100] fills. Two stops is a straight ramp; more shapes it.
  const value = meter
    ? interpolate(
        frame,
        meter.stops.map((_, i) => (i / (meter.stops.length - 1)) * durationInFrames),
        meter.stops,
        {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
      )
    : 0;
  const lo = meter ? Math.min(...meter.stops) : 0;
  const hi = meter ? Math.max(...meter.stops) : 1;
  const fill = meter && hi > lo ? ((value - lo) / (hi - lo)) * 100 : 0;

  // A mark with a colour wash paints the whole frame, so it goes behind the
  // band rather than over it.
  const flash = marks.find(
    (m) => m.kind === 'flash' && frame >= m.atFrame && frame < m.atFrame + MOTION.entrance,
  );

  return (
    <AbsoluteFill>
      {flash && (
        <AbsoluteFill style={{
          backgroundColor: resolveColor(flash.color),
          opacity: interpolate(
            frame, [flash.atFrame, flash.atFrame + MOTION.entrance], [0.8, 0],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
          ),
        }} />
      )}

      <div style={{
        position: 'absolute', top: ZONE.hudTop,
        left: ZONE.hudPadX, right: ZONE.hudPadX,
        opacity: entrance,
      }}>
        {kicker && (
          <div style={{
            fontFamily: FONT_DISPLAY, fontSize: TYPE.hudLabel.size,
            fontWeight: TYPE.hudLabel.weight, color: resolveColor(hud.kickerColor),
            letterSpacing: TYPE.hudLabel.tracking, textTransform: 'uppercase',
            marginBottom: SPACE.md, textShadow: SHADOW.text,
          }}>
            {kicker}
          </div>
        )}
        <div style={{
          fontFamily: FONT_DISPLAY, fontSize: TYPE.hudTitle.size,
          fontWeight: TYPE.hudTitle.weight, color: ROLE.text,
          marginBottom: SPACE.md, textShadow: SHADOW.text,
        }}>
          {label}
        </div>

        {meter && (
          <>
            <div style={{
              width: '100%', height: ZONE.hudMeterHeight, borderRadius: RADIUS.pill,
              backgroundColor: ROLE.border, overflow: 'hidden',
              border: `1px solid ${ROLE.border}`,
            }}>
              <div style={{
                width: `${fill}%`, height: '100%', borderRadius: RADIUS.pill,
                backgroundColor: meter.color
                  ? resolveColor(meter.color)
                  : meterColor(value, meter.stops),
              }} />
            </div>
            <div style={{
              fontFamily: FONT_DISPLAY, fontSize: TYPE.statusLabel.size,
              fontWeight: TYPE.statusLabel.weight, color: ROLE.textMuted,
              marginTop: SPACE.xs, textAlign: 'right', textShadow: SHADOW.text,
            }}>
              {meter.readoutPrefix ? `${meter.readoutPrefix}: ` : ''}
              {Math.round(value)}{meter.unit}
            </div>
          </>
        )}
      </div>

      {marks.map((m, i) =>
        frame >= m.atFrame ? <Mark key={i} mark={m} frame={frame} fps={fps} /> : null,
      )}
    </AbsoluteFill>
  );
};
