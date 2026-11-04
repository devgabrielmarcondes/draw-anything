---
name: draw-anything
description: Draws or exactly copies any image with math. Methods are Bézier vectorization, Fourier series (epicycles), signed distance functions (SDF), implicit/parametric/polar equations, Tupper's formula and other methods. Gives images and animations for social media and video editors (Reels, TikTok, Shorts, YouTube, transparent .mov/.webm), plus Desmos equations or GLSL. Use this skill when the user asks to draw, copy, trace, illustrate or animate something "with math", "with equations", "with Fourier", "with rotating circles", "with SDF", "in Desmos", "with Tupper's formula", or asks for math art, generative art, a name/logo/signature in epicycles, an image changed into equations, or visual math content, also when no method name is given.
---

# Draw Anything

Change a request into a math drawing, and give the math with it. Users are
often content creators and video editors. Give files in the correct format, and
explain the method in simple words.

## Procedure

1. Find the subject, the destination (Reels, post, YouTube, video overlay), static or animated, and the colors. If data is missing, use defaults (square, dark theme). Tell the user the defaults. Do not ask many questions.
2. Select the method (table below). If the user names a method, use it.
3. If the user gives an image, copy it with `trace_image.py`. A copy is more accurate than a new drawing.
4. If there is no image, make the geometry yourself (see "Draw without an image").
5. Make a fast preview (540 px, few frames). Look at it with the image viewer. Correct the proportions, the framing and the colors. Do this again until the result is good.
6. Make the final file at the requested size.
7. Put the files in the output folder and present them. Give a short reply: method, main parameters, and a ready caption.

## Method selection

| Request | Method | Script |
|---|---|---|
| Copy an image (drawing, logo, lettering, silhouette, illustration, photo) | Bézier (Potrace), Fourier per contour for animation | `trace_image.py` |
| Name, signature, new outline, "drawn by circles" | Fourier | `fourier_draw.py` |
| Filled shapes: icon, mascot, logo, scene, pattern, mandala | SDF | `sdf.py` (library) |
| Equation as the subject, famous curve, filled region | Implicit | `curves.py` |
| Spiral, rose, Lissajous, spirograph | Parametric/polar | `curves.py` |
| Pixel art, "formula that draws itself" | Tupper | `tupper.py` |
| Fractal, plant, flow field | Other | your own code (`references/methods.md` §7) |

Fourier alone cannot copy sharp corners exactly (Gibbs effect). For an exact copy, use Bézier. Use Fourier for the animation.

## Scripts

All scripts are in `scripts/`. Run a script with `--help` for all options. Common options:
`--size` (reels, post, square, youtube, thumb, 4k or WxH), `--theme` (dark, light, neon, blueprint, paper), `--transparent`.
Dependencies: numpy, matplotlib, Pillow, imageio/ffmpeg, OpenCV, scikit-image, `potracer` (the script installs it with pip if it is missing).

**Copy an image:**
```bash
python scripts/trace_image.py drawing.jpg --svg d.svg --png d.png --desmos d.txt
python scripts/trace_image.py drawing.jpg --anim d.mp4 --anim-style fourier --centerline --size reels
python scripts/trace_image.py sketch.png --centerline --svg sketch.svg      # editable strokes
python scripts/trace_image.py logo.png --mode color --colors 5 --svg logo.svg
python scripts/trace_image.py photo.jpg --mode edges --anim lines.mp4
```
- `--mode ink` (default): line art, logos, lettering, silhouettes, screenshots. It finds light-on-dark images and removes black bars.
- `--mode color --colors N`: illustrations, prints, paintings, icons, photos. Use 12–16 colors for artworks and photos. Add `--lines` for prints, comics and ink art: it adds top layers for the thin dark outlines and the small light details (foam, stars, highlights). `--detail 1` keeps more small details.
- `--mode edges`: changes a photo into a line drawing.
- `--centerline`: for line art, sketches, handwriting and signatures. Each stroke becomes one editable SVG path with its stroke width (as a pen line in Illustrator/Figma/Inkscape). Junctions, crossings and sharp corners are repaired, straight parts become exact lines, and the stroke ends (round/square) are found from the ink. Override with `--cap` and `--join`. Without `--centerline`, the SVG has filled outlines (best for logos, lettering, silhouettes).
- `--anim-style pen` draws the Bézier curves and then shows the fill. `--anim-style fourier` uses one epicycle chain for each contour or stroke. In color mode, the epicycles draw the longest region outlines (`--max-strokes`, default 800) and then the color vector fades in.
- `--keep-colors` keeps the original colors (ink mode). `--detail N` ignores small spots. `--smooth 0` keeps sharp corners.
- The script prints the accuracy (IoU) and the edge deviation in pixels. For strokes, the edge deviation is the better value: a mean below ~0.8 px is a very accurate copy.
- The script prints the accuracy. Good values: more than 95% for silhouettes and logos, 88–92% for thin outlines, 80–88% for `--centerline` (each stroke has one width). Edge pixels decrease the IoU. In edges mode, the value is not useful. If the value is low, look at the copy and adjust `--threshold` or `--detail`.
- Show the copy next to the original before you make the animation.

**Fourier:** each separate contour gets its own series, thus no lines connect the parts. `--single-line` gives the "one pen stroke" style.
```bash
python scripts/fourier_draw.py --text "Ana" --terms 300 --anim ana.mp4 --size reels --png ana.png
python scripts/fourier_draw.py --svg-path "M100 30 C 160 -20 220 60 100 170 C -20 60 40 -20 100 30 Z" \
       --terms 40 --png heart.png --desmos heart.txt
```
Inputs: `--svg-path`, `--svg-file`, `--text`, `--points` (JSON). Outputs: `--png` (`--fill`), `--anim`, `--svg`, `--desmos` (t from 0 to 1), `--json`.

**SDF:** import it as a library in a short script.
```python
import sys; sys.path.insert(0, "<skill-folder>/scripts")
from sdf import *
P = grid("square", scale=1.2)
body = ellipse(P, 0.6, 0.45)
ears = triangle(mirror_x(P), (0.15, 0.25), (0.5, 0.15), (0.45, 0.72))
cat = smooth_union(body, ears, 0.06)
eyes = circle(translate(mirror_x(P), 0.22, 0.05), 0.07)
render([(cat, "#2b2d42", {"shadow": (0.02, -0.03, 0.05)}), (eyes, "#ffd23f")], "cat.png", theme="paper")
```
The `sdf.py` docstring lists the primitives, operations and layer options. Animation: `animate(lambda t: [layers], "out.mp4", frames=120)`. For Shadertoy/GLSL, read `references/glsl.md`.

**Curves:** the variable `a` goes from 0 to 1 during the animation. Use `::#hex` to set a color.
```bash
python scripts/curves.py --region "(x**2+y**2-1)**3 - x**2*y**3::#e63946" \
       --range -1.6,1.6,-1.3,1.5 --caption '$(x^2+y^2-1)^3 = x^2y^3$' --png heart.png
python scripts/curves.py --polar "1+0.3*cos(7*th+6.283*a)" --anim flower.mp4 --size reels
```

**Tupper:**
```bash
python scripts/tupper.py encode --text "HELLO" --png tupper.png --out k.txt
python scripts/tupper.py encode --ascii drawing.txt --png art.png --out k.txt   # '#' and '.'
python scripts/tupper.py classic --png formula.png
```
Encode checks itself with the real formula. Give the full k in the .txt file.

## Output for video editors

- Social media: `.mp4` (H.264). Slack, email, README: `.gif` (540 px maximum).
- Overlay on footage: use `--transparent` with `.mov` (ProRes 4444 with alpha), `.webm` (VP9 with alpha) or a folder name (PNG sequence). Premiere, DaVinci, After Effects and Final Cut accept the `.mov`. If an editor does not accept alpha video, use the PNG sequence.
- A loop is seamless if the animation uses `a` only in sin/cos(2π·a).
- For more tips (safe areas, durations, series ideas), read `references/creator-playbook.md`.

## Draw without an image

- Divide the subject into 3 to 8 simple shapes (cat = ellipse + 2 triangles + circles).
- Use `mirror_x` for symmetric subjects.
- For Fourier, write a closed SVG path in a 0–200 box with C curves.
- For Tupper, draw the bitmap in ASCII (17 rows, 106 columns maximum).
- Make sure that a person can identify the subject immediately in each preview.

## Limits

Draw original designs, the user's own art and logos, generic shapes and public-domain works. Do not copy or trace characters, mascots, logos or artworks that belong to other persons, also when the user gives the image. Do not make "similar" versions of them. Offer an original design. Copy photos of real persons only if the user owns the photo or has permission.

## Reply

Keep the reply short: what you drew, the method and why (one sentence), the main parameters (terms, equation, short k) and a ready caption. Offer one useful variation in one line.
