import React from 'react';
import {AbsoluteFill, Audio, OffthreadVideo, Sequence, staticFile, useCurrentFrame} from 'remotion';
import type {CutawayData, SegmentData} from './timeline';
import {Cutaway} from './components/Cutaway';
import {MemeOverlay} from './components/MemeOverlay';
import {Stamp} from './components/Stamp';
import {NameTag} from './components/NameTag';
import {EmojiBurst} from './components/EmojiBurst';
import {BossFrame} from './components/BossFrame';
import {SubtitleCaptions} from './components/SubtitleCaptions';
import {PunchText} from './components/PunchText';
import {BootTerminal} from './components/BootTerminal';
import {Spotlight} from './components/Spotlight';
import {Callout} from './components/Callout';
import {BuildList} from './components/BuildList';
import {TwoColumn} from './components/TwoColumn';
import {TalkingHead} from './components/TalkingHead';
import {activeCutaway, CutawaySafeSequence} from './components/CutawaySafe';
import {MOTION, ROLE} from './design';

/**
 * Captions run continuously so no stretch of speech is ever bare, with two
 * exceptions:
 *
 *  - never over a Manim diagram, which carries its own captions and would
 *    end up double-captioned (a screencast is fine -- captions sit in the
 *    lower band, clear of terminal output);
 *  - never while a PunchText is on screen. The punch line quotes the same
 *    words, so running both would print the sentence twice at once. The
 *    punch takes over its moment and the captions resume after it.
 */
const CaptionsGate: React.FC<{
  cutaways: CutawayData[];
  cues: SegmentData['cues'];
  punchTexts: SegmentData['punchTexts'];
  position: SegmentData['captionPos'];
  builds: {fromFrame: number; durationInFrames: number}[];
}> = ({cutaways, cues, punchTexts, position, builds}) => {
  const frame = useCurrentFrame();
  // Captions belong to the SPEAKER, so they stop entirely while a cutaway is
  // up. That is stricter than the old rule (which only excluded Manim) and it
  // is the point: flank captions sit in the wall beside a face, and there is
  // no face during a screencast -- they would just be text over someone's
  // desktop, competing with the thing the cutaway exists to show.
  if (activeCutaway(frame, cutaways)) return null;
  const onScreen = (l: {fromFrame: number; durationInFrames: number}) =>
    frame >= l.fromFrame && frame < l.fromFrame + l.durationInFrames;
  if (punchTexts.some(onScreen)) return null;
  // A build list or a two-column IS the text layer for its moment. Running
  // captions underneath put a second block of words -- and, worse, the
  // caption's own side scrim -- straight over the list, which is exactly the
  // collision that showed up under the i3wm/old-configuration beat.
  if (builds.some(onScreen)) return null;
  return <SubtitleCaptions cues={cues} position={position} />;
};

/**
 * One narration beat: the base talking-head/screencast video plays start to
 * finish with its real audio, unconditionally, from frame 0 -- nothing waits
 * for anything else to finish first. Cutaways play unguarded; every
 * decorative overlay (stamps, emoji, name tags, boss frame,
 * memes) goes through CutawaySafeSequence so none of them can cover a
 * diagram or a screencast. Segments with `cues` also run word-pop captions
 * driven by their own .srt.
 */
export const NarrationSegment: React.FC<{
  segment: SegmentData;
  segmentIndex: number;
  totalSegments: number;
  progressUnit?: {label: string; total: number} | null;
}> = ({
  segment, segmentIndex, totalSegments, progressUnit = null,
}) => {
  const progressPct = ((segmentIndex + 0.5) / totalSegments) * 100;

  return (
    <AbsoluteFill style={{backgroundColor: ROLE.bg}}>
      {/* null for a picture-only montage (the showcase): there is no narration
          take, so the segment's picture comes entirely from its cutaways and
          its audio entirely from a manifest-level bed. */}
      {segment.file ? (
        <TalkingHead
          src={segment.file}
          punches={segment.punches}
          vignetteStrength={segment.vignette}
        />
      ) : null}

      {segment.cutaways.map((c) => (
        <Sequence
          key={`${c.src}-${c.fromFrame}`}
          from={c.fromFrame}
          durationInFrames={c.durationInFrames}
          layout="none"
        >
          <Cutaway cutaway={c} />
        </Sequence>
      ))}

      {segment.overlays.map((o) => (
        <CutawaySafeSequence
          key={`${o.src}-${o.fromFrame}`}
          from={o.fromFrame}
          durationInFrames={o.durationInFrames}
          cutaways={segment.cutaways}
          layout="none"
        >
          <MemeOverlay overlay={o} />
        </CutawaySafeSequence>
      ))}

      {/* SPOTLIGHTS AND CALLOUTS ARE DELIBERATELY *NOT* CutawaySafe.
          Every other decorative layer is, because CLAUDE.md's rule is that
          nothing may be drawn on top of a cutaway -- a meme inset once covered
          a sha256sum digest. These two are the exception on purpose: they are
          not decoration ABOUT the beat, they are the mechanism for READING the
          cutaway, pointing at part of the very content the rule protects.
          A callout is a 3px border and a label in the margin, so it hides
          essentially nothing. A spotlight dims the rest of the picture, which
          is a real cost and the reason this exception is scoped to these two
          components rather than relaxed generally. */}
      {segment.spotlights.map((sp) => (
        <Sequence
          key={`spot-${sp.fromFrame}`}
          from={sp.fromFrame}
          durationInFrames={sp.durationInFrames}
          layout="none"
        >
          <Spotlight spotlight={sp} />
        </Sequence>
      ))}

      {segment.callouts.map((co) => (
        <Sequence
          key={`callout-${co.fromFrame}-${co.label}`}
          from={co.fromFrame}
          durationInFrames={co.durationInFrames}
          layout="none"
        >
          <Callout callout={co} />
        </Sequence>
      ))}

      {segment.buildLists.map((bl) => (
        <CutawaySafeSequence
          key={`build-${bl.fromFrame}`}
          from={bl.fromFrame}
          durationInFrames={bl.durationInFrames}
          cutaways={segment.cutaways}
          layout="none"
        >
          <BuildList buildList={bl} />
        </CutawaySafeSequence>
      ))}

      {segment.twoColumns.map((tc) => (
        <CutawaySafeSequence
          key={`twocol-${tc.fromFrame}`}
          from={tc.fromFrame}
          durationInFrames={tc.durationInFrames}
          cutaways={segment.cutaways}
          layout="none"
        >
          <TwoColumn twoColumn={tc} />
        </CutawaySafeSequence>
      ))}

      {segment.cues.length > 0 && (
        <CaptionsGate
          cutaways={segment.cutaways}
          cues={segment.cues}
          punchTexts={segment.punchTexts}
          position={segment.captionPos}
          builds={[...segment.buildLists, ...segment.twoColumns]}
        />
      )}

      {segment.bootTerminal && (
        <CutawaySafeSequence
          from={segment.bootTerminal.fromFrame}
          durationInFrames={segment.bootTerminal.durationInFrames}
          cutaways={segment.cutaways}
          layout="none"
        >
          <BootTerminal
            lines={segment.bootTerminal.lines}
            durationInFrames={segment.bootTerminal.durationInFrames}
          />
        </CutawaySafeSequence>
      )}

      {segment.punchTexts.map((pt) => (
        <CutawaySafeSequence
          key={`punch-${pt.fromFrame}`}
          from={pt.fromFrame}
          durationInFrames={pt.durationInFrames}
          cutaways={segment.cutaways}
          layout="none"
        >
          <PunchText
            words={pt.words}
            color={pt.color}
            size={pt.size}
            durationInFrames={pt.durationInFrames}
          />
        </CutawaySafeSequence>
      ))}

      {segment.stamps.map((s) => (
        <CutawaySafeSequence
          key={`stamp-${s.text}-${s.fromFrame}`}
          from={s.fromFrame}
          durationInFrames={MOTION.minTextFrames}
          cutaways={segment.cutaways}
          layout="none"
        >
          <Stamp
            text={s.text}
            color={s.color}
            size={s.size}
            durationInFrames={MOTION.minTextFrames}
          />
        </CutawaySafeSequence>
      ))}


      {segment.emoji.map((e) => (
        <CutawaySafeSequence
          key={`emoji-${e.emoji}-${e.fromFrame}`}
          from={e.fromFrame}
          durationInFrames={30}
          cutaways={segment.cutaways}
          layout="none"
        >
          <EmojiBurst emoji={e.emoji} color={e.color} />
        </CutawaySafeSequence>
      ))}

      {segment.nameTags.map((nt) => (
        <CutawaySafeSequence
          key={`nametag-${nt.name}-${nt.fromFrame}`}
          from={nt.fromFrame}
          durationInFrames={nt.durationInFrames}
          cutaways={segment.cutaways}
          layout="none"
        >
          <NameTag name={nt.name} durationInFrames={nt.durationInFrames} />
        </CutawaySafeSequence>
      ))}

      {segment.bossFrame && (
        <CutawaySafeSequence
          from={segment.bossFrame.fromFrame}
          durationInFrames={segment.bossFrame.durationInFrames}
          cutaways={segment.cutaways}
          layout="none"
        >
          <BossFrame
            label={segment.bossFrame.label}
            hpBar={segment.bossFrame.hpBar}
            fastPeersFrame={segment.bossFrame.fastPeersFrame}
            slowPeerFrame={segment.bossFrame.slowPeerFrame}
            powerUpFrame={segment.bossFrame.powerUpFrame}
            slowPeerLabel={segment.bossFrame.slowPeerLabel}
            powerUpLabel={segment.bossFrame.powerUpLabel}
            durationInFrames={segment.bossFrame.durationInFrames}
          />
        </CutawaySafeSequence>
      )}

      {segment.sfx.map((s, i) => (
        <Sequence
          key={`sfx-${i}-${s.fromFrame}`}
          from={s.fromFrame}
          durationInFrames={60}
          layout="none"
        >
          <Audio
            src={staticFile(s.file)}
            volume={(f) => {
              const dbGain = s.gain;
              return Math.pow(10, dbGain / 20);
            }}
          />
        </Sequence>
      ))}

      {/* The status bar and its progress strip are deliberately NOT rendered.
          A permanent green bar across the bottom of every frame reads as a
          UI chrome overlay, not as a film -- it competes with the footage in
          exactly the zone DESIGN.md reserves for captions, and it is on screen
          100% of the runtime, which no functional element earns. The component
          is kept for other videos. */}
    </AbsoluteFill>
  );
};
