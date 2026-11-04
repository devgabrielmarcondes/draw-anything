"""Run color mode on the dataset; metrics at 4x vs clean ground truth.
Usage: python bench.py '{"colors": 16}' [train|test|all] [results.json]"""
import io, json, os, re, sys, tempfile, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np, cairosvg
from PIL import Image
from scipy.ndimage import distance_transform_edt
from skimage.color import rgb2lab, deltaE_ciede2000
from skimage.metrics import structural_similarity

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
sys.path.insert(0, str(HERE.parent.parent / "skills" / "draw-anything" / "scripts"))
import trace_image as T


def load_rgb(path):
    """Same as trace_image.load: RGBA input loses its alpha."""
    return T.load(path)


def vectorize(path, p, meta, out):
    """The color path of trace_image.py main(), with parameters from `p`."""
    t0 = time.time()
    rgb = T.fit_resolution(load_rgb(path))
    h, w = rgb.shape[:2]
    n = meta["gt_colors"] if p.get("colors") == "gt" else int(p.get("colors", 16))
    n = max(2, min(n, p.get("max_colors", 32)))
    cl = T.color_layers(rgb, n, merge=p.get("merge", 7.0), sp=p.get("sp", 4), sr=p.get("sr", 12))
    bg = cl[0][0]
    d, sm, tol = p.get("detail", 4), p.get("smooth", 1.0), p.get("tol", 0.2)
    layers = [(c, T.trace(m, d, sm, tol)) for c, m in cl[1:]]
    if p.get("lines"):
        kl = T.key_lines(rgb)
        if kl: layers.append((kl[0], T.trace(kl[1], d, sm, tol)))
        sp_ = T.bright_spots(rgb)
        if sp_: layers.append((sp_[0], T.trace(sp_[1], 0, sm, tol)))
    T.write_svg(layers, w, h, out, bg)
    return time.time() - t0


def metrics(svg, gt):
    H, W = gt.shape[:2]
    png = cairosvg.svg2png(url=str(svg), output_width=W, output_height=H)
    out = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))
    la, lb = rgb2lab(gt), rgb2lab(out)
    de = deltaE_ciede2000(la, lb)
    ssim = structural_similarity(gt, out, channel_axis=2, data_range=255)

    def edges(lab):   # region borders: a jump of more than 10 ΔE76 to the right or down neighbor
        e = np.zeros(lab.shape[:2], bool)
        e[:, :-1] |= np.linalg.norm(lab[:, 1:] - lab[:, :-1], axis=2) > 10
        e[:-1] |= np.linalg.norm(lab[1:] - lab[:-1], axis=2) > 10
        return e
    e1, e2 = edges(la), edges(lb)
    if e1.any() and e2.any():
        d = np.r_[distance_transform_edt(~e1)[e2], distance_transform_edt(~e2)[e1]] / 4   # input px
        edge = float(d.mean())
    else:
        edge = float("nan")
    txt = Path(svg).read_text(encoding="utf-8")
    return dict(de=float(de.mean()), de95=float(np.percentile(de, 95)), ssim=float(ssim), edge=edge,
                regions=len(re.findall(r"M ", txt)), colors=len(set(re.findall(r'fill="(#[0-9a-f]{6})"', txt))),
                kb=len(txt.encode()) / 1024)


def run_case(args):
    m, p, data = args
    svg = Path(tempfile.gettempdir()) / f"da_color_{os.getpid()}_{m['id']}.svg"
    sec = vectorize(Path(data) / f"{m['id']}.png", p, m, svg)
    gt = np.asarray(Image.open(Path(data) / f"{m['id']}_gt.png").convert("RGB"))
    r = dict(m, sec=sec, **metrics(svg, gt)); svg.unlink()
    return r


def run(p, split="all", data=DATA, procs=None):
    meta = json.load(open(Path(data) / "meta.json"))
    cases = [(m, p, str(data)) for m in meta if split == "all" or m["split"] == split]
    with Pool(procs) as pool:
        return pool.map(run_case, cases)


if __name__ == "__main__":
    params = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    split = sys.argv[2] if len(sys.argv) > 2 else "all"
    res = run(params, split)
    for r in res: print(json.dumps(r))
    json.dump(res, open(sys.argv[3] if len(sys.argv) > 3 else "res.json", "w"))
