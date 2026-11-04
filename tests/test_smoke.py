"""One fast test for each script. Small inputs and few frames: the full run takes less than ~60 s."""
import pytest
from PIL import Image, ImageDraw


def nonempty(path):
    assert path.exists() and path.stat().st_size > 0, path
    return path


@pytest.fixture
def lineart(tmp_path):
    im = Image.new("RGB", (160, 160), "white"); d = ImageDraw.Draw(im)
    d.line([(20, 140), (80, 20), (140, 140), (20, 60), (140, 60), (20, 140)], fill="black", width=4)
    im.save(tmp_path / "lineart.png")
    return tmp_path / "lineart.png"


@pytest.fixture
def colorimg(tmp_path):
    im = Image.new("RGB", (160, 160), (240, 230, 200)); d = ImageDraw.Draw(im)
    d.rectangle((15, 15, 90, 90), fill=(220, 60, 50))
    d.ellipse((60, 55, 145, 140), fill=(40, 90, 160), outline=(20, 20, 20), width=3)
    im.save(tmp_path / "color.png")
    return tmp_path / "color.png"


@pytest.mark.parametrize("script", ["fourier_draw.py", "trace_image.py", "centerline.py",
                                    "curves.py", "tupper.py", "sdf.py"])
def test_help(run, script):
    assert run(script, "--help").strip()


def test_fourier_text(run, tmp_path):
    run("fourier_draw.py", "--text", "Ab", "--terms", "60", "--png", "a.png", "--svg", "a.svg",
        "--desmos", "a.txt", "--anim", "a.gif", "--size", "128x128", "--frames", "4")
    for f in ("a.png", "a.svg", "a.txt", "a.gif"):
        nonempty(tmp_path / f)


def test_sdf_library(tmp_path):
    from sdf import grid, ellipse, triangle, mirror_x, smooth_union, circle, translate, render
    P = grid(128, 128, scale=1.2)
    cat = smooth_union(ellipse(P, 0.6, 0.45), triangle(mirror_x(P), (0.15, 0.25), (0.5, 0.15), (0.45, 0.72)), 0.06)
    eyes = circle(translate(mirror_x(P), 0.22, 0.05), 0.07)
    render([(cat, "#2b2d42", {"shadow": (0.02, -0.03, 0.05)}), (eyes, "#ffd23f")], str(tmp_path / "cat.png"), theme="paper")
    assert Image.open(tmp_path / "cat.png").size == (128, 128)


def test_curves_implicit_heart(run, tmp_path):
    run("curves.py", "--region", "(x**2+y**2-1)**3 - x**2*y**3::#e63946", "--range", "-1.6,1.6,-1.3,1.5",
        "--png", "heart.png", "--size", "128x128")
    nonempty(tmp_path / "heart.png")


def test_tupper_encode_decode(run, tmp_path):
    run("tupper.py", "encode", "--text", "HI", "--out", "k.txt", "--png", "e.png", "--size", "256x128")
    run("tupper.py", "decode", "--k-file", "k.txt", "--png", "d.png", "--size", "256x128")
    assert Image.open(nonempty(tmp_path / "e.png")).tobytes() == Image.open(nonempty(tmp_path / "d.png")).tobytes()


def test_trace_ink(run, lineart, tmp_path):
    out = run("trace_image.py", lineart, "--svg", "ink.svg", "--png", "ink.png", "--desmos", "ink.txt")
    assert "IoU" in out
    for f in ("ink.svg", "ink.png", "ink.txt"):
        nonempty(tmp_path / f)


def test_trace_color_lines(run, colorimg, tmp_path):
    run("trace_image.py", colorimg, "--mode", "color", "--colors", "4", "--lines", "--svg", "c.svg")
    assert nonempty(tmp_path / "c.svg").read_text(encoding="utf-8").count("<path") >= 3


def test_trace_edges(run, colorimg, tmp_path):
    run("trace_image.py", colorimg, "--mode", "edges", "--svg", "e.svg")
    nonempty(tmp_path / "e.svg")


def test_trace_centerline(run, lineart, tmp_path):
    run("trace_image.py", lineart, "--centerline", "--svg", "cl.svg")
    svg = nonempty(tmp_path / "cl.svg").read_text(encoding="utf-8")
    assert "stroke-width" in svg


def test_trace_transparent_mov(run, lineart, tmp_path):
    import subprocess
    import imageio_ffmpeg
    run("trace_image.py", lineart, "--transparent", "--anim", "t.mov", "--size", "128x128", "--frames", "4")
    p = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(nonempty(tmp_path / "t.mov"))],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert "prores" in p.stderr and "yuva444" in p.stderr
