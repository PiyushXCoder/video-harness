import React from 'react';
import {Composition} from 'remotion';
import {FinalVideo} from './FinalVideo';
import {manifest} from './timeline';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="FinalVideo"
      component={FinalVideo}
      durationInFrames={manifest.totalDurationInFrames}
      fps={manifest.fps}
      width={manifest.width}
      height={manifest.height}
    />
  );
};
