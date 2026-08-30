import React from 'react';
import {Composition} from 'remotion';
import {FinalVideo} from './FinalVideo';
import {ReelEndCard} from './compositions/ReelEndCard';
import {Hook} from './compositions/Hook';
import {manifest} from './timeline';
import {hookManifest} from './hook';
import {discoverClips} from './clips';

/**
 * NOTHING PER-VIDEO GOES IN THIS FILE.
 *
 * The three compositions below are structural and belong to the template: the
 * body, the opening, and the vertical end card. Everything else is one
 * episode's clips, which live in ./compositions (gitignored) and register
 * THEMSELVES by exporting a `clipConfig` -- see ./clips.ts. Adding a clip
 * never means editing Root.tsx, and deleting one never leaves a dead id
 * behind pointing at a file that is no longer on disk.
 */
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

      {discoverClips().map((clip) => (
        <Composition
          key={clip.id}
          id={clip.id}
          component={clip.component}
          durationInFrames={clip.durationInFrames}
          fps={clip.fps}
          width={clip.width}
          height={clip.height}
        />
      ))}
    </>
  );
};
