"""E1-T0-3 — grid-geometry analysis of the 8/9 onset-coincidence tally.

Referee M3: on a 2.5x-spaced epoch grid, both the decay onset and the
memorization onset are quantized to grid rungs, and the excess-loss cliff
spans roughly one grid interval — so ANY monotone quantity that crosses its
threshold during the cliff would be recorded as "coinciding". How likely is
the 8/9 tally under such a geometry null?

Two bracketing nulls, both computed from the actual per-cell curves
(pooled medians, coarse grid n in {1,2,4,10,20,40}):

  (a) uniform-rung null: the second (memorization) crossing lands uniformly
      at random on the rungs where a monotone crossing could be recorded
      (rungs n>1 up to the last measured rung, i.e. {2,4,10,20,40} -> p=1/5;
      we also report the tighter {10,20,40} variant, p=1/3, since the canary
      gap is still at baseline through n=4 in every cell).
  (b) cliff-concentrated null: the crossing is placed log-uniformly within
      the cell's transition window W = [last n with excess < eps/5,
      first n with excess > 5*eps]; the coincidence probability is the
      log-width of the decay-onset interval divided by the log-width of W
      (capped at 1). This is the referee's geometry argument made exact.

P(>= 8 of 9 coincide) is computed for each null (Poisson-binomial for (b)).

Output: onset_geometry.json (+ printed summary).
"""
from __future__ import annotations

import itertools
import json
import math
import os

EPS = 0.05
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
GRID = [1, 2, 4, 10, 20, 40]


def p_at_least(k, ps):
    """Poisson-binomial P(X >= k)."""
    n = len(ps)
    # dp over counts
    dp = [1.0] + [0.0] * n
    for p in ps:
        for c in range(n, 0, -1):
            dp[c] = dp[c] * (1 - p) + dp[c - 1] * p
        dp[0] *= (1 - p)
    return sum(dp[k:])


def binom_tail(k, n, p):
    return sum(math.comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1))


def main():
    tc = json.load(open(os.path.join(OUT_DIR, "rfree_two_convention.json")))
    cells = tc["cells"]

    per_cell = {}
    ps_cliff = []
    for name, c in cells.items():
        ex = {int(n): v for n, v in c["excess"].items() if int(n) in GRID}
        ns = sorted(ex)
        onset = next((n for n in ns if n > 1 and ex[n] >= EPS), None)
        # decay-onset interval (prev rung, onset]
        i = ns.index(onset)
        lo_int, hi_int = ns[i - 1], onset
        w_int = math.log(hi_int / lo_int)
        # transition window: last rung with excess < eps/5 .. first with > 5eps
        lo_w = max([n for n in ns if ex[n] < EPS / 5], default=ns[0])
        hi_w = min([n for n in ns if ex[n] > 5 * EPS], default=ns[-1])
        w_cliff = math.log(hi_w / lo_w) if hi_w > lo_w else w_int
        p = min(1.0, w_int / w_cliff)
        ps_cliff.append(p)
        per_cell[name] = {
            "decay_onset": onset,
            "onset_interval": [lo_int, hi_int],
            "cliff_window": [lo_w, hi_w],
            "cliff_grid_intervals": ns.index(hi_w) - ns.index(lo_w),
            "p_coincide_cliff_null": round(p, 3),
        }

    res = {
        "observed": "8/9",
        "uniform_rung_null": {
            "p_per_cell_5rungs": 0.2,
            "P_ge_8of9": binom_tail(8, 9, 0.2),
            "p_per_cell_3rungs": 1 / 3,
            "P_ge_8of9_3rungs": binom_tail(8, 9, 1 / 3),
        },
        "cliff_null": {
            "p_per_cell": {k: v["p_coincide_cliff_null"]
                           for k, v in per_cell.items()},
            "P_ge_8of9": p_at_least(8, ps_cliff),
        },
        "per_cell": per_cell,
    }
    with open(os.path.join(OUT_DIR, "onset_geometry.json"), "w") as f:
        json.dump(res, f, indent=1)

    print(f"uniform-rung null (5 rungs, p=0.2):  P(>=8/9) = "
          f"{res['uniform_rung_null']['P_ge_8of9']:.2e}")
    print(f"uniform-rung null (3 rungs, p=1/3):  P(>=8/9) = "
          f"{res['uniform_rung_null']['P_ge_8of9_3rungs']:.2e}")
    print(f"cliff-concentrated null:             P(>=8/9) = "
          f"{res['cliff_null']['P_ge_8of9']:.3f}")
    for k, v in per_cell.items():
        print(f"  {k:12s} onset={v['decay_onset']:>2} interval={v['onset_interval']}"
              f" cliff={v['cliff_window']} spans {v['cliff_grid_intervals']}"
              f" intervals  p_cliff={v['p_coincide_cliff_null']}")


if __name__ == "__main__":
    main()
