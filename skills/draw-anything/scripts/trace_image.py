#!/usr/bin/env python3
"""
Exact image copy with math: vectorize to Bézier curves (Potrace). Optional:
one Fourier series for each contour, for the epicycle animation.

Use this script to COPY a drawing, logo, lettering, silhouette or pixel art
with the highest accuracy. Each contour becomes cubic Bézier curves (exact
parametric equations). No lines connect separate parts.

Modes:
  ink    (default) separates the ink/shape from the background with a
         threshold (automatic Otsu). For line art, logos, lettering, screenshots.
  color  reduces the image to N colors and vectorizes each layer (stacked, no
         gaps). For flat illustrations, icons, stickers, color pixel art.
  edges  Canny edges. Changes a photo into a line drawing.
  --centerline (ink/edges): line art becomes editable SVG STROKES (one path per
         stroke, with stroke-width), not filled outlines.

Outputs:
  --svg     exact vector (Bézier), scalable
  --png     image rendered from the equations
  --desmos  one parametric equation for each segment (t from 0 to 1)
  --anim    animation: 'pen' (Bézier strokes) or 'fourier' (parallel epicycles,
            one chain for each contour). Use --anim-style.
            .mov/.webm/.png-folder with --transparent for video editors.
  The script always prints the ACCURACY (IoU of the original and the copy).

Examples:
  python trace_image.py drawing.jpg --svg d.svg --png d.png --desmos d.txt
  python trace_image.py logo.png --mode color --colors 4 --png logo_vector.png
  python trace_image.py photo.jpg --mode edges --anim photo.mp4 --anim-style pen
  python trace_image.py signature.png --anim sig.mov --anim-style fourier --centerline --transparent
"""
import argparse, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from _common import parse_size, theme, make_figure, fit_view, save_animation


def _need_potrace():
    try:
        import potrace  # noqa
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "potracer",
                        "--break-system-packages"], check=False)
    import potrace
    return potrace


# ----------------------------------------------------------------------------
# Preprocessing
# ----------------------------------------------------------------------------

def load(path):
    """RGB array. Transparent pixels become white (dropping alpha can make them black)."""
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    return np.asarray(Image.alpha_composite(Image.new("RGBA", im.size, "white"), im).convert("RGB"))


def fit_resolution(rgb, max_side=1600, min_side=1200):
    """Enlarges small images (Potrace then finds smoother, more accurate curves).
    Reduces very large images to keep the number of curves low."""
    from PIL import Image
    h, w = rgb.shape[:2]; s = max(h, w)
    f = max_side / s if s > max_side else (min_side / s if s < min_side else 1.0)
    if f == 1.0:
        return rgb
    im = Image.fromarray(rgb).resize((round(w * f), round(h * f)), Image.LANCZOS)
    return np.asarray(im)


def crop_letterbox(rgb, tol=6, pad=0.05):
    """Removes solid bars at the edges (phone screenshots, video frames) and adds
    a 'pad' margin in the background color."""
    g = rgb.mean(2)
    rows = np.where(g.std(1) > tol)[0]; cols = np.where(g.std(0) > tol)[0]
    if not len(rows) or not len(cols):
        return rgb
    c = rgb[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    if c.shape == rgb.shape:
        return rgb
    border = np.concatenate([c[0], c[-1], c[:, 0], c[:, -1]])
    bgc = np.median(border, 0).astype(rgb.dtype)
    p = int(max(c.shape[:2]) * pad)
    out = np.empty((c.shape[0] + 2 * p, c.shape[1] + 2 * p, 3), rgb.dtype); out[:] = bgc
    out[p:p + c.shape[0], p:p + c.shape[1]] = c
    return out


def ink_mask(rgb, threshold=None, invert=None, blur=0.0):
    from skimage.filters import threshold_otsu, gaussian
    g = rgb.mean(2) / 255.0
    if blur:
        g = gaussian(g, blur)
    border = np.concatenate([g[0], g[-1], g[:, 0], g[:, -1]])
    if invert is None:                       # auto: the background is the main border color
        invert = np.median(border) < 0.5
    if invert:
        g = 1 - g
    t = threshold if threshold is not None else threshold_otsu(g)
    m = g < t
    # salt-and-pepper / sensor noise: many 1-4 px specks -> median filter and redo
    from scipy.ndimage import label
    lab, n = label(m)
    if n:
        sz = np.bincount(lab.ravel()); sz[0] = 0
        small = (sz[1:] <= 3e-5 * m.size).sum()             # ~40 px specks at 1200 px
        if small > max(50, 0.5 * n):
            import cv2
            g8 = cv2.medianBlur((g * 255).astype(np.uint8), 5) / 255.0
            g8 = gaussian(g8, 1.5)
            t = threshold if threshold is not None else threshold_otsu(g8)
            m = g8 < t
            lim = 3e-5 * m.size                       # drop remaining specks and pinholes
            for target in (True, False):
                lab, n = label(m == target)
                sz = np.bincount(lab.ravel()); sz[0] = 0
                tiny = (sz[lab] > 0) & (sz[lab] <= lim)
                m = np.where(tiny, not target, m)
    return m


def edge_mask(rgb, low=60, high=160, thickness=2):
    import cv2
    g = cv2.GaussianBlur(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), (5, 5), 0)
    e = cv2.Canny(g, low, high)
    if thickness > 1:
        e = cv2.dilate(e, np.ones((thickness, thickness), np.uint8))
    return e > 0


def color_layers(rgb, n=4, smooth=1, min_area=None, merge=7.0, sp=6, sr=16):
    """K-means in Lab color space to n colors, small specks merged into their
    neighbors. sp, sr: mean-shift radii.
    Returns [(hex_color, stacked_mask)], back to front."""
    import cv2
    from scipy.ndimage import label, distance_transform_edt
    h, w = rgb.shape[:2]
    # mean-shift flattens paper/photo texture but keeps edges and small details
    img = cv2.pyrMeanShiftFiltering(rgb, sp, sr) if smooth else rgb
    lab_img = cv2.cvtColor(img, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.3)
    _, lab, cen = cv2.kmeans(lab_img, n, None, crit, 4, cv2.KMEANS_PP_CENTERS)
    lab = lab.reshape(h, w)
    # merge near-identical colors (paper texture, soft gradients) to avoid blotches
    cen = cen.astype(float)
    alive = list(range(n))
    while len(alive) > 2:
        best = None
        for i in alive:
            for j in alive:
                if i < j:
                    d = np.linalg.norm(cen[i] - cen[j])
                    if best is None or d < best[0]:
                        best = (d, i, j)
        if best[0] > merge:
            break
        _, i, j = best
        ni, nj = (lab == i).sum(), (lab == j).sum()
        cen[i] = (cen[i] * ni + cen[j] * nj) / max(ni + nj, 1)
        lab[lab == j] = i; alive.remove(j)
    # despeckle: regions smaller than min_area take the label of the nearest large region
    min_area = min_area or max(3, int(3e-6 * h * w))
    keep = np.zeros((h, w), bool)
    for c in range(n):
        comp, k = label(lab == c)
        if k:
            sizes = np.bincount(comp.ravel()); sizes[0] = 0
            keep |= sizes[comp] >= min_area
    _, (ri, ci) = distance_transform_edt(~keep, return_indices=True)
    lab = lab[ri, ci]
    rgbc = cv2.cvtColor(cen.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_LAB2RGB)[0]
    area = np.bincount(lab.ravel(), minlength=n)
    order = [i for i in np.argsort(-area) if area[i] > 0]   # largest area first (background)
    layers = []
    for i, ci_ in enumerate(order):
        stacked = np.isin(lab, order[i:])     # each layer covers the next ones: no gaps
        layers.append(("#%02x%02x%02x" % tuple(int(v) for v in rgbc[ci_]), stacked))
    return layers


def key_lines(rgb, block=25, c=20, thick=5, min_px=30):
    """Thin dark outlines (the 'key block' of prints, comics, ink drawings).
    Returns (hex_color, mask) or None."""
    import cv2
    from scipy.ndimage import label
    L = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)[..., 0]
    dark = cv2.adaptiveThreshold(L, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV,
                                 block | 1, c) > 0
    dark &= L < np.percentile(L, 25)                        # real ink, not texture
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (thick, thick))
    wide = cv2.morphologyEx(dark.astype(np.uint8), cv2.MORPH_OPEN, k) > 0
    thin = dark & ~wide
    m = max(2, int(0.012 * max(thin.shape)))     # ignore the image border (scan edges, frames)
    thin[:m] = thin[-m:] = False; thin[:, :m] = thin[:, -m:] = False
    comp, n = label(thin, structure=np.ones((3, 3)))
    if not n:
        return None
    sz = np.bincount(comp.ravel()); sz[0] = 0
    thin &= sz[comp] >= min_px
    if thin.mean() < 1e-4:
        return None
    col = np.percentile(rgb[thin], 30, axis=0).astype(int)
    return ("#%02x%02x%02x" % tuple(col), thin)


def bright_spots(rgb, size=9, contrast=35, min_px=3):
    """Small light details on darker areas (foam, stars, highlights) that color
    clustering loses. Returns (hex_color, mask) or None."""
    import cv2
    from scipy.ndimage import label
    L = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)[..., 0]
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
    top = cv2.morphologyEx(L, cv2.MORPH_TOPHAT, k)
    m = (top > contrast) & (L > 150)                       # really light, not texture
    comp, n = label(m)
    if not n:
        return None
    sz = np.bincount(comp.ravel()); sz[0] = 0
    m &= (sz[comp] >= min_px) & (sz[comp] <= size * size)
    if m.mean() < 1e-5:
        return None
    col = np.percentile(rgb[m], 75, axis=0).astype(int)
    return ("#%02x%02x%02x" % tuple(col), m)


# ----------------------------------------------------------------------------
# Vectorization (Potrace)
# ----------------------------------------------------------------------------

def trace(mask, turdsize=4, alphamax=1.0, opttolerance=0.2):
    """Boolean mask -> list of closed curves. Each curve is a list of segments:
    ('C', p0, c1, c2, p3) cubic or ('L', p0, p1) line. Pixel units, y UP."""
    potrace = _need_potrace()
    h = mask.shape[0]
    # potracer uses False as "ink"
    path = potrace.Bitmap(~mask).trace(turdsize=turdsize, alphamax=alphamax,
                                       opticurve=True, opttolerance=opttolerance)
    flip = lambda p: np.array([p.x, h - p.y])
    curves = []
    for cv in path:
        cur = flip(cv.start_point); segs = []
        for s in cv.segments:
            if s.is_corner:
                c, e = flip(s.c), flip(s.end_point)
                segs.append(("L", cur, c)); segs.append(("L", c, e))
            else:
                c1, c2, e = flip(s.c1), flip(s.c2), flip(s.end_point)
                segs.append(("C", cur, c1, c2, e))
            cur = e
        curves.append(segs)
    return curves


def sample_curve(segs, per_seg=16):
    t = np.linspace(0, 1, per_seg, endpoint=False)[:, None]
    out = []
    for s in segs:
        if s[0] == "L":
            out.append(s[1] + (s[2] - s[1]) * t)
        else:
            p0, c1, c2, p3 = s[1:]
            out.append((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t ** 2 * c2 + t ** 3 * p3)
    return np.vstack(out)


def to_mpl_path(curves):
    from matplotlib.path import Path
    verts, codes = [], []
    for segs in curves:
        verts.append(segs[0][1]); codes.append(Path.MOVETO)
        for s in segs:
            if s[0] == "L":
                verts.append(s[2]); codes.append(Path.LINETO)
            else:
                verts += [s[2], s[3], s[4]]; codes += [Path.CURVE4] * 3
        verts.append(segs[0][1]); codes.append(Path.CLOSEPOLY)
    return Path(np.array(verts, float), codes)


# ----------------------------------------------------------------------------
# Outputs
# ----------------------------------------------------------------------------

def _num(v):
    """0.01 px precision, no trailing zeros: 12.50 -> 12.5, 3.00 -> 3, -0.00 -> 0."""
    t = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if t == "-0" else t


def svg_d(curves, h):
    parts = []
    f = lambda p: f"{_num(p[0])} {_num(h - p[1])}"
    for segs in curves:
        d = [f"M{f(segs[0][1])}"]
        for s in segs:
            d.append(f"L{f(s[2])}" if s[0] == "L" else f"C{f(s[2])} {f(s[3])} {f(s[4])}")
        parts.append("".join(d) + "Z")
    return "".join(parts)


def is_stroke(layer):
    return len(layer) > 2 and layer[2] == "stroke"


def to_mpl_open_path(segs, closed=False):
    from matplotlib.path import Path
    verts, codes = [segs[0][1]], [Path.MOVETO]
    for s in segs:
        if s[0] == "L":
            verts.append(s[2]); codes.append(Path.LINETO)
        else:
            verts += [s[2], s[3], s[4]]; codes += [Path.CURVE4] * 3
    if closed:
        verts.append(segs[0][1]); codes.append(Path.CLOSEPOLY)
    return Path(np.array(verts, float), codes)


def write_svg(layers, w, h, out, bg=None):
    """Fill layers become one <path> per color (evenodd). Stroke layers become one
    editable <path> per stroke, with stroke-width and round caps/joins."""
    body = [f'<rect id="background" width="{w}" height="{h}" fill="{bg}"/>'] if bg and bg != "none" else []
    for i, layer in enumerate(layers):
        col = layer[0]
        if is_stroke(layer):
            join = layer[3] if len(layer) > 3 else "round"
            g = [f'<path d="{svg_d([st[0]], h)[:-1] if not st[2] else svg_d([st[0]], h)}" '
                 f'stroke-width="{st[1]:.2f}" stroke-linecap="{st[3] if len(st) > 3 else "round"}"/>'
                 for st in layer[1]]
            body.append(f'<g id="strokes-{i + 1}" fill="none" stroke="{col}" '
                        f'stroke-linejoin="{join}" stroke-miterlimit="10">' + "".join(g) + "</g>")
        else:
            body.append(f'<path id="color-{i + 1}" d="{svg_d(layer[1], h)}" fill="{col}" fill-rule="evenodd"/>')
    open(out, "w", encoding="utf-8").write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
                         f'width="{w}" height="{h}">' + "".join(body) + "</svg>")


def desmos_lines(layers, scale=0.01, digits=2):
    """One expression for each segment. Béziers in Bernstein form, t from 0 to 1."""
    out = []
    n = lambda v: f"{v * scale:.{digits}f}"
    for layer in layers:
        curves = [st[0] for st in layer[1]] if is_stroke(layer) else layer[1]
        for segs in curves:
            for s in segs:
                if s[0] == "L":
                    (x0, y0), (x1, y1) = s[1], s[2]
                    out.append(f"\\left({n(x0)}+{n(x1 - x0)}t,{n(y0)}+{n(y1 - y0)}t\\right)")
                else:
                    P = s[1:]
                    bx = (f"(1-t)^3{n(P[0][0])}+3(1-t)^2t{n(P[1][0])}+3(1-t)t^2{n(P[2][0])}+t^3{n(P[3][0])}")
                    by = (f"(1-t)^3{n(P[0][1])}+3(1-t)^2t{n(P[1][1])}+3(1-t)t^2{n(P[2][1])}+t^3{n(P[3][1])}")
                    out.append(f"\\left({bx},{by}\\right)")
    return [l.replace("+-", "-") for l in out]


def _draw_layers(ax, layers, ppu, alpha=1.0):
    """ppu = output pixels per image pixel (scales the stroke widths)."""
    from matplotlib.patches import PathPatch
    for layer in layers:
        col = layer[0]
        if is_stroke(layer):
            join = layer[3] if len(layer) > 3 else "round"
            for st in layer[1]:
                segs, wd, cl = st[:3]
                cap = {"square": "projecting"}.get(st[3], st[3]) if len(st) > 3 else "round"
                ax.add_patch(PathPatch(to_mpl_open_path(segs, cl), facecolor="none", edgecolor=col,
                                       lw=wd * ppu * 0.72, capstyle=cap, joinstyle=join,
                                       alpha=alpha))
        elif layer[1]:
            ax.add_patch(PathPatch(to_mpl_path(layer[1]), facecolor=col, lw=0, alpha=alpha))


def _ppu(ax, size):
    x0, x1 = ax.get_xlim()
    return size[0] / (x1 - x0)


def rasterize(layers, w, h, bg, scale=1.0):
    """Renders the equations back to pixels (to measure accuracy)."""
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(w * scale / 100, h * scale / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, w); ax.set_ylim(0, h); ax.set_axis_off()
    fig.patch.set_facecolor(bg)
    _draw_layers(ax, layers, scale)
    fig.canvas.draw()
    img = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    plt.close(fig)
    return img


def render_png(layers, w, h, out, size, th, bg):
    import matplotlib.pyplot as plt
    size = size or (w, h)
    fig, ax = make_figure(size, {**th, "bg": bg})
    fit_view(ax, [0, w], [0, h], size, margin=0.0 if size == (w, h) else 0.06)
    _draw_layers(ax, layers, _ppu(ax, size))
    fig.savefig(out, facecolor=bg); plt.close(fig)


def animate_pen(layers, w, h, out, size, th, bg, frames=240, fps=30, hold=45):
    """A pen draws all curves at the same time (speed set by length). Fill layers
    then fade in. Stroke layers use their own widths and colors."""
    from matplotlib.collections import LineCollection
    polys = []
    for layer in layers:
        if is_stroke(layer):
            polys += [(layer[0], sample_curve(st[0], 24), st[1]) for st in layer[1]]
        else:
            polys += [(None, sample_curve(segs, 24), None) for segs in layer[1]]
    has_fill = any(not is_stroke(l) for l in layers)

    def frame(i):
        fig, ax = make_figure(size, {**th, "bg": bg})
        fit_view(ax, [0, w], [0, h], size, margin=0.06)
        ppu = _ppu(ax, size)
        f = min(1.0, (i + 1) / frames)
        f = 1 - (1 - f) ** 2      # slow down at the end
        segs, cols, lws = [], [], []
        for col, P, wd in polys:
            k = max(2, int(len(P) * f))
            segs.append(P[:k])
            cols.append(col or th["accent"])
            lws.append(wd * ppu * 0.72 if wd else max(size) / 600)
        ax.add_collection(LineCollection(segs, colors=cols, linewidths=lws, capstyle="round"))
        if i >= frames and has_fill:
            _draw_layers(ax, [l for l in layers if not is_stroke(l)], ppu,
                         alpha=min(1.0, (i - frames) / (hold * 0.5)))
        return fig

    save_animation(frame, frames + hold, out, fps=fps, size=size, transparent=bg == "none")


# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--mode", default="ink", choices=["ink", "color", "edges"])
    ap.add_argument("--colors", type=int, default=4, help="number of colors in color mode")
    ap.add_argument("--lines", action="store_true",
                    help="color mode: add top layers for thin dark outlines and small light details (prints, comics, ink)")
    ap.add_argument("--threshold", type=float, help="threshold 0..1 in ink mode (default: Otsu)")
    ap.add_argument("--invert", choices=["auto", "yes", "no"], default="auto",
                    help="light shape on dark background? (auto: uses the border)")
    ap.add_argument("--no-crop", action="store_true", help="do not remove solid bars at the edges")
    ap.add_argument("--detail", type=int, default=4, help="ignore spots smaller than N px (turdsize)")
    ap.add_argument("--smooth", type=float, default=1.0, help="0 = sharp corners, 1.33 = very smooth")
    ap.add_argument("--tolerance", type=float, default=0.2, help="curve simplification")
    ap.add_argument("--color", help="shape color (ink/edges mode); default: theme")
    ap.add_argument("--keep-colors", action="store_true",
                    help="ink mode: use the original mean colors of shape and background")
    ap.add_argument("--size", help="output size (default: image size)")
    ap.add_argument("--theme", default="dark")
    ap.add_argument("--svg"); ap.add_argument("--png"); ap.add_argument("--desmos")
    ap.add_argument("--anim"); ap.add_argument("--anim-style", default="pen", choices=["pen", "fourier"])
    ap.add_argument("--terms", type=int, default=600, help="total epicycles in fourier style")
    ap.add_argument("--max-strokes", type=int, default=800,
                    help="fourier style in color mode: number of longest outlines to draw")
    ap.add_argument("--centerline", action="store_true",
                    help="line art: vectorize the CENTER of each stroke as an editable SVG stroke")
    ap.add_argument("--cap", default="auto", choices=["auto", "round", "square", "butt"],
                    help="--centerline stroke ends (auto: found from the ink shape)")
    ap.add_argument("--join", default="round", choices=["round", "miter", "bevel"],
                    help="--centerline corner style")
    ap.add_argument("--frames", type=int, default=240); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--transparent", action="store_true",
                    help="transparent background (PNG alpha; animation: .mov/.webm/folder)")
    a = ap.parse_args()

    rgb = load(a.image)
    if not a.no_crop:
        rgb = crop_letterbox(rgb)
    rgb = fit_resolution(rgb)
    h, w = rgb.shape[:2]
    th = theme(a.theme)
    inv = {"auto": None, "yes": True, "no": False}[a.invert]

    if a.mode == "color":
        cl = color_layers(rgb, a.colors)
        bg = cl[0][0]
        layers = [(col, trace(m, a.detail, a.smooth, a.tolerance)) for col, m in cl[1:]]
        if a.lines:
            kl = key_lines(rgb)
            if kl:
                layers.append((kl[0], trace(kl[1], a.detail, a.smooth, a.tolerance)))
            sp = bright_spots(rgb)
            if sp:
                layers.append((sp[0], trace(sp[1], 0, a.smooth, a.tolerance)))
        target = rgb
    else:
        mask = ink_mask(rgb, a.threshold, inv) if a.mode == "ink" else edge_mask(rgb)
        if a.keep_colors:
            fg = "#%02x%02x%02x" % tuple(rgb[mask].mean(0).astype(int))
            bg = "#%02x%02x%02x" % tuple(rgb[~mask].mean(0).astype(int))
        else:
            fg, bg = a.color or th["accent"], th["bg"]
        if a.centerline:
            from centerline import centerline_strokes
            if a.detail:               # remove small spots before the skeleton
                from scipy.ndimage import label
                lab, n = label(mask)
                sizes = np.bincount(lab.ravel())
                mask = mask & (sizes[lab] > a.detail * 4)
            ink = None
            if a.mode == "ink":        # darkness map, 0 = background, 1 = full ink
                g = rgb.mean(2) / 255.0
                lo, hi = np.median(g[~mask]), np.median(g[mask])
                ink = (g - lo) / (hi - lo) if abs(hi - lo) > 0.05 else None
            strokes = centerline_strokes(mask, err=max(0.5, a.tolerance * 5), ink=ink)
            if a.cap != "auto":
                strokes = [(s0, s1, s2, a.cap) for s0, s1, s2, *_ in strokes]
            layers = [(fg, strokes, "stroke", a.join)]
        else:
            layers = [(fg, trace(mask, a.detail, a.smooth, a.tolerance))]
        target = mask

    if layers and is_stroke(layers[0]):
        st = layers[0][1]
        mw = float(np.median([x[1] for x in st])) if st else 0
        print(f"{len(st)} strokes, {sum(len(x[0]) for x in st)} Bézier segments, "
              f"median width {mw:.1f} px, image {w}×{h}")
        if mw > 0.025 * max(w, h):
            print("  warning: these look like filled shapes, not lines; run without --centerline")
    else:
        nseg = sum(len(s) for l in layers for s in l[1])
        ncurv = sum(len(l[1]) for l in layers)
        print(f"{ncurv} closed curves, {nseg} segments (Bézier/lines), image {w}×{h}")

    # accuracy: render the equations and compare with the original
    rec = rasterize(layers, w, h, bg)
    if a.mode == "color":
        err = np.abs(rec.astype(int) - rgb.astype(int)).mean() / 255
        print(f"Color accuracy: {100 * (1 - err):.1f}% (mean difference per pixel)")
    else:
        bgc = np.array([int(bg[i:i + 2], 16) for i in (1, 3, 5)])
        rm = np.abs(rec.astype(int) - bgc).sum(2) > 60
        iou = (rm & target).sum() / max((rm | target).sum(), 1)
        print(f"Accuracy (IoU original ink × copy): {100 * iou:.1f}%")
        from scipy.ndimage import distance_transform_edt, binary_erosion
        e1 = target & ~binary_erosion(target); e2 = rm & ~binary_erosion(rm)
        if e1.any() and e2.any():
            dev = np.r_[distance_transform_edt(~e1)[e2], distance_transform_edt(~e2)[e1]]
            print(f"Edge deviation: mean {dev.mean():.2f} px, 95% ≤ {np.percentile(dev, 95):.2f} px")

    size = parse_size(a.size) if a.size else (w, h)
    if a.transparent:
        bg = "none"
    if a.svg:
        write_svg(layers, w, h, a.svg, bg); print("SVG:", a.svg)
    if a.png:
        render_png(layers, w, h, a.png, size, th, bg); print("PNG:", a.png)
    if a.desmos:
        lines = desmos_lines(layers)
        open(a.desmos, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        print(f"Desmos: {a.desmos} ({len(lines)} expressions)")
        if len(lines) > 1500:
            print("  warning: too many expressions; increase --detail/--tolerance or use a smaller image")
    if a.anim:
        if a.anim_style == "pen":
            animate_pen(layers, w, h, a.anim, size, th, bg, a.frames, a.fps)
        else:
            from fourier_draw import fourier_multi, render_animation_multi
            reveal = None
            if a.mode == "color":
                # the outlines of the color regions: long, continuous "coloring book" lines
                cand = []
                for layer in layers:
                    for segs in layer[1]:
                        P = sample_curve(segs, 8)
                        L = float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())
                        edge = ((P[:, 0] < 0.015 * w) | (P[:, 0] > 0.985 * w) |
                                (P[:, 1] < 0.015 * h) | (P[:, 1] > 0.985 * h)).mean()
                        big = np.ptp(P[:, 0]) > 0.9 * w and np.ptp(P[:, 1]) > 0.9 * h
                        if L > 0.03 * max(w, h) and edge < 0.2 and not big:   # skip the frame
                            cand.append((L, P))
                cand.sort(key=lambda x: -x[0])
                conts = [P for _, P in cand[: a.max_strokes]]
                k_px = min(size[0] / w, size[1] / h)
                lws = [max(0.7, 1.1 * k_px * 0.72)] * len(conts)
                lw_px = None
                print(f"fourier: {len(conts)} region outlines, then the color layers fade in")
                art = rasterize(layers, w, h, bg, scale=max(1.0, min(size[0] / w, size[1] / h)))

                def reveal(ax, al):
                    ax.imshow(art, extent=(0, w, 0, h), alpha=al, interpolation="antialiased",
                              zorder=0)
                    ax.set_aspect("equal")
                bg = th["bg"]
            elif layers and is_stroke(layers[0]):
                conts = []
                for segs, wd, cl, *_ in layers[0][1]:
                    P = sample_curve(segs, 12)
                    conts.append(P if cl else np.vstack([P, P[::-1]]))   # open: out and back
                k_px = min(size[0] / w, size[1] / h) * 0.72      # image px -> points
                lws = [max(0.8, x[1] * k_px) for x in layers[0][1]]
                lw_px = None
            else:
                conts = [sample_curve(s, 12) for l in layers for s in l[1]]
                lw_px, lws = None, None
            series = fourier_multi(conts, a.terms)
            render_animation_multi(series, a.anim, size, {**th, "bg": bg}, frames=a.frames,
                                   fps=a.fps, fill_end=False, line_px=lw_px,
                                   view=(0, w, 0, h), line_widths=lws, reveal=reveal,
                                   hold=90 if reveal else 40)
        print("Animation:", a.anim)


if __name__ == "__main__":
    main()
