import React from 'react';
import {AbsoluteFill, Audio, Series, staticFile} from 'remotion';
import {manifest} from './timeline';
import {NarrationSegment} from './NarrationSegment';
import {EndCard2} from './components/EndCard2';

/**
 * The whole video. One <Series> so every offset is derived, never hand-typed.
 * There is no separate title card or silent pre-roll: segment 0's own real
 * audio+picture start at frame 0, and its on-screen text comes from its own
 * .srt cues (see SubtitleCaptions). End card 2.0 wraps up. Music bed ducks
 * under speech via volume curves.
 */
export const FinalVideo: React.FC = () => {
  return (
    <AbsoluteFill>
      <Audio
        src={staticFile('audio/bed.wav')}
        volume={(f) => {
          const sec = f / manifest.fps;
          if (sec < 8) return 0.15;
          if (sec < 9) return 0.15 + (sec - 8) * 0.15;
          return 0.3;
        }}
      />

      <Series>
        {manifest.segments.map((segment, i) => (
          <Series.Sequence key={segment.id} durationInFrames={segment.durationInFrames}>
            <NarrationSegment
              segment={segment}
              segmentIndex={i}
              totalSegments={manifest.segments.length}
              progressUnit={manifest.progressUnit}
            />
          </Series.Sequence>
        ))}
        <Series.Sequence durationInFrames={manifest.endCardFrames}>
          <EndCard2
            progressLabel={manifest.endCard.progressLabel}
            headline={manifest.endCard.headline}
            subline={manifest.endCard.subline}
          />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
