import json, sys, collections, numpy as np
r = json.load(open(sys.argv[1]))
by = collections.defaultdict(list)
for x in r: by[(x["kind"], x["method"])].append(x)
print(f"{'kind':14s}{'meth':7s}{'IoU':>6s}{'cham':>6s}{'h95':>6s}{'eul':>5s}{'seg':>6s}{'s':>5s}")
for (k, m), xs in sorted(by.items()):
    f = lambda key: np.mean([x[key] for x in xs])
    print(f"{k:14s}{m:7s}{f('iou'):6.3f}{f('chamfer'):6.2f}{f('h95'):6.2f}{f('euler'):5.1f}{f('nseg'):6.0f}{f('sec'):5.1f}")
for m in ("fill", "center"):
    xs = [x for x in r if x["method"] == m]
    if xs: print(m, "ALL  IoU %.3f  chamfer %.2f  h95 %.2f  euler %.1f" % tuple(np.mean([x[k] for x in xs]) for k in ("iou", "chamfer", "h95", "euler")))
