# Changelog

All notable changes to this project are in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Tests: smoke test for each script, Tupper encode/decode round trip, benchmark regression gate (`slow`).
- CI on GitHub Actions: ruff and fast tests on each push, all tests each week.
- `scripts/package_skill.py` builds `dist/draw-anything.skill`.
- `benchmark/gen.py` has a `generate()` function that makes a subset of the dataset.
- Color-mode benchmark in `benchmark/color/`: 16 kinds of synthetic images, CIEDE2000, SSIM and edge metrics.

### Fixed
- Windows: scripts write text files (SVG, Desmos, JSON, Tupper k) in UTF-8. Before, `tupper.py encode --out` failed with `UnicodeEncodeError` on the `≤` character.
- Windows: scripts write console output in UTF-8. Before, `fourier_draw.py --help` and `tupper.py --help` failed when the output went to a pipe.
- `sdf.py --help` prints the library help. Before, it tried to save the demo image to a file named `--help`.
- `centerline.py --help` prints the library help. Before, it printed nothing.
- `trace_image.py` puts transparent pixels on a white background. Before, it dropped the alpha channel and transparent areas often became black. Color-mode benchmark, test split: ΔE 4.69 → 2.12 (16 colors).

### Changed
- `centerline.py` is 2.2× faster (the node centers are found in one pass). The strokes are identical.
- Benchmark: `bench.py` and `gen.py` use paths relative to their own directory. They no longer use `/home/claude/...` or `/tmp`.

## [0.1.0] - 2026-11-03

### Added
- First public release of the `draw-anything` skill.
- Methods: Potrace and Bézier vectorization, centerline strokes, Fourier series (epicycles), SDF, implicit, parametric and polar curves, Tupper's formula.
- Exports: MP4, GIF, transparent MOV/WebM, SVG and Desmos equations.
- Vectorization benchmark with a train/test split.
