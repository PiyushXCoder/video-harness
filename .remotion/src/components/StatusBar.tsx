import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {ROLE, FONT_DISPLAY, SIZE, WEIGHT} from '../design';

const BAR_HEIGHT = 56;
const GRID_COLS = 48;
const GRID_ROWS = 4;

type StatusBarProps = {
  statusText: string;
  progressPct: number;
  segmentFrame: number;
  segmentDuration: number;
  // What the progress counter is counting, e.g. {label: 'pieces', total: 24868}.
  // Omit to hide the counter -- this is per-video copy and must NOT be
  // hardcoded here; the template has no idea what your video counts.
  unit?: {label: string; total: number} | null;
};

export const StatusBar: React.FC<StatusBarProps> = ({
  statusText, progressPct, segmentFrame, segmentDuration, unit = null,
}) => {
  const frame = useCurrentFrame();
  const filledCount = Math.floor((progressPct / 100) * GRID_COLS * GRID_ROWS);

  return (
    <div style={{
      position: 'absolute', bottom: 0, left: 0, right: 0, height: BAR_HEIGHT,
      backgroundColor: ROLE.surface + 'ee',
      borderTop: `1px solid ${ROLE.border}`,
      display: 'flex', alignItems: 'center', padding: '0 24px', gap: 20,
      fontFamily: FONT_DISPLAY, fontSize: SIZE.sm,
    }}>
      <div style={{display: 'flex', gap: 2, flexShrink: 0}}>
        {Array.from({length: GRID_COLS * GRID_ROWS}).map((_, i) => (
          <div key={i} style={{
            width: 6, height: 6, borderRadius: 1,
            backgroundColor: i < filledCount ? ROLE.accent : ROLE.border,
            transition: 'background-color 0.1s',
          }} />
        ))}
      </div>

      {unit && (
        <div style={{color: ROLE.textMuted, fontSize: SIZE.xs, flexShrink: 0}}>
          {unit.label}: {Math.floor((progressPct / 100) * unit.total).toLocaleString()}
          {' / '}{unit.total.toLocaleString()}
        </div>
      )}

      <div style={{flex: 1}} />

      <div style={{
        color: ROLE.accent, fontSize: SIZE.xs, fontWeight: WEIGHT.semibold,
        letterSpacing: '0.5px',
      }}>
        {statusText}
      </div>
    </div>
  );
};
