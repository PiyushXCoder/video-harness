import React from 'react';
import {spring, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {ROLE, FONT_DISPLAY, SIZE, WEIGHT, SHADOW, glow} from '../design';

type EndCardProps = {
  // All copy is per-video and comes from the manifest. Nothing here is
  // hardcoded, so the template ships without any channel-specific wording.
  progressLabel: string;
  headline: string;
  subline: string;
};

export const EndCard2: React.FC<EndCardProps> = ({progressLabel, headline, subline}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();

  const barProgress = spring({
    frame: frame - 15,
    fps,
    config: {damping: 30, stiffness: 80, mass: 1.5},
  });
  const barWidth = interpolate(barProgress, [0, 1], [0, 800]);

  const ctaProgress = spring({
    frame: frame - 30,
    fps,
    config: {damping: 10, stiffness: 200, mass: 0.6},
  });

  const nextProgress = spring({
    frame: frame - 45,
    fps,
    config: {damping: 10, stiffness: 200, mass: 0.6},
  });

  return (
    <div style={{
      position: 'absolute', inset: 0,
      background: `linear-gradient(180deg, ${ROLE.bg} 0%, ${ROLE.surface} 100%)`,
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: 40,
    }}>
      {/* Progress bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 16,
      }}>
        <span style={{
          fontFamily: FONT_DISPLAY, fontSize: SIZE.lg, color: ROLE.textMuted,
        }}>{progressLabel}</span>
        <div style={{
          width: 800, height: 32, borderRadius: 16,
          background: ROLE.border, overflow: 'hidden',
          position: 'relative',
        }}>
          <div style={{
            width: barWidth, height: '100%', borderRadius: 16,
            background: `linear-gradient(90deg, ${ROLE.accent}, ${ROLE.accent})`,
            boxShadow: `0 0 30px ${ROLE.accent}66`,
          }} />
        </div>
        <span style={{
          fontFamily: FONT_DISPLAY, fontSize: SIZE.lg, fontWeight: WEIGHT.bold,
          color: ROLE.accent,
          opacity: interpolate(barProgress, [0.5, 1], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          }),
        }}>100%</span>
      </div>

      {/* Seed CTA */}
      <div style={{
        transform: `scale(${ctaProgress}) translateY(${(1 - ctaProgress) * 30}px)`,
        fontFamily: FONT_DISPLAY, fontSize: SIZE.hero, fontWeight: WEIGHT.bold,
        color: ROLE.warning,
        textShadow: `${glow(ROLE.warning)}, ${SHADOW.textSoft}`,
      }}>
        {headline}
      </div>

      {/* Next-up */}
      <div style={{
        transform: `scale(${nextProgress}) translateY(${(1 - nextProgress) * 20}px)`,
        fontFamily: FONT_DISPLAY, fontSize: SIZE.xl, color: ROLE.textMuted,
        opacity: nextProgress,
        textShadow: SHADOW.textSoft,
      }}>
        {subline}
      </div>
    </div>
  );
};
