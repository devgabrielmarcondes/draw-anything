#!/usr/bin/env python3
"""
2D signed distance functions (SDF) with numpy.

An SDF gives, for each point p, the distance to the shape edge: negative
inside, positive outside, zero on the edge. Combine primitives with union,
intersection, subtraction and their "smooth" forms to make complex shapes.

Typical use (in a short script):

    import sys; sys.path.insert(0, "<skill>/scripts")
    from sdf import *
    P = grid(1080, 1080, scale=1.2)            # coordinates in [-1.2, 1.2] on the short side
    head = circle(P, 0.55)
    ears = circle(translate(mirror_x(P), 0.45, 0.5), 0.22)
    bear = smooth_union(head, ears, 0.08)
    render([(bear, "#c68642"), (circle(P, 0.1), "#2b1d14")], "bear.png", theme="paper")

Primitives: circle, box, rounded_box, segment, capsule, triangle, polygon,
            ellipse, star, heart, ring, arc, moon, cross, vesica, egg
Operations: union, intersect, subtract, smooth_union, smooth_intersect,
            smooth_subtract, xor, round_, onion, lerp
Space:      translate, rotate, scale, mirror_x, repeat, repeat_polar, twist
Render:     render(layers, out, ...) | animate(scene_fn, out, frames, ...)
Layer options: {"mode": "fill"|"outline"|"bands", "stroke", "glow",
                "shadow": (dx, dy, blur), "alpha"}. Negative dy = down.
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from _common import parse_size, theme as get_theme, save_animation

# ----------------------------------------------------------------------------
# Space
# ----------------------------------------------------------------------------

class P2:
    """Pair of arrays (x, y) plus the pixel size for antialiasing."""
    def __init__(self, x, y, px):
        self.x, self.y, self.px = x, y, px
    def __iter__(self):
        return iter((self.x, self.y))


def grid(width=1080, height=1080, scale=1.0, center=(0.0, 0.0)):
    """Coordinate grid. 'scale' is the visible half-width on the SHORT side.
    y points up (math axes). Accepts width='reels' etc."""
    if isinstance(width, str):
        width, height = parse_size(width)
    m = min(width, height)
    xs = (np.arange(width) - (width - 1) / 2) / (m / 2) * scale + center[0]
    ys = ((height - 1) / 2 - np.arange(height)) / (m / 2) * scale + center[1]
    X, Y = np.meshgrid(xs, ys)
    return P2(X, Y, 2 * scale / m)


def translate(p, dx, dy):
    return P2(p.x - dx, p.y - dy, p.px)

def rotate(p, ang):
    """Turns the SHAPE counterclockwise by 'ang' radians."""
    c, s = np.cos(ang), np.sin(ang)
    return P2(c * p.x + s * p.y, -s * p.x + c * p.y, p.px)

def scale(p, k):
    """Use: shape(scale(P, k)) * k. Multiply the distance by k again."""
    return P2(p.x / k, p.y / k, p.px / k)

def mirror_x(p):
    """Mirror symmetry on the y axis (draw only the right side)."""
    return P2(np.abs(p.x), p.y, p.px)

def repeat(p, cx, cy):
    """Infinite grid repetition with period (cx, cy). 0 turns off the axis."""
    x = p.x - cx * np.round(p.x / cx) if cx else p.x
    y = p.y - cy * np.round(p.y / cy) if cy else p.y
    return P2(x, y, p.px)

def repeat_polar(p, n):
    """Repeats n copies around the origin (flowers, gears, mandalas)."""
    a = np.arctan2(p.y, p.x); r = np.hypot(p.x, p.y)
    sector = 2 * np.pi / n
    a = (a + sector / 2) % sector - sector / 2
    return P2(r * np.cos(a), r * np.sin(a), p.px)

def twist(p, k):
    """Twist: the turn angle increases with the distance from the origin."""
    r = np.hypot(p.x, p.y); a = k * r
    c, s = np.cos(a), np.sin(a)
    return P2(c * p.x - s * p.y, s * p.x + c * p.y, p.px)

# ----------------------------------------------------------------------------
# Primitives (classic Inigo Quilez formulas, adapted to numpy)
# ----------------------------------------------------------------------------

def _len(x, y): return np.hypot(x, y)

def circle(p, r):
    return _len(p.x, p.y) - r

def ellipse(p, a, b):
    """Ellipse with semi-axes a, b. Accurate distance (Newton on the nearest-point angle)."""
    x, y = np.abs(p.x), np.abs(p.y)
    th = np.arctan2(a * y, b * x)
    for _ in range(8):
        c, s = np.cos(th), np.sin(th)
        f = (a * a - b * b) * c * s - x * a * s + y * b * c
        df = (a * a - b * b) * (c * c - s * s) - x * a * c - y * b * s
        th = np.clip(th - f / np.where(np.abs(df) < 1e-12, 1e-12, df), 0, np.pi / 2)
    d = np.hypot(x - a * np.cos(th), y - b * np.sin(th))
    return np.where((x / a) ** 2 + (y / b) ** 2 < 1, -d, d)

def box(p, w, h):
    """Rectangle with half-width w and half-height h."""
    dx, dy = np.abs(p.x) - w, np.abs(p.y) - h
    return _len(np.maximum(dx, 0), np.maximum(dy, 0)) + np.minimum(np.maximum(dx, dy), 0)

def rounded_box(p, w, h, r):
    return box(p, w - r, h - r) - r

def segment(p, a, b):
    """Unsigned distance to the segment a-b."""
    ax, ay = a; bx, by = b
    pax, pay = p.x - ax, p.y - ay; bax, bay = bx - ax, by - ay
    h = np.clip((pax * bax + pay * bay) / (bax * bax + bay * bay), 0, 1)
    return _len(pax - bax * h, pay - bay * h)

def capsule(p, a, b, r):
    return segment(p, a, b) - r

def polygon(p, verts):
    """Any polygon (vertices in order). Exact."""
    v = np.asarray(verts, float); n = len(v)
    d = (p.x - v[0, 0]) ** 2 + (p.y - v[0, 1]) ** 2
    s = np.ones_like(p.x)
    j = n - 1
    for i in range(n):
        ex, ey = v[j] - v[i]
        wx, wy = p.x - v[i, 0], p.y - v[i, 1]
        h = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey), 0, 1)
        bx, by = wx - ex * h, wy - ey * h
        d = np.minimum(d, bx * bx + by * by)
        c1 = p.y >= v[i, 1]; c2 = p.y < v[j, 1]; c3 = ex * wy > ey * wx
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        s = np.where(flip, -s, s)
        j = i
    return s * np.sqrt(d)

def triangle(p, a, b, c):
    return polygon(p, [a, b, c])

def star(p, r, n=5, m=2.5):
    """Star with n points. m between 2 and n sets how thin the points are."""
    an = np.pi / n; en = np.pi / m
    acs = np.array([np.cos(an), np.sin(an)]); ecs = np.array([np.cos(en), np.sin(en)])
    bn = np.mod(np.arctan2(p.x, p.y), 2 * an) - an
    l = _len(p.x, p.y)
    qx, qy = l * np.cos(bn), l * np.abs(np.sin(bn))
    qx, qy = qx - r * acs[0], qy - r * acs[1]
    t = np.clip(-(qx * ecs[0] + qy * ecs[1]), 0, r * acs[1] / ecs[1])
    qx, qy = qx + ecs[0] * t, qy + ecs[1] * t
    return _len(qx, qy) * np.sign(qx)

def heart(p, s=1.0):
    """Centered heart (height ~1.1*s). Approximate inside."""
    x = np.abs(p.x) / s; y = p.y / s + 0.55
    d1 = _len(x - 0.25, y - 0.75) - np.sqrt(2) / 4
    m = 0.5 * np.maximum(x + y, 0)
    d2 = np.sqrt(np.minimum((x - 1) ** 2 + (y - 1) ** 2, (x - m) ** 2 + (y - m) ** 2)) * np.sign(x - y)
    return np.where(y + x > 1, d1, d2) * s

def ring(p, r, w):
    return np.abs(circle(p, r)) - w

def arc(p, r, w, ang_from, ang_to):
    """Thick arc between two angles (radians)."""
    a = np.arctan2(p.y, p.x)
    mid = (ang_from + ang_to) / 2; half = (ang_to - ang_from) / 2
    da = np.abs((a - mid + np.pi) % (2 * np.pi) - np.pi)
    inside = da <= half
    e1 = (r * np.cos(ang_from), r * np.sin(ang_from)); e2 = (r * np.cos(ang_to), r * np.sin(ang_to))
    cap = np.minimum(_len(p.x - e1[0], p.y - e1[1]), _len(p.x - e2[0], p.y - e2[1]))
    return np.where(inside, np.abs(_len(p.x, p.y) - r), cap) - w

def moon(p, r_out, r_in, offset):
    return subtract(circle(p, r_out), circle(translate(p, offset, 0), r_in))

def cross(p, w, h, r=0.0):
    return union(rounded_box(p, w, h, r), rounded_box(p, h, w, r))

def vesica(p, r, d):
    return intersect(circle(translate(p, -d, 0), r), circle(translate(p, d, 0), r))

def egg(p, ra, rb):
    """Vertical egg (bottom radius ra, top radius rb < ra). I. Quilez formula."""
    k = np.sqrt(3.0)
    x = np.abs(p.x); y = p.y
    r = ra - rb
    return np.where(y < 0, _len(x, y) - r,
           np.where(k * (x + r) < y, _len(x, y - k * r),
                    _len(x + r, y) - 2 * r)) - rb

# ----------------------------------------------------------------------------
# Boolean operations
# ----------------------------------------------------------------------------

def union(*ds):
    return np.minimum.reduce(ds)

def intersect(*ds):
    return np.maximum.reduce(ds)

def subtract(a, b):
    """a minus b."""
    return np.maximum(a, -b)

def xor(a, b):
    return np.maximum(np.minimum(a, b), -np.maximum(a, b))

def smooth_union(a, b, k=0.1):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)

def smooth_subtract(a, b, k=0.1):
    h = np.clip(0.5 - 0.5 * (a + b) / k, 0, 1)
    return a * (1 - h) + (-b) * h + k * h * (1 - h)

def smooth_intersect(a, b, k=0.1):
    h = np.clip(0.5 - 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h + k * h * (1 - h)

def round_(d, r):
    return d - r

def onion(d, w):
    """Changes the shape into an outline of width w (you can stack it)."""
    return np.abs(d) - w

def lerp(a, b, t):
    """Morph between two shapes (t from 0 to 1)."""
    return a * (1 - t) + b * t

# ----------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------

def _rgb(c):
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], float) / 255


def _coverage(d, px):
    """Antialiasing: coverage 0..1 with a ~1 pixel transition on the edge."""
    return np.clip(0.5 - d / px, 0, 1)


def compose(layers, size, th, px, mode="fill", stroke=None, glow=0.0, shadow=None, bg=None,
            transparent=False):
    """layers: list of (sdf, color) or (sdf, color, options). Painted in order.
    Returns RGB, or RGBA if transparent=True."""
    h, w = size[1], size[0]
    img = np.ones((h, w, 3)) * (0 if transparent else _rgb(bg or th["bg"]))
    A = np.zeros((h, w)) if transparent else np.ones((h, w))
    stroke = stroke or 3 * px

    def over(col, a):            # "over" compositing with straight alpha
        nonlocal img, A
        nA = a + A * (1 - a)
        img = (np.asarray(col) * a[..., None] + img * (A * (1 - a))[..., None]) / np.maximum(nA, 1e-6)[..., None]
        A = nA

    for layer in layers:
        d, col = layer[0], _rgb(layer[1])
        opts = layer[2] if len(layer) > 2 else {}
        lm = opts.get("mode", mode)
        alpha = opts.get("alpha", 1.0)
        if shadow or opts.get("shadow"):
            sx, sy, blur = opts.get("shadow", shadow)
            ds = np.roll(np.roll(d, int(round(-sy / px)), 0), int(round(sx / px)), 1)
            over(np.zeros(3), np.clip(0.5 - ds / max(blur, px), 0, 1) * 0.35 * alpha)
        if glow or opts.get("glow"):
            g = opts.get("glow", glow)
            over(col, np.exp(-np.maximum(d, 0) / g) * 0.6 * alpha)
        if lm == "fill":
            a = _coverage(d, px)
        elif lm == "outline":
            a = _coverage(np.abs(d) - opts.get("stroke", stroke) / 2, px)
        elif lm == "bands":   # classic distance view (Shadertoy style)
            k = opts.get("period", 0.08)
            base = np.where(d > 0, 0.9, 0.55)
            band = 0.82 + 0.18 * np.cos(2 * np.pi * d / k)
            shade = (base * band * (1 - np.exp(-6 * np.abs(d))))[..., None]
            tint = np.where(d[..., None] > 0, col * 0.25 + 0.6, col)
            img = tint * shade; A = np.ones((h, w))
            a = _coverage(np.abs(d) - px, px)
            col = _rgb(th["fg"])
        else:
            raise ValueError(f"unknown mode: {lm}")
        over(col, a * alpha)
    img = np.clip(img, 0, 1)
    return np.dstack([img, A]) if transparent else img


def render(layers, out, size="square", theme="dark", scale=None, **kw):
    """Renders layers to PNG/JPG. All SDFs must use the same grid.
    transparent=True writes a PNG with alpha."""
    from PIL import Image
    if not isinstance(layers, (list, tuple)) or not isinstance(layers[0], (list, tuple)):
        layers = [(layers, get_theme(theme)["fill"])]
    d0 = layers[0][0]
    hgt, wid = d0.shape
    th = get_theme(theme)
    px = kw.pop("px", None) or _estimate_px(layers)
    img = compose(layers, (wid, hgt), th, px, **kw)
    Image.fromarray((img * 255).astype(np.uint8)).save(out)
    return out


def _estimate_px(layers):
    d = layers[0][0]
    gy, gx = np.gradient(d)
    g = np.median(np.hypot(gx, gy))   # |∇d|≈1 per unit => px ≈ gradient per pixel
    return float(g) if g > 0 else 0.002


def animate(scene_fn, out, frames=120, fps=30, size="square", theme="dark", transparent=False, **kw):
    """scene_fn(t) -> layers, with t in [0, 1). Output .mp4/.gif (seamless loop),
    or with transparent=True: .mov, .webm or a folder (PNG sequence)."""
    th = get_theme(theme)

    def frame(i):
        layers = scene_fn(i / frames)
        hgt, wid = layers[0][0].shape
        return compose(layers, (wid, hgt), th, _estimate_px(layers), transparent=transparent, **kw)

    return save_animation(frame, frames, out, fps=fps, transparent=transparent)


if __name__ == "__main__":
    # Demo: flower with smooth union
    P = grid(1080, 1080, scale=1.3)
    petal = ellipse(translate(repeat_polar(P, 8), 0.55, 0), 0.32, 0.14)
    center = circle(P, 0.22)
    flower = smooth_union(petal, center, 0.06)
    out = sys.argv[1] if len(sys.argv) > 1 else "sdf_demo.png"
    render([(flower, "#ff6f91", {"glow": 0.08}), (center, "#ffc75f")], out, theme="dark")
    print(out)
