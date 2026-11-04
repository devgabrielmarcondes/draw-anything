"""
Shared tools: output sizes, color themes and animation output.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Common sizes for content creators (width x height in px)
FORMATS = {
    "reels": (1080, 1920),     # Reels / TikTok / Shorts (9:16)
    "story": (1080, 1920),
    "post": (1080, 1350),      # Instagram feed (4:5)
    "square": (1080, 1080),    # 1:1
    "youtube": (1920, 1080),   # 16:9
    "thumb": (1280, 720),
    "4k": (3840, 2160),
}

THEMES = {
    "dark":   {"bg": "#0b0d12", "fg": "#f5f5f0", "accent": "#ffcc4d", "muted": "#3a4150", "fill": "#ffcc4d"},
    "light":  {"bg": "#fbfaf6", "fg": "#15171c", "accent": "#e4572e", "muted": "#c9c6bd", "fill": "#e4572e"},
    "neon":   {"bg": "#05010f", "fg": "#e9e4ff", "accent": "#00f0ff", "muted": "#3b1f66", "fill": "#ff2bd6"},
    "blueprint": {"bg": "#0f3d6e", "fg": "#e8f1fb", "accent": "#ffffff", "muted": "#3f6d99", "fill": "#9cc7f0"},
    "paper":  {"bg": "#f3ead8", "fg": "#2b2118", "accent": "#a23b2a", "muted": "#cdbf9f", "fill": "#2b2118"},
}


def parse_size(size):
    """Accepts 'reels', 'square', '1080x1920' etc. Returns (w, h)."""
    if size is None:
        return FORMATS["square"]
    if size in FORMATS:
        return FORMATS[size]
    w, h = size.lower().split("x")
    return int(w), int(h)


def theme(name):
    return THEMES.get(name, THEMES["dark"])


def make_figure(size, th, dpi=100):
    """Figure with no margins, no axes and the theme background.
    th["bg"] == "none" gives a transparent background."""
    w, h = size
    fig = plt.figure(figsize=(w / dpi, h / dpi), dpi=dpi)
    fig.patch.set_facecolor(th["bg"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(th["bg"])
    ax.set_axis_off()
    ax.set_aspect("equal")
    return fig, ax


def transparent_theme(th):
    return {**th, "bg": "none"}


def fit_view(ax, xs, ys, size, margin=0.12):
    """Fits the data in the view. Keeps the aspect ratio of the output size."""
    w, h = size
    xmin, xmax = float(np.min(xs)), float(np.max(xs))
    ymin, ymax = float(np.min(ys)), float(np.max(ys))
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    dx = max(xmax - xmin, 1e-9) * (1 + 2 * margin)
    dy = max(ymax - ymin, 1e-9) * (1 + 2 * margin)
    aspect = w / h
    if dx / dy > aspect:
        dy = dx / aspect
    else:
        dx = dy * aspect
    ax.set_xlim(cx - dx / 2, cx + dx / 2)
    ax.set_ylim(cy - dy / 2, cy + dy / 2)


def save_animation(frames_fn, n_frames, out, fps=30, size=(1080, 1080), dpi=100,
                   transparent=False):
    """frames_fn(i) -> matplotlib figure or RGB(A) array. Output by extension:
    .mp4 (H.264), .gif, and with transparent=True: .mov (ProRes 4444 + alpha),
    .webm (VP9 + alpha) or a folder name (PNG sequence with alpha)."""
    import imageio.v2 as imageio
    ext = os.path.splitext(out)[1].lower()
    seq = transparent and ext in ("", ".png")
    if transparent and ext in (".mp4", ".gif"):
        print("note: .mp4/.gif have no alpha; use .mov, .webm or a folder")
        transparent = False
    if seq:
        folder = out[:-4] if ext == ".png" else out
        os.makedirs(folder, exist_ok=True)
        writer = None
    elif ext == ".mov":
        writer = imageio.get_writer(out, fps=fps, codec="prores_ks", macro_block_size=1,
                                    pixelformat="yuva444p10le" if transparent else "yuv422p10le",
                                    ffmpeg_params=["-profile:v", "4444" if transparent else "3"])
    elif ext == ".webm":
        writer = imageio.get_writer(out, fps=fps, codec="libvpx-vp9", macro_block_size=1,
                                    pixelformat="yuva420p" if transparent else "yuv420p",
                                    ffmpeg_params=["-b:v", "0", "-crf", "30", "-auto-alt-ref", "0"])
    elif ext == ".mp4":
        writer = imageio.get_writer(out, fps=fps, codec="libx264", quality=8,
                                    macro_block_size=8, pixelformat="yuv420p")
    else:
        writer = imageio.get_writer(out, mode="I", duration=1000 / fps, loop=0)
    for i in range(n_frames):
        res = frames_fn(i)
        if isinstance(res, np.ndarray):
            img = res
        else:
            res.canvas.draw()
            img = np.asarray(res.canvas.buffer_rgba()).copy()
            plt.close(res)
        if img.dtype != np.uint8:
            img = (np.clip(img, 0, 1) * 255).astype(np.uint8)
        if not transparent:
            img = img[..., :3]
        if seq:
            imageio.imwrite(os.path.join(folder, f"frame_{i:05d}.png"), img)
        else:
            writer.append_data(img)
    if writer:
        writer.close()
    return out
