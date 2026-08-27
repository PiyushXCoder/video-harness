import React from 'react';
import {Composition} from 'remotion';
import {FinalVideo} from './FinalVideo';
import {ReelEndCard} from './compositions/ReelEndCard';
import {manifest} from './timeline';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="FinalVideo"
        component={FinalVideo}
        durationInFrames={manifest.totalDurationInFrames}
        fps={manifest.fps}
        width={manifest.width}
        height={manifest.height}
      />
      <Composition
        id="ReelEndCard"
        component={ReelEndCard}
        durationInFrames={105}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
