import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {SIZE, resolveColor, glow} from '../design';

interface Props {
  emoji: string;
  color?: string;
}

export const EmojiBurst: React.FC<Props> = ({
  emoji,
  color = 'text',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const progress = spring({
    frame,
    fps,
    config: {damping: 8, stiffness: 300, mass: 0.4},
  });
  const scale = progress;
  const opacity = frame < 5 ? progress : 1 - Math.max(0, (frame - 30) / 10);

  return (
    // Upper-right, not dead center -- a talking-head shot keeps the face
    // roughly centered, and a 120px+ emoji at screen center landed directly
    // on it (found sitting on top of the speaker's face right after the
    // manim-overlap fix moved it off the diagram).
    <div style={{
      position: 'absolute', top: '22%', left: '80%',
      transform: `translate(-50%, -50%) scale(${scale * 1.5})`,
      fontSize: SIZE.emoji,
      opacity,
      filter: `drop-shadow(${glow(resolveColor(color), 30, '80')})`,
    }}>
      {emoji}
    </div>
  );
};
