# Color-mode benchmark

This benchmark measures `trace_image.py --mode color` on a synthetic dataset with exact ground truth.

## Dataset

`gen.py` makes 16 kinds × 3 seeds = 48 cases. Each case has a degraded input (320 px) and a clean ground truth at 4×. Seeds 0–1 are the train split (for tuning). Seed 2 is the test split (held out).

| Kind | What it tests |
|---|---|
| flat, icon, logo, poster | Flat colors, sharp edges |
| grad_linear, grad_radial | Smooth gradients |
| paper | Paper texture under flat colors |
| woodcut | Dark key lines over flat colors |
| pointillism | Many small dots |
| close_colors | Two colors that are almost the same |
| soft | Blurred edges |
| jpeg | Strong JPEG artifacts |
| photo | A photo-like image with noise |
| alpha | An RGBA input with a transparent background |
| tiny | A very small input |
| many_colors | More colors than `--colors` |

```bash
python gen.py                          # make data/
python bench.py '{"colors": 16}' test res.json
python report.py res.json              # table by kind
```

`bench.py` runs the color path of `trace_image.py` with the parameters in the JSON (`colors`, `merge`, `sp`, `sr`, `detail`, `smooth`, `tol`, `lines`). It needs `cairosvg` (Linux or WSL; it does not load on Windows without Cairo).

## Metrics

The output SVG is rendered at 4× and compared with the ground truth.

| Metric | Meaning |
|---|---|
| de, de95 | Mean and 95th percentile of the CIEDE2000 color difference. Lower is better. Below 1 is not visible; below 3 is hard to see. |
| ssim | Structural similarity. Higher is better. |
| edge | Mean distance between the region borders (Lab jump > 10) of the output and of the ground truth, in input pixels. `nan` when the ground truth has no sharp borders. |
| regions | Number of closed paths in the SVG. |
| colors | Number of distinct fill colors. |
| kb, sec | SVG size and run time. |

## Baseline (v0.1.0, all splits)

`base_c16.json` uses 16 colors (the advice in SKILL.md). `base_c4.json` uses 4 colors (the CLI default).

| Kind | ΔE, 16 colors | ΔE, 4 colors | Regions, 16 | Regions, 4 |
|---|---|---|---|---|
| alpha | **43.26** | **43.25** | 1084 | 108 |
| photo | 6.22 | 8.36 | 42797 | 3614 |
| many_colors | 5.45 | **15.49** | 472 | 35 |
| paper | 4.28 | 5.41 | 3254 | 35 |
| jpeg | 2.43 | 3.47 | 908 | 38 |
| pointillism | 2.43 | 2.56 | 14357 | 1083 |
| woodcut | 1.92 | 1.41 | 6011 | 109 |
| grad_radial | 1.73 | 2.85 | 45 | 87 |
| grad_linear | 1.53 | 4.19 | 94 | 6 |
| soft | 1.45 | 2.78 | 70 | 8 |
| close_colors | 1.39 | 1.38 | 3 | 2 |
| icon | 1.31 | 0.95 | 891 | 26 |
| tiny | 1.09 | 1.42 | 294 | 9 |
| flat | 1.02 | 3.11 | 277 | 8 |
| poster | 0.88 | 3.80 | 956 | 13 |
| logo | 0.88 | 0.49 | 815 | 22 |
| **All** | **4.83** | **6.31** | **4520** | **325** |

Worst cases:

- **alpha:** the transparent background became black, because `load()` dropped the alpha channel. ΔE 43 with any number of colors.
- **photo, pointillism, paper:** 16 colors make thousands of small regions (up to 12 MB of SVG and 8 minutes for one photo).
- **many_colors:** 4 colors are not sufficient (ΔE 15.5).
- **Flat art with 16 colors** (icon, logo, flat, poster): the extra colors go to the antialiased edges. This makes 10–40× more regions than 4 colors, for the same or a worse ΔE.

## Tuning

Each candidate was run on the train split and compared with the baseline. Only a change that improves the train split is run on the test split.

| Candidate (train split, 16 colors) | ΔE | de95 | Regions | kB | Result |
|---|---|---|---|---|---|
| Baseline | 4.90 | 11.48 | 4492 | 1456 | |
| Composite transparent pixels over white | **2.28** | **5.61** | 4593 | 1486 | Adopted |
| Automatic number of colors, median error ≤ 3 | 2.71 | 7.56 | 6983 | 2344 | Rejected |
| Automatic number of colors, p95 error ≤ 12 | 2.30 | 5.64 | 7428 | 2487 | Rejected |
| Automatic number of colors, p97 error ≤ 15 | 2.24 | 5.79 | 7370 | 2455 | Rejected |

The automatic number of colors (all three rows include the white compositing) fixes `many_colors` (ΔE 5.7 → 2.0), but it makes worse gradients (ΔE 1.6 → 3.4) and gives 60% more regions and 1.7× larger SVG files than the white compositing alone. It is not adopted.

Test split (held out), with the adopted change:

| Test split | ΔE, 16 colors | de95, 16 colors | ΔE, 4 colors | de95, 4 colors |
|---|---|---|---|---|
| Baseline | 4.69 | 11.54 | 6.03 | 15.10 |
| Composite over white | **2.12** | **5.84** | **3.41** | **9.97** |

On the test split, the `alpha` case goes from ΔE 43.2 to 1.4 (16 colors) and from 42.9 to 1.2 (4 colors). The mean of the other 15 cases changes by less than 0.04 (k-means noise).

Result files: `base_c16.json`, `base_c4.json` (baseline, all splits), `white_c16_train.json`, `white_c16_test.json`, `white_c4_test.json`.

Not tested yet: the merge threshold (7.0), the mean-shift radii (4, 12), the `--lines` thresholds, and SVG gradients.
