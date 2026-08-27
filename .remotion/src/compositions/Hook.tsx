import React from 'react';
import {
  AbsoluteFill,
  Audio,
  OffthreadVideo,
  Sequence,
  Series,
  staticFile,
} from 'remotion';
import {hookManifest} from '../hook';
import type {HookBeatData, HookCutawayData} from '../hook';
import {MOCHA} from '../palette';
import {Cutaway} from '../components/Cutaway';
import {MemeOverlay} from '../components/MemeOverlay';
import {Stamp} from '../components/Stamp';
import {EmojiBurst} from '../components/EmojiBurst';
import {SubtitleCaptions} from '../components/SubtitleCaptions';
import {BootTerminal} from '../components/BootTerminal';
import {HookText} from '../components/HookText';
import {CutawaySafeSequence} from '../components/CutawaySafe';

/**
 * A gate that is cutaway-safe only when the beat asked to be.
 *
 * The body enforces cutaway-safety unconditionally (a meme inset once
 * covered a sha256sum digest). The hook does not: it may deliberately lay
 * type over a montage shot, because whether the hook obeys the body's
 * layering rules is decided in plans/hook.md. `cutawaySafe: false` is
 * therefore a legal, recorded editorial choice -- not an oversight.
 */
const BeatLayer: React.FC<{
  from: number;
  durationInFrames: number;
  cutaways: HookCutawayData[];
  safe: boolean;
  children: React.ReactNode;
}> = ({from, durationInFrames, cutaways, safe, children}) =>
  safe ? (
    <CutawaySafeSequence
      from={from}
      durationInFrames={durationInFrames}
      cutaways={cutaways}
      layout="none"
    >
      {children}
    </CutawaySafeSequence>
  ) : (
    <Sequence from={from} durationInFrames={durationInFrames} layout="none">
      {children}
    </Sequence>
  );

/**
 * One beat of the hook.
 *
 * The base picture is OPTIONAL. A beat with `source: null` renders only its
 * background plus its layers, which is what makes a pure motion-graphics
 * hook expressible at all -- the body's NarrationSegment renders
 * <OffthreadVideo src={staticFile(segment.file)}> unconditionally and so
 * cannot represent one.
 */
const HookBeat: React.FC<{beat: HookBeatData}> = ({beat}) => {
  const safe = beat.cutawaySafe;

  return (
    <AbsoluteFill style={{backgroundColor: beat.background}}>
      {beat.source && (
        <OffthreadVideo
          src={staticFile(beat.source.src)}
          startFrom={beat.source.startFromFrame}
          muted={beat.source.muted}
        />
      )}

      {/* Cutaways are never gated -- they ARE the content. */}
      {beat.cutaways.map((c) => (
        <Sequence
          key={`${c.src}-${c.fromFrame}`}
          from={c.fromFrame}
          durationInFrames={c.durationInFrames}
          layout="none"
        >
          <Cutaway
            cutaway={{
              ...c,
              hold: false,
              muted: true,
            }}
          />
        </Sequence>
      ))}

      {beat.overlays.map((o) => (
        <BeatLayer
          key={`${o.src}-${o.fromFrame}`}
          from={o.fromFrame}
          durationInFrames={o.durationInFrames}
          cutaways={beat.cutaways}
          safe={safe}
        >
          <MemeOverlay overlay={o} />
        </BeatLayer>
      ))}

      {beat.cues.length > 0 && <SubtitleCaptions cues={beat.cues} />}

      {beat.bootTerminal && (
        <BeatLayer
          from={beat.bootTerminal.fromFrame}
          durationInFrames={beat.bootTerminal.durationInFrames}
          cutaways={beat.cutaways}
          safe={safe}
        >
          <BootTerminal
            lines={beat.bootTerminal.lines}
            durationInFrames={beat.bootTerminal.durationInFrames}
          />
        </BeatLayer>
      )}

      {beat.texts.map((t, i) => (
        <BeatLayer
          key={`text-${i}-${t.fromFrame}`}
          from={t.fromFrame}
          durationInFrames={t.durationInFrames}
          cutaways={beat.cutaways}
          safe={safe}
        >
          <HookText
            words={t.words}
            color={t.color}
            size={t.size}
            anchor={t.anchor}
            durationInFrames={t.durationInFrames}
          />
        </BeatLayer>
      ))}

      {beat.stamps.map((s) => (
        <BeatLayer
          key={`stamp-${s.text}-${s.fromFrame}`}
          from={s.fromFrame}
          // 35, not 30: Stamp fades out over frames 25->35, so a 30-frame
          // window clips its own exit. The body still uses 30.
          durationInFrames={35}
          cutaways={beat.cutaways}
          safe={safe}
        >
          <Stamp text={s.text} color={s.color} size={s.size} />
        </BeatLayer>
      ))}

      {beat.emoji.map((e) => (
        <BeatLayer
          key={`emoji-${e.emoji}-${e.fromFrame}`}
          from={e.fromFrame}
          durationInFrames={30}
          cutaways={beat.cutaways}
          safe={safe}
        >
          <EmojiBurst emoji={e.emoji} color={e.color} />
        </BeatLayer>
      ))}

      {beat.sfx.map((s, i) => (
        <Sequence
          key={`sfx-${i}-${s.fromFrame}`}
          from={s.fromFrame}
          durationInFrames={60}
          layout="none"
        >
          <Audio src={staticFile(s.file)} volume={Math.pow(10, s.gain / 20)} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

/**
 * The first ~30 seconds, as its own composition.
 *
 * Separate from <FinalVideo> on purpose. The hook is free to break the
 * body's rules -- text at frame centre, a beat with no speaker, decoration
 * over a cutaway -- and those freedoms should not leak into the 20 minutes
 * that follow. Every offset comes from a <Series> so nothing is hand-typed,
 * and every duration arrives from the manifest already in frames.
 *
 * Prepending this to the main timeline is deliberately NOT done yet -- that
 * flow changes separately.
 */
export const Hook: React.FC = () => {
  const music = hookManifest.music;

  return (
    <AbsoluteFill style={{backgroundColor: MOCHA.base}}>
      {music && (
        <Audio src={staticFile(music.file)} volume={Math.pow(10, music.gainDb / 20)} />
      )}

      <Series>
        {hookManifest.beats.map((beat) => (
          <Series.Sequence key={beat.id} durationInFrames={beat.durationInFrames}>
            <HookBeat beat={beat} />
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  );
};
