"""Synthetic vectorization benchmark. Each case: degraded input (1x) + clean ground truth (4x).
Standard and unusual cases. Train seeds 0-1, test seed 2 (held out)."""
import numpy as np, matplotlib, io, json, os
matplotlib.use("Agg"); import matplotlib.pyplot as plt
matplotlib.rcParams["text.hinting"] = "none"; matplotlib.rcParams["text.hinting_factor"] = 1
from PIL import Image, ImageFilter
S = 320; K = 4
def fig_for(px, bg):
    f = plt.figure(figsize=(px / 100, px / 100), dpi=100); a = f.add_axes([0, 0, 1, 1])
    a.set_xlim(0, 1); a.set_ylim(0, 1); a.set_axis_off(); f.patch.set_facecolor(bg); return f, a
def render(draw, px, bg):
    f, a = fig_for(px, bg); draw(a, px / S); b = io.BytesIO(); f.savefig(b, facecolor=bg); plt.close(f)
    return Image.open(b).convert("RGB")
def bez(rng, n=1):
    out = []
    for _ in range(n):
        P = rng.uniform(0.1, 0.9, (4, 2)); t = np.linspace(0, 1, 200)[:, None]
        out.append(((1-t)**3*P[0] + 3*(1-t)**2*t*P[1] + 3*(1-t)*t**2*P[2] + t**3*P[3]))
    return out
def kinds():
    K_ = {}
    def lines(rng, lw, n=6, col="k"):
        cs = bez(rng, n)
        return lambda a, s: [a.plot(*c.T, color=col, lw=lw * s, solid_capstyle="round") for c in cs]
    def shapes(r):
        polys = [r.uniform(.1, .9, (r.integers(3, 7), 2)) for _ in range(3)]
        circ = [(r.uniform(.25, .75, 2), r.uniform(.05, .15)) for _ in range(2)]
        return (lambda a, s: [a.add_patch(plt.Polygon(p, color="k", lw=0)) for p in polys]
                + [a.add_patch(plt.Circle(c, q, color="k", lw=0)) for c, q in circ]), "white", None
    K_["shapes"] = shapes
    K_["lineart"] = lambda r: (lines(r, 2.5), "white", None)
    def text(r):
        w = "".join(r.choice(list("AaBgRSQ&%@ç"), 6))
        return (lambda a, s: a.text(.5, .5, w, fontsize=48 * s, ha="center", va="center", family="DejaVu Serif")), "white", None
    K_["text"] = text
    K_["hairline"] = lambda r: (lines(r, 0.7), "white", None)
    K_["thick"] = lambda r: (lines(r, 18, 3), "white", None)
    def parallel(r):
        y0 = r.uniform(.3, .4); x = np.linspace(.1, .9, 100); amp = r.uniform(.02, .08)
        return (lambda a, s: [a.plot(x, y0 + i * .025 + amp * np.sin(6 * x), "k", lw=2.5 * s) for i in range(8)]), "white", None
    K_["parallel"] = parallel
    def shallow(r):
        ang = np.radians(r.uniform(8, 20))
        return (lambda a, s: [a.plot([.1, .9], [.5 - .4 * np.tan(sg * ang), .5 + .4 * np.tan(sg * ang)], "k", lw=2.5 * s) for sg in (1, -1)]
                + [a.plot([.1, .9], [.2, .25], "k", lw=2.5 * s)]), "white", None
    K_["shallow_cross"] = shallow
    def spiral(r):
        t = np.linspace(0, r.uniform(14, 20) * np.pi, 3000); rr = .4 * t / t[-1]
        return (lambda a, s: a.plot(.5 + rr * np.cos(t), .5 + rr * np.sin(t), "k", lw=2 * s)), "white", None
    K_["spiral_tight"] = spiral
    def dots(r):
        P = r.uniform(.05, .95, (250, 2)); R = r.uniform(.004, .012, 250)
        return (lambda a, s: [a.add_patch(plt.Circle(p, q, color="k", lw=0)) for p, q in zip(P, R)]), "white", None
    K_["stipple"] = dots
    def hatch(r):
        ang = r.uniform(0, np.pi)
        def d(a, s):
            for k in np.linspace(-1, 1, 30):
                c, sn = np.cos(ang), np.sin(ang); p = np.array([.5, .5]) + k * .5 * np.array([-sn, c])
                a.plot([p[0] - c, p[0] + c], [p[1] - sn, p[1] + sn], "k", lw=1.5 * s)
            a.add_patch(plt.Rectangle((0, 0), 1, .18, color="white", zorder=3, lw=0))
        return d, "white", None
    K_["hatching"] = hatch
    K_["jpeg"] = lambda r: (lines(r, 2.5), "white", "jpeg")
    K_["noisy"] = lambda r: (lines(r, 2.5), "white", "noise")
    K_["blurry"] = lambda r: (lines(r, 3), "white", "blur")
    K_["tiny"] = lambda r: (lines(r, 2.5, 4), "white", "tiny")
    K_["inverted"] = lambda r: (lines(r, 2.5, 6, "white"), "#101010", None)
    K_["paper"] = lambda r: (lines(r, 2.5), "#efe6d2", "paper")
    K_["color_lines"] = lambda r: (lines(r, 3, 6, "#c0392b"), "#a8d8ea", None)
    return K_
def degrade(img, how, rng):
    if how == "jpeg":
        b = io.BytesIO(); img.save(b, "JPEG", quality=15); return Image.open(b).convert("RGB")
    a = np.asarray(img).astype(float)
    if how == "noise":
        a += rng.normal(0, 28, a.shape); m = rng.random(a.shape[:2]) < .01; a[m] = rng.choice([0, 255], m.sum())[:, None]
    if how == "paper":
        y, x = np.mgrid[:a.shape[0], :a.shape[1]] / a.shape[0]
        a = a * (0.75 + 0.25 * x)[..., None] + rng.normal(0, 10, a.shape[:2])[..., None]
    if how == "blur":
        return img.filter(ImageFilter.GaussianBlur(2.2))
    if how == "tiny":
        return img.resize((S // 3, S // 3), Image.LANCZOS)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA, exist_ok=True); meta = []
for name, mk in kinds().items():
    for seed in range(3):
        rng = np.random.default_rng(sum(map(ord, name)) + seed * 7919)
        draw, bg, how = mk(rng)
        gt = render(draw, S * K, bg); inp = degrade(render(draw, S, bg), how, rng)
        cid = f"{name}_{seed}"; inp.save(f"{DATA}/{cid}.png"); gt.save(f"{DATA}/{cid}_gt.png")
        meta.append({"id": cid, "kind": name, "split": "test" if seed == 2 else "train",
                     "lineart": name not in ("shapes", "text", "thick", "stipple")})
json.dump(meta, open(f"{DATA}/meta.json", "w"), indent=0); print(len(meta), "cases")
