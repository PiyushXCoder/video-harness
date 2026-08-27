import React from 'react';
import {spring, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {ROLE, FONT_DISPLAY, SIZE, WEIGHT, SHADOW, glow} from '../design';

/**
 * ReelEndCard — 1080×1920 vertical end card for reels/shorts.
 * 3.5 s (105 frames @ 30 fps). Mirrors EndCard2 but vertical layout.
 * CTA: "Full video on YouTube" / "Link in description ↓"
 *
 * Rendered once and concatenated after each reel body via ffmpeg concat.
 * See scripts/extract_reels.py ensure_endcard() and docs for spec.
 */
export const ReelEndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Staggered springs: headline → subline → arrow
  const headline = spring({
    frame: frame - 6,
    fps,
    config: {damping: 14, stiffness: 180, mass: 0.7},
  });
  const subline = spring({
    frame: frame - 18,
    fps,
    config: {damping: 16, stiffness: 160, mass: 0.7},
  });
  const arrow = spring({
    frame: frame - 30,
    fps,
    config: {damping: 12, stiffness: 200, mass: 0.5},
  });
  const bar = spring({
    frame: frame - 2,
    fps,
    config: {damping: 30, stiffness: 80, mass: 1.2},
  });

  const barW = interpolate(bar, [0, 1], [0, 720], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: `linear-gradient(180deg, ${ROLE.bg} 0%, ${ROLE.surface} 100%)`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 28,
        padding: '0 64px',
      }}
    >
      {/* Thin progress shimmer on top */}
      <div
        style={{
          position: 'absolute',
          top: 80,
          width: 720,
          height: 6,
          borderRadius: 3,
          background: ROLE.border,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: barW,
            height: '100%',
            borderRadius: 3,
            background: `linear-gradient(90deg, ${ROLE.accent}, ${ROLE.accent})`,
            boxShadow: `0 0 16px ${ROLE.accent}88`,
          }}
        />
      </div>

      {/* Headline — spring scale + slide */}
      <div
        style={{
          transform: `scale(${headline}) translateY(${(1 - headline) * 28}px)`,
          opacity: interpolate(headline, [0, 0.6, 1], [0, 1, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          }),
          fontFamily: FONT_DISPLAY,
          fontSize: SIZE.hero,
          fontWeight: WEIGHT.bold,
          color: ROLE.warning,
          textAlign: 'center',
          lineHeight: 1.15,
          textShadow: `${glow(ROLE.warning, 36, '55')}, ${SHADOW.textSoft}`,
        }}
      >
        Full video
        <br />
        on YouTube
      </div>

      {/* Subline */}
      <div
        style={{
          transform: `scale(${subline}) translateY(${(1 - subline) * 20}px)`,
          opacity: interpolate(subline, [0, 0.5, 1], [0, 0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          }),
          fontFamily: FONT_DISPLAY,
          fontSize: SIZE.xl,
          fontWeight: WEIGHT.semibold,
          color: ROLE.text,
          textAlign: 'center',
          letterSpacing: 0.5,
          textShadow: SHADOW.textSoft,
        }}
      >
        Link in description
      </div>

      {/* Arrow — gentle bounce */}
      <div
        style={{
          transform: `scale(${arrow}) translateY(${(1 - arrow) * 16 + Math.sin(frame * 0.18) * 6}px)`,
          opacity: interpolate(arrow, [0, 0.4, 1], [0, 0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          }),
          fontFamily: FONT_DISPLAY,
          fontSize: SIZE.hero,
          color: ROLE.accent,
          textShadow: `0 0 20px ${ROLE.accent}66`,
        }}
      >
        ↓
      </div>

      {/* Bottom hint */}
      <div
        style={{
          position: 'absolute',
          bottom: 180,
          opacity: interpolate(subline, [0.7, 1], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          }),
          fontFamily: FONT_DISPLAY,
          fontSize: SIZE.base,
          color: ROLE.textMuted,
          textAlign: 'center',
        }}
      >
        Watch the complete build →
      </div>
    </div>
  );
};
