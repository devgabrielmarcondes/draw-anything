"""Print a table by case kind. Usage: python report.py results.json [other.json ...]"""
import collections, json, sys
import numpy as np

KEYS = ("de", "de95", "ssim", "edge", "regions", "colors", "kb", "sec")


def summary(r):
    return {k: float(np.nanmean([x[k] for x in r])) for k in KEYS}


if __name__ == "__main__":
    for f in sys.argv[1:]:
        r = json.load(open(f)); by = collections.defaultdict(list)
        for x in r: by[x["kind"]].append(x)
        print(f"== {f}")
        print(f"{'kind':14s}" + "".join(f"{k:>9s}" for k in KEYS))
        for k, xs in sorted(by.items(), key=lambda kv: -summary(kv[1])["de"]):
            s = summary(xs); print(f"{k:14s}" + "".join(f"{s[q]:9.2f}" for q in KEYS))
        s = summary(r); print(f"{'ALL':14s}" + "".join(f"{s[q]:9.2f}" for q in KEYS))
