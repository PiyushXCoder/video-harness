import React from 'react';
import {spring, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {MOCHA, FONT} from '../palette';

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
      background: `linear-gradient(180deg, ${MOCHA.base} 0%, ${MOCHA.mantle} 100%)`,
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: 40,
    }}>
      {/* Progress bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 16,
      }}>
        <span style={{
          fontFamily: FONT, fontSize: 28, color: MOCHA.subtext0,
        }}>{progressLabel}</span>
        <div style={{
          width: 800, height: 32, borderRadius: 16,
          background: MOCHA.surface0, overflow: 'hidden',
          position: 'relative',
        }}>
          <div style={{
            width: barWidth, height: '100%', borderRadius: 16,
            background: `linear-gradient(90deg, ${MOCHA.green}, ${MOCHA.teal})`,
            boxShadow: `0 0 30px ${MOCHA.green}66`,
          }} />
        </div>
        <span style={{
          fontFamily: FONT, fontSize: 28, fontWeight: 700,
          color: MOCHA.green,
          opacity: interpolate(barProgress, [0.5, 1], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          }),
        }}>100%</span>
      </div>

      {/* Seed CTA */}
      <div style={{
        transform: `scale(${ctaProgress}) translateY(${(1 - ctaProgress) * 30}px)`,
        fontFamily: FONT, fontSize: 56, fontWeight: 700,
        color: MOCHA.yellow,
        textShadow: `0 0 40px ${MOCHA.yellow}66, 0 4px 20px rgba(0,0,0,0.8)`,
      }}>
        {headline}
      </div>

      {/* Next-up */}
      <div style={{
        transform: `scale(${nextProgress}) translateY(${(1 - nextProgress) * 20}px)`,
        fontFamily: FONT, fontSize: 32, color: MOCHA.subtext0,
        opacity: nextProgress,
        textShadow: `0 2px 12px rgba(0,0,0,0.6)`,
      }}>
        {subline}
      </div>
    </div>
  );
};
