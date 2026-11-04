#!/usr/bin/env python3
"""
Tupper's self-referential formula (and the generalized form).

    1/2 < ⌊ mod( ⌊y/H⌋ · 2^(−H⌊x⌋ − mod(⌊y⌋, H)), 2 ) ⌋

For 0 ≤ x < W and k ≤ y < k+H, the graph shows a W×H bitmap that is encoded in
the number k (a multiple of H). H=17 and W=106 is the classic formula. One k
draws the formula itself. There is a k for ALL 106×17 images.

Usage:
  python tupper.py encode --text "HELLO WORLD" --png hello.png --out k.txt
  python tupper.py encode --image pixel_art.png --height 17 --png art.png
  python tupper.py encode --ascii drawing.txt        # '#' = on, '.' = off
  python tupper.py decode --k-file k.txt --png check.png
  python tupper.py classic --png tupper.png          # draws the formula itself

Decode calculates the real FORMULA with exact integers. Thus the image
proves that k is correct.

Axes convention: on usual axes (x to the right, y up) the Tupper bitmap shows
ROTATED 180°. Thus people always show the classic graph with the two axes
reversed. This script uses the same convention, so its k values work in other
Tupper plotters. In Desmos/GeoGebra, reverse the axes (or turn the image 180°).
"""
import argparse, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from _common import parse_size, theme

# classic k (Tupper, 2001): draws the formula itself
CLASSIC_K = int(
    "960939379918958884971672962127852754715004339660129306651505519271702802395266424689642842174350718121267153782770623355993237280874144307891325963941337723487857735749823926629715517173716995165232890538221612403238855866184013235585136048828693337902491454229288667081096184496091705183454067827731551705405381627380967602565625016981482083418783163849115590225610003652351370343874461848378737238198224849863465033159410054974700593138339226497249461751545728366702369745461014655997933798537483143786841806593422227898388722980000748404719")

FORMULA = "1/2 < floor(mod(floor(y/{H}) * 2^(-{H}*floor(x) - mod(floor(y), {H})), 2))"


def bitmap_to_k(bmp):
    """bmp: H×W array of 0/1 as you SEE the image (row 0 = top, column 0 = left),
    in the classic reversed-axes convention. Returns (k, H, W)."""
    bmp = np.asarray(bmp).astype(int)
    H, W = bmp.shape
    n = 0
    for x in range(W - 1, -1, -1):
        for y0 in range(H - 1, -1, -1):       # y0 = 0 is the BOTTOM row
            n = (n << 1) | int(bmp[y0, W - 1 - x])
    return n * H, H, W


def k_to_bitmap(k, H=17, W=106):
    """Calculates the Tupper formula for each point (exact integers)."""
    bmp = np.zeros((H, W), int)
    for x in range(W):
        for y0 in range(H):
            y = k + y0
            # ⌊ mod(⌊y/H⌋ · 2^(−H·x − y0), 2) ⌋ == bit (H·x + y0) of ⌊y/H⌋
            v = ((y // H) >> (H * x + (y % H))) & 1
            bmp[y0, W - 1 - x] = 1 if 0.5 < v else 0
    return bmp


def text_bitmap(text, H=17, font=None):
    from PIL import Image, ImageDraw, ImageFont
    font = font or "DejaVuSansMono-Bold.ttf"
    best = None
    for fs in range(H + 4, 6, -1):           # largest font that fits in H rows
        try:
            f = ImageFont.truetype(font, fs)
        except OSError:
            f = ImageFont.load_default(); fs = 0
        l, t, r, b = f.getbbox(text)
        if b - t <= H - 2 or fs == 0:
            img = Image.new("L", (r - l + 4, H), 0)
            ImageDraw.Draw(img).text((2 - l, (H - (b - t)) // 2 - t), text, fill=255, font=f)
            best = (np.asarray(img) > 110).astype(int)
            break
    return best


def image_bitmap(path, H=17, W=None, threshold=128, invert=False):
    from PIL import Image
    im = Image.open(path).convert("L")
    if W is None:
        W = max(1, round(im.width * H / im.height))
    im = im.resize((W, H), Image.LANCZOS)
    a = np.asarray(im)
    on = a < threshold
    return (~on if invert else on).astype(int)


def ascii_bitmap(path):
    rows = [r.rstrip("\n") for r in open(path, encoding="utf-8") if r.strip()]
    W = max(len(r) for r in rows)
    return np.array([[1 if c in "#X█*1@" else 0 for c in r.ljust(W)] for r in rows])


def pad(bmp, W=None):
    H, w = bmp.shape
    W = W or max(w, 106 if H == 17 else w)
    if w >= W:
        return bmp
    left = (W - w) // 2
    return np.pad(bmp, ((0, 0), (left, W - w - left)))


def render(bmp, out, k=None, size="youtube", th_name="dark", grid=True, show_k=True):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    th = theme(th_name); w, h = parse_size(size)
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_facecolor(th["bg"])
    H, W = bmp.shape
    ax = fig.add_axes([0.05, 0.3, 0.9, 0.5] if show_k and k else [0.03, 0.1, 0.94, 0.8])
    ax.imshow(bmp, cmap=ListedColormap([th["bg"], th["accent"]]), interpolation="nearest",
              aspect="equal", extent=(0, W, 0, H))
    if grid:
        for x in range(W + 1): ax.axvline(x, color=th["muted"], lw=0.3, alpha=0.5)
        for y in range(H + 1): ax.axhline(y, color=th["muted"], lw=0.3, alpha=0.5)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_color(th["muted"])
    if show_k and k is not None:
        ks = str(k)
        short = ks if len(ks) <= 60 else f"{ks[:28]}…{ks[-28:]}  ({len(ks)} digits)"
        fig.text(0.5, 0.17, r"$\frac{1}{2} < \left\lfloor \mathrm{mod}\left(\left\lfloor \frac{y}{%d} \right\rfloor 2^{-%d\lfloor x \rfloor - \mathrm{mod}(\lfloor y \rfloor, %d)}, 2\right)\right\rfloor$" % (H, H, H),
                 ha="center", color=th["fg"], fontsize=w / 70)
        fig.text(0.5, 0.07, f"k = {short}", ha="center", color=th["muted"] if th_name != "dark" else "#9aa3b2",
                 fontsize=w / 95, family="monospace")
    fig.savefig(out, facecolor=th["bg"]); plt.close(fig)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("encode")
    src = e.add_mutually_exclusive_group(required=True)
    src.add_argument("--text"); src.add_argument("--image"); src.add_argument("--ascii")
    e.add_argument("--height", type=int, default=17)
    e.add_argument("--width", type=int, help="final width (default: 106 if H=17)")
    e.add_argument("--font"); e.add_argument("--invert", action="store_true")
    d = sub.add_parser("decode")
    g = d.add_mutually_exclusive_group(required=True)
    g.add_argument("--k"); g.add_argument("--k-file")
    d.add_argument("--height", type=int, default=17); d.add_argument("--width", type=int, default=106)
    c = sub.add_parser("classic")
    for p in (e, d, c):
        p.add_argument("--png"); p.add_argument("--out", help="write k + formula to .txt")
        p.add_argument("--size", default="youtube"); p.add_argument("--theme", default="dark")
        p.add_argument("--no-grid", action="store_true"); p.add_argument("--no-k", action="store_true")
    a = ap.parse_args()

    if a.cmd == "encode":
        H = a.height
        if a.text: bmp = text_bitmap(a.text, H, a.font)
        elif a.image: bmp = image_bitmap(a.image, H, a.width, invert=a.invert)
        else: bmp = ascii_bitmap(a.ascii); H = bmp.shape[0]
        bmp = pad(bmp, a.width)
        k, H, W = bitmap_to_k(bmp)
        assert (k_to_bitmap(k, H, W) == bmp).all(), "check failed"
    elif a.cmd == "decode":
        k = int(open(a.k_file, encoding="utf-8").read().split()[0]) if a.k_file else int(a.k)
        H, W = a.height, a.width
        bmp = k_to_bitmap(k, H, W)
    else:
        k, H, W = CLASSIC_K, 17, 106
        bmp = k_to_bitmap(k, H, W)

    print(f"Bitmap {W}×{H}  |  k has {len(str(k))} digits")
    if a.out:
        open(a.out, "w", encoding="utf-8").write(f"{k}\n\n# Formula (plot 0 ≤ x < {W}, k ≤ y < k+{H}):\n"
                               f"# {FORMULA.format(H=H)}\n")
        print("k written to", a.out)
    png = a.png or ("tupper.png" if not a.out else None)
    if png:
        render(bmp, png, k, a.size, a.theme, grid=not a.no_grid, show_k=not a.no_k)
        print("PNG:", png)


if __name__ == "__main__":
    main()
