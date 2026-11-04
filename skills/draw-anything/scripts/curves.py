#!/usr/bin/env python3
"""
Math curves: implicit, parametric and polar equations.

Each curve is a numpy expression as text. You can combine many --implicit,
--region, --parametric and --polar curves. Add '::#hex' to set the color.
The variable 'a' goes from 0 to 1 during an animation (use it to morph).

  Implicit    f(x,y)=0        --implicit "(x**2+y**2-1)**3 - x**2*y**3"
  Region      f(x,y)<=0       --region   "(x**2+y**2-1)**3 - x**2*y**3::#e63946"
  Parametric  (x(t), y(t))    --parametric "sin(3*t); sin(4*t)" --t-range 0,6.2832
  Polar       r(th)           --polar "cos(4*th)" --th-range 0,6.2832

Functions: sin cos tan asin acos atan atan2 sinh cosh tanh exp log
sqrt abs floor ceil mod sign minimum maximum hypot pi e clip where.

Examples:
  python curves.py --region "(x**2+y**2-1)**3 - x**2*y**3" --png heart.png \
         --range -1.5,1.5,-1.3,1.5 --caption "$(x^2+y^2-1)^3 = x^2y^3$"
  python curves.py --polar "1+0.3*cos(7*th+6.283*a)" --anim flower.mp4 --size reels
  python curves.py --implicit "sin(x)*cos(y)-0.3*cos(6.283*a)" --range -8,8,-8,8 \
         --anim field.gif --axes
"""
import argparse, sys, os
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from _common import parse_size, theme, make_figure, fit_view, save_animation, transparent_theme

NS = {k: getattr(np, k) for k in
      "sin cos tan arcsin arccos arctan arctan2 sinh cosh tanh exp log log2 log10 sqrt abs "
      "floor ceil mod sign minimum maximum hypot pi e clip where real imag".split()}
NS.update(asin=np.arcsin, acos=np.arccos, atan=np.arctan, atan2=np.arctan2, ln=np.log)


def ev(expr, **vars_):
    with np.errstate(all="ignore"):
        return eval(expr, {"__builtins__": {}}, {**NS, **vars_})


def split_color(spec, default):
    if "::" in spec:
        e, c = spec.rsplit("::", 1)
        return e.strip(), c.strip()
    return spec.strip(), default


def draw(ax, a, args, th, size, view):
    xmin, xmax, ymin, ymax = view
    res = args.res
    asp = (xmax - xmin) / (ymax - ymin)
    nx, ny = (res, int(res / asp)) if asp >= 1 else (int(res * asp), res)
    X, Y = np.meshgrid(np.linspace(xmin, xmax, nx), np.linspace(ymin, ymax, ny))
    lw = max(size) / 360 * args.lw
    palette = [th["accent"], th["fill"], th["fg"], "#4cc9f0", "#f72585", "#80ed99"]
    ci = 0

    def nxt():
        nonlocal ci
        c = palette[ci % len(palette)]; ci += 1
        return c

    for spec in args.region:
        e, col = split_color(spec, nxt())
        Z = ev(e, x=X, y=Y, a=a)
        ax.contourf(X, Y, Z, levels=[-np.inf, 0], colors=[col])
    for spec in args.implicit:
        e, col = split_color(spec, nxt())
        Z = ev(e, x=X, y=Y, a=a)
        ax.contour(X, Y, Z, levels=[0], colors=[col], linewidths=lw)
    for spec in args.parametric:
        e, col = split_color(spec, nxt())
        fx, fy = e.split(";")
        t0, t1 = args.t_range
        t = np.linspace(t0, t1, args.samples)
        x = ev(fx, t=t, a=a) * np.ones_like(t); y = ev(fy, t=t, a=a) * np.ones_like(t)
        ax.plot(x, y, color=col, lw=lw, solid_capstyle="round")
    for spec in args.polar:
        e, col = split_color(spec, nxt())
        t0, t1 = args.th_range
        th_ = np.linspace(t0, t1, args.samples)
        r = ev(e, th=th_, t=th_, a=a) * np.ones_like(th_)
        ax.plot(r * np.cos(th_), r * np.sin(th_), color=col, lw=lw, solid_capstyle="round")


def auto_view(args):
    """No --range: find the area from parametric/polar curves. Else use [-2,2]²."""
    pts = []
    for spec in args.parametric:
        e, _ = split_color(spec, "")
        fx, fy = e.split(";"); t = np.linspace(*args.t_range, 2000)
        pts.append(np.c_[ev(fx, t=t, a=0) * np.ones_like(t), ev(fy, t=t, a=0) * np.ones_like(t)])
    for spec in args.polar:
        e, _ = split_color(spec, ""); th_ = np.linspace(*args.th_range, 2000)
        r = ev(e, th=th_, t=th_, a=0) * np.ones_like(th_)
        pts.append(np.c_[r * np.cos(th_), r * np.sin(th_)])
    if pts:
        P = np.vstack(pts); P = P[np.isfinite(P).all(1)]
        return P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max()
    return -2, 2, -2, 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--implicit", action="append", default=[])
    ap.add_argument("--region", action="append", default=[])
    ap.add_argument("--parametric", action="append", default=[])
    ap.add_argument("--polar", action="append", default=[])
    ap.add_argument("--range", help="xmin,xmax,ymin,ymax")
    ap.add_argument("--t-range", default="0,6.283185307")
    ap.add_argument("--th-range", default="0,6.283185307")
    ap.add_argument("--samples", type=int, default=6000)
    ap.add_argument("--res", type=int, default=1400, help="grid resolution for implicit curves")
    ap.add_argument("--lw", type=float, default=1.0, help="line width multiplier")
    ap.add_argument("--axes", action="store_true", help="graphing-calculator axes and grid")
    ap.add_argument("--caption", help="text or equation (mathtext: $...$) at the bottom")
    ap.add_argument("--size", default="square"); ap.add_argument("--theme", default="dark")
    ap.add_argument("--png"); ap.add_argument("--anim")
    ap.add_argument("--transparent", action="store_true",
                    help="transparent background (PNG alpha; animation: .mov/.webm/folder)")
    ap.add_argument("--frames", type=int, default=150); ap.add_argument("--fps", type=int, default=30)
    argv = sys.argv[1:]   # accept "--range -2,2,-2,2" (value starts with '-')
    for i in range(len(argv) - 1):
        if argv[i] in ("--range", "--t-range", "--th-range") and argv[i + 1].startswith("-"):
            argv[i] = argv[i] + "=" + argv[i + 1]; argv[i + 1] = None
    a = ap.parse_args([v for v in argv if v is not None])
    a.t_range = [float(v) for v in a.t_range.split(",")]
    a.th_range = [float(v) for v in a.th_range.split(",")]
    size, th = parse_size(a.size), theme(a.theme)
    if a.transparent:
        th = transparent_theme(th)

    if a.range:
        xmin, xmax, ymin, ymax = [float(v) for v in a.range.split(",")]
    else:
        xmin, xmax, ymin, ymax = auto_view(a)

    def figure(av):
        fig, ax = make_figure(size, th)
        fit_view(ax, [xmin, xmax], [ymin, ymax], size, margin=0.08 if not a.range else 0)
        view = (*ax.get_xlim(), *ax.get_ylim())
        if a.axes:
            import matplotlib.ticker as mt
            ax.set_axis_on()
            for s in ax.spines.values(): s.set_visible(False)
            ax.xaxis.set_major_locator(mt.MaxNLocator(10)); ax.yaxis.set_major_locator(mt.MaxNLocator(10))
            ax.grid(True, color=th["muted"], lw=0.6, alpha=0.6)
            ax.axhline(0, color=th["fg"], lw=1, alpha=0.6); ax.axvline(0, color=th["fg"], lw=1, alpha=0.6)
            ax.tick_params(colors=th["fg"], labelsize=max(size) / 110, direction="in", pad=-max(size) / 40)
        draw(ax, av, a, th, size, view)
        if a.caption:
            fig.text(0.5, 0.06, a.caption, ha="center", va="center", color=th["fg"],
                     fontsize=max(size) / 45)
        return fig

    if not a.png and not a.anim:
        a.png = "curve.png"
    if a.png:
        figure(0.0).savefig(a.png, facecolor=th["bg"]); print("PNG:", a.png)
    if a.anim:
        save_animation(lambda i: figure(i / a.frames), a.frames, a.anim, fps=a.fps,
                       transparent=a.transparent)
        print("Animation:", a.anim)


if __name__ == "__main__":
    main()
