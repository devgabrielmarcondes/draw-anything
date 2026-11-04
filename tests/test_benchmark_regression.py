"""Benchmark regression gate on a small subset (fill mode). Run with: pytest -m slow"""
import sys

import numpy as np
import pytest

from conftest import ROOT

sys.path.insert(0, str(ROOT / "benchmark"))
KINDS = ("lineart", "shapes", "noisy")


@pytest.mark.slow
def test_fill_mode_quality(tmp_path):
    pytest.importorskip("cairosvg")
    import bench
    import gen
    res = []
    for m in gen.generate(tmp_path, names=KINDS):
        svg, *_ = bench.vectorize(tmp_path / f"{m['id']}.png", "fill", {})
        r = bench.metrics(svg, bench.gt_mask(tmp_path / f"{m['id']}_gt.png"))
        res.append(r)
        assert r["iou"] >= 0.90, (m["id"], r)
        assert r["chamfer"] <= 0.30, (m["id"], r)
    # Per case, "shapes" has Euler errors of 2-4 (small slivers). Check the mean of the subset.
    assert np.mean([r["euler"] for r in res]) <= 2, res
