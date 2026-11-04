# Methods reference

Contents: 1 Fourier · 2 Bézier copy · 3 SDF · 4 Implicit · 5 Parametric/polar · 6 Tupper · 7 Other methods · 8 Combinations

## 1. Fourier series (epicycles)

A closed curve z(t) = x(t) + i·y(t), t ∈ [0, 2π), is z(t) = Σ c_k·e^{ikt}, with c_k = (1/N)·Σ z_n·e^{−2πikn/N} (the FFT of the points). Each term is a circle with radius |c_k|, frequency k and phase arg(c_k).

- Terms: 10–30 give a soft, stylized line. 80–200 give an accurate line. Short text: 100–300 in total. Detailed logos: 300–600.
- Each separate contour has its own series. The script divides the terms by perimeter.
- `--single-line` connects all contours with a minimum spanning tree. The bridges are short and the pen walks them out and back.
- Sharp corners need infinite terms (Gibbs effect). For an exact copy, use §2.
- Desmos: more than ~150 terms make the expression slow. Use 40–80 terms.
- SVG paths by hand: use a 0–200 box, C curves, and close with Z.

## 2. Exact image copy (Bézier / Potrace)

`trace_image.py`: image → mask (Otsu threshold, k-means colors or Canny edges) → Potrace (optimized cubic Bézier curves) → outputs.
Each segment is B(t) = (1−t)³P₀ + 3(1−t)²tP₁ + 3(1−t)t²P₂ + t³P₃, t ∈ [0, 1]. This is the default parametric domain in Desmos.

- Color mode: mean-shift filter (removes paper/photo texture, keeps edges) → k-means in Lab → near colors merged (ΔE < 7) → 1–3 px specks removed → layers stacked (each layer covers the next layers, thus no gaps).
- `--lines`: key lines = adaptive threshold on L, dark (L < 25th percentile), thin (morphological opening removes wide areas). Light details = white top-hat (9 px, contrast > 35, L > 150). Both are top layers.
- `--centerline`: skeleton → graph → near junctions merged, short spurs removed → at each junction, the most collinear branches continue (good continuation) → the distorted skeleton zone near a junction (~w / 2sin(φ/2)) is skipped → corner apex = intersection of the two arm lines → free ends extended to the real ink end → straight parts become lines, other parts Schneider Béziers. Width = ink amount / stroke length (antialiasing included). Cap shape is tested at each free end. The SVG has one `<path>` per stroke. For the Fourier animation, an open stroke is walked out and back.
- The fill SVG has one `<path>` per color (`id="color-N"`). The stroke SVG has one `<g id="strokes-N">`.
- Desmos becomes slow with more than ~1500 expressions. Increase `--detail` and `--tolerance`, or use fewer colors.

## 3. Signed distance functions (SDF)

d(p) < 0 inside, = 0 on the edge, > 0 outside.
Union = min(a,b). Intersection = max(a,b). Subtraction = max(a,−b).
Smooth union (k = blend radius): h = clamp(½ + ½(b−a)/k, 0, 1), d = mix(b, a, h) − k·h(1−h).

- Symmetry: `mirror_x(P)`. Draw only one side.
- Polar repetition: `repeat_polar(P, n)` + one petal = flower, gear or mandala.
- Outline: `onion(d, w)`. Stack it for rings.
- Morph: `lerp(d1, d2, t)`. For a loop, use t = ½ − ½·cos(2πa).
- Scale: `shape(scale(P, k)) * k` keeps the correct distance.
- `heart` is approximate inside. A large smooth_union can show small corners.

## 4. Implicit equations f(x, y) = 0

- `--implicit` draws the line (zero level). `--region` fills f ≤ 0.
- Examples: heart (x²+y²−1)³ − x²y³; lemniscate (x²+y²)² − 2(x²−y²); superellipse |x|^n + |y|^n − 1; folium x³+y³−3xy.
- min(f1, f2) = union. max(f1, f2) = intersection. The edge stays correct.
- Increase `--res` (default 1400) for thin curves or 4K.

## 5. Parametric and polar curves

- Lissajous (sin(a·t+δ), sin(b·t)). Rose r = cos(kθ). Spiral r = θ. Cardioid r = 1 − cos θ.
- Butterfly: r = e^{sin θ} − 2cos 4θ + sin⁵((2θ−π)/24), θ ∈ [0, 24π] (`--th-range 0,75.4`).
- Spirograph: x = (R−r)cos t + d·cos((R−r)t/r), y = (R−r)sin t − d·sin((R−r)t/r).
- Parametric input uses `;` between x(t) and y(t).

## 6. Tupper's formula

½ < ⌊mod(⌊y/H⌋·2^(−H⌊x⌋ − mod(⌊y⌋, H)), 2)⌋ draws the bitmap in the bits of k/H, for k ≤ y < k+H. Classic: H = 17, W = 106.

- `encode --text`: up to ~11 characters fit in 106 columns.
- `encode --image`: good for pixel art and high-contrast silhouettes. Photos become noise.
- `encode --ascii`: you can draw pixel art directly with `#` and `.`.
- k has ~500 digits. In a post, show the start and the end. Give the full .txt file.
- The axes convention is in the `tupper.py` docstring.

## 7. Other methods (write the code with numpy/matplotlib)

- L-systems: plants, trees, Koch/Hilbert curves. Good for growth animations.
- IFS / chaos game: Barnsley fern, Sierpiński triangle.
- Escape-time: Mandelbrot/Julia zoom (render time can be long).
- Flow fields: lines that follow a vector field.
- Maurer rose, times-table cardioid: high effect with little code.
- 3D: ray marching of SDFs in GLSL (`glsl.md`).

## 8. Combinations

- SDF drawing + Fourier animation of its outline: get the contour with `plt.contour(d, [0])` and use `--points`.
- Implicit curve as background + SDF subject in front.
- Tupper of a name + epicycles of the same name, side by side.
