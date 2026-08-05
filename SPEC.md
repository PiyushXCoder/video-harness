# Machine Specification

Host: Jethalal (Arch Linux)

## OS
- Arch Linux, kernel 6.18.41-1-lts, x86_64

## CPU
- Intel Core i7-12700H (12th gen), 14 cores / 20 threads

## RAM
- 15 GiB total, 23 GiB swap

## GPU
- NVIDIA GeForce RTX 3050 Laptop, 4 GiB VRAM, driver 610.43.03
- Intel Iris Xe Graphics (integrated, Alder Lake-P)

## Disk
- `/` : 196G (121G free)
- `/home`: 468G (310G free)

## Implications for this project
- 4 GiB VRAM is tight — GPU-accelerated Manim/Remotion renders, cap concurrent render workers, watch OOM on heavy scenes.
- 14C/20T CPU good for parallel encode (ffmpeg) and Remotion CPU rendering.
- Hybrid GPU (Intel + NVIDIA) — for CUDA-dependent tools (e.g. some Manim/OpenGL, ffmpeg nvenc), confirm process runs on NVIDIA GPU (`prime-run`/`nvidia-smi` check), not the Intel iGPU.
- 15 GiB RAM — avoid running heavy render + browser (Remotion uses headless Chromium) + editor simultaneously; watch swap usage.
