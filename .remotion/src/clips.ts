import type React from 'react';
import {VIDEO} from './design';

/**
 * Self-registration for per-video clips.
 *
 * WHY THIS EXISTS
 *
 * `.remotion/src/compositions/` is per-video and gitignored; `Root.tsx` is
 * template and tracked. Registering a clip by hand-editing Root.tsx therefore
 * wrote one episode's names into a tracked file — the last place episode
 * content leaked onto the template side, and one that produced a merge
 * conflict on every video and a Root.tsx full of dead ids referring to files
 * no longer on disk.
 *
 * So a clip declares itself. Export a `clipConfig` beside your component and
 * it is registered; delete the file and it is gone. Root.tsx never changes.
 *
 *     export const TitleCard: React.FC = () => { ... };
 *     export const clipConfig: ClipConfig = {
 *       id: 'title-card', durationInFrames: 90, component: TitleCard,
 *     };
 *
 * A module WITHOUT a `clipConfig` is ignored, which is how the two structural
 * compositions (Hook, ReelEndCard) stay explicitly registered in Root.tsx —
 * their dimensions come from a manifest rather than from a literal, so they
 * cannot describe themselves this way.
 */
export type ClipConfig = {
  /** The id passed to `npx remotion render <id>`. Conventionally kebab-case. */
  id: string;
  durationInFrames: number;
  /**
   * The component itself. Named here rather than guessed from the module's
   * exports: a clip that also exports a helper would be a coin flip, and a
   * missing component should be a type error at compile time, not a surprise
   * at bundle time.
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  component: React.FC<any>;
  // Default to the delivery frame (DESIGN.md 10.7: nothing is scaled). Override
  // only for a deliberately different deliverable, such as a vertical reel.
  fps?: number;
  width?: number;
  height?: number;
};

export type DiscoveredClip = Required<ClipConfig>;

/**
 * Every module in ./compositions that exports a `clipConfig`.
 *
 * `require.context` is a webpack feature and Remotion bundles with webpack
 * (@remotion/bundler). It is resolved at BUILD time, not at runtime, so the
 * directory is scanned when the bundle is made -- adding a file needs a
 * re-bundle, which is what `remotion render` and `remotion studio` already do.
 */
export function discoverClips(): DiscoveredClip[] {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ctx = (require as any).context('./compositions', false, /\.tsx$/);
  const clips: DiscoveredClip[] = [];

  for (const key of ctx.keys() as string[]) {
    const config: ClipConfig | undefined = ctx(key).clipConfig;
    if (!config) continue;
    if (!config.component) {
      throw new Error(`${key}: clipConfig.component is missing.`);
    }
    clips.push({
      id: config.id,
      durationInFrames: config.durationInFrames,
      component: config.component,
      fps: config.fps ?? VIDEO.fps,
      width: config.width ?? VIDEO.width,
      height: config.height ?? VIDEO.height,
    });
  }

  // Two clips claiming one id is a silent overwrite in the studio list, and
  // `remotion render <id>` would pick whichever won. Fail loudly instead.
  const seen = new Set<string>();
  for (const c of clips) {
    if (seen.has(c.id)) {
      throw new Error(`Two compositions both claim the id "${c.id}".`);
    }
    seen.add(c.id);
  }
  // Stable order regardless of filesystem enumeration, so the studio list and
  // `remotion compositions` do not reshuffle between runs.
  return clips.sort((a, b) => a.id.localeCompare(b.id));
}
