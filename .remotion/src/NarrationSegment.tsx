import React from 'react';
import {AbsoluteFill, Audio, OffthreadVideo, Sequence, staticFile, useCurrentFrame} from 'remotion';
import type {CutawayData, SegmentData} from './timeline';
import {Cutaway} from './components/Cutaway';
import {MemeOverlay} from './components/MemeOverlay';
import {Stamp} from './components/Stamp';
import {NameTag} from './components/NameTag';
import {EmojiBurst} from './components/EmojiBurst';
import {BossFrame} from './components/BossFrame';
import {StatusBar} from './components/StatusBar';
import {SubtitleCaptions} from './components/SubtitleCaptions';
import {PunchText} from './components/PunchText';
import {BootTerminal} from './components/BootTerminal';
import {activeCutaway, CutawaySafeSequence} from './components/CutawaySafe';
import {ROLE} from './design';

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
}> = ({cutaways, cues, punchTexts}) => {
  const frame = useCurrentFrame();
  const active = activeCutaway(frame, cutaways);
  if (active?.src.startsWith('manim/')) return null;
  const punchOnScreen = punchTexts.some(
    (p) => frame >= p.fromFrame && frame < p.fromFrame + p.durationInFrames,
  );
  if (punchOnScreen) return null;
  return <SubtitleCaptions cues={cues} />;
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
      <OffthreadVideo src={staticFile(segment.file)} />

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

      {segment.cues.length > 0 && (
        <CaptionsGate
          cutaways={segment.cutaways}
          cues={segment.cues}
          punchTexts={segment.punchTexts}
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
          durationInFrames={30}
          cutaways={segment.cutaways}
          layout="none"
        >
          <Stamp text={s.text} color={s.color} size={s.size} />
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

      <StatusBar
        statusText={segment.statusBar}
        progressPct={progressPct}
        segmentFrame={0}
        segmentDuration={segment.durationInFrames}
        unit={progressUnit}
      />
    </AbsoluteFill>
  );
};
