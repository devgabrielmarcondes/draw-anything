import numpy as np
import pytest
from tupper import bitmap_to_k, k_to_bitmap


@pytest.mark.parametrize("seed", range(20))
def test_encode_decode_are_exact_inverses(seed):
    rng = np.random.default_rng(seed)
    H, W = int(rng.integers(1, 30)), int(rng.integers(1, 120))
    bmp = rng.integers(0, 2, (H, W))
    k, h, w = bitmap_to_k(bmp)
    assert (h, w) == (H, W) and k % H == 0
    assert np.array_equal(k_to_bitmap(k, H, W), bmp)


def test_classic_size_all_ones_and_zeros():
    for bmp in (np.ones((17, 106), int), np.zeros((17, 106), int)):
        k, _, _ = bitmap_to_k(bmp)
        assert np.array_equal(k_to_bitmap(k), bmp)
