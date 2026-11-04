"""
Centerline vectorization for line art: the skeleton of each stroke becomes an
editable SVG stroke (cubic Béziers with a stroke width), not a filled outline.

  strokes = centerline_strokes(mask) -> [(segments, width_px, closed, cap), ...]
  cap: "round" or "square" (found from the ink shape at the free ends).

Method: skeleton -> graph -> junction repair (good continuation: the most
collinear branches continue through a junction) -> exact corner apexes (line
intersection) -> free ends extended to the real stroke end -> Schneider Bézier fit.
Segments use the trace_image.py format: ('C', p0, c1, c2, p3), pixel units, y up.
"""
import numpy as np

N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


# ----------------------------------------------------------------------------
# Skeleton -> graph
# ----------------------------------------------------------------------------

def _neighbors(sk, r, c):
    h, w = sk.shape
    for dr, dc in N8:
        rr, cc = r + dr, c + dc
        if 0 <= rr < h and 0 <= cc < w and sk[rr, cc]:
            yield rr, cc


def skeleton_graph(mask):
    """Returns (nodes, edges, dt). nodes: {id: (row, col)}. edges: list of
    [points (N,2) row/col, start_node, end_node]; node -1 = closed loop."""
    import cv2
    from scipy.ndimage import convolve, label
    from skimage.morphology import skeletonize
    sk = skeletonize(mask)
    dt = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
    deg = convolve(sk.astype(int), np.ones((3, 3), int), mode="constant") - 1
    deg[~sk] = 0
    node = sk & (deg != 2)
    lab, n = label(node, structure=np.ones((3, 3)))
    nodes = {i: np.argwhere(lab == i).mean(0) for i in range(1, n + 1)}
    visited = np.zeros_like(sk)
    edges = []
    for r, c in np.argwhere(node):
        for q in _neighbors(sk, r, c):
            if node[q] or visited[q]:
                continue
            a = lab[r, c]; pts = [nodes[a], np.array(q, float)]
            prev, cur = (r, c), q; visited[q] = True; b = None
            while True:
                nb = [p for p in _neighbors(sk, *cur) if p != prev and not (visited[p] and not node[p])]
                nn = [p for p in nb if node[p] and not (lab[p] == a and len(pts) < 3)]
                if nn:
                    b = lab[nn[0]]; pts.append(nodes[b]); break
                nb = [p for p in nb if not node[p]]
                if not nb:
                    break
                prev, cur = cur, nb[0]; visited[cur] = True; pts.append(np.array(cur, float))
            if b is None:      # dead end inside the skeleton (rare): make a free node
                b = max(nodes) + 1; nodes[b] = pts[-1]
            edges.append([np.array(pts), a, b])
    for r, c in np.argwhere(node):          # direct links between two node clusters
        for q in _neighbors(sk, r, c):
            if node[q] and lab[q] > lab[r, c]:
                edges.append([np.array([nodes[lab[r, c]], nodes[lab[q]]]), lab[r, c], lab[q]])
    for r, c in np.argwhere(sk & ~node):    # isolated closed loops
        if visited[r, c]:
            continue
        loop = [(r, c)]; visited[r, c] = True; cur = (r, c)
        while True:
            nxt = next((q for q in _neighbors(sk, *cur) if not visited[q]), None)
            if nxt is None:
                break
            visited[nxt] = True; loop.append(nxt); cur = nxt
        if len(loop) > 4:
            edges.append([np.array(loop, float), -1, -1])
    return nodes, edges, dt


def _length(p):
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()) if len(p) > 1 else 0.0


def _degrees(edges):
    d = {}
    for p, a, b in edges:
        if a >= 0:
            d[a] = d.get(a, 0) + 1; d[b] = d.get(b, 0) + 1
    return d


def simplify_graph(nodes, edges, w):
    """Merges near junctions (an X crossing gives two nodes) and removes spurs."""
    # 1. collapse short edges between two junctions
    changed = True
    while changed:
        changed = False
        deg = _degrees(edges)
        for k, (p, a, b) in enumerate(edges):
            if a >= 0 and a != b and deg.get(a, 0) >= 3 and deg.get(b, 0) >= 3 and _length(p) < 1.6 * w:
                nodes[a] = (nodes[a] + nodes[b]) / 2
                edges.pop(k)
                for e in edges:
                    if e[1] == b: e[1] = a; e[0] = np.vstack([nodes[a], e[0][1:]])
                    if e[2] == b: e[2] = a; e[0] = np.vstack([e[0][:-1], nodes[a]])
                changed = True
                break
    # 2. remove spurs (free end + junction, short)
    for _ in range(2):
        deg = _degrees(edges)
        keep = []
        for p, a, b in edges:
            if a >= 0 and a != b:
                free = (deg[a] == 1) + (deg[b] == 1)
                junc = (deg[a] >= 3) + (deg[b] >= 3)
                if free == 1 and junc == 1 and _length(p) < 2.0 * w:
                    continue
            keep.append([p, a, b])
        edges = keep
    return nodes, edges


# ----------------------------------------------------------------------------
# Junction repair and stroke assembly
# ----------------------------------------------------------------------------

def _end_dir(p, at_start, r0, r1):
    """Direction that LEAVES the node, measured on the arc [r0, r1] from the node."""
    q = p if at_start else p[::-1]
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))]
    sel = (s >= r0) & (s <= r1)
    if sel.sum() < 2:
        sel = s <= max(r1, s[-1])
    seg = q[sel]
    if len(seg) < 2:
        seg = q[[0, -1]]
    c = seg.mean(0)
    u, sv, vt = np.linalg.svd(seg - c)
    d = vt[0]
    if np.dot(d, q[min(len(q) - 1, max(1, sel.argmax() + sel.sum() - 1))] - q[0]) < 0:
        d = -d
    return d / (np.linalg.norm(d) + 1e-12), c


def _intersect(p, d, q, e):
    """Intersection of lines p + s·d and q + t·e (None if almost parallel)."""
    m = np.array([d, -e]).T
    if abs(np.linalg.det(m)) < 1e-3:
        return None
    s, t = np.linalg.solve(m, q - p)
    return p + s * d


def _trim(p, at_start, r):
    q = p if at_start else p[::-1]
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))]
    out = q[s >= r]
    if len(out) < 2:
        out = q[-2:] if len(q) >= 2 else q
    return out if at_start else out[::-1]


def _extend_free_end(pt, d, mask, w):
    """Moves a free end along d to the real end of the stroke (minus the cap)."""
    h, wd = mask.shape
    t, step = 0.0, 0.5
    while True:
        r, c = (pt + (t + step) * d).round().astype(int)
        if not (0 <= r < h and 0 <= c < wd) or not mask[r, c]:
            break
        t += step
        if t > 4 * w:
            break
    return pt + max(0.0, t - w / 2) * d


def assemble_strokes(nodes, edges, mask, w, smooth=1.5, straight_deg=40):
    from scipy.ndimage import gaussian_filter1d
    deg = _degrees(edges)
    r_trim, r_dir = 1.0 * w, 3.0 * w
    # smooth each edge interior first (vertices at nodes are rebuilt later)
    E = []
    for p, a, b in edges:
        if smooth and len(p) > 5:
            s = gaussian_filter1d(p, smooth, axis=0, mode="wrap" if a < 0 else "nearest")
            if a >= 0:
                s[0], s[-1] = p[0], p[-1]
            p = s
        E.append([p, a, b])
    # ends: (edge, at_start) -> partner end / terminal point
    link, term = {}, {}
    ends_at = {}
    for k, (p, a, b) in enumerate(E):
        if a >= 0:
            ends_at.setdefault(a, []).append((k, True)); ends_at.setdefault(b, []).append((k, False))
    trimmed, trim_r, capv = {}, {}, {}
    for nid, ends in ends_at.items():
        info = []
        for k, st in ends:
            p = E[k][0]
            if deg[nid] == 1:            # free end: the skeleton tail is not reliable
                L = _length(p)
                d, c = _end_dir(p, st, min(w, L / 4), min(3 * w, L / 2))
                q = _trim(p, st, min(w, L / 4))
                pt = q[0] if st else q[-1]
                pt = c + np.dot(pt - c, d) * d          # project onto the end line
                E[k][0] = q
                end = _extend_free_end(pt, -d, mask, w)
                term[(k, st)] = end
                capv[(k, st)] = _cap_shape(end, -d, mask, w)
                continue
            L = _length(p)
            d, c = _end_dir(p, st, min(r_trim, L / 3), min(r_dir, L * 0.8))
            info.append((k, st, d, c))
        # pair the most opposite directions (good continuation); deg 2 always pairs
        pairs, used = [], set()
        cand = sorted(((np.dot(x[2], y[2]), i, j) for i, x in enumerate(info)
                       for j, y in enumerate(info) if i < j))
        for dot, i, j in cand:
            if i in used or j in used:
                continue
            if len(info) == 2 or dot < -np.cos(np.radians(straight_deg)):
                pairs.append((i, j)); used |= {i, j}
        partner = {}
        for i, j in pairs:
            partner[i] = j; partner[j] = i
        # the skeleton bends near a junction over ~w / (2 sin(φ/2)), φ = the smallest
        # angle to another branch. Skip that zone, measure directions after it.
        rad = {}
        for i, (k, st, d, c) in enumerate(info):
            others = [np.arccos(np.clip(np.dot(d, y[2]), -1, 1)) for j, y in enumerate(info)
                      if j != i and j != partner.get(i)]
            if i in partner and len(info) == 2:
                others.append(np.arccos(np.clip(np.dot(d, info[partner[i]][2]), -1, 1)))
            phi = min(others) if others else np.pi
            r = float(np.clip(0.5 * w / max(np.sin(phi / 2), 0.1) + 0.5 * w, w, 5 * w))
            L = _length(E[k][0])
            rad[i] = min(r, L / 3)
            d2, c2 = _end_dir(E[k][0], st, rad[i], min(rad[i] + 3 * w, L * 0.8))
            info[i] = (k, st, d2, c2)
            trim_r[(k, st)] = rad[i]; trimmed[(k, st)] = True
        for i, j in pairs:
            (ki, si, di, ci), (kj, sj, dj, cj) = info[i], info[j]
            theta = np.arccos(np.clip(np.dot(di, dj), -1, 1))      # angle between arms
            if theta >= np.radians(180 - straight_deg):
                x = None                     # straight crossing: no extra vertex
            else:                            # corner: the apex is the line intersection
                x = _intersect(ci, di, cj, dj)
                if x is None or np.linalg.norm(x - nodes[nid]) > 5 * w:
                    x = nodes[nid]
            link[(ki, si)] = ((kj, sj), x); link[(kj, sj)] = ((ki, si), x)
        for i, (k, st, d, c) in enumerate(info):
            if i in used:
                continue
            # T-junction stem: end where its line meets the node (projected)
            term[(k, st)] = c + np.dot(nodes[nid] - c, d) * d
    # trim edges near junctions
    P = []
    for k, (p, a, b) in enumerate(E):
        q = p
        for st in (True, False):
            if trimmed.get((k, st)):
                q = _trim(q, st, trim_r.get((k, st), min(r_trim, _length(q) / 3)))
        P.append(q)
    # walk chains
    done = set(); strokes = []

    def walk(k, st):
        pts, corners = [], []
        closed = False
        start = (k, st)
        caps = [capv.get(start)]
        if start in term:
            pts.append(term[start])
        while True:
            done.add(k)
            q = P[k] if st else P[k][::-1]
            pts.extend(q)
            far = (k, not st)
            if far in link:
                (k2, st2), x = link[far]
                if k2 in done:
                    if (k2, st2) == start:
                        if x is not None:
                            corners.append(len(pts)); pts.append(x)
                        closed = True
                    break
                if x is not None:
                    corners.append(len(pts)); pts.append(x)
                k, st = k2, st2
            else:
                if far in term:
                    pts.append(term[far])
                caps.append(capv.get(far))
                break
        caps = [c for c in caps if c]
        cap = "square" if caps and caps.count("square") * 2 >= len(caps) else "round"
        return np.array(pts), corners, closed, cap

    for k, (p, a, b) in enumerate(E):          # open chains start at terminal ends
        for st in (True, False):
            if k not in done and (k, st) in term:
                strokes.append(walk(k, st))
    for k, (p, a, b) in enumerate(E):          # remaining: closed loops
        if k in done:
            continue
        if a < 0:
            done.add(k); strokes.append((P[k], [], True, "round"))
        else:
            pts, corners, closed, cap = walk(k, True)
            strokes.append((pts, corners, True, cap))
    return strokes


def _cap_shape(end, d, mask, w):
    """'square' if the ink has corners past the end point (butt/square pen end),
    else 'round'. d points out of the stroke."""
    n = np.array([-d[1], d[0]])
    h, wd = mask.shape
    hits = 0
    for sgn in (-1, 1):
        r, c = (end + d * 0.35 * w + n * sgn * 0.4 * w).round().astype(int)
        hits += 0 <= r < h and 0 <= c < wd and bool(mask[r, c])
    return "square" if hits == 2 else "round"


def _sharpen(pts, corners, w, angle=28):
    """Keeps only real corners (bridge points with a sharp turn)."""
    keep = []
    for i in corners:
        if 0 < i < len(pts) - 1:
            a = pts[i] - pts[max(0, i - 3)]; b = pts[min(len(pts) - 1, i + 3)] - pts[i]
            cos = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
            if np.degrees(np.arccos(np.clip(cos, -1, 1))) > angle:
                keep.append(i)
    return keep


def _resample(pts, corners, step=1.0):
    """Uniform resampling that keeps the corner points; returns new corner indices."""
    out, newc = [pts[0]], []
    cs = set(corners)
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        L = np.linalg.norm(b - a)
        n = int(L // step)
        for j in range(1, n + 1):
            if j * step < L - 1e-6:
                out.append(a + (b - a) * j * step / L)
        out.append(b)
        if i in cs:
            newc.append(len(out) - 1)
    return np.array(out), newc


# ----------------------------------------------------------------------------
# Bézier fit (Schneider, "An Algorithm for Automatically Fitting Digitized Curves")
# ----------------------------------------------------------------------------

def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _bez(ctrl, t):
    t = np.asarray(t)[:, None]
    p0, p1, p2, p3 = ctrl
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def _bez_d(ctrl, t, order):
    t = np.asarray(t)[:, None]
    p0, p1, p2, p3 = ctrl
    if order == 1:
        return 3 * (1 - t) ** 2 * (p1 - p0) + 6 * (1 - t) * t * (p2 - p1) + 3 * t ** 2 * (p3 - p2)
    return 6 * (1 - t) * (p2 - 2 * p1 + p0) + 6 * t * (p3 - 2 * p2 + p1)


def _generate(pts, u, tl, tr):
    p0, p3 = pts[0], pts[-1]
    A1 = np.outer(3 * (1 - u) ** 2 * u, tl); A2 = np.outer(3 * (1 - u) * u ** 2, tr)
    C = np.array([[(A1 * A1).sum(), (A1 * A2).sum()], [(A1 * A2).sum(), (A2 * A2).sum()]])
    tmp = pts - _bez([p0, p0, p3, p3], u)
    X = np.array([(A1 * tmp).sum(), (A2 * tmp).sum()])
    det = C[0, 0] * C[1, 1] - C[0, 1] * C[1, 0]
    seg = np.linalg.norm(p3 - p0)
    if abs(det) > 1e-12:
        al = (X[0] * C[1, 1] - X[1] * C[0, 1]) / det
        ar = (C[0, 0] * X[1] - C[1, 0] * X[0]) / det
    else:
        al = ar = seg / 3
    if al < 1e-6 * seg or ar < 1e-6 * seg:
        al = ar = seg / 3
    return [p0, p0 + tl * al, p3 + tr * ar, p3]


def _reparam(ctrl, pts, u):
    d = _bez(ctrl, u) - pts
    d1 = _bez_d(ctrl, u, 1); d2 = _bez_d(ctrl, u, 2)
    num = (d * d1).sum(1); den = (d1 * d1 + d * d2).sum(1)
    with np.errstate(all="ignore"):
        step = np.where(np.abs(den) > 1e-12, num / den, 0)
    return np.clip(u - np.nan_to_num(step), 0, 1)


def _fit(pts, tl, tr, err, out, depth=0):
    if len(pts) == 2:
        d = np.linalg.norm(pts[1] - pts[0]) / 3
        out.append([pts[0], pts[0] + tl * d, pts[1] + tr * d, pts[1]]); return
    u = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    u = u / u[-1] if u[-1] > 0 else np.linspace(0, 1, len(pts))
    ctrl = _generate(pts, u, tl, tr)
    for it in range(8):
        e = np.sum((_bez(ctrl, u) - pts) ** 2, axis=1)
        i = int(np.argmax(e))
        if e[i] < err ** 2:
            out.append(ctrl); return
        if e[i] > (4 * err) ** 2 or it == 7:
            break
        u = _reparam(ctrl, pts, u); ctrl = _generate(pts, u, tl, tr)
    if depth > 30 or len(pts) < 4:
        out.append(ctrl); return
    i = int(np.clip(i, 1, len(pts) - 2))
    tc = _unit(pts[i - 1] - pts[i + 1])
    _fit(pts[: i + 1], tl, tc, err, out, depth + 1)
    _fit(pts[i:], -tc, tr, err, out, depth + 1)


def _corners(pts, k=4, angle=55):
    """Indices of sharp corners (direction change > angle over k points)."""
    n = len(pts)
    if n < 2 * k + 1:
        return []
    a = pts[k:-k] - pts[: -2 * k]; b = pts[2 * k:] - pts[k:-k]
    cos = (a * b).sum(1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1) + 1e-9)
    ang = np.degrees(np.arccos(np.clip(cos, -1, 1)))
    idx = [i + k for i in range(1, len(ang) - 1)
           if ang[i] > angle and ang[i] >= ang[i - 1] and ang[i] >= ang[i + 1]]
    keep = []
    for i in idx:
        if not keep or i - keep[-1] > k:
            keep.append(i)
    return keep


def fit_beziers(pts, err=1.0, closed=False, corners=None):
    """Polyline -> list of ('C', p0, c1, c2, p3) or ('L', p0, p1) for straight
    parts. Sharp corners stay sharp.
    corners: known corner indices (else they are detected)."""
    pts = np.asarray(pts, float)
    if closed:
        pts = np.vstack([pts, pts[:1]])
    found = _corners(pts) if corners is None else list(corners)
    cuts = sorted(set([0] + [c for c in found if 0 < c < len(pts) - 1] + [len(pts) - 1]))
    segs = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        part = pts[a:b + 1]
        if len(part) < 2:
            continue
        chord = part[-1] - part[0]; Lc = np.linalg.norm(chord)
        if Lc > 1e-9:          # straight part -> exact line segment
            dev = np.abs(np.cross(chord, part - part[0])) / Lc
            if dev.max() < max(0.8, 0.8 * err):
                segs.append(("L", part[0], part[-1])); continue
        k = min(3, len(part) - 1)
        tl = _unit(part[k] - part[0]); tr = _unit(part[-1 - k] - part[-1])
        out = []
        _fit(part, tl, tr, err, out)
        segs += [("C", *c) for c in out]
    return segs


# ----------------------------------------------------------------------------

def centerline_strokes(mask, err=1.0, smooth=1.5, min_len=3, ink=None):
    """Mask of line art -> [(segments, width_px, closed, cap)], pixel units, y up.
    ink: optional 0..1 darkness map (antialiased edges) for a more exact width."""
    h = mask.shape[0]
    nodes, edges, dt = skeleton_graph(mask)
    vals = dt[dt > 1]
    w = 2 * float(np.median(vals)) - 1 if len(vals) else 2.0     # center dt ≈ w/2 + 0.5
    w = max(w, 2.0)
    nodes, edges = simplify_graph(nodes, edges, w)
    chains = [c for c in assemble_strokes(nodes, edges, mask, w, smooth)
              if len(c[0]) >= 2 and (_length(c[0]) >= min_len or c[2])]
    caps = [c[3] for c in chains]
    chains = [c[:3] for c in chains]
    widths = _stroke_widths(mask, chains, dt, w, ink)
    out = []
    for (pts, corners, closed), width, cap in zip(chains, widths, caps):
        corners = _sharpen(pts, corners, width)
        pts, corners = _resample(pts, corners)
        if closed and len(pts) > 2 and np.linalg.norm(pts[0] - pts[-1]) < 1e-6:
            pts = pts[:-1]
        xy = np.c_[pts[:, 1], h - pts[:, 0]]
        auto = [c for c in _corners(xy) if all(abs(c - k) > 3 for k in corners)]
        out.append((fit_beziers(xy, err, closed, sorted(corners + auto)), width, closed, cap))
    return out


def _stroke_widths(mask, chains, dt, w, ink=None):
    """Width = ink area assigned to the stroke / stroke length. Each ink pixel goes
    to the nearest centerline. More accurate than the distance transform alone."""
    import cv2
    from scipy.ndimage import distance_transform_edt
    h, wd = mask.shape
    ids = np.zeros((h, wd), np.int32)
    for i, (pts, _, closed) in enumerate(chains):
        p = np.c_[pts[:, 1], pts[:, 0]].round().astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(ids, [p], bool(closed), i + 1, 1)
    _, (ri, ci) = distance_transform_edt(ids == 0, return_indices=True)
    owner = ids[ri, ci]
    if ink is None:
        area = np.bincount(owner[mask].ravel(), minlength=len(chains) + 1)
    else:                      # sum the ink in the stroke and its antialiased edge
        from scipy.ndimage import binary_dilation
        reg = binary_dilation(mask, iterations=2)
        area = np.bincount(owner[reg].ravel(), weights=np.clip(ink[reg], 0, 1),
                           minlength=len(chains) + 1)
    out = []
    for i, (pts, _, closed) in enumerate(chains):
        L = _length(pts) + (np.linalg.norm(pts[0] - pts[-1]) if closed else 0)
        rc = np.clip(pts.round().astype(int), 0, np.array(mask.shape) - 1)
        wv = dt[rc[:, 0], rc[:, 1]]
        wdt = 2 * float(np.median(wv[wv > 1])) - 1 if (wv > 1).any() else w
        if L > 2 * w:
            A = area[i + 1]
            # open stroke: ink ≈ w·(L + w) (a half-width cap at each end)
            wi = A / L if closed else (-L + np.sqrt(L * L + 4 * A)) / 2
            # other strokes take the ink at crossings: a much larger distance-map
            # width means the area value is too low (thick stroke crossed by thin ones)
            if wdt > 1.25 * wi:
                wi = wdt
        else:
            wi = wdt
        out.append(float(np.clip(wi, 1.0, 3 * w)))
    return out
