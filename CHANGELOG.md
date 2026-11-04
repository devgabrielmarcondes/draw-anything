# Changelog

All notable changes to this project are in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- Benchmark: `bench.py` and `gen.py` use paths relative to their own directory. They no longer use `/home/claude/...` or `/tmp`.

## [0.1.0] - 2026-11-03

### Added
- First public release of the `draw-anything` skill.
- Methods: Potrace and Bézier vectorization, centerline strokes, Fourier series (epicycles), SDF, implicit, parametric and polar curves, Tupper's formula.
- Exports: MP4, GIF, transparent MOV/WebM, SVG and Desmos equations.
- Vectorization benchmark with a train/test split.
