"""Run the vectorizer on the dataset; metrics at 4x vs clean ground truth."""
import sys, json, time, io, os, tempfile, numpy as np, cairosvg
from pathlib import Path
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
sys.path.insert(0, str(HERE.parent / "skills" / "draw-anything" / "scripts"))
import trace_image as T, centerline as C
from PIL import Image
from scipy.ndimage import distance_transform_edt, binary_erosion
from skimage.measure import euler_number

def gt_mask(path):
    rgb = np.asarray(Image.open(path).convert("RGB"))
    return T.ink_mask(rgb)

def vectorize(path, method, p):
    t0 = time.time()
    rgb = T.fit_resolution(T.load(path))
    if p.get("pre") == "median":
        import cv2; rgb = cv2.medianBlur(rgb, 5)
    if p.get("denoise"):
        import cv2
        g = rgb.mean(2)
        lap = cv2.Laplacian(g.astype(np.float32), cv2.CV_32F)
        noise = 1.4826 * np.median(np.abs(lap - np.median(lap)))    # robust noise estimate
        if noise > p.get("noise_thr", 6):
            rgb = cv2.medianBlur(rgb, 5); rgb = cv2.bilateralFilter(rgb, 7, 40, 5)
    mask = T.ink_mask(rgb, None, None, p.get("blur", 0.0))
    if p.get("thr") == "mid":         # edge at 50% between paper and ink levels
        g = rgb.mean(2) / 255.0
        if np.median(np.concatenate([g[0], g[-1], g[:, 0], g[:, -1]])) < 0.5: g = 1 - g
        lo, hi = np.median(g[mask]), np.median(g[~mask])
        mask = g < (lo + hi) / 2
    h, w = mask.shape
    if method == "fill":
        layers = [("#000000", T.trace(mask, p.get("detail", 4), p.get("smooth", 1.0), p.get("tol", 0.2)))]
    else:
        g = rgb.mean(2) / 255; lo, hi = np.median(g[~mask]), np.median(g[mask])
        ink = (g - lo) / (hi - lo) if abs(hi - lo) > .05 else None
        if p.get("detail", 4):
            from scipy.ndimage import label
            lab, n = label(mask); sz = np.bincount(lab.ravel()); mask = mask & (sz[lab] > p.get("detail", 4) * 4)
        st = C.centerline_strokes(mask, err=p.get("err", 1.0), smooth=p.get("csmooth", 1.5), ink=ink)
        layers = [("#000000", st, "stroke", "round")]
    b = io.StringIO(); fn = os.path.join(tempfile.gettempdir(), "draw_anything_bench.svg")
    T.write_svg(layers, w, h, fn, "#ffffff")
    dt = time.time() - t0
    nseg = sum(len(s) if not T.is_stroke(l) else len(s[0]) for l in layers for s in l[1])
    return fn, nseg, os.path.getsize(fn), dt

def metrics(svg, gtm):
    H, W = gtm.shape
    png = cairosvg.svg2png(url=svg, output_width=W, output_height=H)
    out = np.asarray(Image.open(io.BytesIO(png)).convert("L")) < 128
    inter, uni = (out & gtm).sum(), (out | gtm).sum()
    e1 = gtm & ~binary_erosion(gtm); e2 = out & ~binary_erosion(out)
    if e2.any():
        d = np.r_[distance_transform_edt(~e1)[e2], distance_transform_edt(~e2)[e1]] / 4   # input px
        ch, h95 = float(d.mean()), float(np.percentile(d, 95))
    else:
        ch, h95 = 99.0, 99.0
    eul = abs(euler_number(out, 2) - euler_number(gtm, 2))
    return dict(iou=float(inter / max(uni, 1)), chamfer=ch, h95=h95, euler=int(eul))

if __name__ == "__main__":
    params = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    split = sys.argv[2] if len(sys.argv) > 2 else "all"
    meta = json.load(open(DATA / "meta.json")); res = []
    for m in meta:
        if split != "all" and m["split"] != split: continue
        gtm = gt_mask(DATA / f"{m['id']}_gt.png")
        for method in (["fill", "center"] if m["lineart"] else ["fill"]):
            svg, nseg, size, dt = vectorize(DATA / f"{m['id']}.png", method, params)
            r = dict(m, method=method, nseg=nseg, kb=size / 1024, sec=dt, **metrics(svg, gtm))
            res.append(r); print(json.dumps(r), flush=True)
    json.dump(res, open(sys.argv[3] if len(sys.argv) > 3 else "res.json", "w"))
