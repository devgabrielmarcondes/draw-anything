# Creator playbook

## Sizes and safe areas
reels/story 1080×1920 · post 1080×1350 · square 1080×1080 · youtube 1920×1080 · thumb 1280×720 · 4k 3840×2160 · or WxH.
In 9:16, keep ~15% empty at the top and the bottom. The app interface covers these areas.

## Colors
Themes: dark, light, neon, blueprint, paper. For brand colors, ask for hex values. Use `::#hex` (curves.py), layer colors (sdf.py) or `--color` (trace_image.py).

## Animation
- Duration: 6–12 s, 30 fps.
- For fast tests, use `--size 540x960 --frames 60`. Make the final version after the test.
- Render time: ~0.1–0.3 s per frame at 1080p.
- Overlays: `--transparent` + `.mov`, `.webm` or a folder (PNG sequence).

## What to give with the drawing
1. The final file (PNG, MP4, MOV or GIF).
2. The math as text: equation, number of terms or the Tupper k (.txt).
3. A short caption that explains the method in simple words. Example: "120 circles turn, each on the tip of the previous circle. This is a Fourier series: any closed outline is a sum of rotations."
4. The Desmos version, if it is useful.

## Series ideas
"Your name in epicycles" · "One equation per day" · "Brand logo in SDF" · "Pixel art that is a number" (Tupper) · "5, 20, 100 Fourier terms" · "One shape, four methods" · "This drawing is math" (trace_image + Fourier).
