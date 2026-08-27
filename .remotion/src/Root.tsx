import React from 'react';
import {Composition} from 'remotion';
import {FinalVideo} from './FinalVideo';
import {ReelEndCard} from './compositions/ReelEndCard';
import {Hook} from './compositions/Hook';
import {manifest} from './timeline';
import {hookManifest} from './hook';

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
      {/* The first ~30 seconds. Its own composition so the freedoms it takes
          (text at frame centre, a beat with no speaker) cannot leak into the
          body. Dims/fps/duration come from its own manifest -- run
          scripts/build_hook_manifest.py, or `python3 scripts/hook_lib.py
          --stub` for a placeholder. */}
      <Composition
        id="Hook"
        component={Hook}
        durationInFrames={hookManifest.totalDurationInFrames}
        fps={hookManifest.fps}
        width={hookManifest.width}
        height={hookManifest.height}
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
