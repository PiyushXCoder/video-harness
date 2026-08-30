import {Config} from '@remotion/cli/config';

// Final delivery is 2048x1280 (8:5) -- the screen recorder's native ratio, and
// the size every source already is, so nothing is scaled or cropped and code
// text stays pixel-perfect. See docs/remotion-video-guidelines.md.
Config.setVideoImageFormat('jpeg');
Config.setCodec('h264');

// Export on the NVIDIA GPU. Remotion's bundled FFmpeg has NVENC on Linux x64
// and it applies to h264/h265 only; anything else silently falls back to CPU.
// 'if-possible' keeps the project portable; pass
//   --hardware-acceleration=required
// on the command line when you want a run to FAIL rather than quietly drop to
// software encoding.
Config.setHardwareAcceleration('if-possible');

// Browser rendering is CPU/RAM-bound, not GPU-bound: each worker is a Chromium
// instance. 15 GiB RAM total on this machine, so cap it -- an unbounded
// concurrency will swap and end up slower than a lower number.
Config.setConcurrency(6);

// NO Config.setCrf() here: NVENC has its own rate control and Remotion
// silently falls back to software encoding if a CRF is set alongside
// hardware acceleration ("crf option is not supported with hardware
// acceleration"). This bit us on the very first render of this project --
// the log line is easy to miss among hundreds of "Encoded N/M" lines. If a
// render ever needs to run on CPU (hardware unavailable), set CRF via the
// CLI for that run instead: --crf=18.

Config.setPublicDir('..');
Config.setPublicLicenseKey('free-license');
