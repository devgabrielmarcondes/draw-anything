# Vectorization benchmark

Synthetic dataset with exact ground truth. Each case has a degraded input (320 px) and a clean ground truth (1280 px, 4×). 17 kinds × 3 seeds = 51 cases. Seeds 0–1 = train (for tuning). Seed 2 = test (held out).

Standard kinds: shapes, lineart, text, lineart on paper.
Unusual kinds: hairline (0.7 px), thick (18 px), parallel lines with small gaps, shallow crossings (8–20°), tight spiral, stipple (250 dots), hatching, JPEG q15, gaussian + salt-and-pepper noise, blur (σ 2.2), tiny input (106 px), inverted (light on dark), paper texture with uneven light, colored lines on a colored background.

Metrics (output SVG rendered at 4×, compared with the ground truth):
- IoU: overlap of ink areas.
- chamfer: mean distance between output and ground-truth edges, in input pixels.
- h95: 95th percentile of the same distance (worst-case shape error).
- euler: |Euler number difference| (wrong holes or extra/missing parts = topology errors).
- nseg, kb, sec: complexity, file size, run time.

Run:
```bash
python gen.py                          # makes data/
python bench.py '{}' all results.json  # '{}' = parameters, e.g. '{"err": 0.6}'
python report.py results.json
```
The scripts find `data/` and `skills/draw-anything/scripts` relative to their own location. You can run them from any directory.
