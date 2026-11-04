"""Synthetic benchmark for color mode. Each case: degraded input (1x, 320 px) + clean ground truth (4x).
Standard and unusual cases. Train seeds 0-1, test seed 2 (held out)."""
import io, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from matplotlib import font_manager

S = 320; K = 4; G = S * K
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
FONT = font_manager.findfont("DejaVu Sans:bold")


def hexrgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def palette(rng, n, lmin=30, lmax=230):
    """n random saturated colors, far from each other."""
    out = []
    while len(out) < n:
        c = rng.integers(lmin, lmax, 3)
        if all(np.abs(c - o).sum() > 120 for o in out):
            out.append(c)
    return [tuple(int(v) for v in c) for c in out]


def canvas(bg):
    im = Image.new("RGB", (G, G), bg); return im, ImageDraw.Draw(im)


def P(x):  # unit coordinates -> pixels at 4x
    return float(x) * G


def shape(d, rng, col, kind=None):
    kind = kind or rng.choice(["circle", "rect", "poly", "ellipse"])
    cx, cy = rng.uniform(.2, .8, 2); r = rng.uniform(.08, .25)
    if kind == "circle":
        d.ellipse([P(cx - r), P(cy - r), P(cx + r), P(cy + r)], fill=col)
    elif kind == "ellipse":
        d.ellipse([P(cx - r), P(cy - r * .6), P(cx + r), P(cy + r * .6)], fill=col)
    elif kind == "rect":
        d.rounded_rectangle([P(cx - r), P(cy - r * .7), P(cx + r), P(cy + r * .7)], radius=P(r * .15), fill=col)
    else:
        n = int(rng.integers(3, 7)); a = np.sort(rng.uniform(0, 2 * np.pi, n))
        d.polygon([(P(cx + r * np.cos(t)), P(cy + r * np.sin(t))) for t in a], fill=col)


def text(d, xy, s, size, col):
    d.text((P(xy[0]), P(xy[1])), s, font=ImageFont.truetype(FONT, int(P(size))), fill=col, anchor="mm")


# ---------------------------------------------------------------------------- kinds
# Each kind: rng -> (clean RGB image at 4x, degradation)

def flat(rng):
    cols = palette(rng, 6); im, d = canvas(cols[0])
    for i in range(7):
        shape(d, rng, cols[1 + i % 5])
    return im, None


def icon(rng):
    bg, fg, acc = palette(rng, 3); im, d = canvas((245, 245, 245))
    d.rounded_rectangle([P(.12), P(.12), P(.88), P(.88)], radius=P(.18), fill=bg)
    d.ellipse([P(.3), P(.25), P(.7), P(.65)], fill=fg)
    d.rectangle([P(.42), P(.6), P(.58), P(.78)], fill=fg)
    d.ellipse([P(.42), P(.37), P(.58), P(.53)], fill=acc)
    return im, None


def logo(rng):
    a, b, c = palette(rng, 3); im, d = canvas((255, 255, 255))
    d.ellipse([P(.1), P(.3), P(.42), P(.62)], fill=a)
    d.ellipse([P(.2), P(.38), P(.34), P(.52)], fill=(255, 255, 255))
    d.polygon([(P(.27), P(.3)), (P(.42), P(.3)), (P(.42), P(.45))], fill=b)
    text(d, (.68, .46), "ACME", .13, c)
    d.rectangle([P(.48), P(.58), P(.88), P(.61)], fill=b)
    return im, None


def poster(rng):
    sky, sun, m1, m2, t = palette(rng, 5); im, d = canvas(sky)
    d.ellipse([P(.55), P(.12), P(.85), P(.42)], fill=sun)
    d.polygon([(0, P(.75)), (P(.35), P(.35)), (P(.7), P(.75))], fill=m1)
    d.polygon([(P(.3), P(.8)), (P(.7), P(.45)), (P(1), P(.8))], fill=m2)
    d.rectangle([0, P(.78), G, G], fill=t)
    text(d, (.5, .9), "SUMMER", .09, sky)
    return im, None


def grad_linear(rng):
    c0, c1 = (np.array(c, float) for c in palette(rng, 2)); a = rng.uniform(0, np.pi)
    y, x = np.mgrid[:G, :G] / G; t = np.clip((x - .5) * np.cos(a) + (y - .5) * np.sin(a) + .5, 0, 1)[..., None]
    im = Image.fromarray((c0 * (1 - t) + c1 * t).astype(np.uint8)); d = ImageDraw.Draw(im)
    shape(d, rng, palette(rng, 1)[0], "circle")
    return im, None


def grad_radial(rng):
    c0, c1 = (np.array(c, float) for c in palette(rng, 2)); cx, cy = rng.uniform(.3, .7, 2)
    y, x = np.mgrid[:G, :G] / G; t = np.clip(np.hypot(x - cx, y - cy) / .7, 0, 1)[..., None]
    return Image.fromarray((c0 * (1 - t) + c1 * t).astype(np.uint8)), None


def paper(rng):
    im, _ = flat(rng); return im, "paper"


def woodcut(rng):
    """Prints: flat colors, dark key lines, small light drops (foam, stars)."""
    sky, sea, deep = (230, 220, 195), (70, 120, 160), (25, 50, 90)
    im, d = canvas(sky)
    for k in range(3):
        y0 = .45 + .15 * k + rng.uniform(-.03, .03)
        pts = [(P(x), P(y0 + .06 * np.sin(9 * x + k + rng.uniform(0, 6)))) for x in np.linspace(0, 1, 60)]
        d.polygon(pts + [(G, G), (0, G)], fill=sea if k % 2 == 0 else deep, outline=(20, 20, 25), width=int(P(.008)))
    for _ in range(60):
        x, y = rng.uniform(0, 1), rng.uniform(.5, 1); r = rng.uniform(.004, .01)
        d.ellipse([P(x - r), P(y - r), P(x + r), P(y + r)], fill=(245, 240, 225))
    return im, None


def pointillism(rng):
    cols = palette(rng, 5); im, d = canvas((240, 236, 225))
    for _ in range(900):
        x, y = rng.uniform(0, 1, 2); r = rng.uniform(.004, .012)
        d.ellipse([P(x - r), P(y - r), P(x + r), P(y + r)], fill=cols[int((x + y) * 2.4) % 5])
    return im, None


def close_colors(rng):
    """Regions that differ by less than about 5 ΔE."""
    base = rng.integers(80, 180, 3); im, d = canvas(tuple(int(v) for v in base))
    for i in range(5):
        c = np.clip(base + rng.integers(-6, 7, 3), 0, 255)
        shape(d, rng, tuple(int(v) for v in c))
    return im, None


def soft(rng):
    im, _ = flat(rng); return im, "soft"


def jpeg(rng):
    im, _ = poster(rng); return im, "jpeg"


def photo(rng):
    """Simulated photo: smooth color field (sum of Gaussians) + sensor noise in the input."""
    y, x = np.mgrid[:G, :G] / G; a = np.zeros((G, G, 3))
    for c in palette(rng, 6):
        cx, cy, s = *rng.uniform(0, 1, 2), rng.uniform(.15, .35)
        a += np.array(c, float) * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * s * s))[..., None]
    a = a / a.max() * 235 + 10
    return Image.fromarray(a.astype(np.uint8)), "noise"


def alpha(rng):
    im, _ = icon(rng); return im, "alpha"


def tiny(rng):
    im, _ = flat(rng); return im, "tiny"


def many_colors(rng):
    """40 flat Voronoi cells, each with its own color."""
    pts = rng.uniform(0, 1, (40, 2)); cols = rng.integers(20, 236, (40, 3))
    y, x = np.mgrid[:G, :G] / G
    idx = np.argmin((x[..., None] - pts[:, 0]) ** 2 + (y[..., None] - pts[:, 1]) ** 2, axis=2)
    return Image.fromarray(cols[idx].astype(np.uint8)), None


KINDS = {f.__name__: f for f in (flat, icon, logo, poster, grad_linear, grad_radial, paper, woodcut,
                                  pointillism, close_colors, soft, jpeg, photo, alpha, tiny, many_colors)}


def degrade(gt, how, rng):
    """Clean 4x image -> 1x input (RGB, or RGBA for 'alpha')."""
    im = gt.resize((S, S), Image.LANCZOS)
    if how == "tiny":
        return gt.resize((S // 3, S // 3), Image.LANCZOS)
    if how == "soft":
        return im.filter(ImageFilter.GaussianBlur(1.6))
    if how == "jpeg":
        b = io.BytesIO(); im.save(b, "JPEG", quality=12); return Image.open(b).convert("RGB")
    a = np.asarray(im).astype(float)
    if how == "paper":
        y, x = np.mgrid[:S, :S] / S
        fib = np.asarray(Image.fromarray(rng.normal(128, 40, (S // 4, S // 4)).clip(0, 255).astype(np.uint8))
                         .resize((S, S), Image.BICUBIC), float) - 128
        a = a * (0.85 + 0.15 * x)[..., None] + (0.15 * fib + rng.normal(0, 5, (S, S)))[..., None]
    if how == "noise":
        a = np.asarray(Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), float)
        a += rng.normal(0, 12, a.shape)
    if how == "alpha":
        # The ground truth is the image on white. The input has the background removed:
        # transparent pixels with RGB = 0 (as many editors save them).
        a8 = np.asarray(im); white = (a8 > 240).all(2)
        rgba = np.dstack([a8, np.where(white, 0, 255)]).astype(np.uint8); rgba[white, :3] = 0
        return Image.fromarray(rgba, "RGBA")
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def generate(out=DATA, names=None, seeds=range(3)):
    """Write the cases (all, or only `names` and `seeds`) and meta.json to `out`."""
    os.makedirs(out, exist_ok=True); meta = []
    for name, mk in KINDS.items():
        if names and name not in names: continue
        for seed in seeds:
            rng = np.random.default_rng(sum(map(ord, name)) + seed * 7919)
            gt, how = mk(rng)
            inp = degrade(gt, how, rng)
            cid = f"{name}_{seed}"; inp.save(f"{out}/{cid}.png"); gt.save(f"{out}/{cid}_gt.png")
            ncol = len(np.unique(np.asarray(gt.resize((S, S), Image.NEAREST)).reshape(-1, 3), axis=0))
            meta.append({"id": cid, "kind": name, "split": "test" if seed == 2 else "train",
                         "standard": name in ("flat", "icon", "logo", "poster"), "gt_colors": int(ncol)})
    json.dump(meta, open(f"{out}/meta.json", "w"), indent=0)
    return meta


if __name__ == "__main__":
    print(len(generate()), "cases")
