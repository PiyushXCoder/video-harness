import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {MOCHA, FONT} from '../palette';

type BossFrameProps = {
  label: string;
  hpBar: boolean;
  // Local frames, each keyed in the manifest to the cue that speaks it.
  // null = never show. These replaced booleans + hardcoded fractions, which
  // put the slow/fast peers on screen ~10s before they were mentioned and
  // fired the power-up 9s before "change the whole strategy" is spoken.
  fastPeersFrame: number | null;
  slowPeerFrame: number | null;
  powerUpFrame: number | null;
  durationInFrames: number;
  // Per-video copy for the slow lane, e.g. "peer[7] — crawling...".
  slowPeerLabel?: string;
  // Per-video copy for the power-up banner.
  powerUpLabel?: string;
};

export const BossFrame: React.FC<BossFrameProps> = ({
  label, hpBar, fastPeersFrame, slowPeerFrame, powerUpFrame, durationInFrames,
  slowPeerLabel, powerUpLabel,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const entrance = spring({
    frame,
    fps,
    config: {damping: 14, stiffness: 160},
  });

  const hpValue = interpolate(
    frame,
    [0, durationInFrames * 0.3, durationInFrames * 0.7, durationInFrames],
    [100, 60, 20, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const showFastPeers = fastPeersFrame !== null && frame >= fastPeersFrame;
  const showSlowPeer = slowPeerFrame !== null && frame >= slowPeerFrame;
  const isPowerUp = powerUpFrame !== null && frame >= powerUpFrame;
  const powerUpFlash = isPowerUp && powerUpFrame !== null && frame < powerUpFrame + 6
    ? interpolate(frame, [powerUpFrame, powerUpFrame + 6], [0.8, 0], {
        extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      })
    : 0;

  return (
    <AbsoluteFill>
      {isPowerUp && (
        <AbsoluteFill style={{
          backgroundColor: MOCHA.yellow, opacity: powerUpFlash,
        }} />
      )}

      <div style={{
        position: 'absolute', top: 80, left: 80, right: 80,
        opacity: entrance,
      }}>
        <div style={{
          fontFamily: FONT, fontSize: 18, color: MOCHA.red,
          fontWeight: 700, letterSpacing: '2px', marginBottom: 12,
          textTransform: 'uppercase',
        }}>
          FINAL BOSS
        </div>
        <div style={{
          fontFamily: FONT, fontSize: 32, color: MOCHA.text, fontWeight: 700,
          marginBottom: 16,
        }}>
          {label}
        </div>

        {hpBar && (
          <div style={{
            width: '100%', height: 20, borderRadius: 10,
            backgroundColor: MOCHA.surface0, overflow: 'hidden',
            border: `1px solid ${MOCHA.surface1}`,
          }}>
            <div style={{
              width: `${hpValue}%`, height: '100%',
              backgroundColor: hpValue > 50 ? MOCHA.green
                : hpValue > 20 ? MOCHA.yellow : MOCHA.red,
              borderRadius: 10,
              transition: 'width 0.3s, background-color 0.3s',
            }} />
          </div>
        )}
        {hpBar && (
          <div style={{
            fontFamily: FONT, fontSize: 14, color: MOCHA.subtext0,
            marginTop: 6, textAlign: 'right',
          }}>
            HP: {Math.round(hpValue)}%
          </div>
        )}
      </div>

      {/* top: 260, not 200 -- the HP readout sits at the right end of the bar
          around y=200 and the bolts landed on top of it. */}
      {showFastPeers && fastPeersFrame !== null && (
        <div style={{
          position: 'absolute', top: 260, right: 120,
          display: 'flex', gap: 12,
        }}>
          {['⚡', '⚡', '⚡'].map((e, i) => {
            const pop = spring({
              frame: frame - fastPeersFrame - i * 6,
              fps,
              config: {damping: 10, stiffness: 250},
            });
            return (
              <span key={i} style={{
                fontSize: 28, transform: `scale(${pop})`,
              }}>{e}</span>
            );
          })}
        </div>
      )}

      {showSlowPeer && slowPeerFrame !== null && (
        <div style={{
          position: 'absolute', bottom: 140, left: 120,
          opacity: interpolate(frame - slowPeerFrame, [0, 6], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          }),
        }}>
          <span style={{fontSize: 28}}>🐢</span>
          <span style={{
            fontFamily: FONT, fontSize: 14, color: MOCHA.subtext0,
            marginLeft: 8,
          }}>
            {slowPeerLabel}
          </span>
        </div>
      )}

      {isPowerUp && powerUpFrame !== null && (
        // Bottom band, not dead center -- this used to sit directly on the
        // speaker's face in a talking-head shot.
        <div style={{
          position: 'absolute', top: '78%', left: '50%',
          transform: 'translate(-50%, -50%)',
          fontFamily: FONT, fontSize: 24, color: MOCHA.yellow,
          fontWeight: 700, letterSpacing: '2px',
          opacity: interpolate(frame, [powerUpFrame, powerUpFrame + 10], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          }),
          textShadow: `0 0 30px ${MOCHA.yellow}66, 0 2px 12px rgba(0,0,0,0.8)`,
        }}>
          {powerUpLabel}
        </div>
      )}
    </AbsoluteFill>
  );
};
