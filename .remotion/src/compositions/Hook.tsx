import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Sequence,
  Series,
  interpolate,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import {hookManifest} from '../hook';
import type {HookBeatData, HookCutawayData} from '../hook';
import {ArchiveFrame} from '../components/ArchiveFrame';
import {MemeOverlay} from '../components/MemeOverlay';
import {Stamp} from '../components/Stamp';
import {EmojiBurst} from '../components/EmojiBurst';
import {SubtitleCaptions} from '../components/SubtitleCaptions';
import {BootTerminal} from '../components/BootTerminal';
import {HookText} from '../components/HookText';
import {CutawaySafeSequence} from '../components/CutawaySafe';
import {MOTION, ROLE, resolveColor} from '../design';

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
  const frame = useCurrentFrame();

  // Clamped at both ends -- an unclamped interpolate drifts in exactly the
  // frames nobody previews (CLAUDE.md).
  const fadeIn =
    beat.fadeInFrames > 0
      ? interpolate(frame, [0, beat.fadeInFrames], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })
      : 1;

  return (
    <AbsoluteFill style={{backgroundColor: resolveColor(beat.background), opacity: fadeIn}}>
      {beat.source && (
        <ArchiveFrame
          source={beat.source}
          motion={beat.motion}
          grade={beat.grade}
          durationInFrames={beat.durationInFrames}
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
          <ArchiveFrame
            source={{
              src: c.src,
              startFromFrame: c.startFromFrame,
              srcDurationInFrames: c.srcDurationInFrames,
              muted: true,
              playbackRate: 1,
              inset: c.inset,
            }}
            motion={{kind: 'none', from: 1, to: 1}}
            grade={c.grade}
            durationInFrames={c.durationInFrames}
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
            scrim={t.scrim}
            durationInFrames={t.durationInFrames}
          />
        </BeatLayer>
      ))}

      {beat.stamps.map((s) => (
        <BeatLayer
          key={`stamp-${s.text}-${s.fromFrame}`}
          from={s.fromFrame}
          // MOTION.minTextFrames, not a local number: DESIGN.md 10.8 requires
          // on-screen text to survive 2s, and Stamp now anchors its own exit
          // ramp to the end of the window it is given, so the two can no
          // longer disagree. This beat carries no stamps today, so the change
          // does not re-time the rendered hook.
          durationInFrames={MOTION.minTextFrames}
          cutaways={beat.cutaways}
          safe={safe}
        >
          <Stamp
            text={s.text}
            color={s.color}
            size={s.size}
            durationInFrames={MOTION.minTextFrames}
          />
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
          durationInFrames={s.durationInFrames}
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
  const audio = hookManifest.audio ?? [];

  return (
    <AbsoluteFill style={{backgroundColor: ROLE.bg}}>
      {music && (
        <Audio src={staticFile(music.file)} volume={Math.pow(10, music.gainDb / 20)} />
      )}

      {/* Voice and beds sit OUTSIDE the <Series>, on the hook's own
          timeline. A beat's own sfx are clipped to that beat by its
          <Series.Sequence>, so anything crossing a cut -- a chant running
          from beat 3 into beat 5, a 7.6s riser under a 2.8s beat -- can only
          live here. */}
      {audio.map((v, i) => (
        <Sequence
          key={`${v.kind}-${i}-${v.fromFrame}`}
          from={v.fromFrame}
          durationInFrames={v.durationInFrames}
          layout="none"
        >
          <Audio
            src={staticFile(v.file)}
            startFrom={v.startFromFrame}
            volume={(f) => {
              const g = Math.pow(10, v.gainDb / 20);
              const inG =
                v.fadeInFrames > 0
                  ? interpolate(f, [0, v.fadeInFrames], [0, 1], {
                      extrapolateLeft: 'clamp',
                      extrapolateRight: 'clamp',
                    })
                  : 1;
              const outG =
                v.fadeOutFrames > 0
                  ? interpolate(
                      f,
                      [v.durationInFrames - v.fadeOutFrames, v.durationInFrames],
                      [1, 0],
                      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
                    )
                  : 1;
              return g * inG * outG;
            }}
          />
        </Sequence>
      ))}

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
