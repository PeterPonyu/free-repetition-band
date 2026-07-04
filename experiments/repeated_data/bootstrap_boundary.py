"""Bootstrap audit for the two boundary cells of the free-repetition band (E1).

The small/low and small/med cells sit at excess 0.0498 nats vs the 0.05-nat
threshold at n=10. This script computes, from the existing run logs (main
results dir + the seed-audit extension, seeds s0-s4 at n=10, s0-s2 at n=1):

  1. Per-seed excess values at n=10 for both boundary cells.
  2. A seed-level nonparametric bootstrap (10k resamples) 95% CI on the
     median-excess statistic used by the paper (median val@n=10 - median val@n=1),
     and the bootstrap probability that excess >= 0.05 nats.
  3. A bootstrap CI on the 8/9 decay-onset == memorization-onset coincidence rate.

Pure CPU; reads jsonl logs only.
"""
import json
import random
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve()
RES = HERE.parents[1] / "results"
MAIN = RES / "repeated_data"
AUDIT = RES / "repeated_data_ultragoal_seed_audit"

FREE_EPS = 0.05
B = 10_000
random.seed(20260701)

CELLS = {
    "small/low": ("small_low_U2M_E10", "small_low_U20M_E1"),
    "small/med": ("small_med_U2M_E10", "small_med_U20M_E1"),
}


def final_val(stem_prefix):
    vals = []
    for d in (MAIN, AUDIT):
        for f in sorted(d.glob(f"{stem_prefix}_s*.jsonl")):
            rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
            fin = [r.get("final_val_loss")
                   or r.get("_summary", {}).get("final_val_loss")
                   or r.get("_meta", {}).get("final_val_loss")
                   for r in rows]
            fin = [v for v in fin if v is not None]
            if fin:
                vals.append((f.name, float(fin[-1])))
    return vals


def boot_ci(rep_vals, fresh_vals):
    stats = []
    for _ in range(B):
        r = [random.choice(rep_vals) for _ in rep_vals]
        f = [random.choice(fresh_vals) for _ in fresh_vals]
        stats.append(median(r) - median(f))
    stats.sort()
    lo, hi = stats[int(0.025 * B)], stats[int(0.975 * B) - 1]
    p_ge = sum(s >= FREE_EPS for s in stats) / B
    return lo, hi, p_ge


for label, (rep_stem, fresh_stem) in CELLS.items():
    rep = final_val(rep_stem)
    fresh = final_val(fresh_stem)
    rep_v = [v for _, v in rep]
    fresh_v = [v for _, v in fresh]
    point = median(rep_v) - median(fresh_v)
    lo, hi, p_ge = boot_ci(rep_v, fresh_v)
    print(f"{label}: n=10 seeds={len(rep_v)} {[round(v,4) for v in rep_v]}")
    print(f"          n=1 seeds={len(fresh_v)} {[round(v,4) for v in fresh_v]}")
    print(f"  per-seed excess (vs median fresh): "
          f"{[round(v - median(fresh_v), 4) for v in rep_v]}")
    print(f"  median excess = {point:.4f}; bootstrap 95% CI [{lo:.4f}, {hi:.4f}]; "
          f"P(excess >= 0.05) = {p_ge:.3f}")

# onset-coincidence bootstrap: 8 hits of 9 cells
hits = [1] * 8 + [0]
props = []
for _ in range(B):
    props.append(sum(random.choice(hits) for _ in hits) / 9)
props.sort()
print(f"\nonset coincidence 8/9: bootstrap 95% CI "
      f"[{props[int(0.025*B)]:.3f}, {props[int(0.975*B)-1]:.3f}]")
