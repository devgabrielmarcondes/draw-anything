#!/usr/bin/env python3
"""
Drawing with Fourier series (epicycles).

Changes contours (SVG path, SVG file, text, image or point list) into sums of
turning circles: z(t) = Σ c_k · e^{i k t}, t ∈ [0, 2π).
Each separate contour gets its own series. Thus no lines connect the parts.
Use --single-line to connect all parts in one loop ("one pen stroke" style).

Outputs (use one or more):
  --png      static image of the reconstruction (--fill fills the shapes)
  --anim     epicycle animation (.mp4, .gif; .mov/.webm with --transparent)
  --svg      reconstructed SVG path
  --desmos   parametric equations for Desmos (t from 0 to 1)
  --json     coefficients

Examples:
  python fourier_draw.py --text "Hello" --terms 300 --anim hello.mp4 --size reels
  python fourier_draw.py --svg-path "M0 0 C 50 -80 150 80 200 0 Z" --png wave.png
  python fourier_draw.py --points points.json --terms 40 --desmos eq.txt
"""
import argparse, json, re, sys, os
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from _common import parse_size, theme, make_figure, fit_view, save_animation, transparent_theme

# ----------------------------------------------------------------------------
# Contour input
# ----------------------------------------------------------------------------

def _bezier(pts, n=24):
    t = np.linspace(0, 1, n)[:, None]
    pts = np.asarray(pts, dtype=float)
    if len(pts) == 3:
        p0, p1, p2 = pts
        return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2
    p0, p1, p2, p3 = pts
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)


def _arc(p0, rx, ry, phi, large, sweep, p1, n=32):
    """SVG elliptical arc (endpoint to center conversion, SVG spec F.6)."""
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0:
        return np.array([p0, p1])
    phi = np.radians(phi)
    c, s = np.cos(phi), np.sin(phi)
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1, y1 = c * dx + s * dy, -s * dx + c * dy
    lam = x1 ** 2 / rx ** 2 + y1 ** 2 / ry ** 2
    if lam > 1:
        rx, ry = rx * np.sqrt(lam), ry * np.sqrt(lam)
    num = rx ** 2 * ry ** 2 - rx ** 2 * y1 ** 2 - ry ** 2 * x1 ** 2
    den = rx ** 2 * y1 ** 2 + ry ** 2 * x1 ** 2
    coef = np.sqrt(max(num / den, 0)) * (-1 if large == sweep else 1)
    cx1, cy1 = coef * rx * y1 / ry, -coef * ry * x1 / rx
    cx = c * cx1 - s * cy1 + (p0[0] + p1[0]) / 2
    cy = s * cx1 + c * cy1 + (p0[1] + p1[1]) / 2
    ang = lambda ux, uy, vx, vy: np.arctan2(ux * vy - uy * vx, ux * vx + uy * vy)
    t1 = ang(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry)
    dt = ang((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry)
    if not sweep and dt > 0:
        dt -= 2 * np.pi
    elif sweep and dt < 0:
        dt += 2 * np.pi
    ts = t1 + np.linspace(0, dt, n)
    xs = cx + rx * np.cos(ts) * c - ry * np.sin(ts) * s
    ys = cy + rx * np.cos(ts) * s + ry * np.sin(ts) * c
    return np.stack([xs, ys], 1)


def parse_svg_path(d):
    """Changes the 'd' attribute of a <path> into a list of subpaths (Nx2 arrays).
    Supports M L H V C S Q T A Z (absolute and relative)."""
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", d)
    i, cmd = 0, None
    cur = np.zeros(2); start = np.zeros(2); last_ctrl = None; last_cmd = None
    subpaths, pts = [], []

    def num():
        nonlocal i
        v = float(tokens[i]); i += 1
        return v

    while i < len(tokens):
        if re.match(r"[A-Za-z]", tokens[i]):
            cmd = tokens[i]; i += 1
        elif cmd is None:
            raise ValueError("incorrect SVG path")
        rel = cmd.islower(); C = cmd.upper()
        base = cur if rel else np.zeros(2)
        if C == "M":
            if len(pts) > 1:
                subpaths.append(np.array(pts))
            cur = base + [num(), num()]; start = cur.copy(); pts = [cur.copy()]
            cmd = "l" if rel else "L"   # next pairs are LineTo
        elif C == "L":
            cur = base + [num(), num()]; pts.append(cur.copy())
        elif C == "H":
            x = num(); cur = np.array([cur[0] + x if rel else x, cur[1]]); pts.append(cur.copy())
        elif C == "V":
            y = num(); cur = np.array([cur[0], cur[1] + y if rel else y]); pts.append(cur.copy())
        elif C in "CS":
            if C == "C":
                c1 = base + [num(), num()]
            else:
                c1 = 2 * cur - last_ctrl if last_cmd in "CS" and last_ctrl is not None else cur.copy()
            c2 = base + [num(), num()]; end = base + [num(), num()]
            pts.extend(_bezier([cur, c1, c2, end])[1:]); last_ctrl = c2; cur = end
        elif C in "QT":
            if C == "Q":
                c1 = base + [num(), num()]
            else:
                c1 = 2 * cur - last_ctrl if last_cmd in "QT" and last_ctrl is not None else cur.copy()
            end = base + [num(), num()]
            pts.extend(_bezier([cur, c1, end])[1:]); last_ctrl = c1; cur = end
        elif C == "A":
            rx, ry, rot, la, sw = num(), num(), num(), num(), num()
            end = base + [num(), num()]
            pts.extend(_arc(cur, rx, ry, rot, int(la), int(sw), end)[1:]); cur = end
        elif C == "Z":
            pts.append(start.copy()); cur = start.copy()
            subpaths.append(np.array(pts)); pts = [cur.copy()]
        last_cmd = C
    if len(pts) > 1:
        subpaths.append(np.array(pts))
    # SVG y points down; flip to math axes
    return [p * [1, -1] for p in subpaths]


def contours_from_svg_file(path):
    txt = open(path, encoding="utf-8").read()
    ds = re.findall(r'<path[^>]*?\sd="([^"]+)"', txt, flags=re.S)
    out = []
    for d in ds:
        out += parse_svg_path(d)
    for m in re.finditer(r'<(polygon|polyline)[^>]*?points="([^"]+)"', txt):
        nums = [float(v) for v in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", m.group(2))]
        p = np.array(nums).reshape(-1, 2) * [1, -1]
        if m.group(1) == "polygon":
            p = np.vstack([p, p[:1]])
        out.append(p)
    if not out:
        raise ValueError("no <path>/<polygon> in the SVG")
    return out


def contours_from_text(text, font="DejaVu Sans", weight="bold"):
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    tp = TextPath((0, 0), text, size=100, prop=FontProperties(family=font, weight=weight))
    return [np.asarray(p) for p in tp.to_polygons() if len(p) > 2]


def contours_from_image(path, threshold=0.5, min_len=40, invert=False):
    """Contours of an image (silhouette/logo). Default: dark shape on light background."""
    from PIL import Image
    import matplotlib.pyplot as plt
    img = np.asarray(Image.open(path).convert("L"), dtype=float) / 255.0
    if invert:
        img = 1 - img
    fig = plt.figure()
    cs = plt.contour(img[::-1], levels=[threshold])
    segs = [s for s in cs.allsegs[0] if len(s) >= min_len]
    plt.close(fig)
    if not segs:
        raise ValueError("no contour found; try --threshold or --invert")
    return segs


def contours_from_points(path):
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("contours") or data.get("points")
    if data and isinstance(data[0][0], (int, float)):
        data = [data]
    return [np.asarray(c, dtype=float) for c in data]

# ----------------------------------------------------------------------------
# Fourier core
# ----------------------------------------------------------------------------

def _closest_pair(a, b, step=4):
    A, B = a[::step], b[::step]
    d = np.hypot(A[:, None, 0] - B[None, :, 0], A[:, None, 1] - B[None, :, 1])
    i, j = np.unravel_index(np.argmin(d), d.shape)
    return d[i, j], i * step, j * step


def join_contours(contours):
    """Connects many subpaths into one closed loop (--single-line).

    Method: minimum spanning tree between contours (distance = nearest point pair),
    then depth-first walk. Each bridge is walked out and back on the same path.
    Thus it shows as a short thin line. Open contours are walked out and back."""
    loops = []
    for c in contours:
        c = np.asarray(c, float)
        if len(c) < 2:
            continue
        if np.allclose(c[0], c[-1]):
            c = c[:-1]
        else:
            c = np.vstack([c, c[-2:0:-1]])
        loops.append(c)
    n = len(loops)
    if n == 1:
        return np.vstack([loops[0], loops[0][:1]])
    # Prim
    root = min(range(n), key=lambda i: loops[i][:, 0].min())
    in_tree, children = {root}, {i: {} for i in range(n)}
    entry = {root: int(np.argmin(loops[root][:, 0]))}
    cache = {}
    while len(in_tree) < n:
        best = None
        for a in in_tree:
            for b in range(n):
                if b in in_tree:
                    continue
                key = (a, b)
                if key not in cache:
                    cache[key] = _closest_pair(loops[a], loops[b])
                d, i, j = cache[key]
                if best is None or d < best[0]:
                    best = (d, a, b, i, j)
        _, a, b, i, j = best
        children[a].setdefault(i, []).append(b)
        entry[b] = j
        in_tree.add(b)

    def walk(node):
        c, e = loops[node], entry[node]
        m = len(c)
        pts = []
        for s in range(m + 1):
            idx = (e + s) % m
            pts.append(c[idx])
            if s < m:
                for ch in children[node].get(idx, []):
                    pts.extend(walk(ch))
                    pts.append(c[idx])
        return pts

    return np.array(walk(root))


def resample(pts, n):
    """Resamples by arc length (equal spacing)."""
    pts = np.asarray(pts, float)
    if not np.allclose(pts[0], pts[-1]):
        pts = np.vstack([pts, pts[:1]])
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    u = np.linspace(0, s[-1], n, endpoint=False)
    return np.interp(u, s, pts[:, 0]) + 1j * np.interp(u, s, pts[:, 1])


def fourier_coeffs(z, terms):
    """Returns a list of (k, c_k), sorted by |c_k| (largest first)."""
    N = len(z)
    C = np.fft.fft(z) / N
    k = np.fft.fftfreq(N, 1 / N).astype(int)
    idx = np.argsort(-np.abs(C))[:terms]
    return [(int(k[i]), complex(C[i])) for i in idx]


def evaluate(coeffs, t):
    t = np.asarray(t)
    return sum(c * np.exp(1j * k * t) for k, c in coeffs)


def desmos_equations(coeffs, digits=3):
    """x(t), y(t) as sums of cosines/sines for Desmos. The frequencies include
    the 2π factor, thus t goes from 0 to 1 (the Desmos default domain)."""
    xs, ys = [], []
    for k, c in sorted(coeffs, key=lambda kc: (abs(kc[0]), kc[0])):
        r, ph = abs(c), np.angle(c)
        if r < 10 ** -digits:
            continue
        w = 2 * np.pi * k
        arg = f"{w:.4f}t{'+' if ph >= 0 else '-'}{abs(ph):.{digits}f}" if k else f"{ph:.{digits}f}"
        xs.append(f"{r:.{digits}f}\\cos({arg})")
        ys.append(f"{r:.{digits}f}\\sin({arg})")
    x = "+".join(xs).replace("+-", "-")
    y = "+".join(ys).replace("+-", "-")
    return x, y


# ----------------------------------------------------------------------------
# Many separate contours (default): each contour has its own series.
# Thus NO lines connect the parts (the pen lifts between them).
# ----------------------------------------------------------------------------

def _perimeter(c):
    c = np.asarray(c, float)
    return float(np.hypot(*np.diff(np.vstack([c, c[:1]]), axis=0).T).sum())


def fourier_multi(contours, terms_total=300, min_terms=4, samples_per_unit=None):
    """One Fourier series for each contour. Terms are divided by perimeter
    (large, detailed contours get more circles). Returns a list of coeffs."""
    cs = [np.asarray(c, float) for c in contours if len(c) > 2]
    per = np.array([_perimeter(c) for c in cs])
    total = per.sum()
    out = []
    for c, L in zip(cs, per):
        n = int(np.clip(L / total * 4096, 64, 4096))
        z = resample(c, n)
        k = int(np.clip(round(terms_total * L / total), min_terms, n // 2))
        out.append(fourier_coeffs(z, k))
    return out


def normalize_contours(contours, extent=10.0):
    allp = np.vstack(contours)
    c = (allp.max(0) + allp.min(0)) / 2
    s = extent / max(np.abs(allp - c).max(), 1e-9)
    return [(np.asarray(k, float) - c) * s for k in contours]


def render_static_multi(series, out, size, th, fill=False, lw=None):
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch
    t = np.linspace(0, 2 * np.pi, 1500)
    curves = [evaluate(co, t) for co in series]
    fig, ax = make_figure(size, th)
    lw = lw or max(size) / 400
    if fill:
        verts, codes = [], []
        for z in curves:
            v = np.c_[z.real, z.imag]
            verts.append(v); codes += [Path.MOVETO] + [Path.LINETO] * (len(v) - 2) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(np.vstack(verts), codes), facecolor=th["fill"], lw=0))
    else:
        for z in curves:
            ax.plot(np.r_[z.real, z.real[:1]], np.r_[z.imag, z.imag[:1]], color=th["accent"],
                    lw=lw, solid_capstyle="round", solid_joinstyle="round")
    allz = np.concatenate(curves)
    fit_view(ax, allz.real, allz.imag, size)
    fig.savefig(out, facecolor=th["bg"])
    return out


def render_animation_multi(series, out, size, th, frames=300, fps=30, show_chains=8,
                           max_circles=40, hold=40, fill_end=False, line_px=None, view=None,
                           line_widths=None, reveal=None):
    tr = th["bg"] == "none"
    """Draws all contours AT THE SAME TIME, each with its own epicycle chain.
    Shows the circles of the 'show_chains' largest contours.
    reveal(ax, a): optional, draws an image under the lines in the end pause
    (a goes 0 -> 1); the lines then fade out."""
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    sub = 8
    tf = np.linspace(0, 2 * np.pi, frames * sub + 1)
    traces = [evaluate(co, tf) for co in series]
    allz = np.concatenate(traces)
    lw = max(size) / 420 if line_px is None else line_px * 0.72  # px -> points (dpi 100)
    order = np.argsort([-sum(abs(c) for _, c in co) for co in series])[:show_chains]

    def frame(i):
        fig, ax = make_figure(size, th)
        if view:
            fit_view(ax, view[:2], view[2:], size, margin=0.04)
        else:
            fit_view(ax, allz.real, allz.imag, size, margin=0.08)
        j = min(i, frames) * sub
        segs = [np.c_[z.real[: j + 1], z.imag[: j + 1]] for z in traces]
        line_alpha = 1.0
        if reveal is not None and i >= frames:
            a = min(1.0, (i - frames) / max(1, hold * 0.6))
            a = a * a * (3 - 2 * a)                     # smoothstep
            reveal(ax, a)
            line_alpha = 1 - 0.9 * a
        ax.add_collection(LineCollection(segs, colors=th["accent"], alpha=line_alpha,
                                         linewidths=lw if line_widths is None else line_widths,
                                         capstyle="round", joinstyle="round"))
        if i < frames:
            t = tf[j]
            for idx in order:
                # the chain starts at the contour center (k=0 term), not at the origin
                p = sum(c for k, c in series[idx] if k == 0) + 0j
                pts = [p]; rad = []
                for k, c in series[idx]:
                    if k == 0:
                        continue
                    p = p + c * np.exp(1j * k * t); pts.append(p); rad.append(abs(c))
                P = np.array(pts)
                for n, r in enumerate(rad[:max_circles]):
                    ax.add_patch(plt.Circle((P[n].real, P[n].imag), r, fill=False,
                                            color=th["muted"], lw=max(size) / 1000, alpha=0.9))
                ax.plot(P.real, P.imag, color=th["fg"], lw=max(size) / 1200, alpha=0.7)
        elif fill_end:
            from matplotlib.path import Path
            from matplotlib.patches import PathPatch
            a = min(1.0, (i - frames) / (hold * 0.5))
            verts, codes = [], []
            for z in traces:
                v = np.c_[z.real, z.imag]
                verts.append(v); codes += [Path.MOVETO] + [Path.LINETO] * (len(v) - 2) + [Path.CLOSEPOLY]
            ax.add_patch(PathPatch(Path(np.vstack(verts), codes), facecolor=th["fill"], lw=0, alpha=a))
        return fig

    return save_animation(frame, frames + hold, out, fps=fps, size=size, transparent=tr)


def desmos_multi(series, digits=3):
    lines = []
    for co in series:
        x, y = desmos_equations(co, digits)
        lines.append(f"\\left({x},{y}\\right)")
    return lines

# ----------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------

def render_static(coeffs, out, size, th, original=None, lw=None):
    t = np.linspace(0, 2 * np.pi, 4000)
    z = evaluate(coeffs, t)
    fig, ax = make_figure(size, th)
    if original is not None:
        ax.plot(original.real, original.imag, color=th["muted"], lw=1)
    ax.plot(z.real, z.imag, color=th["accent"], lw=lw or max(size) / 400, solid_capstyle="round")
    fit_view(ax, z.real, z.imag, size)
    fig.savefig(out, facecolor=th["bg"])
    return out


def render_animation(coeffs, out, size, th, frames=240, fps=30, max_circles=80, hold=30):
    tr = th["bg"] == "none"
    import matplotlib.pyplot as plt
    tt = np.linspace(0, 2 * np.pi, frames, endpoint=False)
    full = evaluate(coeffs, np.linspace(0, 2 * np.pi, 3000))
    # fit the view, include the circle radius
    reach = sum(abs(c) for _, c in coeffs[:3])
    xs = np.concatenate([full.real, [coeffs[0][1].real - reach, coeffs[0][1].real + reach]])
    ys = np.concatenate([full.imag, [coeffs[0][1].imag - reach, coeffs[0][1].imag + reach]])
    sub = 16  # subsamples per frame for a smooth line
    tfine = np.linspace(0, 2 * np.pi, frames * sub, endpoint=False)
    trace = evaluate(coeffs, tfine)
    lw = max(size) / 380

    def frame(i):
        fig, ax = make_figure(size, th)
        fit_view(ax, xs, ys, size, margin=0.06)
        j = min(i, frames - 1)
        ax.plot(trace.real[: j * sub + 1], trace.imag[: j * sub + 1], color=th["accent"], lw=lw,
                solid_capstyle="round")
        if i < frames:
            p = sum(c for k, c in coeffs if k == 0) + 0j
            centers = [p]; rad = []
            for k, c in coeffs:
                if k == 0:
                    continue
                p = p + c * np.exp(1j * k * tt[j]); centers.append(p); rad.append(abs(c))
            cs = np.array(centers)
            for n, r in enumerate(rad[:max_circles]):
                ax.add_patch(plt.Circle((cs[n].real, cs[n].imag), r, fill=False,
                                        color=th["muted"], lw=lw * 0.35))
            ax.plot(cs.real, cs.imag, color=th["fg"], lw=lw * 0.45, alpha=0.9)
            ax.plot([cs[-1].real], [cs[-1].imag], "o", color=th["accent"], ms=lw * 2.2)
        else:  # end pause with the full drawing
            ax.plot(full.real, full.imag, color=th["accent"], lw=lw, solid_capstyle="round")
        return fig

    return save_animation(frame, frames + hold, out, fps=fps, size=size, transparent=tr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--svg-path", help="'d' attribute of a <path>")
    src.add_argument("--svg-file", help=".svg file (uses all <path>/<polygon>)")
    src.add_argument("--text", help="text to draw (font outline)")
    src.add_argument("--image", help="PNG/JPG image of a silhouette (for exact copies use trace_image.py)")
    src.add_argument("--points", help="JSON: [[x,y],...] or [[[x,y],...], ...]")
    ap.add_argument("--font", default="DejaVu Sans")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--invert", action="store_true", help="light shape on dark background")
    ap.add_argument("--samples", type=int, default=2048, help="sample points on the contour")
    ap.add_argument("--terms", type=int, default=300,
                    help="total number of epicycles, divided between the contours")
    ap.add_argument("--size", default="square", help="reels|post|square|youtube|WxH")
    ap.add_argument("--theme", default="dark", help="dark|light|neon|blueprint|paper")
    ap.add_argument("--frames", type=int, default=300)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--png"); ap.add_argument("--anim"); ap.add_argument("--svg")
    ap.add_argument("--desmos"); ap.add_argument("--json")
    ap.add_argument("--show-original", action="store_true")
    ap.add_argument("--single-line", action="store_true",
                    help="'one pen stroke' style: one loop that connects all parts")
    ap.add_argument("--fill", action="store_true", help="fill the shapes (multi-contour mode)")
    ap.add_argument("--transparent", action="store_true",
                    help="transparent background (PNG alpha; animation: .mov/.webm/folder)")
    a = ap.parse_args()

    if a.svg_path: cs = parse_svg_path(a.svg_path)
    elif a.svg_file: cs = contours_from_svg_file(a.svg_file)
    elif a.text: cs = contours_from_text(a.text, a.font)
    elif a.image: cs = contours_from_image(a.image, a.threshold, invert=a.invert)
    else: cs = contours_from_points(a.points)

    size, th = parse_size(a.size), theme(a.theme)
    if a.transparent:
        th = transparent_theme(th)
    if not any([a.png, a.anim, a.svg, a.desmos, a.json]):
        a.png = "fourier.png"

    if not a.single_line and len(cs) > 1:
        # default: one series for each contour, no connection lines
        cs = normalize_contours(cs)
        series = fourier_multi(cs, a.terms)
        print(f"{len(series)} contours, {sum(len(s) for s in series)} epicycles in total")
        if a.png:
            render_static_multi(series, a.png, size, th, fill=a.fill); print("PNG:", a.png)
        if a.desmos:
            open(a.desmos, "w", encoding="utf-8").write("\n".join(desmos_multi(series)) + "\n")
            print("Desmos:", a.desmos, "(one line for each contour; t from 0 to 1)")
        if a.json:
            json.dump([[{"k": k, "re": c.real, "im": c.imag} for k, c in co] for co in series],
                      open(a.json, "w", encoding="utf-8"), indent=1); print("JSON:", a.json)
        if a.svg:
            t = np.linspace(0, 2 * np.pi, 800)
            ds = []
            for co in series:
                p = evaluate(co, t)
                ds.append("M " + " L ".join(f"{x:.3f} {-y:.3f}" for x, y in zip(p.real, p.imag)) + " Z")
            open(a.svg, "w", encoding="utf-8").write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-11 -11 22 22">'
                                   f'<path d="{" ".join(ds)}" fill="none" stroke="black" stroke-width="0.06"/></svg>')
            print("SVG:", a.svg)
        if a.anim:
            render_animation_multi(series, a.anim, size, th, frames=a.frames, fps=a.fps,
                                   fill_end=a.fill); print("Animation:", a.anim)
        return

    z = resample(join_contours(cs), a.samples)
    z = z - z.mean()
    z = z / np.abs(z).max() * 10          # normalize to ~[-10, 10] (good for Desmos)
    coeffs = fourier_coeffs(z, a.terms)

    if a.png:
        render_static(coeffs, a.png, size, th, original=z if a.show_original else None)
        print("PNG:", a.png)
    if a.svg:
        p = evaluate(coeffs, np.linspace(0, 2 * np.pi, 1500))
        d = "M " + " L ".join(f"{x:.3f} {-y:.3f}" for x, y in zip(p.real, p.imag)) + " Z"
        vb = f"{p.real.min()-1:.2f} {-p.imag.max()-1:.2f} {np.ptp(p.real)+2:.2f} {np.ptp(p.imag)+2:.2f}"
        open(a.svg, "w", encoding="utf-8").write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">'
                               f'<path d="{d}" fill="none" stroke="black" stroke-width="0.08"/></svg>')
        print("SVG:", a.svg)
    if a.desmos:
        x, y = desmos_equations(coeffs)
        open(a.desmos, "w", encoding="utf-8").write(
            "# Paste the lines into Desmos (t from 0 to 1, the default).\n"
            f"X(t)={x}\nY(t)={y}\n(X(t),Y(t))\n")
        print("Desmos:", a.desmos)
    if a.json:
        json.dump([{"k": k, "re": c.real, "im": c.imag, "raio": abs(c), "fase": float(np.angle(c))}
                   for k, c in coeffs], open(a.json, "w", encoding="utf-8"), indent=1)
        print("JSON:", a.json)
    if a.anim:
        render_animation(coeffs, a.anim, size, th, frames=a.frames, fps=a.fps)
        print("Animation:", a.anim)


if __name__ == "__main__":
    main()
