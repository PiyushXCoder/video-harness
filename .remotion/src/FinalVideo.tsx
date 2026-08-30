import React from 'react';
import {AbsoluteFill, Audio, interpolate, Sequence, Series, staticFile} from 'remotion';
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
      {/* Beds sit on the VIDEO's absolute timeline, outside the <Series>, and
          that is load-bearing: a bed placed inside a segment is clipped by
          that segment's <Series.Sequence>, so a 40s track under a 28s beat is
          silently truncated. Each cue carries its own gain in dB and its own
          fades, because the showcase runs the music loud and the Q4 tour sits
          it under speech -- one global duck curve cannot do both. */}
      {manifest.beds.map((bed, i) => (
        <Sequence
          key={`bed-${i}-${bed.fromFrame}`}
          from={bed.fromFrame}
          durationInFrames={bed.durationInFrames}
          layout="none"
        >
          <Audio
            src={staticFile(bed.file)}
            trimBefore={bed.startFromFrame}
            volume={(f) => {
              const linear = Math.pow(10, bed.gain / 20);
              const inGain = bed.fadeInFrames
                ? interpolate(f, [0, bed.fadeInFrames], [0, 1], {
                    extrapolateLeft: 'clamp',
                    extrapolateRight: 'clamp',
                  })
                : 1;
              const outGain = bed.fadeOutFrames
                ? interpolate(
                    f,
                    [bed.durationInFrames - bed.fadeOutFrames, bed.durationInFrames],
                    [1, 0],
                    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
                  )
                : 1;
              return linear * inGain * outGain;
            }}
          />
        </Sequence>
      ))}

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
